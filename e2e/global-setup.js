const fs = require("fs");
const http = require("http");
const path = require("path");
const { execSync, spawn } = require("child_process");
const { saveControlUrl } = require("./control-url");

const ROOT = path.join(__dirname, "..");
const DISTRO = "Ubuntu-22.04";

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

function candidateUrls() {
  const urls = ["http://127.0.0.1:8765", "http://localhost:8765"];
  try {
    const ip = execSync(`wsl.exe -d ${DISTRO} -- hostname -I`, { encoding: "utf8" })
      .trim()
      .split(/\s+/)
      .find((part) => part && !part.startsWith("::"));
    if (ip) {
      urls.push(`http://${ip}:8765`);
    }
  } catch {
    /* WSL IP optional */
  }
  return urls;
}

async function findControl() {
  for (const url of candidateUrls()) {
    if (await poseReady(url)) {
      return url;
    }
  }
  return null;
}

function startWebControl() {
  const linuxRepo = windowsToWsl(ROOT);
  const logDir = path.join(ROOT, ".run");
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, "web_control.log"), "a");
  const child = spawn(
    "wsl.exe",
    [
      "-d",
      DISTRO,
      "--",
      "bash",
      "-lc",
      `source /opt/ros/humble/setup.bash; python3 -u '${linuxRepo}/scripts/drone_web_control.py'`,
    ],
    {
      cwd: ROOT,
      detached: true,
      stdio: ["ignore", log, log],
      windowsHide: true,
    }
  );
  child.unref();
}

module.exports = async function globalSetup() {
  let url = await findControl();
  if (!url) {
    startWebControl();
    const deadline = Date.now() + 45000;
    while (Date.now() < deadline) {
      url = await findControl();
      if (url) {
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  if (!url) {
    throw new Error("Gazebo deve essere aperto. Poi: npx playwright test");
  }
  saveControlUrl(url);
  process.env.DRONE_CONTROL_URL = url;
};
