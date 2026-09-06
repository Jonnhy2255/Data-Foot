#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import logging
import random
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

# Liste de User-Agents réalistes
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

class LiveMatchesScraper:
    def __init__(self):
        self.matches_data = []
        self.processed_ids = set()
        self.max_retries = 3
        self.timeout = 120000  # 120 secondes
        
    async def scrape(self):
        """Méthode principale de scraping"""
        logger.info("🚀 Démarrage du scraper de matchs en direct")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Tentative {attempt + 1}/{self.max_retries}")
                result = await self._scrape_attempt()
                if result:
                    return result
                logger.warning(f"⚠️ Tentative {attempt + 1}: aucun résultat, nouvelle tentative...")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la tentative {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                wait_time = 15 * (attempt + 1)
                logger.info(f"⏳ Attente de {wait_time} secondes avant réessayer...")
                await asyncio.sleep(wait_time)
        
        return []
    
    async def _scrape_attempt(self):
        """Tentative unique de scraping"""
        async with async_playwright() as p:
            # Sélectionner un User-Agent aléatoire
            user_agent = random.choice(USER_AGENTS)
            logger.info(f"📱 User-Agent: {user_agent[:60]}...")
            
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
                    '--disable-renderer-backgrounding',
                    '--disable-accelerated-2d-canvas',
                    '--disable-canvas-aa',
                    '--disable-2d-canvas-clip-aa',
                    '--disable-gl-drawing-for-tests',
                    '--disable-breakpad',
                    '--disable-crash-reporter',
                    '--disable-component-update',
                    '--disable-domain-reliability',
                    '--disable-ipc-flooding-protection',
                    '--disable-partial-swap',
                    '--disable-print-preview',
                    '--disable-prompt-on-repost',
                    '--disable-renderer-accessibility',
                    '--disable-speech-api',
                    '--disable-sync',
                    '--disable-voice-input',
                    '--disable-bundled-ppapi-flash',
                    '--disable-connect-backup-jobs',
                    '--disable-databases',
                    '--disable-demo-mode',
                    '--disable-device-discovery-notifications',
                    '--disable-file-system',
                    '--disable-hang-monitor',
                    '--disable-infobars',
                    '--disable-javascript-harmony-shipping',
                    '--disable-media-session-api',
                    '--disable-notifications',
                    '--disable-offer-store-unmasked-wallet-cards',
                    '--disable-password-generation',
                    '--disable-permissions-api',
                    '--disable-plugins',
                    '--disable-plugins-discovery',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-rollback',
                    '--disable-pulseaudio',
                    '--disable-quic',
                    '--disable-reading-from-canvas',
                    '--disable-remote-fonts',
                    '--disable-remote-playback-api',
                    '--disable-save-password-bubble',
                    '--disable-search-geolocation-disclosure',
                    '--disable-shared-workers',
                    '--disable-smooth-scrolling',
                    '--disable-software-compositing-fallback',
                    '--disable-speech-input',
                    '--disable-stacked-tab-strip-layout',
                    '--disable-sync-preferences',
                    '--disable-tab-for-desktop-share',
                    '--disable-threaded-animation',
                    '--disable-threaded-scrolling',
                    '--disable-top-sites',
                    '--disable-translate',
                    '--disable-tts',
                    '--disable-usb-keyboard-detect',
                    '--disable-video-capture',
                    '--disable-video-track-encrypted',
                    '--disable-web-animations',
                    '--disable-web-security',
                    '--disable-webusb',
                    '--disable-xss-auditor',
                    '--enable-features=NetworkService,NetworkServiceInProcess'
                ]
            )
            
            try:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=user_agent,
                    locale='fr-FR',
                    timezone_id='Europe/Paris',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                        'Pragma': 'no-cache',
                        'DNT': '1',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"'
                    }
                )
                
                page = await context.new_page()
                
                # Simuler un comportement humain
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['fr-FR', 'fr']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """)
                
                logger.info("🌐 Navigation vers https://1xbet.ci/fr/live")
                
                # Aller sur la page avec retry
                try:
                    await page.goto('https://1xbet.ci/fr/live', wait_until='domcontentloaded', timeout=self.timeout)
                except Exception as e:
                    logger.warning(f"⚠️ Premier chargement échoué: {e}")
                    # Réessayer avec un autre User-Agent
                    await page.reload()
                
                # Attendre que le body soit visible
                try:
                    await page.wait_for_selector('body', state='visible', timeout=30000)
                except Exception as e:
                    logger.warning(f"⚠️ Body non visible: {e}")
                    # Forcer le chargement
                    await page.evaluate('document.body.style.display = "block"')
                    await asyncio.sleep(2)
                
                # Faire quelques actions pour simuler un humain
                await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                await asyncio.sleep(1)
                
                await self.wait_for_page_ready(page)
                await self.scroll_to_load_all_matches(page)
                matches = await self.extract_all_matches(page)
                
                logger.info(f"✅ {len(matches)} matchs récupérés")
                
                if matches:
                    await self.save_matches(matches)
                else:
                    # Tentative avec l'URL alternative
                    logger.info("🔄 Tentative avec l'URL alternative...")
                    await page.goto('https://1xbet.ci/fr/', wait_until='domcontentloaded')
                    await asyncio.sleep(3)
                    await page.goto('https://1xbet.ci/fr/live', wait_until='domcontentloaded')
                    await asyncio.sleep(3)
                    
                    await self.wait_for_page_ready(page)
                    matches = await self.extract_all_matches(page)
                    if matches:
                        await self.save_matches(matches)
                
                await browser.close()
                return matches
                
            except Exception as e:
                logger.error(f"❌ Erreur lors du scraping: {e}")
                await browser.close()
                raise
    
    async def wait_for_page_ready(self, page):
        """Attendre que la page soit prête avec plusieurs stratégies"""
        logger.info("⏳ Attente du chargement de la page...")
        
        # Stratégie 1: Attendre les cartes de matchs
        try:
            await page.wait_for_selector('.ui-game-card', timeout=15000)
            logger.info("✅ Cartes de matchs chargées")
            return
        except:
            pass
        
        # Stratégie 2: Attendre n'importe quel élément de pari
        try:
            await page.wait_for_selector('.betting-layout, .sports-menu-tabs, .dashboard-sport-item', timeout=10000)
            logger.info("✅ Éléments de paris chargés")
            return
        except:
            pass
        
        # Stratégie 3: Attendre le chargement du réseau
        try:
            await page.wait_for_load_state('networkidle', timeout=15000)
            logger.info("✅ Réseau au repos")
            return
        except:
            pass
        
        # Stratégie 4: Attendre un temps fixe pour que le JS s'exécute
        logger.info("⏳ Attente de 5 secondes pour le JS...")
        await asyncio.sleep(5)
        
        # Vérifier la présence de __RCP
        has_rcp = await page.evaluate("""() => {
            return window.__RCP !== undefined;
        }""")
        
        if has_rcp:
            logger.info("✅ window.__RCP présent")
        else:
            logger.warning("⚠️ window.__RCP non trouvé")
    
    async def scroll_to_load_all_matches(self, page):
        """Simuler le scroll pour charger tous les matchs"""
        logger.info("🔄 Scroll pour charger tous les matchs...")
        
        scroll_count = 0
        max_scrolls = 10
        previous_count = 0
        
        for scroll_count in range(max_scrolls):
            try:
                # Scroll avec comportement humain
                await page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                await asyncio.sleep(random.uniform(1.5, 3))
                
                # Compter les matchs visibles
                current_count = await page.evaluate("""() => {
                    return document.querySelectorAll('.ui-game-card').length;
                }""")
                
                logger.info(f"📊 Scroll {scroll_count + 1}: {current_count} matchs visibles")
                
                if current_count == previous_count and scroll_count > 2:
                    if current_count > 0:
                        logger.info(f"📌 {current_count} matchs chargés, arrêt du scroll")
                        break
                    elif scroll_count > 5:
                        logger.info("📌 Aucun match trouvé après plusieurs scrolls")
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
                    
                    const link = card.querySelector('a.ui-game-card__link');
                    if (link) {
                        const href = link.getAttribute('href');
                        const matchMatch = href.match(/\\/(\\d+)-[a-z-]+$/);
                        if (matchMatch) {
                            matchId = matchMatch[1];
                        }
                    }
                    
                    if (!matchId) {
                        const dataId = card.querySelector('[data-game-id]')?.getAttribute('data-game-id');
                        if (dataId) matchId = dataId;
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
        
        # Méthode 3: Extraction directe du HTML
        try:
            content = await page.content()
            if '__RCP' in content:
                import re
                match = re.search(r'window\.__RCP\s*=\s*({.*?});', content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        for key in data:
                            if 'games-live' in data[key]:
                                logger.info(f"✅ {len(data[key]['games-live'])} matchs trouvés dans le HTML")
                                return data[key]['games-live']
                    except:
                        pass
        except:
            pass
        
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
            sport = m.get('sportName', 'Inconnu') or m.get('sport', 'Inconnu')
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