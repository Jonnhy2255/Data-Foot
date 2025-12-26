import fs from 'fs';
import path from 'path';

// Chemin vers le dossier contenant les fichiers JSON
const dataDir = path.resolve('./data');

/**
 * Liste toutes les ligues disponibles dans le dossier data/
 * @returns {string[]} Tableau des noms de ligues
 */
export function listLeagues() {
  try {
    const files = fs.readdirSync(dataDir);

    // Filtrer les fichiers JSON et retirer l'extension
    const leagues = files
      .filter(file => file.endsWith('.json'))
      .map(file => file.replace('.json', ''));

    return leagues;
  } catch (err) {
    console.error('Erreur lors de la lecture du dossier data:', err);
    return [];
  }
}

// Exemple d'utilisation si exécuté directement
if (import.meta.url === process.argv[1] || import.meta.url === `file://${process.argv[1]}`) {
  console.log('Ligues disponibles :', listLeagues());
}