// Domain rules used by the assertions. A physics simulation never repeats the
// exact same numbers, so the checks look at a direction of travel instead.
// These thresholds mirror src/drone_simulator/flight_control.py.
const CENTER_TOLERANCE_M = 1.25;
const MIN_TRAVEL_M = 0.25;
const MIN_TRAVEL_Z_M = 0.15;
const STOPPED_SPEED_MPS = 0.45;

const AXIS = {
  a: { axis: "y", sign: 1 },
  d: { axis: "y", sign: -1 },
  w: { axis: "x", sign: 1 },
  s: { axis: "x", sign: -1 },
  r: { axis: "z", sign: 1 },
  f: { axis: "z", sign: -1 },
};

/**
 * True when at least one sample taken during the hold is far enough from the
 * starting point, in the direction the command promised. Samples are checked
 * one by one because the drone may be recentred halfway through.
 */
function movedTowards(command, start, samples) {
  const { axis, sign } = AXIS[command];
  const minimum = axis === "z" ? MIN_TRAVEL_Z_M : MIN_TRAVEL_M;
  return samples.some((sample) => sign * (sample[axis] - start[axis]) >= minimum);
}

function isNearCenter(sample) {
  return Math.abs(sample.x) <= CENTER_TOLERANCE_M && Math.abs(sample.y) <= CENTER_TOLERANCE_M;
}

function speed(sample) {
  return Math.hypot(sample.vx, sample.vy, sample.vz);
}

function distanceXY(from, to) {
  return Math.hypot(to.x - from.x, to.y - from.y);
}

module.exports = {
  CENTER_TOLERANCE_M,
  STOPPED_SPEED_MPS,
  distanceXY,
  isNearCenter,
  movedTowards,
  speed,
};
