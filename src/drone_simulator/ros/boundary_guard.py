#!/usr/bin/env python3
"""Optional watchdog: keeps the drone inside its flight envelope.

Useful when neither the keyboard controller nor the bridge is running, because
both of them already recover the drone on their own.
"""

import rclpy
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty

from ..flight_control import is_outside_area


def main() -> int:
    rclpy.init()
    node = rclpy.create_node("gazebo_boundary_guard")
    reset_client = node.create_client(Empty, "/reset_world")
    reset_pending = False

    def on_odom(message: Odometry) -> None:
        nonlocal reset_pending
        position = message.pose.pose.position
        if is_outside_area(position.x, position.y, position.z) and not reset_pending:
            if reset_client.service_is_ready():
                reset_pending = True
                future = reset_client.call_async(Empty.Request())
                future.add_done_callback(_clear_pending)
                node.get_logger().warn("Flight envelope exceeded; drone reset to center")

    def _clear_pending(_future) -> None:
        nonlocal reset_pending
        reset_pending = False

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
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
