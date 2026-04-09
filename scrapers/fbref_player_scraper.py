import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import gc

def parse_player_row(row, team_name_fallback):
    """Boc tach chi tiet tung cau thu"""
    try:
        if row.get('class') and 'thead' in row.get('class'):
            return None
        
        player_cell = row.find('td', {'data-stat': 'player'})
        if not player_cell:
            return None

        # Trich xuat du lieu
        data = {
            "PlayerName": player_cell.text.strip(),
            "Nation": row.find('td', {'data-stat': 'nationality'}).text.strip().split(' ')[-1] if row.find('td', {'data-stat': 'nationality'}) else "",
            "Pos": row.find('td', {'data-stat': 'position'}).text.strip() if row.find('td', {'data-stat': 'position'}) else "",
            "Team": row.find('td', {'data-stat': 'team'}).text.strip() if row.find('td', {'data-stat': 'team'}) else team_name_fallback,
            "Age": row.find('td', {'data-stat': 'age'}).text.strip()[:2] if row.find('td', {'data-stat': 'age'}) else "",
            "MatchesPlayed": row.find('td', {'data-stat': 'games'}).text.strip() if row.find('td', {'data-stat': 'games'}) else "0",
            "Starts": row.find('td', {'data-stat': 'games_starts'}).text.strip() if row.find('td', {'data-stat': 'games_starts'}) else "0",
            "Minutes": row.find('td', {'data-stat': 'minutes'}).text.strip().replace(',', '') if row.find('td', {'data-stat': 'minutes'}) else "0",
            "Goals": row.find('td', {'data-stat': 'goals'}).text.strip() if row.find('td', {'data-stat': 'goals'}) else "0",
            "Assists": row.find('td', {'data-stat': 'assists'}).text.strip() if row.find('td', {'data-stat': 'assists'}) else "0",
            "xG": row.find('td', {'data-stat': 'xg'}).text.strip() if row.find('td', {'data-stat': 'xg'}) else "0.0",
            "xAG": row.find('td', {'data-stat': 'xg_assist'}).text.strip() if row.find('td', {'data-stat': 'xg_assist'}) else "0.0",
            "YellowCards": row.find('td', {'data-stat': 'cards_yellow'}).text.strip() if row.find('td', {'data-stat': 'cards_yellow'}) else "0",
            "RedCards": row.find('td', {'data-stat': 'cards_red'}).text.strip() if row.find('td', {'data-stat': 'cards_red'}) else "0",
            "PlayerURL": "https://fbref.com" + player_cell.find('a')['href'] if player_cell.find('a') else ""
        }
        return data
    except Exception:
        return None

def main():
    # 1. Doc danh sach tat ca cac giai dau da cao truoc do
    leagues_file = "data/raw/fbref_all_leagues.csv"
    if not os.path.exists(leagues_file):
        print(f"Loi: Khong tim thay file {leagues_file}. Hay cao danh sach giai truoc.")
        return

    df_leagues = pd.read_csv(leagues_file)
    
    # 2. Ket noi vao Chrome Debug
    options = uc.ChromeOptions()
    options.add_argument('--remote-debugging-port=9222')
    try:
        driver = uc.Chrome(options=options, version_main=146)
    except Exception as e:
        print(f"Loi ket noi Chrome Debug: {e}")
        return

    output_dir = "data/raw/players/"
    os.makedirs(output_dir, exist_ok=True)

    # 3. Duyet qua tung giai dau de cao cau thu
    for index, row in df_leagues.iterrows():
        league_id = row['source_id']
        league_name = row['name'].replace(' ', '-')
        season = "2024-2025" # Ban co the thay doi mua giai tai day
        
        output_file = f"{output_dir}players_{league_name}_{season}.csv"
        
        # Neu da cao giai nay roi thi bo qua de tiet kiem thoi gian
        if os.path.exists(output_file):
            print(f"Bo qua {league_name} vi da co file.")
            continue

        url = f"https://fbref.com/en/comps/{league_id}/{season}/stats/{season}-{league_name}-Stats"
        print(f"--- Dang cao: {league_name} (ID: {league_id}) ---")
        
        driver.get(url)
        time.sleep(random.uniform(7, 10)) # Doi load trang va ne bot detection

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', id=lambda x: x and x.startswith('stats_standard'))

        if not table:
            print(f"Khong tim thay bang cho {league_name}. Co the mua giai nay chua co stats.")
            continue

        players_list = []
        rows = table.find('tbody').find_all('tr')
        for r in rows:
            p_data = parse_player_row(r, team_name_fallback="")
            if p_data:
                p_data["League"] = row['name'] # Gan ten giai vao du lieu cau thu
                players_list.append(p_data)

        if players_list:
            pd.DataFrame(players_list).to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"Xong! Luu {len(players_list)} cau thu.")
        
        # Nghi dai mot chut giua cac giai dau lon de tranh bi khoa IP
        time.sleep(random.uniform(5, 8))

    print("--- HOAN THANH CAO TAT CA CAU THU CUA CAC GIAI DAU ---")
    gc.collect()

if __name__ == "__main__":
    import random
    main()