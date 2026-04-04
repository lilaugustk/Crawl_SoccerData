import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os

def fake_del(self): pass
uc.Chrome.__del__ = fake_del

class FlashscoreScraper:
    def __init__(self):
        self.driver = None

    def start_browser(self):
        print("🚀 Khởi động trình duyệt...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        self.driver = uc.Chrome(version_main=146, options=options)

    def scrape_results(self, url):
        if not self.driver: self.start_browser()
        try:
            print(f"🔗 Truy cập: {url}")
            self.driver.get(url)
            time.sleep(4)

            # 1. DỌN DẸP CHƯỚNG NGẠI VẬT
            try:
                cookie_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                cookie_btn.click()
                print("🍪 Đã đóng bảng thông báo Cookie.")
                time.sleep(1)
            except:
                pass

            # 2. CLICK SHOW MORE CHO ĐẾN KHI HẾT
            print("⏳ Đang tải toàn bộ lịch sử trận đấu...")
            while True:
                try:
                    wait = WebDriverWait(self.driver, 4)
                    btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".event__more.event__more--static")))
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    btn.click()
                    time.sleep(2)
                except:
                    print("✅ Đã mở rộng toàn bộ danh sách!")
                    break

            # 3. BÓC TÁCH DỮ LIỆU (Có thêm Round và Date)
            print("🔍 Đang phân tích văn bản...")
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')
            
            results_list = []
            trash_words = ["MATCHES", "FINISHED", "LIVE", "SCHEDULE", "SHOW", "MORE", "BEYOND", "ADVERTISEMENT"]
            
            # Biến lưu trữ trạng thái vòng đấu
            current_round = "Unknown"

            for i in range(len(lines)):
                line = lines[i].strip()
                
                # NẾU DÒNG HIỆN TẠI LÀ VÒNG ĐẤU -> Lưu lại để dùng cho các trận bên dưới
                if line.upper().startswith("ROUND"):
                    current_round = line
                
                # Bắt đầu quét các trận đấu (điều kiện i >= 3 để tránh lỗi i-3)
                if i >= 3 and i < len(lines) - 1:
                    # TÌM ĐIỂM SỐ
                    if lines[i].isdigit() and lines[i+1].isdigit():
                        
                        h_score = lines[i].strip()
                        a_score = lines[i+1].strip()
                        
                        # TÌM TÊN ĐỘI
                        h_team = lines[i-2].strip()
                        a_team = lines[i-1].strip()
                        
                        # TÌM THỜI GIAN
                        match_date = lines[i-3].strip()
                        if "." not in match_date and ":" not in match_date:
                            match_date = "Unknown"
                        
                        # BỘ LỌC BẢO VỆ
                        # Chặn nếu "ROUND" vô tình lọt vào tên đội
                        h_is_trash = any(t in h_team.upper() for t in trash_words) or "ROUND" in h_team.upper()
                        a_is_trash = any(t in a_team.upper() for t in trash_words) or "ROUND" in a_team.upper()
                        
                        if not h_is_trash and not a_is_trash and len(h_team) > 2 and len(a_team) > 2:
                            results_list.append({
                                "Round": current_round,   # Cột vòng đấu
                                "Date": match_date,       # Cột ngày giờ
                                "Home": h_team,
                                "Away": a_team,
                                "HomeScore": int(h_score),
                                "AwayScore": int(a_score)
                            })

            # 4. LƯU DỮ LIỆU
            df = pd.DataFrame(results_list)
            df = df.drop_duplicates()

            if not df.empty:
                os.makedirs("data/raw", exist_ok=True)
                df.to_csv("data/raw/match_results.csv", index=False, encoding="utf-8-sig")
                print(f"\n🎉 THÀNH CÔNG RỰC RỠ! Đã thu thập được {len(df)} trận đấu.")
                print("--- BẢN XEM TRƯỚC ---")
                print(df.head(10))
            else:
                print("\n❌ CẢNH BÁO: Không tìm thấy dữ liệu.")

        except Exception as e:
            print(f"💥 Lỗi phát sinh: {e}")
        finally:
            self.quit()

    def quit(self):
        if self.driver:
            self.driver.quit()
            os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
            print("🧹 Trình duyệt đã được dọn dẹp.")

if __name__ == "__main__":
    scraper = FlashscoreScraper()
    url = "https://www.flashscore.com/football/england/premier-league/results/"
    scraper.scrape_results(url)