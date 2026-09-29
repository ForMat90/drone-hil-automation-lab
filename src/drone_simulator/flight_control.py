"""Shared, ROS-free flight limits and command mapping for the Gazebo drone."""

from __future__ import annotations

import math

# Hold-style control (HTTP bridge, Playwright tests): a force is applied for as
# long as the command is held, so it must be slow enough that a 5 s hold stays
# inside the fence and stays visible.
FORCE_XY = 2.5
FORCE_Z = 3.0
YAW_TORQUE = 0.5
BRAKE_GAIN = 8.0
MAX_SPEED_XY = 0.7
MAX_SPEED_Z = 0.45
MAX_SANE_SPEED = 6.0

# Tap-style control (keyboard): every keypress is a single short impulse, so it
# needs a much bigger push than the hold-style forces above.
MANUAL_IMPULSE_XY = 18.0
MANUAL_IMPULSE_Z = 24.0
MANUAL_YAW_TORQUE = 1.5

# Flight envelope: smaller than the fence you see in Gazebo, so the drone can be
# recovered before it gets hard to see or control.
MAX_X = 9.0
MAX_Y = 7.0
MIN_Z = 1.0
MAX_Z = 8.0
SPAWN_ALTITUDE_M = 3.0
CENTER_TOLERANCE_M = 1.25
CENTER_TOLERANCE_Z = 1.5

# force x, y, z, yaw torque
COMMAND_WRENCH: dict[str, tuple[float, float, float, float]] = {
    "w": (FORCE_XY, 0.0, 0.0, 0.0),
    "s": (-FORCE_XY, 0.0, 0.0, 0.0),
    "a": (0.0, FORCE_XY, 0.0, 0.0),
    "d": (0.0, -FORCE_XY, 0.0, 0.0),
    "r": (0.0, 0.0, FORCE_Z, 0.0),
    "f": (0.0, 0.0, -FORCE_Z, 0.0),
    "q": (0.0, 0.0, 0.0, YAW_TORQUE),
    "e": (0.0, 0.0, 0.0, -YAW_TORQUE),
}

MANUAL_WRENCH: dict[str, tuple[float, float, float, float]] = {
    "w": (MANUAL_IMPULSE_XY, 0.0, 0.0, 0.0),
    "s": (-MANUAL_IMPULSE_XY, 0.0, 0.0, 0.0),
    "a": (0.0, MANUAL_IMPULSE_XY, 0.0, 0.0),
    "d": (0.0, -MANUAL_IMPULSE_XY, 0.0, 0.0),
    "r": (0.0, 0.0, MANUAL_IMPULSE_Z, 0.0),
    "f": (0.0, 0.0, -MANUAL_IMPULSE_Z, 0.0),
    "q": (0.0, 0.0, 0.0, MANUAL_YAW_TORQUE),
    "e": (0.0, 0.0, 0.0, -MANUAL_YAW_TORQUE),
}


def finite_number(value: float, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if math.isnan(number) or math.isinf(number) or abs(number) > 1_000_000:
        return fallback
    return number


def sane_velocity(vx: float, vy: float, vz: float) -> tuple[float, float, float]:
    values = []
    for speed in (vx, vy, vz):
        cleaned = finite_number(speed)
        if abs(cleaned) > MAX_SANE_SPEED:
            cleaned = 0.0
        values.append(cleaned)
    return values[0], values[1], values[2]


def command_wrench(command: str | None) -> tuple[float, float, float, float]:
    if not command:
        return (0.0, 0.0, 0.0, 0.0)
    return COMMAND_WRENCH.get(command.lower(), (0.0, 0.0, 0.0, 0.0))


def brake_wrench(vx: float, vy: float, vz: float) -> tuple[float, float, float, float]:
    """Opposing force so the drone stops when the stick is released."""
    return (-BRAKE_GAIN * vx, -BRAKE_GAIN * vy, -BRAKE_GAIN * vz, 0.0)


def clamp_hold_wrench(
    command: str | None,
    vx: float,
    vy: float,
    vz: float,
) -> tuple[float, float, float, float]:
    """Apply a small command force, but cap speed so the drone stays flyable."""
    vx, vy, vz = sane_velocity(vx, vy, vz)
    if not command:
        return brake_wrench(vx, vy, vz)
    fx, fy, fz, tz = command_wrench(command)
    if abs(vx) >= MAX_SPEED_XY and fx * vx > 0:
        fx = 0.0
    if abs(vy) >= MAX_SPEED_XY and fy * vy > 0:
        fy = 0.0
    if abs(vz) >= MAX_SPEED_Z and fz * vz > 0:
        fz = 0.0
    return (fx, fy, fz, tz)


def is_outside_area(x: float, y: float, z: float) -> bool:
    x, y, z = finite_number(x), finite_number(y), finite_number(z, SPAWN_ALTITUDE_M)
    return abs(x) > MAX_X or abs(y) > MAX_Y or z < MIN_Z or z > MAX_Z


def is_near_center(x: float, y: float, z: float | None = None) -> bool:
    near_xy = abs(x) <= CENTER_TOLERANCE_M and abs(y) <= CENTER_TOLERANCE_M
    if z is None:
        return near_xy
    return near_xy and abs(z - SPAWN_ALTITUDE_M) <= CENTER_TOLERANCE_Z
