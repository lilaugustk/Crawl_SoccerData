import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import gc

def scrape_all_seasons():
    # 1. Doc file giai dau dau vao
    leagues_file = "data/raw/fbref_all_leagues.csv"
    if not os.path.exists(leagues_file):
        print(f"Loi: Khong tim thay file {leagues_file}")
        return

    df_leagues = pd.read_csv(leagues_file)
    output_file = "data/raw/fbref_all_seasons.csv"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    if os.path.exists(output_file):
        os.remove(output_file)

    # 2. Ket noi Chrome Debug
    options = uc.ChromeOptions()
    options.add_argument('--remote-debugging-port=9222')
    try:
        driver = uc.Chrome(options=options, version_main=146)
    except Exception as e:
        print(f"Loi ket noi: {e}. Hay dam bao Chrome Debug da mo!")
        return

    for index, row in df_leagues.iterrows():
        league_id = row['source_id']
        league_name = row['name']
        
        url = f"https://fbref.com/en/comps/{league_id}/history/{league_name.replace(' ', '-')}-Seasons"
        print(f"\n--- Dang cao giai: {league_name} (ID: {league_id}) ---")
        driver.get(url)

        rows_found = []
        for attempt in range(12): 
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', id=lambda x: x and ('seasons' in x or 'history' in x))
            
            if table and table.find('tbody'):
                rows_found = table.find('tbody').find_all('tr')
                if rows_found:
                    print(f"Da thay {len(rows_found)} dong du lieu.")
                    break
            
            print(f"[{attempt+1}] Cho bang du lieu tai...")
            time.sleep(5)

        if not rows_found:
            continue

        current_league_data = []
        for r in rows_found:
            # --- LOGIC LOC DONG LA (TIÊU ĐỀ LẶP LẠI) ---
            # Neu dong co class 'thead', do la dong tieu de lap lai, ta bo qua
            if r.get('class') and 'thead' in r.get('class'):
                continue

            season_cell = r.find('th', {'data-stat': ['year_id', 'season']})
            if not season_cell:
                season_cell = r.find('td', {'data-stat': ['year_id', 'season']})
            
            if season_cell:
                season_text = season_cell.get_text(strip=True)
                
                # Kiem tra them mot lan nua noi dung chu
                if season_text == "Season" or season_text == "":
                    continue

                season_link_tag = season_cell.find('a')
                season_url = "https://fbref.com" + season_link_tag['href'] if season_link_tag else ""
                
                champ_cell = r.find('td', {'data-stat': 'champ'})
                champion = champ_cell.get_text(strip=True) if champ_cell else ""

                current_league_data.append({
                    "league_id": league_id,
                    "league_name": league_name,
                    "season": season_text,
                    "champion": champion,
                    "season_url": season_url
                })

        if current_league_data:
            df_temp = pd.DataFrame(current_league_data)
            file_is_empty = not os.path.exists(output_file) or os.stat(output_file).st_size == 0
            df_temp.to_csv(output_file, mode='a', index=False, header=file_is_empty, encoding='utf-8-sig')
            print(f"Da ghi thanh cong mua giai cua {league_name}.")

        time.sleep(random.uniform(3, 5))

    print("\n--- HOAN THANH TAT CA ---")
    gc.collect()

if __name__ == "__main__":
    scrape_all_seasons()