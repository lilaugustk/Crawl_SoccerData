import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
import os
import sys
import json
import re
import atexit

# 1. KHẮC PHỤC LỖI WINDOWS (WinError 6)
sys.stderr = open(os.devnull, 'w')

class FBrefLeagueUnifiedScraper:
    def __init__(self):
        self.input_csv = "data/raw/fbref_all_seasons.csv"
        self.output_dir = "data/raw/squad_stats"
        os.makedirs(self.output_dir, exist_ok=True)
        
        print("--- KHOI TAO TRINH DUYET (LEAGUE UNIFIED MODE) ---")
        options = uc.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument('--log-level=3')
        
        try:
            self.driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
            atexit.register(self.safe_quit)
        except:
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            atexit.register(self.safe_quit)

    def safe_quit(self):
        try:
            if hasattr(self, 'driver'): self.driver.quit()
        except: pass

    def scrape_squad_stats(self, url, league_name, season):
        """Cào thông số đội bóng từ URL mùa giải"""
        print(f"      + Dang cao mua giai: {season}...", end=" ", flush=True)
        self.driver.get(url)
        time.sleep(6) 
        
        # Phá khóa Comment để lấy dữ liệu ẩn
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        full_html = str(soup)
        for comment in comments:
            full_html += "\n" + str(comment)
        
        processed_soup = BeautifulSoup(full_html, 'html.parser')
        
        season_data = {
            "season": season,
            "url": url,
            "stats": {}
        }

        # Các từ khóa ID bảng mục tiêu
        target_ids = {
            "overall": "overall",
            "standard": "standard",
            "keeper": "keeper",
            "shooting": "shooting",
            "playing_time": "playing_time",
            "miscellaneous": "misc"
        }

        for key, table_id in target_ids.items():
            # Tìm bảng dựa trên regex (phù hợp cho cả League và Cup)
            table = processed_soup.find('table', id=re.compile(f".*{table_id}.*"))
            
            if table:
                rows_list = []
                tbody = table.find('tbody')
                if tbody:
                    for row in tbody.find_all('tr', class_=lambda x: x != 'thead'):
                        squad_cell = row.find(['th', 'td'], {'data-stat': ['team', 'squad']})
                        if not squad_cell: continue
                        
                        squad_dict = {"squad": squad_cell.get_text().strip()}
                        a_link = squad_cell.find('a')
                        if a_link:
                            squad_dict["squad_id"] = a_link['href'].split('/')[-2]

                        for td in row.find_all('td'):
                            stat_name = td.get('data-stat')
                            if stat_name:
                                squad_dict[stat_name] = td.get_text().strip()
                        rows_list.append(squad_dict)
                
                if rows_list:
                    season_data["stats"][key] = rows_list
        
        return season_data

    def start(self):
        if not os.path.exists(self.input_csv):
            print(f"Khong tim thay file: {self.input_csv}")
            return

        df = pd.read_csv(self.input_csv)
        # Sắp xếp theo mùa giải để dữ liệu vào file có thứ tự
        df = df.sort_values(by=['league_name', 'season'], ascending=[True, False])

        # Nhóm theo tên giải đấu
        leagues = df.groupby('league_name')

        for name, group in leagues:
            safe_league_name = re.sub(r'[^\w\s-]', '', name).replace(' ', '_')
            file_path = os.path.join(self.output_dir, f"{safe_league_name}.json")
            
            print(f"\n[*] Dang xu ly giai: {name}")

            # Đọc dữ liệu cũ nếu file đã tồn tại
            existing_data = []
            scraped_seasons = set()
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        scraped_seasons = {s['season'] for s in existing_data}
                except: existing_data = []

            # Duyệt qua từng mùa của giải này
            for _, row in group.iterrows():
                season_val = str(row['season'])
                if season_val in scraped_seasons:
                    continue
                
                try:
                    data = self.scrape_squad_stats(row['season_url'], name, season_val)
                    if data["stats"]:
                        existing_data.append(data)
                        # Lưu lại sau mỗi mùa giải cào được
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(existing_data, f, ensure_ascii=False, indent=4)
                        print("OK")
                    else:
                        print("EMPTY (Bảng trống)")
                    
                    time.sleep(4)
                except Exception as e:
                    print(f"ERROR: {e}")

if __name__ == "__main__":
    scraper = FBrefLeagueUnifiedScraper()
    scraper.start()