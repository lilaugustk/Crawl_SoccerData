import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import sys
import gc
import json
import re

class FBrefMatchDetailScraper:
    def __init__(self, input_file="data/raw/fbref_all_matches.csv", output_file="data/raw/fbref_match_details.jsonl"):
        self.input_file = input_file
        self.output_file = output_file
        
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("Dang khoi tao trinh duyet chong tang hinh...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        self.driver = uc.Chrome(options=options)

    def get_crawled_urls(self):
        """Doc file JSONL de biet URL nao da cao thanh cong"""
        crawled = set()
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if "MatchURL" in data:
                            crawled.add(data["MatchURL"])
                    except: pass
        return crawled

    def get_pending_urls(self):
        """Loc ra cac URL chua cao tu file CSV lich thi dau"""
        if not os.path.exists(self.input_file):
            print(f"Khong tim thay file {self.input_file}")
            return []
        try:
            df = pd.read_csv(self.input_file)
            if 'MatchReportURL' not in df.columns: 
                print("File CSV khong co cot 'MatchReportURL'.")
                return []
            
            urls = df['MatchReportURL'].dropna().unique().tolist()
            valid_urls = [u for u in urls if isinstance(u, str) and u.startswith("http")]
            return valid_urls
        except: return []

    def parse_match(self, html, url):
        """Sieu ham boc tach toan bo ngoc ngach cua 1 tran dau"""
        soup = BeautifulSoup(html, 'html.parser')
        
        match_data = {
            "MatchURL": url,
            "Meta": {},
            "TeamStats": {},
            "Lineups": {"Home": {"Formation": "", "Starters": [], "Bench": []}, 
                        "Away": {"Formation": "", "Starters": [], "Bench": []}},
            "Events": [],
            "PlayerStats": {"Home": [], "Away": []}
        }

        # --- 1. LAY ID DOI BONG & META ---
        home_id, away_id = "", ""
        sb_0 = soup.find('div', id='sb_team_0')
        sb_1 = soup.find('div', id='sb_team_1')
        
        if sb_0 and sb_0.find('a'): home_id = sb_0.find('a')['href'].split('/')[3]
        if sb_1 and sb_1.find('a'): away_id = sb_1.find('a')['href'].split('/')[3]
        
        match_data["Meta"]["HomeTeamID"] = home_id
        match_data["Meta"]["AwayTeamID"] = away_id

        meta_box = soup.find('div', class_='scorebox_meta')
        if meta_box:
            match_data["Meta"]["RawText"] = meta_box.text.strip().replace('\n', ' ')

        # --- 2. LAY TEAM STATS ---
        team_stats = soup.find('table', id='team_stats')
        if team_stats:
            for row in team_stats.find_all('tr'):
                th = row.find('th')
                tds = row.find_all('td')
                if th and len(tds) >= 2 and not th.has_attr('colspan'):
                    stat_name = th.text.strip()
                    match_data["TeamStats"][stat_name] = {
                        "Home": tds[0].text.strip(),
                        "Away": tds[1].text.strip()
                    }
        
        extra_stats = soup.find('div', id='team_stats_extra')
        if extra_stats:
            for div in extra_stats.find_all('div'):
                text = div.text.strip()
                if text.isdigit() == False and len(text) > 2: 
                    prev_div = div.find_previous_sibling('div')
                    next_div = div.find_next_sibling('div')
                    if prev_div and next_div and prev_div.text.isdigit() and next_div.text.isdigit():
                        match_data["TeamStats"][text] = {
                            "Home": prev_div.text.strip(),
                            "Away": next_div.text.strip()
                        }

        # --- 3. LAY SO DO DOI HINH (LINEUPS) ---
        for team_key, div_id in [("Home", "a"), ("Away", "b")]:
            lineup_div = soup.find('div', id=div_id, class_='lineup')
            if lineup_div:
                table = lineup_div.find('table')
                if table:
                    th = table.find('th')
                    if th:
                        form_match = re.search(r'\(([\d\-]+)\)', th.text)
                        if form_match: match_data["Lineups"][team_key]["Formation"] = form_match.group(1)
                    
                    is_bench = False
                    for tr in table.find_all('tr')[1:]: 
                        if tr.find('th', colspan="2"):
                            is_bench = True
                            continue
                        
                        tds = tr.find_all('td')
                        if len(tds) >= 2:
                            shirt = tds[0].text.strip()
                            player_a = tds[1].find('a')
                            if player_a:
                                p_id = player_a['href'].split('/')[3]
                                p_name = player_a.text.strip()
                                p_data = {"PlayerID": p_id, "Name": p_name, "Shirt": shirt}
                                
                                if is_bench: match_data["Lineups"][team_key]["Bench"].append(p_data)
                                else: match_data["Lineups"][team_key]["Starters"].append(p_data)

        # --- 4. LAY DIEN BIEN TRAN DAU (EVENTS) ---
        events_wrap = soup.find('div', id='events_wrap')
        if events_wrap:
            for event in events_wrap.find_all('div', class_=re.compile(r'^event (a|b)$')):
                team_side = "Home" if "a" in event['class'] else "Away"
                time_div = event.find('div')
                event_time = time_div.text.split('’')[0].strip() if time_div else ""
                
                icon_div = event.find('div', class_='event_icon')
                event_type = icon_div['class'][1] if icon_div and len(icon_div['class'])>1 else "unknown"
                
                players = [a.text for a in event.find_all('a')]
                
                match_data["Events"].append({
                    "Team": team_side,
                    "Time": event_time.replace('&nbsp;', '').strip(),
                    "Type": event_type,
                    "Players": players
                })

        # --- 5. LAY CHI SO CA NHAN (PLAYER MATCH STATS) ---
        for team_key, team_id in [("Home", home_id), ("Away", away_id)]:
            if not team_id: continue
            stat_table = soup.find('table', id=f'stats_{team_id}_summary')
            if stat_table and stat_table.find('tbody'):
                for tr in stat_table.find('tbody').find_all('tr'):
                    if 'spacer' in tr.get('class', []): continue
                    
                    player_th = tr.find('th', {'data-stat': 'player'})
                    if not player_th or not player_th.find('a'): continue
                    
                    p_id = player_th.find('a')['href'].split('/')[3]
                    
                    p_stats = {"PlayerID": p_id, "Name": player_th.text.strip()}
                    for td in tr.find_all('td'):
                        stat_name = td.get('data-stat')
                        if stat_name:
                            p_stats[stat_name] = td.text.strip()
                            
                    match_data["PlayerStats"][team_key].append(p_stats)

        return match_data

    def run(self):
        urls = self.get_pending_urls()
        crawled = self.get_crawled_urls()
        pending = [u for u in urls if u not in crawled]
        
        print(f"Tong so tran: {len(urls)} | Da cao: {len(crawled)} | Can cao: {len(pending)}")
        print("Do tre an toan: 6 giay/request")
        
        for url in pending:
            print(f"Dang quet: {url} ...", end=" ", flush=True)
            try:
                self.driver.get(url)
                time.sleep(6) 
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                if "429 Too Many Requests" in soup.text or "Rate Limited" in soup.text:
                    print("\nBi chan (429)! FBref yeu cau nghi ngoi.")
                    break
                
                match_data = self.parse_match(self.driver.page_source, url)
                
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(match_data, ensure_ascii=False) + '\n')
                print("Thanh cong!")
                
            except Exception as e:
                print(f"Loi: {e}")

        print(f"\nHOAN THANH DEEP SCRAPE MATCH DETAILS!")
        self.driver.quit()

if __name__ == "__main__":
    scraper = FBrefMatchDetailScraper()
    scraper.run()
    
    sys.stderr = open(os.devnull, 'w')
    del scraper
    gc.collect()
