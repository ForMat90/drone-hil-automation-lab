from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math


class DroneState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    TAKEOFF = "TAKEOFF"
    HOVER = "HOVER"
    LANDING = "LANDING"
    EMERGENCY = "EMERGENCY"


@dataclass
class Telemetry:
    state: DroneState
    altitude_m: float
    speed_mps: float
    battery_pct: float
    yaw_deg: float
    pitch_deg: float
    roll_deg: float
    motors: dict[str, float] = field(default_factory=dict)


class DroneSimulator:
    def __init__(self) -> None:
        self.state = DroneState.IDLE
        self.altitude_m = 0.0
        self.target_altitude_m = 0.0
        self.speed_mps = 0.0
        self.battery_pct = 100.0
        self.yaw_deg = 111.0
        self.pitch_deg = 0.0
        self.roll_deg = 0.0
        self.motors = {
            "front_left": 0.0,
            "front_right": 0.0,
            "rear_left": 0.0,
            "rear_right": 0.0,
        }
        self.environment = [
            {"type": "terrain", "size": (620, 140), "x": 0, "y": 0},
            {"type": "landing_pad", "x": 320, "y": 470, "radius": 90},
            {"type": "tree", "x": 140, "y": 460, "height": 42},
            {"type": "tree", "x": 260, "y": 456, "height": 48},
            {"type": "tree", "x": 440, "y": 456, "height": 44},
            {"type": "tree", "x": 545, "y": 458, "height": 47},
        ]
        self._hold_yaw = 0.0
        self._hold_climb = 0.0
        self._yaw_rate_dps = 18.0
        self._hold_climb_mps = 0.6

    def arm(self) -> bool:
        if self.state != DroneState.IDLE:
            return False
        self.state = DroneState.ARMED
        self._set_motor_power(35.0)
        return True

    def set_altitude(self, target_altitude_m: float) -> bool:
        target = max(0.0, float(target_altitude_m))
        if self.state not in {DroneState.ARMED, DroneState.TAKEOFF, DroneState.HOVER}:
            return False
        self.target_altitude_m = target
        if self.state == DroneState.ARMED:
            self.state = DroneState.TAKEOFF
            self.speed_mps = 1.8
            self._set_motor_power(75.0)
        return True

    def takeoff(self, target_altitude_m: float = 5.0) -> bool:
        if self.state != DroneState.ARMED:
            return False
        self.state = DroneState.TAKEOFF
        self.target_altitude_m = max(0.0, target_altitude_m)
        self.speed_mps = 1.8
        self._set_motor_power(75.0)
        return True

    def land(self) -> bool:
        if self.state not in {DroneState.ARMED, DroneState.TAKEOFF, DroneState.HOVER}:
            return False
        self.state = DroneState.LANDING
        self.target_altitude_m = 0.0
        self.speed_mps = 1.2
        self._set_motor_power(45.0)
        return True

    def emergency_stop(self) -> bool:
        self.state = DroneState.EMERGENCY
        self.speed_mps = 0.0
        self.target_altitude_m = 0.0
        self._set_motor_power(0.0)
        self.battery_pct = max(0.0, self.battery_pct - 5.0)
        return True

    def cancel_action(self) -> bool:
        self.stop_directional()
        self.state = DroneState.IDLE
        self.altitude_m = 0.0
        self.target_altitude_m = 0.0
        self.speed_mps = 0.0
        self.pitch_deg = 0.0
        self.roll_deg = 0.0
        self.yaw_deg = 111.0
        self._set_motor_power(0.0)
        return True

    def yaw_left(self, degrees: float) -> bool:
        self.yaw_deg = (self.yaw_deg - abs(degrees)) % 360.0
        self._set_motor_power(45.0)
        return True

    def yaw_right(self, degrees: float) -> bool:
        self.yaw_deg = (self.yaw_deg + abs(degrees)) % 360.0
        self._set_motor_power(45.0)
        return True

    def start_yaw_left(self) -> None:
        self._hold_yaw = -1.0

    def start_yaw_right(self) -> None:
        self._hold_yaw = 1.0

    def start_climb(self) -> None:
        self._hold_climb = 1.0

    def start_descend(self) -> None:
        self._hold_climb = -1.0

    def stop_directional(self) -> None:
        """Stick released: stop yaw and climb changes immediately."""
        self._hold_yaw = 0.0
        self._hold_climb = 0.0

    def move_up(self, delta_m: float = 1.0) -> bool:
        if self.state not in {DroneState.TAKEOFF, DroneState.HOVER}:
            return False
        self.target_altitude_m = max(0.0, self.target_altitude_m + float(delta_m))
        return True

    def move_down(self, delta_m: float = 1.0) -> bool:
        if self.state not in {DroneState.TAKEOFF, DroneState.HOVER}:
            return False
        self.target_altitude_m = max(0.0, self.target_altitude_m - float(delta_m))
        return True

    def pitch_forward(self, degrees: float) -> bool:
        self.pitch_deg = max(-90.0, min(90.0, degrees))
        return True

    def pitch_back(self, degrees: float) -> bool:
        self.pitch_deg = max(-90.0, min(90.0, -degrees))
        return True

    def roll_left(self, degrees: float) -> bool:
        self.roll_deg = max(-90.0, min(90.0, -degrees))
        return True

    def roll_right(self, degrees: float) -> bool:
        self.roll_deg = max(-90.0, min(90.0, degrees))
        return True

    def update(self, dt: float = 0.1) -> Telemetry:
        if self._hold_yaw:
            self.yaw_deg = (self.yaw_deg + self._hold_yaw * self._yaw_rate_dps * dt) % 360.0
        if self._hold_climb and self.state in {DroneState.TAKEOFF, DroneState.HOVER}:
            self.target_altitude_m = max(
                0.0,
                self.target_altitude_m + self._hold_climb * self._hold_climb_mps * dt,
            )

        if self.state == DroneState.TAKEOFF:
            climb_rate = 2.4
            self.altitude_m += climb_rate * dt
            self.battery_pct = max(0.0, self.battery_pct - 0.08 * dt)
            if abs(self.pitch_deg) < 12.0:
                self.pitch_deg = 12.0
            if abs(self.roll_deg) < 5.0:
                self.roll_deg = 5.0
            if self.altitude_m >= self.target_altitude_m:
                self.altitude_m = self.target_altitude_m
                self.state = DroneState.HOVER
                self.speed_mps = 0.0
                self._set_motor_power(60.0)
                self.pitch_deg *= 0.6
                self.roll_deg *= 0.6

        elif self.state == DroneState.HOVER:
            self.battery_pct = max(0.0, self.battery_pct - 0.03 * dt)
            error = self.target_altitude_m - self.altitude_m
            if abs(error) > 0.02:
                climb = max(-1.2, min(1.2, error * 2.0))
                self.altitude_m += climb * dt
                self.speed_mps = abs(climb)
            else:
                self.altitude_m = self.target_altitude_m
                self.speed_mps = 0.0
            self._set_motor_power(60.0)
            if not self._hold_yaw:
                self.pitch_deg = math.sin(self.yaw_deg / 30.0) * 2.0
                self.roll_deg = math.cos(self.yaw_deg / 28.0) * 2.0

        elif self.state == DroneState.LANDING:
            descend_rate = 2.0
            self.altitude_m = max(0.0, self.altitude_m - descend_rate * dt)
            self.battery_pct = max(0.0, self.battery_pct - 0.05 * dt)
            self.pitch_deg = -8.0
            self.roll_deg = -4.0
            if self.altitude_m <= 0.0:
                self.altitude_m = 0.0
                self.state = DroneState.IDLE
                self.speed_mps = 0.0
                self._set_motor_power(0.0)
                self.pitch_deg = 0.0
                self.roll_deg = 0.0

        elif self.state == DroneState.EMERGENCY:
            self.speed_mps = 0.0
            self._set_motor_power(0.0)
            self.pitch_deg = 18.0
            self.roll_deg = 18.0
            if self.altitude_m > 0.0:
                self.altitude_m = max(0.0, self.altitude_m - 4.0 * dt)
                if self.altitude_m == 0.0:
                    self.state = DroneState.IDLE
                    self._set_motor_power(0.0)
                    self.pitch_deg = 0.0
                    self.roll_deg = 0.0

        return self.get_telemetry()

    def get_telemetry(self) -> Telemetry:
        return Telemetry(
            state=self.state,
            altitude_m=self.altitude_m,
            speed_mps=self.speed_mps,
            battery_pct=self.battery_pct,
            yaw_deg=self.yaw_deg,
            pitch_deg=self.pitch_deg,
            roll_deg=self.roll_deg,
            motors=dict(self.motors),
        )

    def _set_motor_power(self, power: float) -> None:
        for key in self.motors:
            self.motors[key] = power
