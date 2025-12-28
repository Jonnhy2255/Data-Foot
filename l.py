import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import time
import os

# =============================
# CONFIGURATION GLOBALE
# =============================

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime.now()

BASE_URL_TEMPLATE = "https://www.espn.com/soccer/schedule/_/date/{date}/league/{league}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13)"
}

DATA_DIR = "data/football/leagues"
os.makedirs(DATA_DIR, exist_ok=True)

# =============================
# LIGUES
# =============================

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
    "USA - MLS": {"id": "usa.1", "json": "USA_Major_League_Soccer.json"},
    "Venezuela - Primera Division": {"id": "ven.1", "json": "Venezuela_Primera_Division.json"},
    "UEFA Champions League": {"id": "uefa.champions", "json": "UEFA_Champions_League.json"},
    "UEFA Europa League": {"id": "uefa.europa", "json": "UEFA_Europa_League.json"},
    "FIFA Club World Cup": {"id": "fifa.cwc", "json": "FIFA_Club_World_Cup.json"}
}

# =============================
# FONCTION DE RÉCUPÉRATION DES STATS
# =============================

def get_match_stats(game_id):
    url = f"https://africa.espn.com/football/match/_/gameId/{game_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        stats_section = soup.find("section", {"data-testid": "prism-LayoutCard"})
        if not stats_section:
            return {}

        stats = {}
        for row in stats_section.find_all("div", class_="LOSQp"):
            label = row.find("span", class_="OkRBU")
            values = row.find_all("span", class_="bLeWt")
            if label and len(values) >= 2:
                stats[label.text.strip()] = (values[0].text.strip(), values[1].text.strip())

        time.sleep(0.6)
        return stats
    except:
        return {}

# =============================
# FONCTION DE SCRAPING PAR DATE
# =============================

def scrape_date(league_id, date_obj, matches):
    url = BASE_URL_TEMPLATE.format(
        date=date_obj.strftime("%Y%m%d"),
        league=league_id
    )

    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    tables = soup.select("div.ResponsiveTable")

    if not tables:
        return True  # pas de match sur cette date, continuer

    for table in tables:
        for row in table.select("tbody > tr.Table__TR"):
            score_tag = row.select_one("a.AnchorLink.at")
            if not score_tag:
                continue

            if score_tag.text.lower() == "v":
                # Match futur détecté → arrêt immédiat pour ce championnat
                return False

            match_url = score_tag["href"]
            game_id_match = re.search(r"gameId/(\d+)", match_url)
            if not game_id_match:
                continue
            game_id = game_id_match.group(1)

            if game_id in matches:
                continue

            away_tag = row.select_one("span.Table__Team.away a")
            home_tag = row.select_one("span.Table__Team a")
            away = away_tag.text.strip() if away_tag else "Away"
            home = home_tag.text.strip() if home_tag else "Home"

            matches[game_id] = {
                "gameId": game_id,
                "date": date_obj.strftime("%Y-%m-%d"),
                "team1": away,
                "team2": home,
                "score": score_tag.text.strip(),
                "match_url": "https://www.espn.com" + match_url,
                "stats": get_match_stats(game_id)
            }

    return True  # continuer au jour suivant

# =============================
# BOUCLE PRINCIPALE
# =============================

for league_name, league in LEAGUES.items():
    print(f"\n📌 {league_name}")
    matches = {}
    date_cursor = START_DATE

    while date_cursor <= END_DATE:
        has_match = scrape_date(league["id"], date_cursor, matches)

        if not has_match:
            print(f"⏹️ Match futur détecté, arrêt du scraping pour {league_name}")
            break

        date_cursor += timedelta(days=1)
        time.sleep(1)

    path = os.path.join(DATA_DIR, league["json"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(matches.values()), f, indent=2, ensure_ascii=False)

    print(f"✅ {league['json']} → {len(matches)} matchs")