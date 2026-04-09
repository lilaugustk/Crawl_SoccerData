import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import gc
import sys

class FBrefScraperV17:
    def __init__(self, output_dir="data/raw/players/leagues_combined/"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.base_url = "https://fbref.com"

    def start_driver(self):
        options = uc.ChromeOptions()
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--log-level=3')
        return uc.Chrome(options=options, version_main=146, use_subprocess=True)

    def ensure_page_loaded(self, driver, label):
        """Chốt chặn Cloudflare: Đứng đợi cho đến khi thấy nội dung thật"""
        print(f"\n--- Dang truy cap: {label} ---")
        while True:
            src = driver.page_source
            if "nav" in src or "info" in src or "footer" in src:
                print(f"   -> Xac nhan: Da vao trang thanh cong.")
                time.sleep(2)
                break
            print(f"   [Xac minh] Vui long vuot qua Cloudflare/Captcha tren trinh duyet...")
            time.sleep(7)

    def get_uncommented_soup(self, driver):
        """Gỡ comment để làm lộ diện bảng ẩn"""
        return BeautifulSoup(driver.page_source.replace("", ""), 'html.parser')

    def parse_player_rows(self, soup, table_id):
        """Lấy dữ liệu cầu thủ (loại bỏ hàng Header và bảng Squad)"""
        table = soup.find('table', id=lambda x: x and table_id in x and 'squad' not in x)
        if not table: return []
        
        data = []
        tbody = table.find('tbody')
        if not tbody: return []

        for r in tbody.find_all('tr'):
            if 'thead' in r.get('class', []): continue
            p_cell = r.find(['td', 'th'], {'data-stat': 'player'})
            if not p_cell or not p_cell.find('a'): continue
            
            pid = p_cell.find('a')['href'].split('/')[3]
            stats = {"PlayerID": pid, "Name": p_cell.text.strip()}
            for td in r.find_all('td'):
                stat_name = td.get('data-stat')
                if stat_name: stats[stat_name] = td.text.strip()
            data.append(stats)
        return data

    def build_url(self, base_url, stat_type="stats"):
        """Chèn stats/ shooting/ keepers/ vào URL"""
        parts = base_url.split('/')
        if len(parts) > 2:
            parts.insert(-1, stat_type)
            return "/".join(parts)
        return base_url

    def scrape(self):
        seasons_file = "data/raw/fbref_all_seasons.csv"
        df_seasons = pd.read_csv(seasons_file)
        target_years = ["2024-2025", "2025", "2026"]
        df_targets = df_seasons[df_seasons['season'].isin(target_years)]

        driver = self.start_driver()

        try:
            for _, row in df_targets.iterrows():
                l_raw_name, s_name = str(row['league_name']), str(row['season'])
                l_safe_name = l_raw_name.replace(' ', '_').replace('/', '-')
                out_path = os.path.join(self.output_dir, f"{l_safe_name}.csv")

                # Kiểm tra Resume
                if os.path.exists(out_path):
                    df_ex = pd.read_csv(out_path)
                    if s_name in df_ex['Season'].astype(str).values:
                        print(f"--- Bo qua: {l_raw_name} ({s_name}) ---")
                        continue

                # 1. Truy cập trang Stats chính (Dùng Cách 1: Chèn /stats/)
                stats_url = self.build_url(row['season_url'], "stats")
                driver.get(stats_url)
                self.ensure_page_loaded(driver, f"{l_raw_name} Tổng hợp")
                
                soup = self.get_uncommented_soup(driver)
                player_data = self.parse_player_rows(soup, 'stats_standard')

                if player_data:
                    # TRƯỜNG HỢP A: Có bảng tổng hợp
                    print(f"   -> Thay bang Player ({len(player_data)} cau thu). Dang lay tiep tab...")
                    df_final = pd.DataFrame(player_data)
                    
                    for t_type in ["shooting", "keepers"]:
                        driver.get(self.build_url(row['season_url'], t_type))
                        time.sleep(3)
                        t_soup = self.get_uncommented_soup(driver)
                        t_data = self.parse_player_rows(t_soup, f'stats_{t_type[:-1]}')
                        if t_data:
                            df_t = pd.DataFrame(t_data)
                            cols = df_t.columns.difference(df_final.columns).tolist() + ['PlayerID']
                            df_final = pd.merge(df_final, df_t[cols], on='PlayerID', how='left')

                    df_final['League'], df_final['Season'] = l_raw_name, s_name
                    header = not os.path.exists(out_path)
                    df_final.to_csv(out_path, mode='a', index=False, header=header, encoding='utf-8-sig')
                    print(f"   => Luu xong file league.")

                else:
                    # TRƯỜNG HỢP B: Chỉ có bảng Squad (như Conference League bạn vừa gửi)
                    print("   -> Trang khong co Player Stats. Dang truy cap tung doi...")
                    # Tìm link các đội từ bảng Squad Stats
                    squad_table = soup.find('table', id=lambda x: x and 'stats_squads_standard' in x)
                    if squad_table:
                        s_links = list(set([a['href'] for a in squad_table.find_all('a', href=True) if '/squads/' in a['href']]))
                        print(f"   -> Tim thay {len(s_links)} doi bóng.")
                        
                        for s_link in s_links:
                            t_url = self.base_url + s_link
                            driver.get(t_url)
                            self.ensure_page_loaded(driver, f"Doi: {s_link.split('/')[-2]}")
                            
                            # Ở trang đội bóng, player stats thường hiện sẵn
                            t_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            t_data = self.parse_player_rows(t_soup, 'stats_standard')
                            if t_data:
                                df_t = pd.DataFrame(t_data)
                                df_t['League'], df_t['Season'] = l_raw_name, s_name
                                header = not os.path.exists(out_path)
                                df_t.to_csv(out_path, mode='a', index=False, header=header, encoding='utf-8-sig')
                                print(f"      + OK: {s_link.split('/')[-2]}")
                            gc.collect()
                            time.sleep(random.uniform(2, 4))
                    else:
                        print("   -> Khong tim thay bat ky du lieu nao.")

                time.sleep(random.uniform(5, 10))

        finally:
            driver.quit()

if __name__ == "__main__":
    sys.stderr = open(os.devnull, 'w')
    scraper = FBrefScraperV17()
    scraper.scrape()