#!/usr/bin/env python3
"""Keyboard controller for the demo Gazebo drone."""

import sys
import time

import rclpy
from geometry_msgs.msg import Wrench
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty


# These limits are smaller than the visible fence so the controller can recover
# the drone before it becomes difficult to see or control.
MAX_X = 9.0
MAX_Y = 7.0
MIN_Z = 1.0
MAX_Z = 8.0
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
    position = {"x": 0.0, "y": 0.0, "z": 3.0}

    def on_odom(message: Odometry) -> None:
        position["x"] = message.pose.pose.position.x
        position["y"] = message.pose.pose.position.y
        position["z"] = message.pose.pose.position.z

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
    deadline = time.monotonic() + 10.0
    while publisher.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    if publisher.get_subscription_count() < 1:
        node.get_logger().error("Gazebo non e attivo: avvia prima run_gazebo_3d.sh")
        return 1

    print(HELP, flush=True)
    forces = {
        "w": (18.0, 0.0, 0.0),
        "s": (-18.0, 0.0, 0.0),
        "a": (0.0, 18.0, 0.0),
        "d": (0.0, -18.0, 0.0),
        "r": (0.0, 0.0, 24.0),
        "f": (0.0, 0.0, -24.0),
    }
    torques = {"q": 1.5, "e": -1.5}

    try:
        while rclpy.ok():
            key = read_key().lower()
            message = Wrench()
            if key == "x":
                publisher.publish(message)
                continue
            if key == "\x03":
                break
            if key not in forces and key not in torques:
                publisher.publish(message)
                continue

            force = forces.get(key, (0.0, 0.0, 0.0))
            message.force.x, message.force.y, message.force.z = force
            message.torque.z = torques.get(key, 0.0)
            publisher.publish(message)
            rclpy.spin_once(node, timeout_sec=0.01)
            outside_area = (
                abs(position["x"]) > MAX_X
                or abs(position["y"]) > MAX_Y
                or position["z"] < MIN_Z
                or position["z"] > MAX_Z
            )
            if outside_area:
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
