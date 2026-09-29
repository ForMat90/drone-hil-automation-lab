const { getControlUrl } = require("./control-url");

const HOLD_MS = 5000;
const STEP_MS = 200;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pose(request) {
  const response = await request.get(`${getControlUrl()}/api/pose`);
  const text = (await response.text()).replace(/\bNaN\b/g, "0").replace(/\b-?Infinity\b/g, "0");
  return JSON.parse(text);
}

async function hold(request, command, durationMs = HOLD_MS) {
  await request.post(`${getControlUrl()}/api/hold`, { data: { command } });
  const samples = [];
  for (let elapsed = 0; elapsed < durationMs; elapsed += STEP_MS) {
    await sleep(STEP_MS);
    samples.push(await pose(request));
  }
  await request.post(`${getControlUrl()}/api/release`, { data: {} });
  return samples;
}

async function resetWorld(request) {
  await request.post(`${getControlUrl()}/api/release`, { data: {} });
  await request.post(`${getControlUrl()}/api/reset`, { data: {} });
  for (let i = 0; i < 40; i += 1) {
    const current = await pose(request);
    if (Math.abs(current.x) < 1.25 && Math.abs(current.y) < 1.25) {
      return;
    }
    await sleep(150);
  }
}

async function stopDrone(request) {
  await request.post(`${getControlUrl()}/api/release`, { data: {} });
  await request.post(`${getControlUrl()}/api/reset`, { data: {} });
}

module.exports = { HOLD_MS, pose, hold, resetWorld, sleep, stopDrone };
