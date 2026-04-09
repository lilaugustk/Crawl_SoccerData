import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import gc
import sys

class FBrefLeagueLiveScraper:
    def __init__(self, output_file="data/raw/fbref_all_leagues.csv"):
        self.output_file = output_file
        self.base_url = "https://fbref.com"
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("Đang khởi tạo trình duyệt (Chế độ chống tàng hình v146)...")
        options = uc.ChromeOptions()
        
        # Các tham số giúp 'giả dạng' người dùng thật
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        try:
            # Ép version 146 theo máy của bạn để tránh lỗi SessionNotCreated
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception:
            print("Đang thử khởi tạo với chế độ dự phòng...")
            self.driver = uc.Chrome(options=options, use_subprocess=True)

    def run(self):
        try:
            url = f"{self.base_url}/en/comps/"
            print(f"Đang truy cập trực tiếp: {url}")
            self.driver.get(url)

            # --- BƯỚC QUAN TRỌNG: ĐỢI VÀ GIẢ LẬP NGƯỜI DÙNG ---
            print("Đang đợi 15 giây để trang tải và vượt qua Cloudflare...")
            # Trong lúc này, nếu thấy Captcha, bạn hãy tự tay Click vào nó nhé!
            time.sleep(15) 

            # Cuộn chuột xuống từ từ để FBref tưởng người thật đang đọc
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(500, 1000);")
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            target_tables = {
                'comps_club': 'Domestic',
                'comps_1_fa_club_league_senior': 'Domestic',
                'comps_intl_club_cup': 'International Cup',
                'comps_intl_fa_nonqualifier_senior': 'National Team'
            }

            all_leagues = []

            for table_id, category in target_tables.items():
                table = soup.find('table', id=table_id)
                if not table:
                    print(f"⚠️ Cảnh báo: Vẫn chưa tìm thấy bảng {table_id}. Có thể bị FBref chặn nội dung.")
                    continue
                
                print(f"✅ Đã tìm thấy bảng {table_id}. Đang lấy dữ liệu...")
                rows = table.find('tbody').find_all('tr')

                for row in rows:
                    if row.get('class') and 'thead' in row.get('class'): continue
                    
                    name_cell = row.find('th', {'data-stat': 'league_name'})
                    if not name_cell or not name_cell.find('a'): continue

                    name = name_cell.text.strip()
                    link = name_cell.find('a')['href']
                    source_id = link.split('/')[3]

                    # Tách mã quốc gia
                    country_cell = row.find('td', {'data-stat': 'country'})
                    country_name = country_cell.text.strip() if country_cell else "International"
                    country_code = "INTL"
                    if country_cell and country_cell.find('span'):
                        classes = country_cell.find('span').get('class', [])
                        for cls in classes:
                            if cls.startswith('f-') and cls != 'f-i':
                                country_code = cls.replace('f-', '').replace('gb-', '').upper()

                    # Mùa giải và cấp độ
                    gender = row.find('td', {'data-stat': 'gender'}).text.strip()
                    level = row.find('td', {'data-stat': 'tier'}).text.strip() if row.find('td', {'data-stat': 'tier'}) else "Cup"
                    first_season = row.find('td', {'data-stat': 'minseason'}).text.strip()
                    last_season = row.find('td', {'data-stat': 'maxseason'}).text.strip()

                    all_leagues.append({
                        'source_id': source_id,
                        'name': name,
                        'category': category,
                        'country': country_name,
                        'country_code': country_code,
                        'gender': gender,
                        'level': level,
                        'first_season': first_season,
                        'last_season': last_season,
                        'logo_url': f"https://cdn.ssref.net/req/202603251/tlogo/fb/{source_id}.png"
                    })

            if all_leagues:
                df = pd.DataFrame(all_leagues)
                df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
                print(f"\n🔥 THÀNH CÔNG RỰC RỠ! Đã cào được {len(all_leagues)} giải đấu.")
                print(f"Dữ liệu lưu tại: {self.output_file}")
            else:
                print("\n❌ Thất bại: Trang web trả về dữ liệu rỗng. Hãy thử lại sau vài phút.")

        except Exception as e:
            print(f"\n❌ Lỗi hệ thống: {e}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    scraper = FBrefLeagueLiveScraper()
    scraper.run()

    sys.stderr = open(os.devnull, 'w')
    del scraper
    gc.collect()