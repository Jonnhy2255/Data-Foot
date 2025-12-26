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

# Créer le dossier s'il n'existe pas
os.makedirs(DATA_DIR, exist_ok=True)

# === Toutes les ligues avec leurs fichiers JSON ===
LEAGUES = {
    "Premier League": {"code": "eng.1", "json": "England_Premier_League.json"},
    "LaLiga": {"code": "esp.1", "json": "Spain_Laliga.json"},
    "Bundesliga": {"code": "ger.1", "json": "bundesliga.json"},
    "Argentina - Primera Nacional": {"code": "arg.2", "json": "Argentina_Primera_Nacional.json"},
    "Austria - Bundesliga": {"code": "aut.1", "json": "Austria_Bundesliga.json"},
    "Belgium - Jupiler Pro League": {"code": "bel.1", "json": "Belgium_Jupiler_Pro_League.json"},
    "Brazil - Serie A": {"code": "bra.1", "json": "Brazil_Serie_A.json"},
    "Brazil - Serie B": {"code": "bra.2", "json": "Brazil_Serie_B.json"},
    "Chile - Primera Division": {"code": "chi.1", "json": "Chile_Primera_Division.json"},
    "China - Super League": {"code": "chn.1", "json": "China_Super_League.json"},
    "Colombia - Primera A": {"code": "col.1", "json": "Colombia_Primera_A.json"},
    "England - National League": {"code": "eng.5", "json": "England_National_League.json"},
    "France - Ligue 1": {"code": "fra.1", "json": "France_Ligue_1.json"},
    "Greece - Super League 1": {"code": "gre.1", "json": "Greece_Super_League_1.json"},
    "Italy - Serie A": {"code": "ita.1", "json": "Italy_Serie_A.json"},
    "Japan - J1 League": {"code": "jpn.1", "json": "Japan_J1_League.json"},
    "Mexico - Liga MX": {"code": "mex.1", "json": "Mexico_Liga_MX.json"},
    "Netherlands - Eredivisie": {"code": "ned.1", "json": "Netherlands_Eredivisie.json"},
    "Paraguay - Division Profesional": {"code": "par.1", "json": "Paraguay_Division_Profesional.json"},
    "Peru - Primera Division": {"code": "per.1", "json": "Peru_Primera_Division.json"},
    "Portugal - Primeira Liga": {"code": "por.1", "json": "Portugal_Primeira_Liga.json"},
    "Romania - Liga I": {"code": "rou.1", "json": "Romania_Liga_I.json"},
    "Russia - Premier League": {"code": "rus.1", "json": "Russia_Premier_League.json"},
    "Saudi Arabia - Pro League": {"code": "ksa.1", "json": "Saudi_Arabia_Pro_League.json"},
    "Sweden - Allsvenskan": {"code": "swe.1", "json": "Sweden_Allsvenskan.json"},
    "Switzerland - Super League": {"code": "sui.1", "json": "Switzerland_Super_League.json"},
    "Turkey - Super Lig": {"code": "tur.1", "json": "Turkey_Super_Lig.json"},
    "USA - Major League Soccer": {"code": "usa.1", "json": "USA_Major_League_Soccer.json"},
    "Venezuela - Primera Division": {"code": "ven.1", "json": "Venezuela_Primera_Division.json"},
    "UEFA Champions League": {"code": "uefa.champions", "json": "UEFA_Champions_League.json"},
    "UEFA Europa League": {"code": "uefa.europa", "json": "UEFA_Europa_League.json"},
    "FIFA Club World Cup": {"code": "fifa.cwc", "json": "FIFA_Club_World_Cup.json"}
}


def get_json_path(json_filename: str) -> str:
    """Retourne le chemin complet du fichier JSON dans le dossier leagues."""
    return os.path.join(DATA_DIR, json_filename)


def safe_load_json(json_path: str):
    """Charge un fichier JSON même vide ou corrompu."""
    if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {m["gameId"]: m for m in data if "gameId" in m}
            elif isinstance(data, dict):
                return data
            else:
                return {}
    except (json.JSONDecodeError, ValueError):
        print(f"⚠️ Fichier {json_path} vide ou invalide, recréé.")
        return {}


# === Dates à traiter ===
dates_to_fetch = [
    (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y%m%d"),
    (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
]

# === Boucle sur toutes les ligues ===
for league_name, league_info in LEAGUES.items():
    BASE_URL = f"https://www.espn.com/soccer/schedule/_/date/{{date}}/league/{league_info['code']}"
    JSON_FILE = get_json_path(league_info["json"])

    existing_matches = safe_load_json(JSON_FILE)
    total_new = 0

    for date_str in dates_to_fetch:
        print(f"\n📅 {league_name} - récupération matchs du {date_str}")
        try:
            res = requests.get(BASE_URL.format(date=date_str), headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.content, "html.parser")
        except Exception as e:
            print(f"⚠️ Erreur réseau {league_name} ({date_str}): {e}")
            continue

        tables = soup.select("div.ResponsiveTable")
        new_matches = {}

        for table in tables:
            date_title_tag = table.select_one("div.Table__Title")
            date_text = date_title_tag.text.strip() if date_title_tag else date_str

            rows = table.select("tbody > tr.Table__TR")
            for row in rows:
                try:
                    teams = row.select("span.Table__Team a.AnchorLink:last-child")
                    score_tag = row.select_one("a.AnchorLink.at")
                    if len(teams) != 2 or not score_tag:
                        continue

                    team1 = teams[0].text.strip()
                    team2 = teams[1].text.strip()
                    score = score_tag.text.strip()

                    if score.lower() == "v":
                        continue

                    match_url = score_tag["href"]
                    match_id_match = re.search(r"gameId/(\d+)", match_url)
                    if not match_id_match:
                        continue

                    game_id = match_id_match.group(1)
                    if game_id in existing_matches:
                        continue

                    match_data = {
                        "gameId": game_id,
                        "date": date_text,
                        "team1": team1,
                        "score": score,
                        "team2": team2,
                        "title": f"{team1} VS {team2}",
                        "match_url": "https://www.espn.com" + match_url
                    }

                    new_matches[game_id] = match_data
                    existing_matches[game_id] = match_data
                except Exception as e:
                    print(f"⚠️ Parsing {league_name} ({date_str}): {e}")
                    continue

        total_new += len(new_matches)
        print(f"✅ {league_name}: {len(new_matches)} nouveaux matchs pour {date_str}")

    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(list(existing_matches.values()), f, indent=2, ensure_ascii=False)
        print(f"💾 {league_name} sauvegardé : {len(existing_matches)} matchs (+{total_new} nouveaux).")
    except Exception as e:
        print(f"⚠️ Erreur écriture {JSON_FILE}: {e}")
