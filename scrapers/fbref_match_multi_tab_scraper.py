import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import zipfile
from multiprocessing import Pool
from datetime import date, timedelta

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_user, proxy_pass, ext_path):
    """Tạo Extension để tự động điền User/Pass cho Proxy"""
    manifest_json = """
    {
        "version": "1.0.0", "manifest_version": 2, "name": "Chrome Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": { "scripts": ["background.js"] }, "minimum_chrome_version":"22.0.0"
    } """
    background_js = """
    var config = { mode: "fixed_servers", rules: { singleProxy: { scheme: "http", host: "%s", port: parseInt(%s) }, bypassList: ["localhost"] } };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    chrome.webRequest.onAuthRequired.addListener(function(details) {
        return { authCredentials: { username: "%s", password: "%s" } };
    }, {urls: ["<all_urls>"]}, ['blocking']);
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)
    with zipfile.ZipFile(ext_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

def parse_match_row(row, league_name, match_date):
    """Hàm bóc tách đầy đủ tất cả các cột dữ liệu"""
    try:
        if 'spacer' in row.get('class', []): return None
        
        score_td = row.find('td', {'data-stat': 'score'})
        home_td = row.find('td', {'data-stat': 'home_team'})
        away_td = row.find('td', {'data-stat': 'away_team'})
        
        if not score_td or not home_td or not away_td: return None

        cells = {
            "MatchDate": match_date,
            "League": league_name,
            "Wk": row.find('td', {'data-stat': 'gameweek'}).text.strip() if row.find('td', {'data-stat': 'gameweek'}) else "",
            "Time": row.find('td', {'data-stat': 'start_time'}).text.strip() if row.find('td', {'data-stat': 'start_time'}) else "",
            "HomeTeam": home_td.text.strip(),
            "HomeScore": score_td.text.strip().split('–')[0] if '–' in score_td.text else "",
            "AwayScore": score_td.text.strip().split('–')[1] if '–' in score_td.text else "",
            "AwayTeam": away_td.text.strip(),
            "Attendance": row.find('td', {'data-stat': 'attendance'}).text.strip() if row.find('td', {'data-stat': 'attendance'}) else "",
            "Venue": row.find('td', {'data-stat': 'venue'}).text.strip() if row.find('td', {'data-stat': 'venue'}) else "",
            "Referee": row.find('td', {'data-stat': 'referee'}).text.strip() if row.find('td', {'data-stat': 'referee'}) else "",
        }

        # Lấy URL Match Report
        report_td = row.find('td', {'data-stat': 'match_report'})
        if report_td and report_td.find('a'):
            cells["MatchReportURL"] = "https://fbref.com" + report_td.find('a')['href']
        else:
            cells["MatchReportURL"] = ""
            
        return cells
    except Exception:
        return None

def scrape_year_process(data_package):
    year, proxy_str = data_package
    p = proxy_str.split(':') # host:port:user:pass
    
    # Tạo Extension Proxy riêng
    ext_path = os.path.abspath(f"proxy_auth_{year}.zip")
    create_proxy_auth_extension(p[0], p[1], p[2], p[3], ext_path)

    # Đường dẫn file và thư mục chuẩn đồ án
    output_file = f"data/raw/fbref_all_matches/fbref_all_matches_{year}.csv"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Profile riêng biệt để chạy đa luồng không bị lỗi WinError 183
    user_data_dir = os.path.abspath(f"chrome_profiles/profile_{year}")
    
    options = uc.ChromeOptions()
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument(f'--load-extension={ext_path}')
    options.add_argument('--start-maximized')
    options.add_argument('--blink-settings=imagesEnabled=false')

    driver = None
    try:
        print(f"[Bot {year}] Đang khởi động trình duyệt...")
        driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31) if year < date.today().year else date.today()
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"https://fbref.com/en/matches/{date_str}"
            
            driver.get(url)
            
            # Đợi xác minh Cloudflare (người dùng tích tay)
            verified = False
            for i in range(15):
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                if soup.find('table', class_='stats_table'):
                    verified = True
                    break
                if i % 5 == 0:
                    print(f"[Bot {year}] Đang đợi xác minh tại ngày {date_str}...")
                time.sleep(2)
            
            if verified:
                day_matches = []
                tables = soup.find_all('table', class_='stats_table')
                for table in tables:
                    caption = table.find('caption')
                    league = caption.text.replace('Table', '').strip() if caption else "Unknown"
                    tbody = table.find('tbody')
                    if not tbody: continue
                    
                    for row in tbody.find_all('tr'):
                        m_data = parse_match_row(row, league, date_str)
                        if m_data: day_matches.append(m_data)
                
                if day_matches:
                    df = pd.DataFrame(day_matches)
                    df.to_csv(output_file, mode='a', index=False, header=not os.path.exists(output_file), encoding='utf-8-sig')
                    print(f"[Bot {year}] Đã lưu {date_str}: {len(day_matches)} trận.")
            else:
                print(f"[Bot {year}] Bỏ qua {date_str} do không vượt được Cloudflare.")

            current_date += timedelta(days=1)
            time.sleep(random.uniform(2, 5))

    except Exception as e:
        print(f"[Bot {year}] Lỗi: {e}")
    finally:
        if driver: driver.quit()
        if os.path.exists(ext_path): os.remove(ext_path)

if __name__ == "__main__":
    # Thay thông tin Proxy chuẩn của bạn vào đây
    proxies = [
        "183.80.41.3:22113:lvhZVm:mCEXYj",
        "183.80.41.3:18785:lvhZVm:mCEXYj"
    ]
    
    # Chia việc cào 2 năm song song
    tasks = [(2023, proxies[0]), (2024, proxies[1])]
    
    print("--- HỆ THỐNG CÀO MULTI-TAB ĐẦY ĐỦ TRƯỜNG DỮ LIỆU ---")
    with Pool(processes=2) as pool:
        pool.map(scrape_year_process, tasks)