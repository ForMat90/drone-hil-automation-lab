#!/usr/bin/env python3
"""Black-box smoke test for the running Gazebo drone scene."""

import sys
try:
    import rclpy
    from nav_msgs.msg import Odometry
except ModuleNotFoundError:
    rclpy = None
    Odometry = None


def main() -> int:
    if rclpy is None:
        print("Run this test inside Ubuntu 22.04 after sourcing ROS 2 Humble.")
        return 2

    rclpy.init()
    node = rclpy.create_node("drone_gazebo_smoke_test")
    telemetry = {"altitude": None}

    def on_odom(message: Odometry) -> None:
        telemetry["altitude"] = message.pose.pose.position.z

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)

    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.1)
    measured = telemetry["altitude"]
    if measured is None:
        node.get_logger().error("Drone odometry was not published")
        return 1
    passed = measured > 2.5
    node.get_logger().info(f"Drone odometry altitude: {measured:.2f} m")

    node.destroy_node()
    rclpy.shutdown()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
