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

    # 1. Doc toan bo danh sach doi can cao
    df_all = pd.read_csv(input_file)
    df_all.columns = df_all.columns.str.strip()
    
    # 2. KIEM TRA CAC DOI DA CAO (Resuming logic)
    crawled_ids = set()
    if os.path.exists(output_file):
        try:
            # Vi file cua ban hien tai KHONG CO TIEU DE (Header), chung ta phai doc kieu header=None
            df_existing = pd.read_csv(output_file, header=None)
            # Cot 0 trong file logo cua ban la ClubID
            crawled_ids = set(df_existing[0].astype(str).str.strip().unique())
            print(f"Tim thay {len(crawled_ids)} doi da duoc cao logo truoc do.")
        except Exception as e:
            print(f"Luu y: Khong the doc file da co ({e}), se cao moi.")

    # 3. Loc ra danh sach thuc su can cao tiep
    df_to_crawl = df_all[~df_all['ClubID'].astype(str).str.strip().isin(crawled_ids)]
    print(f"Con lai: {len(df_to_crawl)} doi can quet.")

    if df_to_crawl.empty:
        print("Tat ca cac doi trong danh sach deu da co logo!")
        return

    # 4. Cau hinh trinh duyet
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--remote-debugging-port=9222') # Dung port debug de on dinh

    print("Dang mo trinh duyet...")
    try:
        driver = uc.Chrome(options=options, version_main=146)
    except Exception as e:
        print(f"Loi trinh duyet: {e}")
        return

    try:
        for index, row in df_to_crawl.iterrows():
            club_id = str(row['ClubID']).strip()
            club_url = row['URL']
            
            print(f"Dang lay logo: {row['ClubName']} (ID: {club_id})...", end=" ", flush=True)
            
            driver.get(club_url)
            
            logo_url = ""
            # Vong lap cho tai logo (ne anh transparent)
            for attempt in range(2): 
                time.sleep(3) 
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                logo_div = soup.find('div', class_='media-item logo')
                if logo_div:
                    img_tag = logo_div.find('img', class_='teamlogo') or logo_div.find('img')
                    if img_tag and img_tag.get('src'):
                        src = img_tag.get('src')
                        if 'transparent' not in src:
                            logo_url = src
                            break
                print(".", end="", flush=True)
            
            if logo_url:
                if logo_url.startswith('/'):
                    logo_url = "https://cdn.ssref.net" + logo_url
                
                # Luu du lieu: ClubID, ClubName, LogoURL, Country
                res = [club_id, row['ClubName'], logo_url, row['Country']]
                
                # Ghi tiep vao file (Append mode), KHONG ghi tieu de de dong bo voi du lieu cu cua ban
                pd.DataFrame([res]).to_csv(output_file, mode='a', index=False, header=False, encoding='utf-8-sig')
                print(" OK.")
            else:
                print(" Khong tim thay.")

            # Delay ngan giua cac yeu cau
            time.sleep(random.uniform(2, 4))
            
            if index % 20 == 0:
                gc.collect()

    except Exception as e:
        print(f"\nLoi trong qua trinh: {e}")
    finally:
        print("\nDang dong trinh duyet an toan...")
        try:
            driver.close()
            time.sleep(1)
            driver.quit()
        except:
            pass
        print("Done.")

if __name__ == "__main__":
    fetch_logos()