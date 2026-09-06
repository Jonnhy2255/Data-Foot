"""
Scraper Playwright — récupère pays / championnats / nombre d'événements live
depuis https://melbet.ci/fr/live/football

Sortie : championnats_live.csv (pays, championnat, nombre_evenements, lien)
"""

import re
import csv
import random
from playwright.sync_api import sync_playwright

URL = "https://melbet.ci/fr/live/football"
OUTPUT_CSV = "championnats_live.csv"

# Pool de User-Agents desktop réalistes et à jour (rotation aléatoire à chaque run)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
window.chrome = { runtime: {} };
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
);
Object.defineProperty(navigator, 'webgl', { get: () => undefined });
"""


def make_stealth_context(browser):
    ua = random.choice(USER_AGENTS)
    context = browser.new_context(
        user_agent=ua,
        viewport={"width": 1920, "height": 1080},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
        },
    )
    context.add_init_script(STEALTH_INIT_SCRIPT)
    return context


def parse_country_and_league(title: str):
    """
    Découpe un titre du type :
    'Championnat de Russie. Première Ligue' -> ('Russie', 'Première Ligue')
    Retombe sur le titre entier si le motif ne correspond pas.
    """
    m = re.match(r"Championnats? d[eu']\s*([^.]+)\.?\s*(.*)", title, re.IGNORECASE)
    if m:
        country = m.group(1).strip()
        league = m.group(2).strip() or title
        return country, league
    return "Inconnu", title


def scrape():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = make_stealth_context(browser)
        page = context.new_page()

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(random.randint(2000, 4000))  # laisser le JS s'exécuter

        try:
            page.wait_for_selector(".dashboard-champ-item-template", timeout=30000)
        except Exception:
            # Sauvegarde de debug si la structure a changé / page bloquée
            page.screenshot(path="debug_screenshot.png", full_page=True)
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            browser.close()
            raise RuntimeError(
                "Impossible de trouver les championnats. "
                "Voir debug_screenshot.png / debug_page.html"
            )

        items = page.query_selector_all(".dashboard-champ-item-template")
        for item in items:
            link_el = item.query_selector("a.dashboard-champ-item-template__link")
            href = link_el.get_attribute("href") if link_el else None

            title_el = item.query_selector(".dashboard-champ-item-template-title__title")
            raw_title = title_el.inner_text().strip() if title_el else ""

            count_el = item.query_selector(".dashboard-champ-games-count")
            count_text = count_el.inner_text().strip() if count_el else ""
            count_match = re.search(r"\d+", count_text)
            event_count = int(count_match.group()) if count_match else 0

            clean_title = raw_title.replace(count_text, "").strip()
            country, league = parse_country_and_league(clean_title)

            results.append(
                {
                    "pays": country,
                    "championnat": league,
                    "nombre_evenements": event_count,
                    "lien": f"https://melbet.ci{href}" if href else "",
                }
            )

        browser.close()
    return results


def save_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["pays", "championnat", "nombre_evenements", "lien"]
        )
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    data = scrape()
    save_csv(data, OUTPUT_CSV)
    print(f"{len(data)} championnats extraits -> {OUTPUT_CSV}")
