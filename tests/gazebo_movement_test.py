#!/usr/bin/env python3
"""Integration test for manual-style directional commands in Gazebo."""

import sys

try:
    import rclpy
    from geometry_msgs.msg import Wrench
    from nav_msgs.msg import Odometry
    from std_srvs.srv import Empty
except ModuleNotFoundError:
    rclpy = None
    Wrench = None
    Odometry = None


def main() -> int:
    if rclpy is None:
        print("Run this test inside Ubuntu 22.04 after sourcing ROS 2 Humble.")
        return 2

    rclpy.init()
    node = rclpy.create_node("gazebo_movement_test")
    # Send a force to Gazebo and use odometry as the observable result.
    publisher = node.create_publisher(Wrench, "/drone/gazebo_ros_force", 10)
    reset_client = node.create_client(Empty, "/reset_world")
    position = {"x": None, "y": None, "z": None}

    def on_odom(message: Odometry) -> None:
        pose = message.pose.pose.position
        position.update(x=pose.x, y=pose.y, z=pose.z)

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
    if reset_client.wait_for_service(timeout_sec=10.0):
        future = reset_client.call_async(Empty.Request())
        rclpy.spin_until_future_complete(node, future, timeout_sec=3.0)
    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.1)
    start = position.copy()
    if start["x"] is None:
        node.get_logger().error("Odometria del drone non disponibile")
        return 1

    request = Wrench()
    request.force.x = 18.0
    for _ in range(10):
        publisher.publish(request)
        rclpy.spin_once(node, timeout_sec=0.1)

    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.1)
    end = position.copy()
    moved = end["x"] > start["x"] + 0.05
    node.get_logger().info(f"X: {start['x']:.2f} -> {end['x']:.2f} m")

    node.destroy_node()
    rclpy.shutdown()
    return 0 if moved else 1


if __name__ == "__main__":
    sys.exit(main())
