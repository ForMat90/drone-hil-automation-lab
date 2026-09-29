#!/usr/bin/env python3
"""Keep the demo drone inside its bounded training area."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import rclpy
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty

from drone_simulator.flight_control import is_outside_area


def main() -> int:
    rclpy.init()
    node = rclpy.create_node("gazebo_boundary_guard")
    reset_client = node.create_client(Empty, "/reset_world")
    reset_pending = False

    def on_odom(message: Odometry) -> None:
        nonlocal reset_pending
        pose = message.pose.pose.position
        outside = is_outside_area(pose.x, pose.y, pose.z)
        if outside and not reset_pending and reset_client.service_is_ready():
            reset_pending = True
            reset_client.call_async(Empty.Request())
            node.get_logger().warn("Flight envelope exceeded; drone reset to center")

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
    node.create_timer(0.1, lambda: None)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
