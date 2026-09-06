#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class LiveMatchesScraper:
    def __init__(self):
        self.matches_data = []
        self.processed_ids = set()
        self.max_retries = 2
        self.timeout = 90000  # 90 secondes
        
    async def scrape(self):
        """Méthode principale de scraping avec gestion d'erreurs"""
        logger.info("🚀 Démarrage du scraper de matchs en direct")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{self.max_retries}")
                return await self._scrape_attempt()
            except Exception as e:
                logger.error(f"❌ Erreur lors de la tentative {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(10 * (attempt + 1))
        
        return []
    
    async def _scrape_attempt(self):
        """Tentative unique de scraping"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-dev-tools',
                    '--no-zygote',
                    '--single-process',
                    '--disable-logging',
                    '--log-level=3',
                    '--disable-extensions',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--mute-audio',
                    '--no-default-browser-check',
                    '--no-first-run',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            try:
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
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
                
                # Intercepter les requêtes pour déboguer
                async def log_request(request):
                    if 'api' in request.url.lower() or 'match' in request.url.lower():
                        logger.debug(f"🔍 Requête: {request.url}")
                
                page.on('request', log_request)
                
                logger.info("🌐 Navigation vers https://1xbet.ci/fr/live")
                
                # Aller sur la page avec plus de temps
                await page.goto('https://1xbet.ci/fr/live', wait_until='commit', timeout=self.timeout)
                
                # Attendre que le DOM soit chargé
                await page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # Faire un premier scroll
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
                await asyncio.sleep(2)
                
                await self.wait_for_page_ready(page)
                await self.scroll_to_load_all_matches(page)
                matches = await self.extract_all_matches(page)
                
                logger.info(f"✅ {len(matches)} matchs récupérés")
                
                if matches:
                    await self.save_matches(matches)
                else:
                    # Essayer une méthode alternative
                    logger.info("🔄 Tentative de récupération depuis le HTML direct...")
                    html_matches = await self.extract_from_html(page)
                    if html_matches:
                        await self.save_matches(html_matches)
                        matches = html_matches
                
                await browser.close()
                return matches
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du scraping: {e}")
                await browser.close()
                raise
    
    async def wait_for_page_ready(self, page):
        """Attendre que la page soit prête"""
        logger.info("⏳ Attente du chargement de la page...")
        
        # Attendre que le corps soit chargé
        await page.wait_for_selector('body', timeout=30000)
        
        # Attendre les éléments principaux
        selectors = [
            '.ui-game-card',
            '.betting-layout',
            '.sports-menu-tabs',
            '.dashboard-sport-item'
        ]
        
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                logger.info(f"✅ Sélecteur trouvé: {selector}")
                break
            except:
                continue
        
        # Attendre un peu pour que le JS s'exécute
        await asyncio.sleep(3)
        
        # Vérifier la présence de __RCP
        has_rcp = await page.evaluate("""() => {
            return window.__RCP !== undefined;
        }""")
        
        if has_rcp:
            logger.info("✅ window.__RCP présent")
        else:
            logger.warning("⚠️ window.__RCP non trouvé")
        
        # Faire un scroll pour déclencher le chargement
        await page.evaluate('window.scrollTo(0, 100)')
        await asyncio.sleep(1)
    
    async def scroll_to_load_all_matches(self, page):
        """Simuler le scroll pour charger tous les matchs"""
        logger.info("🔄 Scroll pour charger tous les matchs...")
        
        scroll_count = 0
        max_scrolls = 15
        previous_count = 0
        
        for scroll_count in range(max_scrolls):
            try:
                # Scroll
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                
                # Compter les matchs visibles
                current_count = await page.evaluate("""() => {
                    return document.querySelectorAll('.ui-game-card').length;
                }""")
                
                logger.info(f"📊 Scroll {scroll_count + 1}: {current_count} matchs visibles")
                
                if current_count == previous_count and scroll_count > 2:
                    logger.info("📌 Plus de nouveaux matchs chargés")
                    break
                
                previous_count = current_count
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du scroll: {e}")
                break
        
        # Remonter en haut
        await page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(1)
        
        logger.info(f"✅ Scroll terminé: {scroll_count + 1} scrolls")
    
    async def extract_all_matches(self, page):
        """Extraire les matchs avec leurs IDs"""
        logger.info("📊 Extraction des données des matchs...")
        
        matches = []
        
        # Méthode 1: Depuis JSON
        try:
            json_data = await page.evaluate("""() => {
                if (window.__RCP) {
                    const keys = Object.keys(window.__RCP);
                    for (const key of keys) {
                        if (window.__RCP[key] && window.__RCP[key]['games-live']) {
                            return window.__RCP[key]['games-live'];
                        }
                    }
                }
                return null;
            }""")
            
            if json_data and len(json_data) > 0:
                logger.info(f"✅ {len(json_data)} matchs trouvés dans le JSON")
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
                    
                    if match.get('unparsedScoresData'):
                        scores = match.get('unparsedScoresData', {})
                        match_data['score_home'] = scores.get('scoreOpp1')
                        match_data['score_away'] = scores.get('scoreOpp2')
                        match_data['current_period'] = scores.get('currentPeriodName')
                        match_data['time_seconds'] = scores.get('timer', {}).get('timeSec')
                    
                    matches.append(match_data)
                
                if matches:
                    return matches
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction JSON: {e}")
        
        # Méthode 2: Depuis le DOM
        logger.info("🔄 Utilisation de la méthode DOM...")
        
        try:
            dom_matches = await page.evaluate("""() => {
                const matchCards = document.querySelectorAll('.ui-game-card');
                const results = [];
                const seenIds = new Set();
                
                matchCards.forEach(card => {
                    let matchId = null;
                    
                    // Chercher l'ID dans le lien
                    const link = card.querySelector('a.ui-game-card__link');
                    if (link) {
                        const href = link.getAttribute('href');
                        const matchMatch = href.match(/\\/(\\d+)-[a-z-]+$/);
                        if (matchMatch) {
                            matchId = matchMatch[1];
                        }
                    }
                    
                    // Chercher l'ID dans un attribut data
                    if (!matchId) {
                        const dataAttrs = card.querySelectorAll('[data-game-id], [data-id], [data-v-]');
                        for (const el of dataAttrs) {
                            const id = el.getAttribute('data-game-id') || el.getAttribute('data-id');
                            if (id && id.match(/^\\d+$/)) {
                                matchId = id;
                                break;
                            }
                        }
                    }
                    
                    if (!matchId) {
                        // Utiliser un ID basé sur le contenu
                        const teams = card.querySelectorAll('.ui-game-card-scoreboard__name');
                        if (teams.length >= 2) {
                            matchId = teams[0].textContent.trim() + '-' + teams[1].textContent.trim();
                        }
                    }
                    
                    if (seenIds.has(matchId)) return;
                    seenIds.add(matchId);
                    
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
                logger.info(f"✅ {len(dom_matches)} matchs trouvés dans le DOM")
                return dom_matches
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction DOM: {e}")
        
        return matches
    
    async def extract_from_html(self, page):
        """Extraire les matchs directement du HTML"""
        logger.info("📄 Extraction directe du HTML...")
        
        try:
            content = await page.content()
            
            # Chercher les données dans le HTML
            if '__RCP' in content:
                import re
                import json
                
                # Essayer d'extraire __RCP du HTML
                match = re.search(r'window\.__RCP\s*=\s*({.*?});', content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        for key in data:
                            if 'games-live' in data[key]:
                                logger.info(f"✅ {len(data[key]['games-live'])} matchs trouvés")
                                return data[key]['games-live']
                    except:
                        pass
            
            return []
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction HTML: {e}")
            return []
    
    async def _handle_response(self, response):
        """Gérer les réponses HTTP"""
        if response.status >= 400:
            logger.warning(f"⚠️ Réponse HTTP {response.status}: {response.url}")
    
    async def save_matches(self, matches):
        """Sauvegarder les matchs en JSON"""
        if not matches:
            logger.warning("❌ Aucun match à sauvegarder")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'matches_live_{timestamp}.json'
        filename_short = 'matches_live.json'
        
        data = {
            'scraped_at': datetime.now().isoformat(),
            'total_matches': len(matches),
            'matches': matches
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        with open(filename_short, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Données sauvegardées dans: {filename}")
        logger.info(f"✅ Données sauvegardées dans: {filename_short}")
        
        # Résumé
        logger.info(f"\n📊 Résumé:")
        logger.info(f"   - Total matchs: {len(matches)}")
        
        sports = {}
        for m in matches:
            sport = m.get('sportName', 'Inconnu')
            sports[sport] = sports.get(sport, 0) + 1
        
        for sport, count in sports.items():
            logger.info(f"   - {sport}: {count} matchs")

async def main():
    """Fonction principale"""
    try:
        scraper = LiveMatchesScraper()
        matches = await scraper.scrape()
        
        if matches:
            logger.info(f"\n✅ Scraping terminé avec succès! {len(matches)} matchs récupérés.")
            # Afficher les 5 premiers matchs
            logger.info("\n🔍 Aperçu des 5 premiers matchs:")
            for i, match in enumerate(matches[:5]):
                name1 = match.get('firstOpponentName', '?') or match.get('homeTeam', '?')
                name2 = match.get('secondOpponentName', '?') or match.get('awayTeam', '?')
                champ = match.get('champName', 'Championnat inconnu') or match.get('championship', 'Championnat inconnu')
                score_h = match.get('score_home', '0') or match.get('scoreHome', '0')
                score_a = match.get('score_away', '0') or match.get('scoreAway', '0')
                logger.info(f"   {i+1}. {name1} {score_h} - {score_a} {name2} ({champ})")
            
            sys.exit(0)
        else:
            logger.error("❌ Aucun match récupéré.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())