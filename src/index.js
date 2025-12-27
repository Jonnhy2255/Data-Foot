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
   1️⃣ Lister les ligues disponibles (nom + id)
      Le JSON n'est pas exposé côté client
   ========================================================= */
export function listLeagues() {
  if (!fs.existsSync(leagueIdsPath)) {
    throw new Error('league-ids.json introuvable');
  }

  const leagueIds = readJSON(leagueIdsPath);

  return Object.entries(leagueIds).map(([name, data]) => ({
    name,
    id: data.id
  }));
}

/* =========================================================
   2️⃣ Récupérer les N derniers matchs d’une ligue
      ⚠️ Le serveur lit le champ "json" côté serveur
   ========================================================= */
export function getLastMatches(leagueId, n = 5) {
  if (!fs.existsSync(leagueIdsPath)) {
    throw new Error('league-ids.json introuvable');
  }

  const leagueIds = readJSON(leagueIdsPath);

  // Cherche la ligue par id
  const leagueEntry = Object.values(leagueIds).find(l => l.id === leagueId);
  if (!leagueEntry) {
    throw new Error(`Aucune ligue trouvée pour l'id ${leagueId}`);
  }

  const fileName = leagueEntry.json;
  if (!fileName) {
    throw new Error(`Aucun fichier JSON associé à l'id ${leagueId}`);
  }

  const filePath = path.join(leaguesDir, fileName);
  if (!fs.existsSync(filePath)) {
    throw new Error(`Fichier JSON introuvable côté serveur : ${fileName}`);
  }

  const matches = readJSON(filePath);
  if (!Array.isArray(matches)) {
    throw new Error('Format JSON invalide (attendu: tableau)');
  }

  return matches.slice(-n).reverse(); // les derniers n matchs
}

/* =========================================================
   🔧 Test direct en CLI
   ========================================================= */
if (process.argv[1] === __filename) {
  console.log('\n📋 Ligues disponibles :');
  console.table(listLeagues());

  console.log('\n⚽ 2 derniers matchs – LaLiga');
  console.table(getLastMatches('esp.1', 2));
}