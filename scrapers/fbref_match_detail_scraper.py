import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import os
import sys  
import gc
import re

class FBrefMatchDetailScraper:
    def __init__(self):
        # self.input_csv = "data/raw/fbref_all_matches/fbref_all_matches_2026.csv"
        # self.output_dir = "data/raw/fbref_match_details"
        # self.output_jsonl = f"{self.output_dir}/details_2026.jsonl"
        
        self.input_csv = "data/raw/fbref_all_matches/fbref_all_matches_2024.csv"
        self.output_dir = "data/raw/fbref_match_details"
        self.output_jsonl = f"{self.output_dir}/details_2024.jsonl"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        print("--- KHOI TAO TRINH DUYET (CHROME 146) ---")
        options = uc.ChromeOptions()
        # Chạy ẩn danh để hạn chế cache và tăng tốc độ load
        options.add_argument("--incognito") 
        try:
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception as e:
            self.driver = uc.Chrome(options=options)

    def clean_text(self, text):
        if not text: return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def get_already_scraped_ids(self):
        scraped_ids = set()
        if os.path.exists(self.output_jsonl):
            with open(self.output_jsonl, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Chỉ coi là đã cào nếu có đủ thông tin quan trọng
                        if data.get('match_id') and data.get('home_team_id'):
                            scraped_ids.add(data['match_id'])
                    except: continue
        return scraped_ids

    def parse_match_details(self, soup, match_id):
        data = {
            "match_id": match_id,
            "home_team_id": "",
            "away_team_id": "",
            "home_manager": "",
            "away_manager": "",
            "home_formation": "",
            "away_formation": "",
            "team_stats": {"home": {}, "away": {}},
            "player_stats": [],
            "match_events": []
        }

        # 1. Lấy Team ID và Manager từ Scorebox (Phần quan trọng nhất)
        scorebox = soup.find('div', class_='scorebox')
        if scorebox:
            # Lấy Team IDs từ các link squads
            team_links = scorebox.select('div > strong > a[href*="/squads/"]')
            if len(team_links) >= 2:
                data["home_team_id"] = team_links[0]['href'].split('/squads/')[1].split('/')[0]
                data["away_team_id"] = team_links[1]['href'].split('/squads/')[1].split('/')[0]

            # Lấy HLV
            mgr_divs = [d for d in scorebox.find_all('div', class_='datapoint') if "Manager" in d.text]
            if len(mgr_divs) >= 2:
                h_mgr_raw = re.sub(r'^\d+', '', mgr_divs[0].text.replace('Manager:', ''))
                a_mgr_raw = re.sub(r'^\d+', '', mgr_divs[1].text.replace('Manager:', ''))
                data["home_manager"] = self.clean_text(h_mgr_raw)
                data["away_manager"] = self.clean_text(a_mgr_raw)

        # 2. Formation (Sơ đồ chiến thuật)
        lineups = soup.find_all('div', class_='lineup')
        if len(lineups) >= 2:
            h_th = lineups[0].find('th')
            a_th = lineups[1].find('th')
            if h_th and '(' in h_th.text: data["home_formation"] = h_th.text.split('(')[-1].replace(')', '').strip()
            if a_th and '(' in a_th.text: data["away_formation"] = a_th.text.split('(')[-1].replace(')', '').strip()

        # 3. Team Stats (Possession, Shots, vv...)
        ts_div = soup.find('div', id='team_stats')
        if ts_div:
            curr_label = ""
            for row in ts_div.find_all('tr'):
                th = row.find('th')
                if th and th.get('colspan') == "2":
                    curr_label = th.text.strip().lower().replace(' ', '_')
                    continue
                tds = row.find_all('td')
                if len(tds) >= 2 and curr_label:
                    h_val = tds[0].text.strip().split('—')[-1].split('of')[0].replace('%','').strip()
                    a_val = tds[1].text.strip().split('—')[0].split('of')[0].replace('%','').strip()
                    data["team_stats"]["home"][curr_label] = h_val
                    data["team_stats"]["away"][curr_label] = a_val

        # 4. Player Stats (Thông số cầu thủ)
        p_tables = soup.find_all('table', id=re.compile(r'stats_.*_summary'))
        for table in p_tables:
            t_id = table.get('id').split('_')[1]
            tbody = table.find('tbody')
            if not tbody: continue
            for row in tbody.find_all('tr'):
                p_th = row.find('th', {'data-stat': 'player'})
                if not p_th or not p_th.find('a'): continue
                p_id = p_th.find('a')['href'].split('/players/')[1].split('/')[0]
                p_data = {
                    "player_id": p_id, "team_id": t_id, "is_captain": "(C)" in p_th.text,
                    "position": row.find('td', {'data-stat': 'position'}).text.strip(),
                    "age": row.find('td', {'data-stat': 'age'}).text.strip(),
                    "minutes": row.find('td', {'data-stat': 'minutes'}).text.strip(),
                    "details": {}
                }
                for stat in ['goals', 'assists', 'shots', 'shots_on_target', 'tackles_won', 'interceptions', 'crosses']:
                    tag = row.find('td', {'data-stat': stat})
                    p_data["details"][stat] = tag.text.strip() if tag else "0"
                data["player_stats"].append(p_data)

        # 5. Match Events (Diễn biến trận đấu)
        e_wrap = soup.find('div', id='events_wrap')
        if e_wrap:
            for ev in e_wrap.find_all('div', class_='event'):
                time_div = ev.find('div')
                event_time = "".join(re.findall(r'[\d+]+', time_div.text)) if time_div else ""
                icon = ev.find('div', class_='event_icon')
                e_type = icon.get('class')[1] if icon and len(icon.get('class')) > 1 else "other"
                desc = self.clean_text(ev.text).replace('—', '-').replace('’', "'")
                data["match_events"].append({"time": event_time, "type": e_type, "description": desc})

        return data

    def run(self):
        if not os.path.exists(self.input_csv):
            print(f"Loi: Khong tim thay {self.input_csv}")
            return

        df = pd.read_csv(self.input_csv)
        scraped_ids = self.get_already_scraped_ids()
        
        pending = []
        for _, row in df.iterrows():
            url = row.get('MatchReportURL')
            if pd.isna(url) or '/matches/' not in str(url): continue
            m_id = url.strip().split('/matches/')[1].split('/')[0]
            if m_id not in scraped_ids:
                m_date = row.get('MatchDate') or row.get('date') or 'N/A'
                h_team = row.get('Home') or row.get('home_team') or 'Unknown'
                a_team = row.get('Away') or row.get('away_team') or 'Unknown'
                
                pending.append({
                    "id": m_id, "url": url.strip(), "date": str(m_date),
                    "match_name": f"{h_team} vs {a_team}"
                })

        total = len(pending)
        print(f"\n=== BAT DAU CAO CHI TIET (ROBUST VERSION) ===")
        print(f"Tong so tran can xu ly: {total}")
        print("-" * 80)

        count = 0
        try:
            for item in pending:
                count += 1
                percent = (count / total) * 100
                print(f"[{count}/{total}] [{percent:.1f}%] [{item['date']}] {item['id']} | {item['match_name']}...", end=" ", flush=True)
                
                try:
                    self.driver.get(item['url'])
                    # Tăng thời gian chờ lên 10s để đảm bảo load hết bảng stats
                    time.sleep(4) 
                    
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    data = self.parse_match_details(soup, item['id'])
                    
                    # Kiểm tra dữ liệu rác trước khi ghi
                    if not data["home_team_id"]:
                        print("BO QUA (Trang chua load xong)")
                        continue

                    with open(self.output_jsonl, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    print("DONE!")
                except Exception as e:
                    print(f"LOI -> {e}")
                    time.sleep(4)
        finally:
            print("-" * 80)
            print(f"TIEN DO: {count}/{total} tran.")
            try: self.driver.quit()
            except: pass

if __name__ == "__main__":
    scraper = FBrefMatchDetailScraper()
    scraper.run()
    sys.stderr = open(os.devnull, 'w')  
    del scraper 
    gc.collect()