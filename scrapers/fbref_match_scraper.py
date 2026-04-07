import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
from datetime import date, timedelta, datetime
import time
import os
import sys  
import gc

class FBrefMatchScraper:
    def __init__(self, start_date_str="1888-01-01", output_file="data/raw/fbref_all_matches/fbref_all_matches_2026.csv"):
        self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        self.end_date = date.today()
        self.output_file = output_file
        
        # Tạo thư mục nếu chưa có
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        # Khởi tạo vũ khí qua mặt Cloudflare
        print("Dang khoi tao trinh duyet chong tàng hình...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        self.driver = uc.Chrome(options=options, version_main=146)

    def get_already_crawled_dates(self):
        """Kiểm tra file cũ để biết đã cào đến ngày nào, chống lỗi file rỗng"""
        if os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            try:
                df = pd.read_csv(self.output_file)
                if not df.empty and 'MatchDate' in df.columns:
                    return set(df['MatchDate'].unique())
            except pd.errors.EmptyDataError:
                return set()
        return set()

    def parse_match_row(self, row, league_name, match_date):
        """Bóc tách dữ liệu từ một hàng <tr>"""
        try:
            # Chỉ lấy các hàng có dữ liệu thực sự
            if 'spacer' in row.get('class', []): return None

            cells = {
                "MatchDate": match_date,
                "League": league_name,
                "Wk": row.find('td', {'data-stat': 'gameweek'}).text.strip(),
                "Time": row.find('td', {'data-stat': 'start_time'}).text.strip(),
                "Home": row.find('td', {'data-stat': 'home_team'}).text.strip(),
                "Score": row.find('td', {'data-stat': 'score'}).text.strip(),
                "Away": row.find('td', {'data-stat': 'away_team'}).text.strip(),
                "Attendance": row.find('td', {'data-stat': 'attendance'}).text.strip(),
                "Venue": row.find('td', {'data-stat': 'venue'}).text.strip(),
                "Referee": row.find('td', {'data-stat': 'referee'}).text.strip(),
            }

            # Lấy Link Match Report
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
        
        print(f"\nBat dau cao tu {self.start_date} den {self.end_date}")
        print(f"Do tre an toan: 5 giay/request (Trinh duyet se tu dong chay)")

        while current_date <= self.end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in crawled_dates:
                current_date += timedelta(days=1)
                continue

            url = f"https://fbref.com/en/matches/{date_str}"
            print(f"Dang quet ngay: {date_str}...", end=" ", flush=True)

            try:
                # Dùng Chrome thật để truy cập (Vượt Cloudflare 403)
                self.driver.get(url)
                
                # Ngủ 5 giây để FBref load xong và không khoá IP
                time.sleep(5) 

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Kiểm tra xem có bị quá tải 429 không
                if "429 Too Many Requests" in soup.text or "Rate Limited" in soup.text:
                    print("\nBi chan (429)! FBref yeu cau nghi ngoi. Dung script.")
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
                    # Sửa lỗi mất Header nếu file có sẵn nhưng trống rỗng (0 bytes)
                    header = not os.path.exists(self.output_file) or os.path.getsize(self.output_file) == 0
                    df_day.to_csv(self.output_file, mode='a', index=False, header=header)
                    print(f"Lay duoc {len(day_matches)} tran.")
                else:
                    print("Khong co tran nao.")

            except Exception as e:
                print(f"Loi: {e}")

            current_date += timedelta(days=1)

        print(f"\nHOAN THANH! Du lieu nam tai: {self.output_file}")
        self.driver.quit()

if __name__ == "__main__":
    # KHỞI TẠO TỪ NĂM 1888
    # ĐÃ CÀO ĐƯỢC TỪ 01/01/1888 - 30/06/1909
    scraper = FBrefMatchScraper(start_date_str="2026-01-01") #(YYYY-MM-DD)
    scraper.run()
    
    # --- TUYỆT CHIÊU CUỐI: Ép dọn rác ngay lập tức trong im lặng ---
    sys.stderr = open(os.devnull, 'w')
    del scraper 
    gc.collect()