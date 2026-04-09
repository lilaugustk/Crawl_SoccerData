import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import gc

class FBrefAutoPlayerScraper:
    def __init__(self, seasons_file="data/raw/fbref_all_seasons.csv", 
                 output_file="data/raw/fbref_players_stats.csv"):
        self.seasons_file = seasons_file
        self.output_file = output_file
        self.base_url = "https://fbref.com"
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

        print("Dang khoi tao trinh duyet phien ban V5...")
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        
        try:
            self.driver = uc.Chrome(options=options, version_main=146)
        except Exception as e:
            print(f"Loi khoi tao: {e}")
            self.driver = None

    def handle_popups(self):
        """Tu dong dong thong bao Privacy/Cookie nhu trong anh cua ban"""
        try:
            # Thu click nut 'Accept All' bang JavaScript de nhanh va chinh xac
            self.driver.execute_script("""
                var acceptBtn = document.querySelector('#osano-cm-accept-all');
                if(acceptBtn) { acceptBtn.click(); }
                var privacyOverlay = document.querySelector('.osano-cm-window');
                if(privacyOverlay) { privacyOverlay.remove(); }
            """)
            time.sleep(2)
        except:
            pass

    def get_squad_urls_from_league(self, league_season_url):
        self.driver.get(league_season_url)
        time.sleep(5)
        self.handle_popups()
        
        # Cuon trang de kich hoat render bảng
        self.driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(3)

        squad_links = []
        # Tim moi o co data-stat="team" (Dua theo anh Inspector {8DCA2FD4...}.jpg ban gui)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        team_cells = soup.find_all('td', {'data-stat': 'team'})
        
        if not team_cells:
            print("Khong tim thay o 'team', thu tim trong toan bo the <a>...")
            # Backup plan: Tim tat ca link co dang /squads/
            team_cells = soup.find_all('a', href=True)
            for a in team_cells:
                if '/en/squads/' in a['href'] and 'Stats' in a.get_text():
                    url = self.base_url + a['href']
                    if url not in [s['team_url'] for s in squad_links]:
                        squad_links.append({"team_name": a.get_text().replace(' Stats',''), "team_url": url})
        else:
            for cell in team_cells:
                a_tag = cell.find('a', href=True)
                if a_tag:
                    url = self.base_url + a_tag['href']
                    name = a_tag.get_text(strip=True)
                    if url not in [s['team_url'] for s in squad_links]:
                        squad_links.append({"team_name": name, "team_url": url})
        
        return squad_links

    def scrape_players_from_squad(self, squad_url, team_name, league_id, season_name):
        self.driver.get(squad_url)
        rows_found = []
        # Vong lap cho bang Standard Stats hien ra
        for attempt in range(10):
            time.sleep(4)
            self.driver.execute_script("window.scrollBy(0, 500);")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            table = soup.find('table', id=lambda x: x and x.startswith('stats_standard'))
            if table and table.find('tbody'):
                rows_found = table.find('tbody').find_all('tr')
                if rows_found: break
            print(".", end="", flush=True)
        
        if not rows_found: return []

        player_list = []
        # Lay TeamID tu URL
        team_id = squad_url.split('/')[squad_url.split('/').index('squads') + 1]

        for r in rows_found:
            if r.get('class') and ('thead' in r.get('class') or 'spacer' in r.get('class')):
                continue
            
            p_cell = r.find('th', {'data-stat': 'player'}) or r.find('td', {'data-stat': 'player'})
            if not p_cell or not p_cell.find('a'): continue

            p_link = p_cell.find('a')
            player_list.append({
                "Season": season_name,
                "LeagueID": league_id,
                "TeamID": team_id,
                "TeamName": team_name,
                "PlayerID": p_link['href'].split('/')[3],
                "PlayerName": p_cell.get_text(strip=True),
                "Nation": r.find('td', {'data-stat': 'nationality'}).get_text(strip=True).split(' ')[-1] if r.find('td', {'data-stat': 'nationality'}) else "",
                "Pos": r.find('td', {'data-stat': 'position'}).get_text(strip=True) if r.find('td', {'data-stat': 'position'}) else "",
                "Age": r.find('td', {'data-stat': 'age'}).get_text(strip=True) if r.find('td', {'data-stat': 'age'}) else "",
                "MP": r.find('td', {'data-stat': 'games'}).get_text(strip=True) or "0",
                "Min": (r.find('td', {'data-stat': 'minutes'}).get_text(strip=True) or "0").replace(',', ''),
                "Gls": r.find('td', {'data-stat': 'goals'}).get_text(strip=True) or "0",
                "Ast": r.find('td', {'data-stat': 'assists'}).get_text(strip=True) or "0",
                "xG": r.find('td', {'data-stat': 'xg'}).get_text(strip=True) or "0.0",
                "PlayerURL": self.base_url + p_link['href']
            })
        return player_list

    def run(self):
        if not os.path.exists(self.seasons_file): return
        df_seasons = pd.read_csv(self.seasons_file)
        
        # Resume logic: Lay LeagueID + Season làm key
        finished_tasks = set()
        if os.path.exists(self.output_file):
            try:
                df_done = pd.read_csv(self.output_file, usecols=['LeagueID', 'Season'])
                finished_tasks = set(df_done['LeagueID'].astype(str) + "_" + df_done['Season'].astype(str))
            except: pass

        for _, s_info in df_seasons.iterrows():
            l_id, s_name = str(s_info['league_id']), str(s_info['season'])
            if f"{l_id}_{s_name}" in finished_tasks:
                print(f"Skipping {s_info['league_name']} {s_name}")
                continue

            print(f"\n>>> PROCESSING: {s_info['league_name']} | {s_name}")
            squads = self.get_squad_urls_from_league(s_info['season_url'])
            
            if not squads:
                print("Failed to get squads. Possible block or layout change.")
                continue

            for squad in squads:
                print(f"--- {squad['team_name']}:", end=" ", flush=True)
                data = self.scrape_players_from_squad(squad['team_url'], squad['team_name'], l_id, s_name)
                
                if data:
                    df_temp = pd.DataFrame(data)
                    # Ghi tiep vao file
                    is_empty = not os.path.exists(self.output_file) or os.stat(self.output_file).st_size == 0
                    df_temp.to_csv(self.output_file, mode='a', index=False, header=is_empty, encoding='utf-8-sig')
                    print(f"Done ({len(data)} p).")
                else: print("Error.")
                
                # Delay an toan de ne Cloudflare
                time.sleep(random.uniform(5, 9))
            gc.collect()

if __name__ == "__main__":
    scraper = FBrefAutoPlayerScraper()
    scraper.run()