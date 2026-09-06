import asyncio
import json
from playwright.async_api import async_playwright
import os
from datetime import datetime

class LiveMatchesScraper:
    def __init__(self):
        self.matches_data = []
        self.processed_ids = set()
        
    async def scrape(self):
        """Méthode principale de scraping"""
        async with async_playwright() as p:
            # Configuration du navigateur avec des en-têtes réalistes
            browser = await p.chromium.launch(
                headless=False,  # Mettre à True pour une exécution invisible
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--start-maximized'
                ]
            )
            
            # Créer un contexte avec des en-têtes personnalisés
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='fr-FR',
                timezone_id='Europe/Paris',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'DNT': '1'
                }
            )
            
            page = await context.new_page()
            
            # Intercepter les requêtes pour voir les appels API (optionnel)
            # await self.setup_request_interception(page)
            
            print("🌐 Navigation vers la page des matchs en direct...")
            await page.goto('https://1xbet.ci/fr/live', wait_until='domcontentloaded')
            
            # Attendre que la page soit prête
            await self.wait_for_page_ready(page)
            
            # Simuler le scroll pour charger tous les matchs
            await self.scroll_to_load_all_matches(page)
            
            # Récupérer tous les matchs
            print("📊 Récupération des données des matchs...")
            matches = await self.extract_all_matches(page)
            
            # Sauvegarder les données
            await self.save_matches(matches)
            
            await browser.close()
            return matches
    
    async def wait_for_page_ready(self, page):
        """Attendre que la page soit complètement chargée"""
        print("⏳ Attente du chargement de la page...")
        
        try:
            # Attendre que les cartes de matchs apparaissent
            await page.wait_for_selector('.ui-game-card', timeout=30000)
            print("✅ Les cartes de matchs sont chargées")
            
            # Attendre que le réseau soit calme
            await page.wait_for_load_state('networkidle')
            
            # Attendre que les données JSON soient chargées
            await page.wait_for_function(
                """() => {
                    return window.__RCP !== undefined && 
                           window.__RCP[Object.keys(window.__RCP)[0]] !== undefined &&
                           window.__RCP[Object.keys(window.__RCP)[0]]['games-live'] !== undefined;
                }""",
                timeout=15000
            )
            print("✅ Les données JSON sont chargées")
            
        except Exception as e:
            print(f"⚠️  Timeout ou erreur lors du chargement: {e}")
            # Continuer quand même, on récupérera ce qui est disponible
    
    async def scroll_to_load_all_matches(self, page):
        """Simuler le scroll pour charger tous les matchs"""
        print("🔄 Scroll pour charger tous les matchs...")
        
        # Nombre de scrolls et temps d'attente entre chaque
        scroll_count = 0
        max_scrolls = 20  # Limite pour éviter une boucle infinie
        previous_height = 0
        no_change_counter = 0
        
        while scroll_count < max_scrolls:
            # Scroll en bas de la page
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Attendre le chargement de nouveaux éléments
            await page.wait_for_timeout(1500)
            
            # Vérifier si de nouveaux matchs sont apparus
            current_height = await page.evaluate('document.body.scrollHeight')
            
            if current_height == previous_height:
                no_change_counter += 1
                if no_change_counter >= 3:
                    print("📌 Plus de nouveaux matchs chargés, arrêt du scroll")
                    break
            else:
                no_change_counter = 0
                print(f"📜 Scroll {scroll_count + 1}: Nouveaux matchs chargés")
            
            previous_height = current_height
            scroll_count += 1
            
            # Si on a beaucoup scrollé, vérifier si on est en bas
            if scroll_count >= max_scrolls - 1:
                # Un dernier scroll pour être sûr
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)
                break
        
        # Remonter légèrement pour faciliter l'extraction
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await page.wait_for_timeout(1000)
        
        print(f"✅ Scroll terminé: {scroll_count} scrolls effectués")
    
    async def extract_all_matches(self, page):
        """Extraire tous les matchs avec leurs IDs"""
        print("📊 Extraction des données des matchs...")
        
        matches = []
        match_ids = set()
        
        # Méthode 1: Extraire depuis les données JSON (plus fiable)
        try:
            json_data = await page.evaluate("""() => {
                // Récupérer les données JSON
                if (window.__RCP) {
                    const firstKey = Object.keys(window.__RCP)[0];
                    if (firstKey && window.__RCP[firstKey]['games-live']) {
                        return window.__RCP[firstKey]['games-live'];
                    }
                }
                return null;
            }""")
            
            if json_data and len(json_data) > 0:
                print(f"✅ {len(json_data)} matchs trouvés dans les données JSON")
                for match in json_data:
                    match_data = {
                        'id': match.get('id'),
                        'mainGameId': match.get('mainGameId'),
                        'sportId': match.get('sportId'),
                        'champId': match.get('champId'),
                        'countryId': match.get('countryId'),
                        'sportName': match.get('sportName'),
                        'champName': match.get('champName'),
                        'firstOpponentName': match.get('firstOpponentName'),
                        'secondOpponentName': match.get('secondOpponentName'),
                        'firstOpponentLogo': match.get('firstOpponentLogoFileNames', [''])[0] if match.get('firstOpponentLogoFileNames') else '',
                        'secondOpponentLogo': match.get('secondOpponentLogoFileNames', [''])[0] if match.get('secondOpponentLogoFileNames') else '',
                        'startUnixTimestamp': match.get('startUnixTimestamp'),
                        'sectionType': match.get('sectionType'),
                        'isGameOver': match.get('isGameOver'),
                        'hasScores': match.get('hasScores'),
                        'gameStatus': match.get('gameStatus')
                    }
                    
                    # Ajouter les scores si disponibles
                    if match.get('unparsedScoresData'):
                        scores = match.get('unparsedScoresData', {})
                        match_data['score_home'] = scores.get('scoreOpp1')
                        match_data['score_away'] = scores.get('scoreOpp2')
                        match_data['current_period'] = scores.get('currentPeriodName')
                        match_data['time_seconds'] = scores.get('timer', {}).get('timeSec')
                    
                    matches.append(match_data)
                    match_ids.add(match_data['id'])
                
                print(f"📊 {len(matches)} matchs extraits avec succès")
                return matches
                
        except Exception as e:
            print(f"⚠️  Erreur lors de l'extraction JSON: {e}")
        
        # Méthode 2: Extraire depuis le DOM (fallback)
        print("🔄 Utilisation de la méthode DOM (fallback)...")
        
        try:
            dom_matches = await page.evaluate("""() => {
                const matchCards = document.querySelectorAll('.ui-game-card');
                const results = [];
                const seenIds = new Set();
                
                matchCards.forEach(card => {
                    // Essayer de trouver l'ID du match
                    let matchId = null;
                    const link = card.querySelector('a.ui-game-card__link');
                    if (link) {
                        const href = link.getAttribute('href');
                        const matchMatch = href.match(/\/(\d+)-[a-z-]+$/);
                        if (matchMatch) {
                            matchId = matchMatch[1];
                        }
                    }
                    
                    // Si pas d'ID trouvé, utiliser un ID généré
                    if (!matchId) {
                        const dataId = card.getAttribute('data-v-') || 
                                      card.querySelector('[data-game-id]')?.getAttribute('data-game-id');
                        if (dataId) matchId = dataId;
                    }
                    
                    // Vérifier les doublons
                    if (seenIds.has(matchId)) return;
                    seenIds.add(matchId);
                    
                    // Extraire les informations
                    const teamNames = card.querySelectorAll('.ui-game-card-scoreboard__name');
                    const scores = card.querySelectorAll('.ui-game-card-scoreboard-score');
                    const champ = card.querySelector('.ui-game-card__name');
                    const time = card.querySelector('.ui-game-card__data');
                    const period = card.querySelector('.ui-game-card__period');
                    
                    results.push({
                        id: matchId || 'unknown',
                        homeTeam: teamNames[0]?.textContent?.trim() || '',
                        awayTeam: teamNames[1]?.textContent?.trim() || '',
                        scoreHome: scores[0]?.textContent?.trim() || '0',
                        scoreAway: scores[1]?.textContent?.trim() || '0',
                        championship: champ?.textContent?.trim() || '',
                        time: time?.textContent?.trim() || '',
                        period: period?.textContent?.trim() || '',
                        isLive: card.classList.contains('ui-game-card--live')
                    });
                });
                
                return results;
            }""")
            
            if dom_matches and len(dom_matches) > 0:
                print(f"✅ {len(dom_matches)} matchs trouvés dans le DOM")
                # Convertir en format standard
                for match in dom_matches:
                    matches.append({
                        'id': match.get('id'),
                        'firstOpponentName': match.get('homeTeam'),
                        'secondOpponentName': match.get('awayTeam'),
                        'score_home': match.get('scoreHome'),
                        'score_away': match.get('scoreAway'),
                        'champName': match.get('championship'),
                        'current_period': match.get('period'),
                        'time_display': match.get('time'),
                        'is_live': match.get('isLive', True)
                    })
                
                return matches
                
        except Exception as e:
            print(f"⚠️  Erreur lors de l'extraction DOM: {e}")
        
        return matches
    
    async def setup_request_interception(self, page):
        """Intercepter les requêtes pour analyse (optionnel)"""
        async def handle_request(request):
            if 'api' in request.url or 'match' in request.url:
                print(f"🔍 Requête: {request.method} {request.url}")
        
        page.on('request', handle_request)
    
    async def save_matches(self, matches):
        """Sauvegarder les matchs en JSON"""
        if not matches:
            print("❌ Aucun match à sauvegarder")
            return
        
        # Créer le nom du fichier avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'matches_live_{timestamp}.json'
        filename_short = 'matches_live.json'  # Version sans timestamp
        
        # Sauvegarder avec timestamp
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_matches': len(matches),
                'matches': matches
            }, f, ensure_ascii=False, indent=2)
        
        # Sauvegarder la version courte
        with open(filename_short, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_matches': len(matches),
                'matches': matches
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Données sauvegardées dans: {filename}")
        print(f"✅ Données sauvegardées dans: {filename_short}")
        
        # Afficher un résumé
        print(f"\n📊 Résumé:")
        print(f"   - Total matchs: {len(matches)}")
        
        # Compter par sport
        sports = {}
        for m in matches:
            sport = m.get('sportName', 'Inconnu')
            sports[sport] = sports.get(sport, 0) + 1
        
        for sport, count in sports.items():
            print(f"   - {sport}: {count} matchs")

async def main():
    """Fonction principale"""
    print("🚀 Démarrage du scraper de matchs en direct 1xBet...")
    
    scraper = LiveMatchesScraper()
    matches = await scraper.scrape()
    
    if matches:
        print(f"\n✅ Scraping terminé avec succès! {len(matches)} matchs récupérés.")
        # Afficher les 5 premiers matchs
        print("\n🔍 Aperçu des 5 premiers matchs:")
        for i, match in enumerate(matches[:5]):
            print(f"   {i+1}. {match.get('firstOpponentName', '?')} vs {match.get('secondOpponentName', '?')} "
                  f"({match.get('champName', 'Championnat inconnu')})")
    else:
        print("\n❌ Aucun match récupéré. Vérifiez la connexion ou la structure du site.")

if __name__ == "__main__":
    asyncio.run(main())