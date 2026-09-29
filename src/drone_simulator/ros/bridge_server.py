#!/usr/bin/env python3
"""HTTP bridge between the Playwright tests (Windows) and Gazebo (Linux/ROS 2).

The tests speak HTTP, Gazebo speaks ROS, so this node exposes four endpoints and
translates them into Wrench messages: hold a command, release it, read the pose,
reset the world.
"""

from __future__ import annotations

import json
import math
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..flight_control import (
    SPAWN_ALTITUDE_M,
    clamp_hold_wrench,
    finite_number,
    is_near_center,
    is_outside_area,
)

try:
    import rclpy
    from geometry_msgs.msg import Wrench
    from nav_msgs.msg import Odometry
    from std_srvs.srv import Empty
except ModuleNotFoundError:
    print("Run this module inside Ubuntu 22.04 after sourcing ROS 2 Humble.", file=sys.stderr)
    raise SystemExit(2)

HOST = "0.0.0.0"
PORT = 8765


class DroneBridge:
    """Shared state between the HTTP threads and the ROS thread."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.command: str | None = None
        self.pose = {
            "x": 0.0,
            "y": 0.0,
            "z": SPAWN_ALTITUDE_M,
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
            "yaw": 0.0,
        }
        self.reset_pending = False
        self.reset_request = False

    def set_command(self, command: str | None) -> None:
        with self.lock:
            self.command = command

    def request_reset(self) -> None:
        with self.lock:
            self.command = None
            self.reset_request = True

    def take_reset_request(self) -> bool:
        with self.lock:
            requested = self.reset_request
            self.reset_request = False
        return requested

    def snapshot(self) -> dict[str, float]:
        with self.lock:
            return {
                "x": finite_number(self.pose["x"]),
                "y": finite_number(self.pose["y"]),
                "z": finite_number(self.pose["z"], SPAWN_ALTITUDE_M),
                "vx": finite_number(self.pose["vx"]),
                "vy": finite_number(self.pose["vy"]),
                "vz": finite_number(self.pose["vz"]),
                "yaw": finite_number(self.pose["yaw"]),
            }


bridge = DroneBridge()


def yaw_degrees(orientation) -> float:
    q = orientation
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.degrees(math.atan2(siny, cosy))


def ros_loop() -> None:
    rclpy.init()
    node = rclpy.create_node("drone_bridge_server")
    publisher = node.create_publisher(Wrench, "/drone/gazebo_ros_force", 10)
    reset_client = node.create_client(Empty, "/reset_world")

    def on_odom(message: Odometry) -> None:
        position = message.pose.pose.position
        twist = message.twist.twist
        with bridge.lock:
            bridge.pose.update(
                x=finite_number(position.x),
                y=finite_number(position.y),
                z=finite_number(position.z, SPAWN_ALTITUDE_M),
                vx=finite_number(twist.linear.x),
                vy=finite_number(twist.linear.y),
                vz=finite_number(twist.linear.z),
                yaw=finite_number(yaw_degrees(message.pose.pose.orientation)),
            )

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)

    # Gazebo subscribes to the force topic through its plugin: no subscriber
    # means the world is not up yet.
    started = node.get_clock().now().nanoseconds / 1e9
    while publisher.get_subscription_count() < 1:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.get_clock().now().nanoseconds / 1e9 - started > 15.0:
            node.get_logger().error("Gazebo non e attivo: avvia prima run_gazebo_windows.ps1")
            break

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            pose = bridge.snapshot()
            with bridge.lock:
                command = bridge.command
            fx, fy, fz, tz = clamp_hold_wrench(command, pose["vx"], pose["vy"], pose["vz"])
            message = Wrench()
            message.force.x = fx
            message.force.y = fy
            message.force.z = fz
            message.torque.z = tz
            publisher.publish(message)

            if reset_client.service_is_ready() and bridge.take_reset_request():
                publisher.publish(Wrench())
                reset_client.call_async(Empty.Request())

            if is_outside_area(pose["x"], pose["y"], pose["z"]) and not bridge.reset_pending:
                publisher.publish(Wrench())
                if reset_client.wait_for_service(timeout_sec=0.2):
                    bridge.reset_pending = True
                    future = reset_client.call_async(Empty.Request())
                    future.add_done_callback(lambda _f: setattr(bridge, "reset_pending", False))
                    node.get_logger().warn("Limite area/quota raggiunto: drone riportato al centro")
            elif is_near_center(pose["x"], pose["y"], pose["z"]):
                bridge.reset_pending = False
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


class ControlHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/api"}:
            self._send_json(
                200,
                {
                    "service": "drone-bridge",
                    "endpoints": {
                        "GET /api/pose": "current position, velocity and yaw",
                        "POST /api/hold": "hold a command: w s a d r f q e",
                        "POST /api/release": "release the command, the drone brakes",
                        "POST /api/reset": "put the drone back at the center",
                    },
                },
            )
            return
        if self.path == "/api/pose":
            self._send_json(200, bridge.snapshot())
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}

        if self.path == "/api/hold":
            command = str(data.get("command", "")).lower()
            bridge.set_command(None if command == "x" else command)
            self._send_json(200, {"ok": True, "command": command})
            return
        if self.path == "/api/release":
            bridge.set_command(None)
            self._send_json(200, {"ok": True})
            return
        if self.path == "/api/reset":
            bridge.request_reset()
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "not found"})


def main() -> int:
    threading.Thread(target=ros_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), ControlHandler)
    print("Bridge ROS per i test Playwright. Per volare a mano usa run_manual_control_windows.ps1", flush=True)
    print(f"http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
