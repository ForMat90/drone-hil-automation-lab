#!/usr/bin/env python3
"""Keyboard controller for the Gazebo drone: one keypress, one impulse.

This is the manual flight path and it talks to ROS directly, with no HTTP and no
browser in between. The Playwright tests use bridge_server.py instead.
"""

import sys
import time

import rclpy
from geometry_msgs.msg import Wrench
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty

from ..flight_control import MANUAL_WRENCH, SPAWN_ALTITUDE_M, is_outside_area

HELP = "w/s: avanti/indietro | a/d: sinistra/destra | r/f: su/giu | q/e: yaw | x: stop | Ctrl+C: esci"


def read_key() -> str:
    """Read one key without blocking, then restore the terminal settings."""
    import select
    import termios
    import tty

    settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        return sys.stdin.read(1) if ready else ""
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


def main() -> int:
    rclpy.init()
    node = rclpy.create_node("manual_drone_control")
    publisher = node.create_publisher(Wrench, "/drone/gazebo_ros_force", 10)
    reset_client = node.create_client(Empty, "/reset_world")
    position = {"x": 0.0, "y": 0.0, "z": SPAWN_ALTITUDE_M}

    def on_odom(message: Odometry) -> None:
        position["x"] = message.pose.pose.position.x
        position["y"] = message.pose.pose.position.y
        position["z"] = message.pose.pose.position.z

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
    deadline = time.monotonic() + 10.0
    while publisher.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    if publisher.get_subscription_count() < 1:
        node.get_logger().error("Gazebo non e attivo: avvia prima run_gazebo_windows.ps1")
        return 1

    print(HELP, flush=True)
    try:
        while rclpy.ok():
            key = read_key().lower()
            message = Wrench()
            if key == "\x03":
                break
            if key not in MANUAL_WRENCH:
                # Unknown key or "x": publish a null wrench, which stops pushing.
                publisher.publish(message)
                continue

            fx, fy, fz, tz = MANUAL_WRENCH[key]
            message.force.x, message.force.y, message.force.z = fx, fy, fz
            message.torque.z = tz
            publisher.publish(message)
            rclpy.spin_once(node, timeout_sec=0.01)

            if is_outside_area(position["x"], position["y"], position["z"]):
                publisher.publish(Wrench())
                if reset_client.wait_for_service(timeout_sec=1.0):
                    reset_client.call_async(Empty.Request())
                node.get_logger().warn("Limite area/quota raggiunto: drone riportato al centro")
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
