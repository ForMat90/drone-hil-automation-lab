const fs = require("fs");
const path = require("path");

const FILE = path.join(__dirname, "..", ".run", "control-url.txt");

function saveControlUrl(url) {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.writeFileSync(FILE, url, "utf8");
}

function getControlUrl() {
  try {
    const value = fs.readFileSync(FILE, "utf8").trim();
    if (value) {
      return value.replace(/\/$/, "");
    }
  } catch {
    /* use fallback */
  }
  return (process.env.DRONE_CONTROL_URL || "http://127.0.0.1:8765").replace(/\/$/, "");
}

module.exports = { getControlUrl, saveControlUrl };
