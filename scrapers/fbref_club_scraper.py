import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import sys
import gc

class FBrefDeepClubScraper:
    def __init__(self, output_file="data/raw/fbref_all_clubs_deep_v2.csv"):
        self.output_file = output_file
        self.base_url = "https://fbref.com"
        
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("Khoi tao trinh duyet chong tang hinh...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        self.driver = uc.Chrome(options=options, version_main=146)

    def get_already_crawled_countries(self):
        if os.path.exists(self.output_file):
            try:
                df = pd.read_csv(self.output_file)
                if not df.empty and 'Country' in df.columns:
                    return set(df['Country'].unique())
            except pd.errors.EmptyDataError:
                # Nếu file tồn tại nhưng trống rỗng, coi như chưa cào gì
                return set()
        return set()

    def get_country_links(self):
        url = f"{self.base_url}/en/squads/"
        print("LOP 1: Dang lay danh sach URL Quoc gia...")
        self.driver.get(url)
        time.sleep(10) 
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        country_links = []
        
        table = soup.find('table', id='countries')
        if not table:
            print("Khong tim thay bang Quoc gia. Co the bi block.")
            return []
            
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            if 'spacer' in row.get('class', []): continue
            
            country_th = row.find('th', {'data-stat': 'country'})
            if country_th and country_th.find('a'):
                a_tag = country_th.find('a')
                country_name = a_tag.text.replace('Football Clubs', '').strip()
                country_url = self.base_url + a_tag['href']
                gov_body = row.find('td', {'data-stat': 'governing_body'}).text.strip()
                
                country_links.append({
                    "name": country_name,
                    "url": country_url,
                    "gov": gov_body
                })
                
        print(f"Da tim thay {len(country_links)} Quoc gia. Bat dau vao LOP 2...")
        return country_links

    def run(self):
        try:
            countries = self.get_country_links()
            if not countries: return
            
            crawled_countries = self.get_already_crawled_countries()
            
            for country in countries:
                if country['name'] in crawled_countries:
                    continue
                    
                print(f"Dang quet {country['name']}...", end=" ", flush=True)
                self.driver.get(country['url'])
                time.sleep(6) 
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # --- THAY ĐỔI QUAN TRỌNG: NHẮM THẲNG VÀO BẢNG ID="CLUBS" ---
                club_table = soup.find('table', id='clubs')
                if not club_table:
                    print("Khong tim thay bang CLB (co the chua duoc ho tro hoac bi an).")
                    continue
                
                club_list = []
                tbody = club_table.find('tbody')
                rows = tbody.find_all('tr') if tbody else []

                for row in rows:
                    if 'spacer' in row.get('class', []): continue
                    
                    team_th = row.find('th', {'data-stat': 'team'})
                    if not team_th or not team_th.find('a'): continue
                    
                    a_tag = team_th.find('a')
                    href = a_tag.get('href', '')
                    club_name = a_tag.text.strip()
                    
                    parts = href.split('/')
                    if len(parts) > 3:
                        club_id = parts[3]
                        
                        # Bóc tách các cột dữ liệu theo đúng cấu trúc FBref
                        gender = row.find('td', {'data-stat': 'gender'}).text.strip() if row.find('td', {'data-stat': 'gender'}) else ""
                        comp = row.find('td', {'data-stat': 'comp'}).text.strip() if row.find('td', {'data-stat': 'comp'}) else ""
                        min_season = row.find('td', {'data-stat': 'min_season'}).text.strip() if row.find('td', {'data-stat': 'min_season'}) else ""
                        max_season = row.find('td', {'data-stat': 'max_season'}).text.strip() if row.find('td', {'data-stat': 'max_season'}) else ""
                        num_comps = row.find('td', {'data-stat': 'num_comps'}).text.strip() if row.find('td', {'data-stat': 'num_comps'}) else ""
                        champs = row.find('td', {'data-stat': 'first_place_finishes'}).text.strip() if row.find('td', {'data-stat': 'first_place_finishes'}) else ""
                        other_names = row.find('td', {'data-stat': 'other_names'}).text.strip() if row.find('td', {'data-stat': 'other_names'}) else ""

                        club_list.append({
                            "ClubID": club_id,
                            "ClubName": club_name,
                            "Country": country['name'],
                            "GoverningBody": country['gov'],
                            "Gender": gender,
                            "Comp": comp,
                            "From": min_season,
                            "To": max_season,
                            "NumComps": num_comps,
                            "Champs": champs,
                            "OtherNames": other_names,
                            "URL": self.base_url + href
                        })
                
                if club_list:
                    df = pd.DataFrame(club_list)
                    header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0
                    df.to_csv(self.output_file, mode='a', index=False, header=header)
                    print(f"Lay duoc {len(club_list)} CLB.")
                else:
                    print("Khong co CLB nao hoac bi chan.")
                    
        except Exception as e:
            print(f"\nLoi he thong: {e}")
        finally:
            self.driver.quit()
            print(f"\nHOAN THANH DEEP SCRAPE! Du lieu tai: {self.output_file}")

if __name__ == "__main__":
    scraper = FBrefDeepClubScraper(output_file="data/raw/fbref_all_clubs.csv")
    scraper.run()
    
    sys.stderr = open(os.devnull, 'w')
    del scraper
    gc.collect()