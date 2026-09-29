#!/usr/bin/env python3
"""HTTP control panel + ROS bridge for the Gazebo drone (hold to move, release to stop)."""

from __future__ import annotations

import json
import math
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drone_simulator.flight_control import (  # noqa: E402
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
    print("Run this script inside Ubuntu 22.04 after sourcing ROS 2 Humble.", file=sys.stderr)
    raise SystemExit(2)

HTML_PATH = ROOT / "src" / "drone_simulator" / "static" / "control.html"
HOST = "0.0.0.0"
PORT = 8765


class DroneBridge:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.command: str | None = None
        self.pose = {
            "x": 0.0,
            "y": 0.0,
            "z": 3.0,
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

    def snapshot(self) -> dict[str, float]:
        with self.lock:
            return {
                "x": finite_number(self.pose["x"]),
                "y": finite_number(self.pose["y"]),
                "z": finite_number(self.pose["z"], 3.0),
                "vx": finite_number(self.pose["vx"]),
                "vy": finite_number(self.pose["vy"]),
                "vz": finite_number(self.pose["vz"]),
                "yaw": finite_number(self.pose["yaw"]),
            }


bridge = DroneBridge()


def ros_loop() -> None:
    rclpy.init()
    node = rclpy.create_node("drone_web_control")
    publisher = node.create_publisher(Wrench, "/drone/gazebo_ros_force", 10)
    reset_client = node.create_client(Empty, "/reset_world")

    def on_odom(message: Odometry) -> None:
        pose = message.pose.pose.position
        twist = message.twist.twist
        q = message.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.degrees(math.atan2(siny, cosy))
        with bridge.lock:
            bridge.pose.update(
                x=finite_number(pose.x),
                y=finite_number(pose.y),
                z=finite_number(pose.z, 3.0),
                vx=finite_number(twist.linear.x),
                vy=finite_number(twist.linear.y),
                vz=finite_number(twist.linear.z),
                yaw=finite_number(yaw),
            )

    node.create_subscription(Odometry, "/drone/odom", on_odom, 10)
    deadline_start = node.get_clock().now().nanoseconds / 1e9
    while publisher.get_subscription_count() < 1:
        rclpy.spin_once(node, timeout_sec=0.1)
        now = node.get_clock().now().nanoseconds / 1e9
        if now - deadline_start > 15.0:
            node.get_logger().error("Gazebo non e attivo: avvia prima run_gazebo_3d.sh")
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

            if bridge.reset_request and reset_client.wait_for_service(timeout_sec=0.2):
                bridge.reset_request = False
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

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._send(200, HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/api/pose":
            payload = json.dumps(bridge.snapshot(), allow_nan=False).encode("utf-8")
            self._send(200, payload, "application/json")
            return
        self._send(404, b"not found", "text/plain")

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
            self._send(200, b'{"ok":true}', "application/json")
            return
        if self.path == "/api/release":
            bridge.set_command(None)
            self._send(200, b'{"ok":true}', "application/json")
            return
        if self.path == "/api/reset":
            bridge.set_command(None)
            bridge.reset_request = True
            self._send(200, b'{"ok":true}', "application/json")
            return
        self._send(404, b"not found", "text/plain")


def main() -> int:
    ros_thread = threading.Thread(target=ros_loop, daemon=True)
    ros_thread.start()
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
