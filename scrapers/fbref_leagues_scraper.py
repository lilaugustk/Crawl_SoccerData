import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment
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
        self.driver = None

    def start_driver(self):
        print("Dang khoi tao trinh duyet (Safe Mode)...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        # Them cac flag on dinh cho Windows
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception as e:
            print(f"Loi khoi tao driver: {e}")
            sys.exit(1)

    def safe_quit(self):
        """Khac phuc triet de loi WinError 6 khi dong trinh duyet"""
        if self.driver:
            print("\nDang dong trinh duyet an toan...")
            try:
                # Dong cua so hien tai
                self.driver.close()
                time.sleep(1)
                # Thoat tien trinh
                self.driver.quit()
            except Exception:
                # Neu handle da bi Windows thu hoi truoc do, bo qua de ne loi WinError 6
                pass
            finally:
                self.driver = None
                gc.collect()

    def parse_table(self, table_soup, category_name):
        leagues = []
        tbody = table_soup.find('tbody')
        rows = tbody.find_all('tr') if tbody else []
        
        for row in rows:
            if 'thead' in row.get('class', []): continue
            
            name_cell = row.find('th', {'data-stat': 'league_name'}) or row.find('td', {'data-stat': 'league_name'})
            if not name_cell or not name_cell.find('a'): continue

            name = name_cell.text.strip()
            link = name_cell.find('a')['href']
            source_id = link.split('/')[3]

            country_cell = row.find('td', {'data-stat': 'country'})
            country_name = country_cell.text.strip() if country_cell else "International"
            
            # Lay ma quoc gia tu class icon
            country_code = "INTL"
            if country_cell and country_cell.find('span'):
                classes = country_cell.find('span').get('class', [])
                for cls in classes:
                    if cls.startswith('f-') and cls != 'f-i':
                        country_code = cls.replace('f-', '').replace('gb-', '').upper()

            leagues.append({
                'source_id': source_id,
                'name': name,
                'category': category_name,
                'country': country_name,
                'country_code': country_code,
                'gender': row.find('td', {'data-stat': 'gender'}).text.strip() if row.find('td', {'data-stat': 'gender'}) else "M",
                'level': row.find('td', {'data-stat': 'tier'}).text.strip() if row.find('td', {'data-stat': 'tier'}) else "",
                'first_season': row.find('td', {'data-stat': 'minseason'}).text.strip() if row.find('td', {'data-stat': 'minseason'}) else "",
                'last_season': row.find('td', {'data-stat': 'maxseason'}).text.strip() if row.find('td', {'data-stat': 'maxseason'}) else "",
                'logo_url': f"https://cdn.ssref.net/req/202603251/tlogo/fb/{source_id}.png"
            })
        return leagues

    def run(self):
        try:
            self.start_driver()
            url = f"{self.base_url}/en/comps/"
            self.driver.get(url)
            print("Cho trang tai va quet cac bang an...")
            time.sleep(15) 

            # Cuon trang de kich hoat tat ca phan tu
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            all_data = []

            # 1. Quet bang hien (Visible)
            for table in soup.find_all('table', class_='stats_table'):
                all_data.extend(self.parse_table(table, table.get('id', 'Standard')))

            # 2. Quet bang an trong Comment (Hidden) - RAT QUAN TRONG
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                if '<table' in comment and 'stats_table' in comment:
                    comment_soup = BeautifulSoup(comment, 'html.parser')
                    table = comment_soup.find('table')
                    if table:
                        all_data.extend(self.parse_table(table, table.get('id', 'Hidden')))

            if all_data:
                df = pd.DataFrame(all_data).drop_duplicates(subset=['source_id'])
                df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
                print(f"\nDa cao thanh cong {len(df)} giai dau.")
            else:
                print("\nKhong tim thay du lieu.")

        except Exception as e:
            print(f"\nLoi trong qua trinh chay: {e}")
        finally:
            self.safe_quit()

if __name__ == "__main__":
    # Tat thong bao loi rac tu chrome
    sys.stderr = open(os.devnull, 'w')
    scraper = FBrefLeagueLiveScraper()
    scraper.run()