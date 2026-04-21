import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta, datetime
import time
import os
import sys  
import gc
import re
import atexit

# CHẶN LỖI WINDOWS NGAY TỪ ĐẦU
sys.stderr = open(os.devnull, 'w')

class FBrefMatchScraper:
    def __init__(self, start_date_str="2026-01-01", output_file="data/raw/fbref_all_matches/fbref_all_matches_2026.csv"):
        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        self.end_date = date.today()
        self.output_file = output_file
        
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("--- KHOI TAO TRINH DUYET (MATCH MODE) ---")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument("--incognito")
        
        try:
            self.driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
        except Exception:
            self.driver = uc.Chrome(options=options, use_subprocess=True)
        
        atexit.register(self.safe_quit)

    def safe_quit(self):
        try:
            if hasattr(self, 'driver'): self.driver.quit()
        except: pass

    def get_already_crawled_dates(self):
        if os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            try:
                df = pd.read_csv(self.output_file)
                date_col = 'date' if 'date' in df.columns else 'MatchDate'
                if not df.empty and date_col in df.columns:
                    return set(df[date_col].astype(str).unique())
            except Exception:
                return set()
        return set()

    def parse_match_row(self, row, league_name, league_id, match_date):
        """Bổ sung thêm league_id, home_id, away_id"""
        try:
            if 'spacer' in row.get('class', []): return None

            score_td = row.find('td', {'data-stat': 'score'})
            home_td = row.find('td', {'data-stat': 'home_team'})
            away_td = row.find('td', {'data-stat': 'away_team'})
            
            if not score_td or not home_td or not away_td:
                return None

            # BÓC TÁCH ID ĐỘI BÓNG TỪ LINK
            home_link = home_td.find('a')
            away_link = away_td.find('a')
            
            home_id = home_link['href'].split('/')[3] if home_link else ""
            away_id = away_link['href'].split('/')[3] if away_link else ""

            cells = {
                "date": match_date,
                "league_id": league_id,
                "league": league_name,
                "wk": row.find('td', {'data-stat': 'gameweek'}).text.strip() if row.find('td', {'data-stat': 'gameweek'}) else "",
                "time": row.find('td', {'data-stat': 'start_time'}).text.strip() if row.find('td', {'data-stat': 'start_time'}) else "",
                "home_id": home_id, # Cột mới
                "home_team": home_td.text.strip(),
                "home_score": score_td.text.strip().split('–')[0] if '–' in score_td.text else "",
                "away_score": score_td.text.strip().split('–')[1] if '–' in score_td.text else "",
                "away_team": away_td.text.strip(),
                "away_id": away_id, # Cột mới
                "attendance": row.find('td', {'data-stat': 'attendance'}).text.strip() if row.find('td', {'data-stat': 'attendance'}) else "",
                "venue": row.find('td', {'data-stat': 'venue'}).text.strip() if row.find('td', {'data-stat': 'venue'}) else "",
                "referee": row.find('td', {'data-stat': 'referee'}).text.strip() if row.find('td', {'data-stat': 'referee'}) else "",
            }

            report_td = row.find('td', {'data-stat': 'match_report'})
            if report_td and report_td.find('a'):
                cells["MatchReportURL"] = "https://fbref.com" + report_td.find('a')['href']
            else:
                cells["MatchReportURL"] = ""
            
            return cells
        except Exception:
            return None

    def run(self):
        current_date = self.start_date
        crawled_dates = self.get_already_crawled_dates()
        
        print(f"Bắt đầu quét từ {self.start_date} đến {self.end_date}")

        while current_date <= self.end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in crawled_dates:
                current_date += timedelta(days=1)
                continue

            url = f"https://fbref.com/en/matches/{date_str}"
            print(f"[*] Ngày: {date_str}...", end=" ", flush=True)

            try:
                self.driver.get(url)
                time.sleep(7) 

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                if "429 Too Many Requests" in soup.text:
                    print("Bị chặn (429)! Dừng script.")
                    break
                    
                tables = soup.find_all('table', class_='stats_table')
                day_matches = []
                for table in tables:
                    caption = table.find('caption')
                    league_name = caption.text.replace('Table', '').strip() if caption else "Unknown League"
                    
                    # Lấy League ID từ ID bảng (sched_YYYY-YYYY_ID_1)
                    league_id = ""
                    table_id_attr = table.get('id', '')
                    id_match = re.search(r'_(\d+)_1$', table_id_attr)
                    if id_match:
                        league_id = id_match.group(1)
                    else:
                        link_tag = table.find('a', href=re.compile(r'/en/comps/\d+/'))
                        if link_tag:
                            league_id = link_tag['href'].split('/')[3]

                    tbody = table.find('tbody')
                    if not tbody: continue
                        
                    rows = tbody.find_all('tr')
                    for row in rows:
                        match_data = self.parse_match_row(row, league_name, league_id, date_str)
                        if match_data:
                            day_matches.append(match_data)

                if day_matches:
                    df_day = pd.DataFrame(day_matches)
                    header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0
                    df_day.to_csv(self.output_file, mode='a', index=False, header=header, encoding='utf-8-sig')
                    print(f"OK ({len(day_matches)} trận)")
                else:
                    # Ghi log ngày không có trận để không quét lại
                    if not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0:
                        pd.DataFrame(columns=["date"]).to_csv(self.output_file, index=False)
                    with open(self.output_file, 'a', encoding='utf-8-sig') as f:
                        f.write(f"{date_str},,,,,,,,,,,,,\n")
                    print("Không có trận.")

            except Exception as e:
                print(f"Lỗi: {e}")
                time.sleep(10)

            current_date += timedelta(days=1)

        print(f"Hoàn thành! File: {self.output_file}")
        self.safe_quit()

if __name__ == "__main__":
    scraper = FBrefMatchScraper(start_date_str="2026-01-01")
    scraper.run()
    gc.collect()