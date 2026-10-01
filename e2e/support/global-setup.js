// Before any test: find the bridge, or start it inside WSL and wait for it.
const fs = require("fs");
const http = require("http");
const path = require("path");
const { execSync, spawn } = require("child_process");
const { saveControlUrl } = require("./control-url");

const ROOT = path.join(__dirname, "..", "..");
const DISTRO = "Ubuntu-22.04";
const PORT = 8765;
const START_TIMEOUT_MS = 45000;

function windowsToWsl(winPath) {
  const resolved = path.resolve(winPath);
  const match = resolved.match(/^([A-Za-z]):[\\/](.*)$/);
  if (!match) {
    return resolved.replace(/\\/g, "/");
  }
  return `/mnt/${match[1].toLowerCase()}/${match[2].replace(/\\/g, "/")}`;
}

function poseReady(baseUrl) {
  return new Promise((resolve) => {
    const req = http.get(`${baseUrl}/api/pose`, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/** Depending on the WSL networking mode the bridge answers on localhost or on the WSL IP. */
function candidateUrls() {
  // An explicit URL wins: it is how the tests are pointed at the Docker
  // container or at a bridge running on another machine.
  const explicit = process.env.DRONE_CONTROL_URL;
  const urls = explicit ? [explicit.replace(/\/$/, "")] : [];
  urls.push(`http://127.0.0.1:${PORT}`, `http://localhost:${PORT}`);
  try {
    const ip = execSync(`wsl.exe -d ${DISTRO} -- hostname -I`, { encoding: "utf8" })
      .trim()
      .split(/\s+/)
      .find((part) => part && !part.startsWith("::"));
    if (ip) {
      urls.push(`http://${ip}:${PORT}`);
    }
  } catch {
    /* the WSL IP is a bonus, not a requirement */
  }
  return urls;
}

async function findBridge() {
  for (const url of candidateUrls()) {
    if (await poseReady(url)) {
      return url;
    }
  }
  return null;
}

function startBridge() {
  const linuxRepo = windowsToWsl(ROOT);
  const logDir = path.join(ROOT, ".run");
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, "bridge.log"), "a");
  const child = spawn(
    "wsl.exe",
    [
      "-d",
      DISTRO,
      "--",
      "bash",
      "-lc",
      // Started from src/ so "python3 -m" finds the package without touching the ROS PYTHONPATH.
      `source /opt/ros/humble/setup.bash; cd '${linuxRepo}/src'; python3 -u -m drone_simulator.ros.bridge_server`,
    ],
    { cwd: ROOT, detached: true, stdio: ["ignore", log, log], windowsHide: true }
  );
  child.unref();
}

module.exports = async function globalSetup() {
  let url = await findBridge();
  if (!url) {
    startBridge();
    const deadline = Date.now() + START_TIMEOUT_MS;
    while (!url && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      url = await findBridge();
    }
  }
  if (!url) {
    throw new Error("Gazebo deve essere aperto. Apri .\\scripts\\run_gazebo_windows.ps1, poi: npx playwright test");
  }
  saveControlUrl(url);
  process.env.DRONE_CONTROL_URL = url;
};
