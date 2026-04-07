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
        self.input_csv = "data/raw/fbref_all_matches/fbref_all_matches_2026.csv"
        self.output_dir = "data/raw/fbref_match_details"
        self.output_jsonl = f"{self.output_dir}/details_2026.jsonl"
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        print("Dang khoi tao trinh duyet (Version 146)...")
        options = uc.ChromeOptions()
        
        try:
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception as e:
            print(f"Loi khoi tao ban 146: {e}")
            print("Dang thu khoi tao lai bang cach tu dong...")
            self.driver = uc.Chrome(options=options)

    def get_already_scraped_ids(self):
        scraped_ids = set()
        if os.path.exists(self.output_jsonl):
            with open(self.output_jsonl, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        scraped_ids.add(data['match_id'])
                    except: continue
        return scraped_ids

    def parse_match_details(self, soup, match_id):
        data = {
            "match_id": match_id,
            "home_manager": "",
            "away_manager": "",
            "home_formation": "",
            "away_formation": "",
            "team_stats": {"home": {}, "away": {}},
            "player_stats": [],
            "match_events": []
        }

        # 1. Lay HLV tu Scorebox (Xoa so o dau ten)
        scorebox = soup.find('div', class_='scorebox')
        if scorebox:
            datapoints = scorebox.find_all('div', class_='datapoint')
            mgr_list = [d for d in datapoints if "Manager" in d.text]
            if len(mgr_list) >= 2:
                data["home_manager"] = re.sub(r'^\d+', '', mgr_list[0].text.replace('Manager:', '').strip()).strip()
                data["away_manager"] = re.sub(r'^\d+', '', mgr_list[1].text.replace('Manager:', '').strip()).strip()

        # 2. Lay So do tu Lineup
        lineups = soup.find_all('div', class_='lineup')
        if len(lineups) >= 2:
            h_f = lineups[0].find('th')
            a_f = lineups[1].find('th')
            if h_f and '(' in h_f.text: data["home_formation"] = h_f.text.split('(')[-1].replace(')', '').strip()
            if a_f and '(' in a_f.text: data["away_formation"] = a_f.text.split('(')[-1].replace(')', '').strip()

        # 3. Team Stats chính (Possession, Shots on Target, Saves)
        ts_div = soup.find('div', id='team_stats')
        if ts_div:
            current_stat = ""
            for row in ts_div.find_all('tr'):
                th = row.find('th')
                if th and th.get('colspan') == "2":
                    current_stat = th.text.strip().lower().replace(' ', '_')
                    continue
                tds = row.find_all('td')
                if len(tds) >= 2 and current_stat:
                    data["team_stats"]["home"][current_stat] = tds[0].text.strip().replace('%', '')
                    data["team_stats"]["away"][current_stat] = tds[1].text.strip().replace('%', '')

        # 4. Team Stats Extra (Fouls, Corners, Crosses, Interceptions, Offsides)
        extra_div = soup.find('div', id='team_stats_extra')
        if extra_div:
            divs = extra_div.find_all('div', recursive=False)
            for div in divs:
                items = div.find_all('div')
                for i in range(3, len(items), 3):
                    v_h = items[i].text.strip()
                    lbl = items[i+1].text.strip().lower()
                    v_a = items[i+2].text.strip()
                    data["team_stats"]["home"][lbl] = v_h
                    data["team_stats"]["away"][lbl] = v_a

        # 5. Player Stats (Summary tables)
        p_tables = soup.find_all('table', id=re.compile(r'stats_.*_summary'))
        for table in p_tables:
            t_id = table.get('id').split('_')[1]
            tbody = table.find('tbody')
            if not tbody: continue
            for row in tbody.find_all('tr'):
                p_th = row.find('th', {'data-stat': 'player'})
                if not p_th or not p_th.find('a'): continue
                p_id = p_th.find('a')['href'].split('/players/')[1].split('/')[0]
                
                # Check captain
                is_cap = "(C)" in p_th.text
                
                p_data = {
                    "player_id": p_id,
                    "team_id": t_id,
                    "is_captain": is_cap,
                    "position": row.find('td', {'data-stat': 'position'}).text.strip(),
                    "age": row.find('td', {'data-stat': 'age'}).text.strip(),
                    "minutes": row.find('td', {'data-stat': 'minutes'}).text.strip(),
                    "details": {
                        "goals": row.find('td', {'data-stat': 'goals'}).text.strip(),
                        "assists": row.find('td', {'data-stat': 'assists'}).text.strip(),
                        "shots": row.find('td', {'data-stat': 'shots'}).text.strip(),
                        "shots_on_target": row.find('td', {'data-stat': 'shots_on_target'}).text.strip(),
                        "tackles_won": row.find('td', {'data-stat': 'tackles_won'}).text.strip(),
                        "interceptions": row.find('td', {'data-stat': 'interceptions'}).text.strip(),
                        "crosses": row.find('td', {'data-stat': 'crosses'}).text.strip()
                    }
                }
                data["player_stats"].append(p_data)

        # 6. Match Events
        e_wrap = soup.find('div', id='events_wrap')
        if e_wrap:
            for ev in e_wrap.find_all('div', class_='event'):
                time_val = ev.find('div').text.strip().replace('’', '')
                icon_div = ev.find('div', class_='event_icon')
                e_type = icon_div.get('class')[1] if icon_div and len(icon_div.get('class')) > 1 else "other"
                data["match_events"].append({"time": time_val, "type": e_type, "desc": ev.text.strip()})

        return data

    def run(self):
        if not os.path.exists(self.input_csv):
            print(f"Loi: Khong tim thay file {self.input_csv}")
            return

        df = pd.read_csv(self.input_csv)
        scraped_ids = self.get_already_scraped_ids()
        
        pending_matches = []
        for _, row in df.iterrows():
            url = row.get('MatchReportURL') 
            if pd.isna(url) or not isinstance(url, str) or '/matches/' not in url:
                continue
            m_id = url.strip().split('/matches/')[1].split('/')[0]
            if m_id not in scraped_ids:
                pending_matches.append((m_id, url.strip()))

        print(f"Tong so tran can xu ly: {len(pending_matches)}")

        try:
            for m_id, url in pending_matches:
                print(f"Dang xu ly tran: {m_id}...", end=" ", flush=True)
                try:
                    self.driver.get(url)
                    time.sleep(7)
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    data = self.parse_match_details(soup, m_id)
                    
                    with open(self.output_jsonl, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    print("Xong!")
                except Exception as e:
                    print(f"Loi tai tran {m_id}: {e}")
                    time.sleep(5)
        finally:
            try:
                self.driver.quit()
            except: pass

if __name__ == "__main__":
    scraper = FBrefMatchDetailScraper()
    scraper.run()
    sys.stderr = open(os.devnull, 'w')  
    del scraper 
    gc.collect()