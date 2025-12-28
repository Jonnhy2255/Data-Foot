import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import time

# =============================
# CONFIGURATION GLOBALE
# =============================

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime.now()

BASE_URL_TEMPLATE = "https://www.espn.com/soccer/schedule/_/date/{date}/league/{league}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# =============================
# LIGUES
# =============================

LEAGUES = {
    "Premier League": {
        "id": "eng.1",
        "json": "England_Premier_League.json"
    },
    "LaLiga": {
        "id": "esp.1",
        "json": "Spain_Laliga.json"
    },
    "Bundesliga": {
        "id": "ger.1",
        "json": "Germany_Bundesliga.json"
    },
    "Argentina - Primera Nacional": {
        "id": "arg.2",
        "json": "Argentina_Primera_Nacional.json"
    },
    "Austria - Bundesliga": {
        "id": "aut.1",
        "json": "Austria_Bundesliga.json"
    },
    "Belgium - Jupiler Pro League": {
        "id": "bel.1",
        "json": "Belgium_Jupiler_Pro_League.json"
    }
}

# =============================
# STATS PAR GAMEID
# =============================

def get_match_stats(game_id):
    url = f"https://africa.espn.com/football/match/_/gameId/{game_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        stats_section = soup.find("section", {"data-testid": "prism-LayoutCard"})
        if not stats_section:
            return {}

        stats = {}
        rows = stats_section.find_all("div", class_="LOSQp")

        for row in rows:
            label = row.find("span", class_="OkRBU")
            values = row.find_all("span", class_="bLeWt")

            if label and len(values) >= 2:
                stats[label.text.strip()] = {
                    "home": values[0].text.strip(),
                    "away": values[1].text.strip()
                }

        time.sleep(0.8)
        return stats

    except Exception as e:
        print(f"❌ Stats échouées ({game_id}) : {e}")
        return {}

# =============================
# SCRAPING PAR DATE
# =============================

def extract_matches_for_date(league_id, date_obj, all_matches):
    date_str = date_obj.strftime("%Y%m%d")
    url = BASE_URL_TEMPLATE.format(date=date_str, league=league_id)

    print(f"📅 {league_id} | {date_str}")

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
    except Exception as e:
        print("Erreur requête :", e)
        return True

    tables = soup.select("div.ResponsiveTable")

    for table in tables:
        date_title = table.select_one("div.Table__Title")
        match_date = date_title.text.strip() if date_title else date_str

        rows = table.select("tbody > tr.Table__TR")

        for row in rows:
            try:
                away = row.select_one("span.Table__Team.away a.AnchorLink:last-child")
                home = row.select_one("span.Table__Team a.AnchorLink:last-child")
                score_tag = row.select_one("a.AnchorLink.at")

                if not away or not home or not score_tag:
                    continue

                score = score_tag.text.strip()

                # ⛔ ARRÊT AU PREMIER MATCH FUTUR
                if score.lower() == "v":
                    return False

                match_url = score_tag["href"]
                match_id = re.search(r"gameId/(\d+)", match_url)

                if not match_id:
                    continue

                game_id = match_id.group(1)

                if game_id in all_matches:
                    continue

                stats = get_match_stats(game_id)

                all_matches[game_id] = {
                    "gameId": game_id,
                    "date": match_date,
                    "team_home": home.text.strip(),
                    "team_away": away.text.strip(),
                    "score": score,
                    "league": league_id,
                    "match_url": "https://www.espn.com" + match_url,
                    "stats": stats
                }

            except Exception as e:
                print("Erreur ligne :", e)

    return True

# =============================
# BOUCLE PRINCIPALE
# =============================

for league_name, league in LEAGUES.items():
    print(f"\n===== {league_name} =====")

    all_matches = {}
    current_date = START_DATE

    while current_date <= END_DATE:
        should_continue = extract_matches_for_date(
            league["id"],
            current_date,
            all_matches
        )

        if not should_continue:
            print(f"⛔ Arrêt automatique le {current_date.strftime('%Y-%m-%d')}")
            break

        current_date += timedelta(days=1)
        time.sleep(1)

    with open(league["json"], "w", encoding="utf-8") as f:
        json.dump(list(all_matches.values()), f, indent=2, ensure_ascii=False)

    print(f"✅ {league['json']} généré — {len(all_matches)} matchs")