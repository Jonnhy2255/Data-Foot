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

START_DATE = datetime(2025, 12, 24)
END_DATE = datetime(2025, 12, 27)

BASE_URL_TEMPLATE = "https://www.espn.com/soccer/schedule/_/date/{date}/league/{league}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
}

DATA_DIR = "data/football/leagues"
os.makedirs(DATA_DIR, exist_ok=True)

# =============================
# LIGUE UNIQUE
# =============================

LEAGUES = {
    "Italy - Serie A": {
        "id": "ita.1",
        "json": "Italy_Serie_A_2025-12-24_to_2025-12-27.json"
    }
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
                stats[label.text.strip()] = {
                    "away": values[0].text.strip(),
                    "home": values[1].text.strip()
                }

        time.sleep(0.6)
        return stats

    except Exception as e:
        print(f"❌ Stats error {game_id} :", e)
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
        return False

    found_played_match = False

    for table in tables:
        for row in table.select("tbody > tr.Table__TR"):
            score_tag = row.select_one("a.AnchorLink.at")
            if not score_tag or score_tag.text.lower() == "v":
                continue

            found_played_match = True

            match_url = score_tag["href"]
            game_id_match = re.search(r"gameId/(\d+)", match_url)
            if not game_id_match:
                continue

            game_id = game_id_match.group(1)

            if game_id in matches:
                continue

            # ✅ SÉLECTEURS ESPN CORRIGÉS
            away_tag = row.select_one(
                "span.Table__Team.away a.AnchorLink:last-child"
            )
            home_tag = row.select_one(
                "span.Table__Team:not(.away) a.AnchorLink:last-child"
            )

            away = away_tag.text.strip() if away_tag else "Unknown"
            home = home_tag.text.strip() if home_tag else "Unknown"

            matches[game_id] = {
                "gameId": game_id,
                "date": date_obj.strftime("%Y-%m-%d"),
                "team1": away,
                "team2": home,
                "score": score_tag.text.strip(),
                "league": league_id,
                "title": f"{away} VS {home}",
                "match_url": "https://www.espn.com" + match_url,
                "stats": get_match_stats(game_id)
            }

    return found_played_match

# =============================
# BOUCLE PRINCIPALE
# =============================

for league_name, league in LEAGUES.items():
    print(f"\n📌 {league_name}")
    matches = {}
    date_cursor = START_DATE

    while date_cursor <= END_DATE:
        scrape_date(league["id"], date_cursor, matches)
        date_cursor += timedelta(days=1)
        time.sleep(1)

    path = os.path.join(DATA_DIR, league["json"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(matches.values()), f, indent=2, ensure_ascii=False)

    print(f"✅ {league['json']} → {len(matches)} matchs")