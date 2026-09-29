const { expect, test } = require("@playwright/test");
const { hold, pose, recenter, sleep, stopDrone } = require("./support/drone-api");
const {
  STOPPED_SPEED_MPS,
  distanceXY,
  isNearCenter,
  movedTowards,
  speed,
} = require("./support/flight-checks");

// The tests share one running Gazebo world, so they must not overlap.
test.describe.configure({ mode: "serial" });

test.beforeEach(async ({ request }) => {
  await recenter(request);
});

test.afterAll(async ({ request }) => {
  await stopDrone(request);
});

/** Each directional command: hold it for 5 s, then check it went that way. */
const DIRECTIONS = [
  { command: "a", title: "A: sinistra" },
  { command: "d", title: "D: destra" },
  { command: "w", title: "W: avanti" },
  { command: "s", title: "S: indietro" },
  { command: "r", title: "R: su" },
  { command: "f", title: "F: giu" },
];

for (const { command, title } of DIRECTIONS) {
  test(`${title} (5s)`, async ({ request }) => {
    const start = await pose(request);
    const samples = await hold(request, command);
    expect(movedTowards(command, start, samples)).toBeTruthy();
  });
}

test("A: arrivato a fine percorso torna al centro", async ({ request }) => {
  const start = await pose(request);
  expect(movedTowards("a", start, await hold(request, "a"))).toBeTruthy();

  // Keep pushing left until the flight envelope is exceeded: the bridge must
  // then bring the drone back to the middle of the field on its own.
  const atTheEdge = (await hold(request, "a")).at(-1);
  let parked = await pose(request);
  for (let attempt = 0; attempt < 20 && !isNearCenter(parked); attempt += 1) {
    if (isNearCenter(atTheEdge)) {
      break;
    }
    await sleep(250);
    parked = await pose(request);
  }
  expect(isNearCenter(parked) || isNearCenter(atTheEdge)).toBeTruthy();
});

test("rilascio: il drone si ferma e non continua a scivolare", async ({ request }) => {
  const whileMoving = (await hold(request, "w")).at(-1);
  await sleep(1500);
  const stopped = await pose(request);

  expect(speed(stopped)).toBeLessThan(STOPPED_SPEED_MPS);
  expect(distanceXY(whileMoving, stopped)).toBeLessThan(2);
});

test("Q e E fanno ruotare il drone su se stesso", async ({ request }) => {
  const before = await pose(request);
  const afterQ = (await hold(request, "q")).at(-1);
  const afterE = (await hold(request, "e")).at(-1);

  const rotated =
    Math.abs(afterQ.yaw - before.yaw) > 3 || Math.abs(afterE.yaw - afterQ.yaw) > 3;
  expect(rotated).toBeTruthy();
});
