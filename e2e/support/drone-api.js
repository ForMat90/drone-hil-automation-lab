// HTTP client for the bridge exposed by src/drone_simulator/ros/bridge_server.py.
// This is the only file that knows how to talk to the drone.
const { getControlUrl } = require("./control-url");
const { isNearCenter } = require("./flight-checks");

const HOLD_MS = 5000;
const SAMPLE_MS = 200;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pose(request) {
  const response = await request.get(`${getControlUrl()}/api/pose`);
  // Gazebo can report NaN right after a reset, which is not valid JSON.
  const text = (await response.text()).replace(/\bNaN\b/g, "0").replace(/\b-?Infinity\b/g, "0");
  return JSON.parse(text);
}

async function release(request) {
  await request.post(`${getControlUrl()}/api/release`, { data: {} });
}

/**
 * Hold a command like a finger kept on a stick, sampling the pose along the way,
 * then let it go. Returns every sample taken during the hold.
 */
async function hold(request, command, durationMs = HOLD_MS) {
  await request.post(`${getControlUrl()}/api/hold`, { data: { command } });
  const samples = [];
  for (let elapsed = 0; elapsed < durationMs; elapsed += SAMPLE_MS) {
    await sleep(SAMPLE_MS);
    samples.push(await pose(request));
  }
  await release(request);
  return samples;
}

/** Put the drone back at the center and wait until it is actually there. */
async function recenter(request) {
  await release(request);
  await request.post(`${getControlUrl()}/api/reset`, { data: {} });
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (isNearCenter(await pose(request))) {
      return;
    }
    await sleep(150);
  }
}

async function stopDrone(request) {
  await release(request);
  await request.post(`${getControlUrl()}/api/reset`, { data: {} });
}

module.exports = { HOLD_MS, hold, pose, recenter, release, sleep, stopDrone };
