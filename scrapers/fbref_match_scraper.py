import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta, datetime
import time
import os
import sys  
import gc

class FBrefMatchScraper:
    def __init__(self, start_date_str="1912-06-12", output_file="data/raw/fbref_all_matches/fbref_all_matches_1888_1950.csv"):
        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        # self.end_date = date.today()
        self.end_date = date.today()
        self.output_file = output_file
        
        # Tao thu muc neu chua co
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("Dang khoi tao trinh duyet...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        
        # Khac phuc loi phien ban 146/147
        try:
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception as e:
            print(f"Loi phien ban 146, dang thu tu dong: {e}")
            self.driver = uc.Chrome(options=options)

    def get_already_crawled_dates(self):
        if os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            try:
                df = pd.read_csv(self.output_file)
                # Kiem tra ca ten cot kieu moi hoac cu neu ban co thay doi
                date_col = 'MatchDate' if 'MatchDate' in df.columns else 'date'
                if not df.empty and date_col in df.columns:
                    return set(df[date_col].astype(str).unique())
            except Exception:
                return set()
        return set()

    def parse_match_row(self, row, league_name, match_date):
        try:
            if 'spacer' in row.get('class', []): return None

            # Lay cac o du lieu chinh
            score_td = row.find('td', {'data-stat': 'score'})
            home_td = row.find('td', {'data-stat': 'home_team'})
            away_td = row.find('td', {'data-stat': 'away_team'})
            
            if not score_td or not home_td or not away_td:
                return None

            cells = {
                "date": match_date,
                "league": league_name,
                "wk": row.find('td', {'data-stat': 'gameweek'}).text.strip() if row.find('td', {'data-stat': 'gameweek'}) else "",
                "time": row.find('td', {'data-stat': 'start_time'}).text.strip() if row.find('td', {'data-stat': 'start_time'}) else "",
                "home_team": home_td.text.strip(),
                "home_score": score_td.text.strip().split('–')[0] if '–' in score_td.text else "",
                "away_score": score_td.text.strip().split('–')[1] if '–' in score_td.text else "",
                "away_team": away_td.text.strip(),
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
        
        print(f"Bat dau quet tu {self.start_date} den {self.end_date}")

        while current_date <= self.end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in crawled_dates:
                current_date += timedelta(days=1)
                continue

            url = f"https://fbref.com/en/matches/{date_str}"
            print(f"Dang quet ngay: {date_str}...", end=" ", flush=True)

            try:
                self.driver.get(url)
                time.sleep(7) 

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                if "429 Too Many Requests" in soup.text:
                    print("Bi chan (429)! Dung script.")
                    break
                    
                tables = soup.find_all('table', class_='stats_table')
                day_matches = []
                for table in tables:
                    caption = table.find('caption')
                    league = caption.text.replace('Table', '').strip() if caption else "Unknown League"
                    tbody = table.find('tbody')
                    if not tbody: continue
                        
                    rows = tbody.find_all('tr')
                    for row in rows:
                        match_data = self.parse_match_row(row, league, date_str)
                        if match_data:
                            day_matches.append(match_data)

                if day_matches:
                    df_day = pd.DataFrame(day_matches)
                    header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0
                    df_day.to_csv(self.output_file, mode='a', index=False, header=header, encoding='utf-8-sig')
                    print(f"Lay duoc {len(day_matches)} tran.")
                else:
                    # Ghi ngay vao log file rong de lan sau khong quet lai
                    pd.DataFrame([{"date": date_str}]).to_csv(self.output_file, mode='a', index=False, header=not os.path.exists(self.output_file))
                    print("Khong co tran nao.")

            except Exception as e:
                print(f"Loi: {e}")
                time.sleep(7)

            current_date += timedelta(days=1)

        print(f"Hoan thanh! File luu tai: {self.output_file}")
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    # Bat dau tu dau nam 2026
    scraper = FBrefMatchScraper(start_date_str="1912-06-12")
    # scraper = FBrefMatchScraper(start_date_str="2026-01-01")
    scraper.run()
    
    sys.stderr = open(os.devnull, 'w')
    del scraper 
    gc.collect()