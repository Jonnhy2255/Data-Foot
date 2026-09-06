const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

class LiveMatchesScraper {
    constructor() {
        this.matchesData = [];
        this.processedIds = new Set();
    }

    async scrape() {
        console.log('🚀 Démarrage du scraper...');
        
        const browser = await chromium.launch({
            headless: false,
            args: [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        });

        const context = await browser.newContext({
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale: 'fr-FR',
            timezoneId: 'Europe/Paris',
            extraHttpHeaders: {
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
        });

        const page = await context.newPage();

        try {
            console.log('🌐 Navigation vers la page...');
            await page.goto('https://1xbet.ci/fr/live', { waitUntil: 'domcontentloaded' });

            // Attendre le chargement
            await this.waitForPageReady(page);

            // Scroll pour charger tous les matchs
            await this.scrollToLoadAllMatches(page);

            // Extraire les données
            const matches = await this.extractAllMatches(page);

            // Sauvegarder
            await this.saveMatches(matches);

            await browser.close();
            return matches;

        } catch (error) {
            console.error('❌ Erreur:', error);
            await browser.close();
            throw error;
        }
    }

    async waitForPageReady(page) {
        console.log('⏳ Attente du chargement...');
        
        try {
            await page.waitForSelector('.ui-game-card', { timeout: 30000 });
            console.log('✅ Cartes de matchs chargées');
            
            await page.waitForLoadState('networkidle');
            
            // Attendre les données JSON
            await page.waitForFunction(
                `() => {
                    return window.__RCP !== undefined && 
                           window.__RCP[Object.keys(window.__RCP)[0]] !== undefined &&
                           window.__RCP[Object.keys(window.__RCP)[0]]['games-live'] !== undefined;
                }`,
                { timeout: 15000 }
            );
            console.log('✅ Données JSON chargées');
            
        } catch (error) {
            console.log('⚠️ Timeout partiel, continuation...');
        }
    }

    async scrollToLoadAllMatches(page) {
        console.log('🔄 Scroll pour charger tous les matchs...');
        
        let scrollCount = 0;
        const maxScrolls = 20;
        let previousHeight = 0;
        let noChangeCounter = 0;

        while (scrollCount < maxScrolls) {
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
            await page.waitForTimeout(1500);

            const currentHeight = await page.evaluate('document.body.scrollHeight');
            
            if (currentHeight === previousHeight) {
                noChangeCounter++;
                if (noChangeCounter >= 3) {
                    console.log('📌 Plus de nouveaux matchs, arrêt du scroll');
                    break;
                }
            } else {
                noChangeCounter = 0;
                console.log(`📜 Scroll ${scrollCount + 1}: Nouveaux matchs chargés`);
            }

            previousHeight = currentHeight;
            scrollCount++;
        }

        // Remonter légèrement
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)');
        await page.waitForTimeout(1000);
        
        console.log(`✅ Scroll terminé: ${scrollCount} scrolls`);
    }

    async extractAllMatches(page) {
        console.log('📊 Extraction des matchs...');
        
        // Méthode 1: Depuis JSON
        try {
            const jsonData = await page.evaluate(`() => {
                if (window.__RCP) {
                    const firstKey = Object.keys(window.__RCP)[0];
                    if (firstKey && window.__RCP[firstKey]['games-live']) {
                        return window.__RCP[firstKey]['games-live'];
                    }
                }
                return null;
            }`);

            if (jsonData && jsonData.length > 0) {
                console.log(`✅ ${jsonData.length} matchs trouvés dans le JSON`);
                const matches = jsonData.map(match => ({
                    id: match.id,
                    mainGameId: match.mainGameId,
                    sportId: match.sportId,
                    champId: match.champId,
                    countryId: match.countryId,
                    sportName: match.sportName,
                    champName: match.champName,
                    firstOpponentName: match.firstOpponentName,
                    secondOpponentName: match.secondOpponentName,
                    score_home: match.unparsedScoresData?.scoreOpp1 || 0,
                    score_away: match.unparsedScoresData?.scoreOpp2 || 0,
                    current_period: match.unparsedScoresData?.currentPeriodName || '',
                    time_seconds: match.unparsedScoresData?.timer?.timeSec || 0,
                    isGameOver: match.isGameOver || false,
                    startTimestamp: match.startUnixTimestamp
                }));
                return matches;
            }
        } catch (error) {
            console.log('⚠️ Erreur extraction JSON:', error.message);
        }

        // Méthode 2: Depuis le DOM
        console.log('🔄 Utilisation de la méthode DOM (fallback)...');
        try {
            const domMatches = await page.evaluate(`() => {
                const matchCards = document.querySelectorAll('.ui-game-card');
                const results = [];
                const seenIds = new Set();

                matchCards.forEach(card => {
                    // Trouver l'ID
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
            }`);

            if (domMatches && domMatches.length > 0) {
                console.log(`✅ ${domMatches.length} matchs trouvés dans le DOM`);
                return domMatches;
            }
        } catch (error) {
            console.log('⚠️ Erreur extraction DOM:', error.message);
        }

        return [];
    }

    async saveMatches(matches) {
        if (!matches || matches.length === 0) {
            console.log('❌ Aucun match à sauvegarder');
            return;
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const filename = `matches_live_${timestamp}.json`;
        const filenameShort = 'matches_live.json';

        const data = {
            scraped_at: new Date().toISOString(),
            total_matches: matches.length,
            matches: matches
        };

        fs.writeFileSync(filename, JSON.stringify(data, null, 2), 'utf8');
        fs.writeFileSync(filenameShort, JSON.stringify(data, null, 2), 'utf8');

        console.log(`✅ Données sauvegardées dans: ${filename}`);
        console.log(`✅ Données sauvegardées dans: ${filenameShort}`);
        
        // Résumé
        console.log(`\n📊 Résumé:`);
        console.log(`   - Total matchs: ${matches.length}`);
        
        const sports = {};
        matches.forEach(m => {
            const sport = m.sportName || 'Inconnu';
            sports[sport] = (sports[sport] || 0) + 1;
        });
        
        Object.entries(sports).forEach(([sport, count]) => {
            console.log(`   - ${sport}: ${count} matchs`);
        });
    }
}

// Exécution
async function main() {
    const scraper = new LiveMatchesScraper();
    try {
        const matches = await scraper.scrape();
        console.log(`\n✅ Scraping terminé! ${matches.length} matchs récupérés.`);
    } catch (error) {
        console.error('❌ Erreur fatale:', error);
    }
}

main();