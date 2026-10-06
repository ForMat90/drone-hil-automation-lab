// Keyboard flight against the Docker bridge. Gazebo stays up when this exits:
// Ctrl+C only releases the stick. The automated tests use the same bridge.
const BASE = (process.env.DRONE_CONTROL_URL || "http://127.0.0.1:8765").replace(/\/$/, "");

const KEYS = {
  w: "w",
  s: "s",
  a: "a",
  d: "d",
  r: "r",
  f: "f",
  q: "q",
  e: "e",
};

const HELP = "w/s avanti/indietro | a/d sinistra/destra | r/f su/giu | q/e yaw | x stop | Ctrl+C esci";

async function post(path, body) {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!response.ok) {
    throw new Error(`${path} ha risposto ${response.status}. Gazebo e' acceso? npm run drone:gazebo`);
  }
}

async function hold(command) {
  await post("/api/hold", { command });
}

async function release() {
  await post("/api/release", {});
}

function arg(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? null : process.argv[index + 1];
}

async function pulse(command, ms) {
  await hold(command);
  await new Promise((resolve) => setTimeout(resolve, ms));
  await release();
}

async function interactive() {
  if (!process.stdin.isTTY) {
    throw new Error("Serve un terminale interattivo. Per una spinta singola: node scripts/docker_manual.js --command a --ms 2000");
  }
  const readline = require("readline");
  readline.emitKeypressEvents(process.stdin);
  process.stdin.setRawMode(true);
  process.stdin.resume();

  let releaseTimer = null;
  const armRelease = () => {
    clearTimeout(releaseTimer);
    // Key repeat keeps this from firing while the key is held down.
    releaseTimer = setTimeout(() => {
      release().catch(() => {});
    }, 180);
  };

  console.log(HELP);
  console.log(BASE);

  process.stdin.on("keypress", (_text, key) => {
    if (!key) return;
    if (key.ctrl && key.name === "c") {
      clearTimeout(releaseTimer);
      release().finally(() => process.exit(0));
      return;
    }
    const name = (key.name || key.sequence || "").toLowerCase();
    if (name === "x") {
      clearTimeout(releaseTimer);
      release().catch((error) => console.error(error.message));
      return;
    }
    const command = KEYS[name];
    if (!command) return;
    hold(command)
      .then(armRelease)
      .catch((error) => console.error(error.message));
  });
}

async function main() {
  const command = arg("--command");
  if (command) {
    const ms = Number(arg("--ms") || 1500);
    await pulse(command, ms);
    return;
  }
  await interactive();
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
