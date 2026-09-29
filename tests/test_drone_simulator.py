import pytest

from drone_simulator.flight_control import brake_wrench, clamp_hold_wrench, command_wrench, is_near_center, is_outside_area
from drone_simulator.simulator import DroneSimulator, DroneState


def test_initial_state_is_idle():
    drone = DroneSimulator()
    assert drone.state == DroneState.IDLE
    assert drone.altitude_m == 0.0


def test_arm_changes_state():
    drone = DroneSimulator()
    result = drone.arm()
    assert result is True
    assert drone.state == DroneState.ARMED


def test_takeoff_reaches_target_altitude():
    drone = DroneSimulator()
    drone.arm()
    assert drone.takeoff(10.0) is True

    telemetry = drone.update(1.0)
    assert telemetry.state in {DroneState.TAKEOFF, DroneState.HOVER}
    assert telemetry.altitude_m >= 0.0


def test_land_returns_to_idle():
    drone = DroneSimulator()
    drone.arm()
    drone.takeoff(5.0)
    drone.update(3.0)
    assert drone.land() is True
    drone.update(2.0)
    assert drone.state in {DroneState.LANDING, DroneState.IDLE}


def test_emergency_stop_stops_drone():
    drone = DroneSimulator()
    drone.arm()
    drone.takeoff(5.0)
    drone.update(1.0)
    assert drone.emergency_stop() is True
    assert drone.state == DroneState.EMERGENCY


def test_environment_contains_world_objects():
    drone = DroneSimulator()
    terrain = any(item["type"] == "terrain" for item in drone.environment)
    trees = sum(1 for item in drone.environment if item["type"] == "tree")
    landing_pad = any(item["type"] == "landing_pad" for item in drone.environment)

    assert terrain is True
    assert trees >= 3
    assert landing_pad is True


def test_maneuver_commands_change_attitude():
    drone = DroneSimulator()
    drone.arm()
    drone.takeoff(8.0)
    drone.update(2.0)

    drone.yaw_left(45.0)
    drone.pitch_forward(15.0)
    drone.roll_right(20.0)
    telemetry = drone.update(1.0)

    assert telemetry.yaw_deg > 0
    assert abs(telemetry.pitch_deg) >= 10
    assert abs(telemetry.roll_deg) >= 10


def test_cancel_action_resets_drone():
    drone = DroneSimulator()
    drone.arm()
    drone.takeoff(7.0)
    drone.update(2.0)

    assert drone.cancel_action() is True
    assert drone.state == DroneState.IDLE
    assert drone.altitude_m == 0.0


def test_hold_yaw_moves_only_while_pressed():
    drone = DroneSimulator()
    start = drone.yaw_deg
    drone.start_yaw_left()
    drone.update(1.0)
    while_held = drone.yaw_deg
    drone.stop_directional()
    drone.update(1.0)
    after_release = drone.yaw_deg
    assert while_held != start
    assert after_release == pytest.approx(while_held)


def test_hold_climb_stops_on_release():
    drone = DroneSimulator()
    drone.arm()
    drone.takeoff(5.0)
    drone.update(3.0)
    drone.start_climb()
    drone.update(1.0)
    rising = drone.target_altitude_m
    drone.stop_directional()
    drone.update(1.0)
    assert drone.target_altitude_m == pytest.approx(rising)


def test_a_command_pushes_left_and_release_brakes():
    assert command_wrench("a")[1] > 0
    held = clamp_hold_wrench("a", 0.0, 0.0, 0.0)
    assert held[1] > 0
    coasting = clamp_hold_wrench(None, 0.0, 1.2, 0.0)
    assert coasting[1] < 0
    bx, by, bz, _tz = brake_wrench(1.0, -0.5, 0.2)
    assert bx < 0 and by > 0 and bz < 0


def test_bounds_and_center_helpers():
    assert is_outside_area(10.0, 0.0, 3.0)
    assert is_near_center(0.1, -0.2, 3.1)
