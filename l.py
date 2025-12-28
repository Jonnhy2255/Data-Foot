import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import time

# =============================
# CONFIGURATION DES LIGUES
# =============================

LEAGUES = {
    "ita.1": {
        "json_file": "seriea_2025-12-24_to_2025-12-27.json",
        "start_date": datetime(2025, 12, 24),
        "end_date": datetime(2025, 12, 27)
    }
}

BASE_URL_TEMPLATE = "https://www.espn.com/soccer/schedule/_/date/{date}/league/{league}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# =============================
# 🔍 FONCTION STATS PAR GAMEID
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
        stat_rows = stats_section.find_all("div", class_="LOSQp")

        for row in stat_rows:
            name_tag = row.find("span", class_="OkRBU")
            values = row.find_all("span", class_="bLeWt")
            if name_tag and len(values) >= 2:
                stats[name_tag.text.strip()] = (
                    values[0].text.strip(),
                    values[1].text.strip()
                )

        time.sleep(0.8)
        return stats

    except Exception as e:
        print(f"❌ Erreur stats match {game_id} : {e}")
        return {}

# =============================
# SCRAPING MATCHS PAR DATE
# =============================

def extract_matches_for_date(league_code, date_obj, all_matches):
    date_str = date_obj.strftime("%Y%m%d")
    url = BASE_URL_TEMPLATE.format(date=date_str, league=league_code)

    print(f"Scraping {league_code} - {date_str}...")

    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, "html.parser")
    except Exception as e:
        print("Erreur requête :", e)
        return True

    tables = soup.select("div.ResponsiveTable")

    for table in tables:
        date_title_tag = table.select_one("div.Table__Title")
        date_text = date_title_tag.text.strip() if date_title_tag else date_str

        rows = table.select("tbody > tr.Table__TR")
        for row in rows:
            try:
                away_team_tag = row.select_one("span.Table__Team.away a.AnchorLink:last-child")
                home_team_tag = row.select_one("span.Table__Team a.AnchorLink:last-child")
                score_tag = row.select_one("a.AnchorLink.at")

                if not away_team_tag or not home_team_tag or not score_tag:
                    continue

                team1 = away_team_tag.text.strip()
                team2 = home_team_tag.text.strip()
                score = score_tag.text.strip()

                if score.lower() == "v":
                    return False

                match_url = score_tag["href"]
                match_id_match = re.search(r"gameId/(\d+)", match_url)
                if not match_id_match:
                    continue

                game_id = match_id_match.group(1)

                if game_id not in all_matches:
                    stats = get_match_stats(game_id)

                    all_matches[game_id] = {
                        "gameId": game_id,
                        "date": date_text,
                        "team1": team1,
                        "team2": team2,
                        "score": score,
                        "title": f"{team1} VS {team2}",
                        "league": league_code,
                        "match_url": "https://www.espn.com" + match_url,
                        "stats": stats
                    }

            except Exception as e:
                print("Erreur ligne :", e)

    return True

# =============================
# BOUCLE PRINCIPALE
# =============================

for league_code, info in LEAGUES.items():
    all_matches = {}
    current_date = info["start_date"]

    while current_date <= info["end_date"]:
        if not extract_matches_for_date(league_code, current_date, all_matches):
            break
        current_date += timedelta(days=1)
        time.sleep(1)

    with open(info["json_file"], "w", encoding="utf-8") as f:
        json.dump(list(all_matches.values()), f, indent=2, ensure_ascii=False)

    print(f"✅ {info['json_file']} généré ({len(all_matches)} matchs)")