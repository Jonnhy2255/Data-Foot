const fs = require("fs");
const path = require("path");

function listLeagues() {
  const dataDir = path.join(__dirname, "..", "data");
  return fs.readdirSync(dataDir).filter(file => file.endsWith(".json"));
}

module.exports = { listLeagues };

