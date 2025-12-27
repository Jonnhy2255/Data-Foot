import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import time

# Ligues avec leurs codes ESPN, nom du fichier JSON et dates officielles
LEAGUES = {
    "ger.1": {
        "json_file": "bundesliga2024-2025.json",
        "start_date": datetime(2024, 8, 23),
        "end_date": datetime(2025, 5, 17)
    },
    "ita.1": {
        "json_file": "seriea2024-2025.json",
        "start_date": datetime(2024, 8, 17),
        "end_date": datetime(2025, 5, 25)
    },
    "fra.1": {
        "json_file": "ligue1_2024-2025.json",
        "start_date": datetime(2024, 8, 10),
        "end_date": datetime(2025, 5, 25)
    }
}

BASE_URL_TEMPLATE = "https://www.espn.com/soccer/schedule/_/date/{date}/league/{league}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
}

def extract_matches_for_date(league_code, date_obj, all_matches):
    date_str = date_obj.strftime("%Y%m%d")
    url = BASE_URL_TEMPLATE.format(date=date_str, league=league_code)
    print(f"Scraping {league_code} - {date_str}...")

    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, "html.parser")
    except Exception as e:
        print(f"Erreur lors de la requête {date_str} pour {league_code} :", e)
        return True

    tables = soup.select("div.ResponsiveTable")
    for table in tables:
        date_title_tag = table.select_one("div.Table__Title")
        date_text = date_title_tag.text.strip() if date_title_tag else date_str

        rows = table.select("tbody > tr.Table__TR")
        for row in rows:
            try:
                away_team_tag = row.select_one("td.events__col span.Table__Team.away a.AnchorLink:last-child")
                home_team_tag = row.select_one("td.colspan__col span.Table__Team a.AnchorLink:last-child")
                score_tag = row.select_one("td.colspan__col a.AnchorLink.at")

                if not away_team_tag or not home_team_tag or not score_tag:
                    continue

                team1 = away_team_tag.text.strip()
                team2 = home_team_tag.text.strip()
                score = score_tag.text.strip()

                # Arrêter le scraping si match à venir
                if score.lower() == "v":
                    print(f"Match à venir détecté : {team1} VS {team2}. Arrêt du scraping pour {league_code}.")
                    return False

                # Ignorer certains matchs US
                if "USMNT" in team1 or "USWNT" in team1 or "USMNT" in team2 or "USWNT" in team2:
                    continue

                match_url = score_tag["href"]
                match_id_match = re.search(r"gameId/(\d+)", match_url)
                if not match_id_match:
                    continue

                game_id = match_id_match.group(1)

                if game_id not in all_matches:
                    all_matches[game_id] = {
                        "gameId": game_id,
                        "date": date_text,
                        "team1": team1,
                        "score": score,
                        "team2": team2,
                        "title": f"{team1} VS {team2}",
                        "match_url": "https://www.espn.com" + match_url,
                        "league": league_code
                    }

            except Exception as e:
                print("Erreur lors du traitement d'une ligne :", e)
                continue

    return True

# Boucle principale pour chaque ligue
for league_code, info in LEAGUES.items():
    print(f"\n📌 Début du scraping pour la ligue {league_code}")
    all_matches = {}
    current_date = info["start_date"]
    while current_date <= info["end_date"]:
        should_continue = extract_matches_for_date(league_code, current_date, all_matches)
        if not should_continue:
            break
        current_date += timedelta(days=1)
        time.sleep(1)

    # Sauvegarde JSON spécifique à la ligue
    with open(info["json_file"], "w", encoding="utf-8") as f:
        json.dump(list(all_matches.values()), f, indent=2, ensure_ascii=False)

    print(f"✅ {info['json_file']} généré avec {len(all_matches)} matchs.\n")