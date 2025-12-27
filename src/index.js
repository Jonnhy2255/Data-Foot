import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

/* ===== Résolution chemins ESM ===== */
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/* ===== Dossiers ===== */
const leaguesDir = path.resolve(__dirname, '../data/football/leagues');
const leagueIdsPath = path.resolve(__dirname, '../data/football/league-ids.json');

/* ===== Utils ===== */
function readJSON(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

/* =========================================================
   1️⃣ Lister les ligues disponibles (nom + id ESPN)
   ========================================================= */
export function listLeagues() {
  if (!fs.existsSync(leagueIdsPath)) {
    throw new Error('league-ids.json introuvable');
  }

  const leagueIds = readJSON(leagueIdsPath);

  return Object.entries(leagueIds).map(([name, data]) => ({
    name,
    id: data.id,
    file: data.file
  }));
}

/* =========================================================
   2️⃣ Récupérer les N derniers matchs d’une ligue
   ========================================================= */
export function getLastMatches(leagueName, n = 5) {
  if (!fs.existsSync(leagueIdsPath)) {
    throw new Error('league-ids.json introuvable');
  }

  const leagueIds = readJSON(leagueIdsPath);
  const league = leagueIds[leagueName];

  if (!league) {
    throw new Error(`Ligue inconnue : ${leagueName}`);
  }

  const leagueFile = path.join(leaguesDir, league.file);

  if (!fs.existsSync(leagueFile)) {
    throw new Error(`Fichier de matchs introuvable : ${league.file}`);
  }

  const matches = readJSON(leagueFile);

  if (!Array.isArray(matches)) {
    throw new Error('Format JSON invalide (attendu: tableau)');
  }

  // ESPN est déjà chronologique → on prend la fin
  return matches.slice(-n).reverse();
}

/* =========================================================
   🔧 Test direct en CLI
   ========================================================= */
if (process.argv[1] === __filename) {
  console.log('\n📋 Ligues disponibles :');
  console.table(listLeagues());

  console.log('\n⚽ 3 derniers matchs – Premier League');
  console.table(getLastMatches('England_Premier_League', 3));
}