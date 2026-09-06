#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

# Récupération des variables d'environnement
MAX_SCROLLS = int(os.environ.get('MAX_SCROLLS', '20'))
HEADLESS = os.environ.get('HEADLESS', 'true').lower() == 'true'

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
        self.max_retries = 3
        self.timeout = 60000
        self.max_scrolls = MAX_SCROLLS
        
    async def scrape(self):
        """Méthode principale de scraping"""
        logger.info("🚀 Démarrage du scraper de matchs en direct")
        logger.info(f"📋 Configuration: max_scrolls={self.max_scrolls}, headless={HEADLESS}")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{self.max_retries}")
                return await self._scrape_attempt()
            except Exception as e:
                logger.error(f"❌ Erreur lors de la tentative {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(5 * (attempt + 1))
        
        return []
    
    async def _scrape_attempt(self):
        """Tentative unique de scraping"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
            )
            
            try:
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
                
                logger.info("🌐 Navigation vers https://1xbet.ci/fr/live")
                await page.goto('https://1xbet.ci/fr/live', wait_until='domcontentloaded', timeout=self.timeout)
                
                await self.wait_for_page_ready(page)
                await self.scroll_to_load_all_matches(page)
                matches = await self.extract_all_matches(page)
                
                logger.info(f"✅ {len(matches)} matchs récupérés")
                await self.save_matches(matches)
                
                await browser.close()
                return matches
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du scraping: {e}")
                await browser.close()
                raise
    
    async def wait_for_page_ready(self, page):
        """Attendre que la page soit prête"""
        logger.info("⏳ Attente du chargement de la page...")
        
        try:
            await page.wait_for_selector('.ui-game-card', timeout=30000)
            logger.info("✅ Cartes de matchs chargées")
            
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            await page.wait_for_function(
                """() => {
                    return window.__RCP !== undefined && 
                           window.__RCP[Object.keys(window.__RCP)[0]] !== undefined &&
                           window.__RCP[Object.keys(window.__RCP)[0]]['games-live'] !== undefined;
                }""",
                timeout=15000
            )
            logger.info("✅ Données JSON chargées")
            
        except TimeoutError:
            logger.warning("⚠️ Timeout lors du chargement, continuation...")
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors du chargement: {e}")
    
    async def scroll_to_load_all_matches(self, page):
        """Simuler le scroll pour charger tous les matchs"""
        logger.info(f"🔄 Scroll pour charger tous les matchs (max: {self.max_scrolls})...")
        
        scroll_count = 0
        previous_height = 0
        no_change_counter = 0
        
        while scroll_count < self.max_scrolls:
            try:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(1.5)
                
                current_height = await page.evaluate('document.body.scrollHeight')
                
                if current_height == previous_height:
                    no_change_counter += 1
                    if no_change_counter >= 3:
                        logger.info("📌 Plus de nouveaux matchs chargés")
                        break
                else:
                    no_change_counter = 0
                    if scroll_count % 5 == 0:
                        logger.info(f"📜 Scroll {scroll_count + 1}: Nouveaux matchs chargés")
                
                previous_height = current_height
                scroll_count += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors du scroll: {e}")
                break
        
        try:
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors du repositionnement: {e}")
        
        logger.info(f"✅ Scroll terminé: {scroll_count} scrolls")
    
    async def extract_all_matches(self, page):
        """Extraire les matchs avec leurs IDs"""
        logger.info("📊 Extraction des données des matchs...")
        
        matches = []
        
        # Méthode 1: Depuis JSON
        try:
            json_data = await page.evaluate("""() => {
                if (window.__RCP) {
                    const firstKey = Object.keys(window.__RCP)[0];
                    if (firstKey && window.__RCP[firstKey]['games-live']) {
                        return window.__RCP[firstKey]['games-live'];
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
                
                return matches
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction JSON: {e}")
        
        # Méthode 2: Depuis le DOM
        logger.info("🔄 Utilisation de la méthode DOM (fallback)...")
        
        try:
            dom_matches = await page.evaluate("""() => {
                const matchCards = document.querySelectorAll('.ui-game-card');
                const results = [];
                const seenIds = new Set();
                
                matchCards.forEach(card => {
                    let matchId = null;
                    const link = card.querySelector('a.ui-game-card__link');
                    if (link) {
                        const href = link.getAttribute('href');
                        const matchMatch = href.match(/\\/(\\d+)-[a-z-]+$/);
                        if (matchMatch) {
                            matchId = matchMatch[1];
                        }
                    }
                    
                    if (!matchId) {
                        const dataId = card.getAttribute('data-v-') || 
                                      card.querySelector('[data-game-id]')?.getAttribute('data-game-id');
                        if (dataId) matchId = dataId;
                    }
                    
                    if (seenIds.has(matchId)) return;
                    seenIds.add(matchId);
                    
                    const teamNames = card.querySelectorAll('.ui-game-card-scoreboard__name');
                    const scores = card.querySelectorAll('.ui-game-card-scoreboard-score');
                    const champ = card.querySelector('.ui-game-card__name');
                    const time = card.querySelector('.ui-game-card__data');
                    const period = card.querySelector('.ui-game-card__period');
                    const isLive = card.classList.contains('ui-game-card--live');
                    
                    results.push({
                        id: matchId || 'unknown',
                        homeTeam: teamNames[0]?.textContent?.trim() || '',
                        awayTeam: teamNames[1]?.textContent?.trim() || '',
                        scoreHome: scores[0]?.textContent?.trim() || '0',
                        scoreAway: scores[1]?.textContent?.trim() || '0',
                        championship: champ?.textContent?.trim() || '',
                        time: time?.textContent?.trim() || '',
                        period: period?.textContent?.trim() || '',
                        isLive: isLive
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
            sys.exit(0)
        else:
            logger.error("❌ Aucun match récupéré.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())