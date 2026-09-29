const { expect, test } = require("@playwright/test");
const { HOLD_MS, hold, pose, resetWorld, sleep, stopDrone } = require("./drone-api");

const AXIS = {
  a: { axis: "y", sign: 1 },
  d: { axis: "y", sign: -1 },
  w: { axis: "x", sign: 1 },
  s: { axis: "x", sign: -1 },
  r: { axis: "z", sign: 1 },
  f: { axis: "z", sign: -1 },
};

function moved(start, samples, command, minimum = 0.25) {
  const { axis, sign } = AXIS[command];
  return samples.some((sample) => sign * (sample[axis] - start[axis]) >= minimum);
}

function nearCenter(sample) {
  return Math.abs(sample.x) <= 1.25 && Math.abs(sample.y) <= 1.25;
}

test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ request }) => {
  await resetWorld(request);
});

test.afterAll(async ({ request }) => {
  await stopDrone(request);
});

test("A: sinistra 5s e ritorno al centro", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "a", HOLD_MS);
  expect(moved(start, samples, "a")).toBeTruthy();

  const towardEdge = await hold(request, "a", HOLD_MS);
  const last = towardEdge.at(-1);
  let parked = await pose(request);
  for (let i = 0; i < 20; i += 1) {
    if (nearCenter(parked) || (last && nearCenter(last))) {
      break;
    }
    await sleep(250);
    parked = await pose(request);
  }
  expect(nearCenter(parked) || (last && nearCenter(last))).toBeTruthy();
});

test("D: destra 5s", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "d", HOLD_MS);
  expect(moved(start, samples, "d")).toBeTruthy();
});

test("W: avanti 5s", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "w", HOLD_MS);
  expect(moved(start, samples, "w")).toBeTruthy();
});

test("S: indietro 5s", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "s", HOLD_MS);
  expect(moved(start, samples, "s")).toBeTruthy();
});

test("R: su 5s", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "r", HOLD_MS);
  expect(moved(start, samples, "r", 0.15)).toBeTruthy();
});

test("F: giu 5s", async ({ request }) => {
  const start = await pose(request);
  const samples = await hold(request, "f", HOLD_MS);
  expect(moved(start, samples, "f", 0.15)).toBeTruthy();
});

test("rilascio: il drone si ferma", async ({ request }) => {
  const samples = await hold(request, "w", HOLD_MS);
  const moving = samples.at(-1);
  await sleep(1500);
  const stopped = await pose(request);
  const speed = Math.hypot(stopped.vx, stopped.vy, stopped.vz);
  expect(speed).toBeLessThan(0.45);
  expect(Math.hypot(stopped.x - moving.x, stopped.y - moving.y)).toBeLessThan(2);
});

test("Q e E cambiano lo yaw", async ({ request }) => {
  const before = await pose(request);
  const afterQ = (await hold(request, "q", HOLD_MS)).at(-1);
  const afterE = (await hold(request, "e", HOLD_MS)).at(-1);
  const changed =
    Math.abs(afterQ.yaw - before.yaw) > 3 || Math.abs(afterE.yaw - afterQ.yaw) > 3;
  expect(changed).toBeTruthy();
});
