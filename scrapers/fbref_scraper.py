import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import pandas as pd
import time
import os

# Vô hiệu hóa hàm hủy gây lỗi WinError 6
import selenium.webdriver.chrome.webdriver as webdriver
def fake_del(self): pass
uc.Chrome.__del__ = fake_del

class FbrefScraper:
    def __init__(self):
        self.driver = None

    def start_browser(self):
        print("🚀 Đang mở trình duyệt để bạn 'vượt rào' thủ công...")
        options = uc.ChromeOptions()
        # Không dùng headless để bạn có thể nhìn thấy và tương tác
        self.driver = uc.Chrome(version_main=146, options=options)

    def scrape_league_stats(self):
        url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        
        if not self.driver:
            self.start_browser()

        try:
            self.driver.get(url)
            
            print("\n⚠️  QUAN TRỌNG:")
            print("1. Nếu thấy vòng xoáy Cloudflare, hãy chờ nó tự chạy.")
            print("2. Nếu nó yêu cầu tích vào ô 'I am human', hãy dùng chuột tích vào đó.")
            print("3. KHI NÀO BẠN THẤY BẢNG KẾT QUẢ HIỆN RA, hãy quay lại đây nhấn Enter.")
            
            input("Nhấn Enter tại đây sau khi trang web đã load xong bảng kết quả: ")

            # Lấy toàn bộ HTML
            html_content = self.driver.page_source
            
            # MẸO QUAN TRỌNG: Loại bỏ các thẻ ghi chú # Vì Fbref thường giấu bảng xG trong đó để chống bot
            html_content = html_content.replace("", "")
            
            input("👉 Nhấn Enter tại đây sau khi trang web đã load xong bảng kết quả...")

            # 1. Lấy mã nguồn và MỞ KHÓA bảng ẩn (Fbref thường giấu bảng trong comment)
            html_content = self.driver.page_source
            html_content = html_content.replace("", "")
            
            print("⏳ Đang quét tìm bảng dữ liệu...")

            try:
                # 2. Dùng Pandas quét toàn bộ các bảng có trong trang
                all_tables = pd.read_html(html_content)
                
                found_table = None
                for table in all_tables:
                    # Kiểm tra xem bảng này có phải bảng kết quả không (phải có cột Home và Away)
                    # Chúng ta chuyển tên cột về chữ thường để so sánh cho chắc
                    cols = [str(c).lower() for c in table.columns]
                    if 'home' in cols and 'away' in cols:
                        found_table = table
                        break
                
                if found_table is not None:
                    # 3. Làm sạch dữ liệu
                    # Bỏ các dòng trống hoặc dòng lặp lại tiêu đề
                    df = found_table.dropna(subset=['Home', 'Away', 'Score'])
                    df = df[df['Home'] != 'Home']

                    # 4. Lấy các cột xG (Home_xG thường là 'xG', Away_xG thường là 'xG.1')
                    # Fbref có cấu trúc cột rất đặc thù, ta sẽ lấy theo chỉ số cột nếu tên bị lệch
                    cols_to_keep = ['Date', 'Home', 'xG', 'Score', 'xG.1', 'Away']
                    # Chỉ lấy những cột thực sự tồn tại
                    available = [c for c in cols_to_keep if c in df.columns]
                    df_final = df[available].copy()

                    # Đổi tên cho chuyên nghiệp
                    rename_dict = {'xG': 'Home_xG', 'xG.1': 'Away_xG'}
                    df_final = df_final.rename(columns=rename_dict)

                    # 5. Lưu file
                    os.makedirs("data/raw", exist_ok=True)
                    df_final.to_csv("data/raw/fbref_detailed_stats.csv", index=False, encoding="utf-8-sig")
                    
                    print(f"\n✅ THÀNH CÔNG RỰC RỠ!")
                    print(f"📊 Đã bốc được {len(df_final)} trận đấu.")
                    print(df_final.head(10)) # Chỉ in 10 trận xem thử thôi nhé
                else:
                    print("❌ Vẫn không tìm thấy bảng phù hợp. Hãy chắc chắn bạn đang ở trang 'Scores & Fixtures'.")

            except Exception as e:
                print(f" Lỗi khi xử lý bảng: {e}")

        except Exception as e:
            print(f" Lỗi hệ thống: {e}")
        finally:
            if self.driver:
                print("Đang dọn dẹp trình duyệt...")
                self.driver.quit()
                os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")

if __name__ == "__main__":
    scraper = FbrefScraper()
    scraper.scrape_league_stats()