import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import gc

def fetch_logos():
    input_file = "data/raw/fbref_all_clubs_1.csv"
    output_file = "data/raw/fbref_clubs_with_logos_final.csv"
    
    if not os.path.exists(input_file):
        print("Loi: Khong tim thay file dau vao fbref_all_clubs_1.csv")
        return

    # Doc du lieu va kiem tra cac doi da cao roi de chay tiep suc
    df_all = pd.read_csv(input_file)
    crawled_ids = set()
    if os.path.exists(output_file):
        try:
            df_existing = pd.read_csv(output_file)
            crawled_ids = set(df_existing['ClubID'].unique())
        except:
            pass

    df_to_crawl = df_all[~df_all['ClubID'].isin(crawled_ids)]
    print(f"Can cao logo cho: {len(df_to_crawl)} doi.")

    if df_to_crawl.empty:
        print("Tat ca da hoan thanh.")
        return

    # Cau hinh Chrome an toan
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    print("Dang mo trinh duyet...")
    driver = uc.Chrome(options=options, version_main=146)

    try:
        for index, row in df_to_crawl.iterrows():
            club_id = row['ClubID']
            club_url = row['URL']
            
            print(f"Dang lay logo: {row['ClubName']}...", end=" ", flush=True)
            
            driver.get(club_url)
            
            # --- CO CHE CHO DU LIEU THUC TE ---
            logo_url = ""
            for attempt in range(10): # Cho toi đa 30-40 giay
                time.sleep(4) 
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Tim the div chua logo va the img teamlogo nhu anh image_63f1a7.jpg
                logo_div = soup.find('div', class_='media-item logo')
                if logo_div:
                    img_tag = logo_div.find('img', class_='teamlogo')
                    if img_tag and img_tag.get('src'):
                        src = img_tag.get('src')
                        if 'transparent' not in src: # Bo qua anh trong suot
                            logo_url = src
                            break
                
                print(".", end="", flush=True)
            
            if logo_url:
                # Chuan hoa link CDN
                if logo_url.startswith('/'):
                    logo_url = "https://cdn.ssref.net" + logo_url
                
                # Luu ngay lap tuc
                res = {"ClubID": club_id, "ClubName": row['ClubName'], "LogoURL": logo_url, "Country": row['Country']}
                pd.DataFrame([res]).to_csv(output_file, mode='a', index=False, 
                                          header=not os.path.exists(output_file), encoding='utf-8-sig')
                print(" Xong.")
            else:
                print(" Khong tim thay.")

            # Nghi ngan giua cac doi
            time.sleep(random.uniform(2, 4))
            
            if index % 20 == 0:
                gc.collect()

    except Exception as e:
        print(f"\nLoi trong qua trinh cào: {e}")
    finally:
        print("\nDang dong trinh duyet an toan...")
        try:
            driver.close()
            time.sleep(2)
            driver.quit()
        except OSError:
            # Khac phuc WinError 6: Neu handle da bi thu hoi thi bo qua
            pass
        print("Hoan thanh.")

if __name__ == "__main__":
    fetch_logos()