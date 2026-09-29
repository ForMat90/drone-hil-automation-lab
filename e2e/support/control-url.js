// The bridge URL is discovered in globalSetup, which runs in another process
// than the tests, so it is handed over through a file.
const fs = require("fs");
const path = require("path");

const FILE = path.join(__dirname, "..", "..", ".run", "control-url.txt");
const FALLBACK = "http://127.0.0.1:8765";

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
    /* not discovered yet: use the default */
  }
  return (process.env.DRONE_CONTROL_URL || FALLBACK).replace(/\/$/, "");
}

module.exports = { getControlUrl, saveControlUrl };
