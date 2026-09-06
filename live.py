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
        
    async def scrape(self):
        """Méthode principale de scraping"""
        logger.info("🚀 Démarrage du scraper de matchs en direct")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{self.max_retries}")
                result = await self._scrape_attempt()
                if result:
                    return result
            except Exception as e:
                logger.error(f"❌ Erreur tentative {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(10)
        
        return []
    
    async def _scrape_attempt(self):
        """Tentative unique de scraping"""
        async with async_playwright() as p:
            # Configuration SIMPLIFIÉE pour GitHub Actions
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
            )
            
            try:
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='fr-FR'
                )
                
                page = await context.new_page()
                
                logger.info("🌐 Navigation vers https://1xbet.ci/fr/live")
                await page.goto('https://1xbet.ci/fr/live', wait_until='domcontentloaded', timeout=60000)
                
                # Attendre que la page soit chargée
                await asyncio.sleep(3)
                
                # Extraire les données
                matches = await self.extract_all_matches(page)
                
                logger.info(f"✅ {len(matches)} matchs récupérés")
                
                if matches:
                    await self.save_matches(matches)
                
                await browser.close()
                return matches
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du scraping: {e}")
                await browser.close()
                raise
    
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
                    
                    const link = card.querySelector('a.ui-game-card__link');
                    if (link) {
                        const href = link.getAttribute('href');
                        const matchMatch = href.match(/\\/(\\d+)-[a-z-]+$/);
                        if (matchMatch) {
                            matchId = matchMatch[1];
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