import os
import sys
import time
import json
import re
import atexit

# 1. KHẮC PHỤC LỖI WINDOWS (Xử lý WinError 6 dứt điểm)
sys.stderr = open(os.devnull, 'w')

try:
    import undetected_chromedriver as uc
    from bs4 import BeautifulSoup
except ImportError:
    print("Vui lòng cài đặt thư viện trước: pip install undetected-chromedriver beautifulsoup4")
    sys.exit()

class FBrefNationUnifiedScraper:
    def __init__(self):
        self.base_url = "https://fbref.com"
        self.root_data_path = "data/raw/players/nations"
        
        print("--- ĐANG KHỞI TẠO TRÌNH DUYỆT (CHROME 146) ---")
        options = uc.ChromeOptions()
        options.add_argument("--incognito")
        options.add_argument('--log-level=3')
        options.add_argument('--disable-gpu')
        
        try:
            # use_subprocess=True giúp tránh lỗi WinError trên Windows hiệu quả nhất
            self.driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
            atexit.register(self.safe_quit)
        except Exception:
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            atexit.register(self.safe_quit)

    def safe_quit(self):
        """Đóng trình duyệt sạch sẽ khi dừng chương trình"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass

    def get_scraped_ids_in_file(self, file_path):
        """Kiểm tra danh sách ID cầu thủ đã có trong file của quốc gia đó"""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {p['player_id'] for p in data}
            except:
                return set()
        return set()

    def get_nations(self):
        """Lấy danh sách tất cả các quốc gia từ trang chủ cầu thủ"""
        url = f"{self.base_url}/en/players/country/"
        print(f"[*] Đang tải danh sách quốc gia...")
        self.driver.get(url)
        time.sleep(7)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        nations = []
        links = soup.select('ul.page_index li div a')
        for a in links:
            href = a.get('href')
            name = a.text.strip()
            if href and "/country/players/" in href:
                nations.append({
                    "name": name,
                    "url": self.base_url + href,
                    "letter": name[0].upper() if name else "#"
                })
        return nations

    def scrape_player_profile(self, player_url, player_id):
        """Truy cập vào URL cầu thủ để lấy thông tin cá nhân cơ bản"""
        try:
            self.driver.get(player_url)
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            info = soup.find('div', id='info')
            if not info: return None

            data = {
                "player_id": player_id,
                "name": info.find('h1').text.strip() if info.find('h1') else "N/A",
                "url": player_url,
                "position": "",
                "footed": "",
                "height": "",
                "weight": "",
                "born": "",
                "current_club": "",
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            for p in info.find_all('p'):
                line = p.get_text().replace('\n', ' ').strip()
                
                if "Position:" in line:
                    data["position"] = line.split("Position:")[1].split("▪")[0].strip()
                    if "Footed:" in line:
                        data["footed"] = line.split("Footed:")[1].strip()
                
                hw = re.search(r'(\d+cm).*?(\d+kg)', line)
                if hw:
                    data["height"] = hw.group(1)
                    data["weight"] = hw.group(2)

                if "Born:" in line:
                    born_match = re.search(r'Born:\s+([A-Za-z]+ \d+, \d{4})', line)
                    data["born"] = born_match.group(1) if born_match else ""

                if "Club:" in line:
                    data["current_club"] = p.find('a').text.strip() if p.find('a') else ""
            
            return data
        except:
            return None

    def start(self):
        try:
            nations = self.get_nations()
            if not nations:
                print("--- KHÔNG TÌM THẤY QUỐC GIA NÀO ---")
                return

            print(f"--- BẮT ĐẦU CÀO {len(nations)} QUỐC GIA ---")

            for nation in nations:
                nation_dir = os.path.join(self.root_data_path, nation['letter'], nation['name'])
                os.makedirs(nation_dir, exist_ok=True)
                json_file = os.path.join(nation_dir, "players.json")

                print(f"\n[*] Quốc gia: {nation['name']}")
                
                # Load dữ liệu cũ nếu có
                scraped_ids = self.get_scraped_ids_in_file(json_file)
                nation_players_list = []
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        nation_players_list = json.load(f)

                self.driver.get(nation['url'])
                time.sleep(5)
                
                # Phá comment trang danh sách quốc gia để tìm cầu thủ in đậm
                content = self.driver.page_source.replace("", "")
                soup = BeautifulSoup(content, 'html.parser')
                
                active_links = soup.select('div.section_content p a:has(strong)')
                if not active_links:
                    active_links = soup.select('div.section_content p strong a')

                print(f"  -> Cầu thủ Active: {len(active_links)}")

                for p_link in active_links:
                    p_href = p_link.get('href')
                    p_id = p_href.split('/')[-2]

                    if p_id in scraped_ids:
                        continue

                    p_name = p_link.text.strip()
                    print(f"     + Đang lấy Profile: {p_name}...", end=" ", flush=True)
                    
                    p_data = self.scrape_player_profile(self.base_url + p_href, p_id)
                    
                    if p_data:
                        nation_players_list.append(p_data)
                        # Lưu đè lại file players.json sau mỗi lần cào thành công 1 người
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(nation_players_list, f, ensure_ascii=False, indent=4)
                        scraped_ids.add(p_id)
                        print("OK")
                    else:
                        print("THẤT BẠI")
                    
                    time.sleep(2.5) # Nghỉ để an toàn

        except Exception as main_e:
            print(f"\n[!] Dừng chương trình: {main_e}")
        finally:
            print("\n--- PHIÊN LÀM VIỆC KẾT THÚC ---")
            self.safe_quit()

if __name__ == "__main__":
    scraper = FBrefNationUnifiedScraper()
    scraper.start()