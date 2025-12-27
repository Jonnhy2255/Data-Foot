import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta, timezone
import re
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
}

# === Dossier de données ===
DATA_DIR = "data/football/leagues"
os.makedirs(DATA_DIR, exist_ok=True)

# === Toutes les ligues avec leurs IDs ESPN ===
LEAGUES = {
    "Premier League": {"id": "eng.1", "json": "England_Premier_League.json"},
    "LaLiga": {"id": "esp.1", "json": "Spain_Laliga.json"},
    "Bundesliga": {"id": "ger.1", "json": "Germany_Bundesliga.json"},
    "Argentina - Primera Nacional": {"id": "arg.2", "json": "Argentina_Primera_Nacional.json"},
    "Austria - Bundesliga": {"id": "aut.1", "json": "Austria_Bundesliga.json"},
    "Belgium - Jupiler Pro League": {"id": "bel.1", "json": "Belgium_Jupiler_Pro_League.json"},
    "Brazil - Serie A": {"id": "bra.1", "json": "Brazil_Serie_A.json"},
    "Brazil - Serie B": {"id": "bra.2", "json": "Brazil_Serie_B.json"},
    "Chile - Primera Division": {"id": "chi.1", "json": "Chile_Primera_Division.json"},
    "China - Super League": {"id": "chn.1", "json": "China_Super_League.json"},
    "Colombia - Primera A": {"id": "col.1", "json": "Colombia_Primera_A.json"},
    "England - National League": {"id": "eng.5", "json": "England_National_League.json"},
    "France - Ligue 1": {"id": "fra.1", "json": "France_Ligue_1.json"},
    "Greece - Super League 1": {"id": "gre.1", "json": "Greece_Super_League_1.json"},
    "Italy - Serie A": {"id": "ita.1", "json": "Italy_Serie_A.json"},
    "Japan - J1 League": {"id": "jpn.1", "json": "Japan_J1_League.json"},
    "Mexico - Liga MX": {"id": "mex.1", "json": "Mexico_Liga_MX.json"},
    "Netherlands - Eredivisie": {"id": "ned.1", "json": "Netherlands_Eredivisie.json"},
    "Paraguay - Division Profesional": {"id": "par.1", "json": "Paraguay_Division_Profesional.json"},
    "Peru - Primera Division": {"id": "per.1", "json": "Peru_Primera_Division.json"},
    "Portugal - Primeira Liga": {"id": "por.1", "json": "Portugal_Primeira_Liga.json"},
    "Romania - Liga I": {"id": "rou.1", "json": "Romania_Liga_I.json"},
    "Russia - Premier League": {"id": "rus.1", "json": "Russia_Premier_League.json"},
    "Saudi Arabia - Pro League": {"id": "ksa.1", "json": "Saudi_Arabia_Pro_League.json"},
    "Sweden - Allsvenskan": {"id": "swe.1", "json": "Sweden_Allsvenskan.json"},
    "Switzerland - Super League": {"id": "sui.1", "json": "Switzerland_Super_League.json"},
    "Turkey - Super Lig": {"id": "tur.1", "json": "Turkey_Super_Lig.json"},
    "USA - Major League Soccer": {"id": "usa.1", "json": "USA_Major_League_Soccer.json"},
    "Venezuela - Primera Division": {"id": "ven.1", "json": "Venezuela_Primera_Division.json"},
    "UEFA Champions League": {"id": "uefa.champions", "json": "UEFA_Champions_League.json"},
    "UEFA Europa League": {"id": "uefa.europa", "json": "UEFA_Europa_League.json"},
    "FIFA Club World Cup": {"id": "fifa.cwc", "json": "FIFA_Club_World_Cup.json"}
}


def get_json_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def safe_load_json(path: str):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {m["gameId"]: m for m in data if "gameId" in m}
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        print(f"⚠️ JSON invalide : {path}")
        return {}


# === Dates à traiter ===
dates_to_fetch = [
    (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y%m%d"),
    (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d"),
]

# === Scraping ===
for league_name, league in LEAGUES.items():
    BASE_URL = f"https://www.espn.com/soccer/schedule/_/date/{{date}}/league/{league['id']}"
    JSON_FILE = get_json_path(league["json"])

    existing_matches = safe_load_json(JSON_FILE)
    total_new = 0

    for date_str in dates_to_fetch:
        print(f"\n📅 {league_name} — {date_str}")
        try:
            res = requests.get(BASE_URL.format(date=date_str), headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "html.parser")
        except Exception as e:
            print(f"⚠️ Réseau {league_name}: {e}")
            continue

        for table in soup.select("div.ResponsiveTable"):
            date_title = table.select_one("div.Table__Title")
            date_text = date_title.text.strip() if date_title else date_str

            for row in table.select("tbody > tr.Table__TR"):
                try:
                    teams = row.select("span.Table__Team a.AnchorLink:last-child")
                    score_tag = row.select_one("a.AnchorLink.at")
                    if len(teams) != 2 or not score_tag:
                        continue

                    score = score_tag.text.strip()
                    if score.lower() == "v":
                        continue

                    match_id = re.search(r"gameId/(\d+)", score_tag["href"])
                    if not match_id:
                        continue

                    game_id = match_id.group(1)
                    if game_id in existing_matches:
                        continue

                    match = {
                        "gameId": game_id,
                        "date": date_text,
                        "team1": teams[0].text.strip(),
                        "score": score,
                        "team2": teams[1].text.strip(),
                        "title": f"{teams[0].text.strip()} VS {teams[1].text.strip()}",
                        "match_url": "https://www.espn.com" + score_tag["href"],
                    }

                    existing_matches[game_id] = match
                    total_new += 1
                except Exception:
                    continue

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(list(existing_matches.values()), f, indent=2, ensure_ascii=False)

    print(f"💾 {league_name} : {len(existing_matches)} matchs (+{total_new})")