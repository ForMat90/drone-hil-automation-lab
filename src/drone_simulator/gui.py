from __future__ import annotations

import tkinter as tk

from .simulator import DroneSimulator, DroneState


class DroneWorldWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Drone Simulator")
        self.geometry("1280x900")
        self.configure(bg="#06131f")

        self.simulator = DroneSimulator()
        self.canvas = tk.Canvas(self, width=1280, height=720, bg="#06131f", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bottom = tk.Frame(self, bg="#06131f", height=180)
        self.bottom.pack(fill=tk.X)
        self.bottom.pack_propagate(False)

        self.state_label = tk.Label(self.bottom, text="IDLE", fg="#facc15", bg="#06131f", font=("Segoe UI", 26, "bold"))
        self.state_label.pack(pady=(18, 0))

        self.meta_label = tk.Label(self.bottom, text="BAT 100.0%  YAW 111°", fg="#e2e8f0", bg="#06131f", font=("Segoe UI", 14))
        self.meta_label.pack()

        self.controls = tk.Frame(self.bottom, bg="#06131f")
        self.controls.pack(pady=(18, 0))

        self.altitude_var = tk.StringVar(value="5")
        self.alt_entry = tk.Entry(self.controls, width=8, font=("Segoe UI", 12), justify="center", textvariable=self.altitude_var)
        self.alt_entry.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(self.controls, text="SET ALT", width=10, height=2, bg="#0f172a", fg="#f8fafc", command=self._set_altitude).pack(side=tk.LEFT, padx=8)

        actions = [
            ("ARM", self._arm),
            ("TAKEOFF", self._takeoff_current),
            ("LAND", self._land),
            ("EMERGENCY STOP", self._emergency),
            ("CANCEL", self._cancel),
        ]
        for label, command in actions:
            tk.Button(
                self.controls,
                text=label,
                width=12,
                height=2,
                bg="#0f172a",
                fg="#f8fafc",
                activebackground="#1d4ed8",
                command=command,
            ).pack(side=tk.LEFT, padx=6)

        hold_actions = [
            ("UP", self.simulator.start_climb),
            ("DOWN", self.simulator.start_descend),
            ("YAW L", self.simulator.start_yaw_left),
            ("YAW R", self.simulator.start_yaw_right),
        ]
        for label, start in hold_actions:
            button = tk.Button(
                self.controls,
                text=label,
                width=10,
                height=2,
                bg="#0f172a",
                fg="#f8fafc",
                activebackground="#1d4ed8",
            )
            button.pack(side=tk.LEFT, padx=6)
            button.bind("<ButtonPress-1>", lambda _event, fn=start: fn())
            button.bind("<ButtonRelease-1>", lambda _event: self.simulator.stop_directional())

        self.bind("<KeyPress-Up>", lambda _event: self.simulator.start_climb())
        self.bind("<KeyPress-Down>", lambda _event: self.simulator.start_descend())
        self.bind("<KeyPress-Left>", lambda _event: self.simulator.start_yaw_left())
        self.bind("<KeyPress-Right>", lambda _event: self.simulator.start_yaw_right())
        self.bind("<KeyPress-w>", lambda _event: self.simulator.start_climb())
        self.bind("<KeyPress-s>", lambda _event: self.simulator.start_descend())
        self.bind("<KeyPress-a>", lambda _event: self.simulator.start_yaw_left())
        self.bind("<KeyPress-d>", lambda _event: self.simulator.start_yaw_right())
        for sequence in (
            "<KeyRelease-Up>",
            "<KeyRelease-Down>",
            "<KeyRelease-Left>",
            "<KeyRelease-Right>",
            "<KeyRelease-w>",
            "<KeyRelease-s>",
            "<KeyRelease-a>",
            "<KeyRelease-d>",
        ):
            self.bind(sequence, lambda _event: self.simulator.stop_directional())

        self.after(50, self._tick)

    def _arm(self) -> None:
        self.simulator.arm()

    def _set_altitude(self) -> None:
        try:
            altitude = float(self.altitude_var.get())
        except ValueError:
            return
        self.simulator.set_altitude(altitude)

    def _takeoff_current(self) -> None:
        try:
            altitude = float(self.altitude_var.get())
        except ValueError:
            altitude = 5.0
        self.simulator.takeoff(altitude)

    def _takeoff(self, altitude: float) -> None:
        self.simulator.takeoff(altitude)

    def _land(self) -> None:
        self.simulator.land()

    def _emergency(self) -> None:
        self.simulator.emergency_stop()

    def _cancel(self) -> None:
        self.simulator.cancel_action()

    def _tick(self) -> None:
        telemetry = self.simulator.update(0.12)
        self._draw_world(telemetry)
        self.state_label.config(text=telemetry.state.value)
        self.meta_label.config(text=f"BAT {telemetry.battery_pct:.1f}%  YAW {telemetry.yaw_deg:.0f}°")
        self.after(50, self._tick)

    def _draw_world(self, telemetry) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, 1280, 700, fill="#071827")

        ground_top = 540
        self.canvas.create_rectangle(0, ground_top, 1280, 700, fill="#1a563d")
        self.canvas.create_rectangle(150, 520, 1130, 560, fill="#2a7b56", outline="#2a7b56")

        for tree_x in [150, 380, 640, 875, 1100]:
            self.canvas.create_oval(tree_x - 50, 365, tree_x + 50, 465, fill="#4eaf5d")
            self.canvas.create_rectangle(tree_x - 10, 465, tree_x + 10, 540, fill="#3d422b")

        pad_x = 640
        pad_y = 520
        self.canvas.create_oval(pad_x - 120, pad_y - 52, pad_x + 120, pad_y + 52, fill="#dfe6ea", outline="#94a3b8", width=3)
        self.canvas.create_oval(pad_x - 40, pad_y - 14, pad_x + 40, pad_y + 14, fill="#74839a")

        world_y = 520 - telemetry.altitude_m * 18.0
        drone_x = 640
        drone_y = int(world_y)
        arm = 80

        body_color = "#dfe7ec" if telemetry.state != DroneState.EMERGENCY else "#e11d48"
        rotor_color = "#4f46e5" if telemetry.state in {DroneState.ARMED, DroneState.TAKEOFF, DroneState.HOVER, DroneState.LANDING} else "#64748b"

        self.canvas.create_oval(drone_x - 62, drone_y - 20, drone_x + 62, drone_y + 20, fill=body_color, outline="#f8fafc", width=2)
        self.canvas.create_line(drone_x - 14, drone_y, drone_x - arm, drone_y - 25, fill="#dbeafe", width=3)
        self.canvas.create_line(drone_x + 14, drone_y, drone_x + arm, drone_y - 25, fill="#dbeafe", width=3)
        self.canvas.create_line(drone_x - 14, drone_y, drone_x - arm, drone_y + 25, fill="#dbeafe", width=3)
        self.canvas.create_line(drone_x + 14, drone_y, drone_x + arm, drone_y + 25, fill="#dbeafe", width=3)

        for dx, dy in [(-arm, -25), (arm, -25), (-arm, 25), (arm, 25)]:
            self.canvas.create_oval(drone_x + dx - 12, drone_y + dy - 12, drone_x + dx + 12, drone_y + dy + 12, fill=rotor_color, outline="#f8fafc")

        self.canvas.create_oval(drone_x - 12, drone_y - 12, drone_x + 12, drone_y + 12, fill="#f8fafc")
        self.canvas.create_line(drone_x - 22, drone_y, drone_x + 22, drone_y, fill="#0f172a", width=2)
        self.canvas.create_line(drone_x, drone_y - 22, drone_x, drone_y + 22, fill="#0f172a", width=2)

        self.canvas.create_text(640, 110, text=f"ALT {telemetry.altitude_m:.1f}m  SPEED {telemetry.speed_mps:.1f}m/s", fill="#f8fafc", font=("Segoe UI", 18, "bold"))

        if telemetry.state == DroneState.TAKEOFF:
            self.canvas.create_text(640, 150, text="TAKEOFF", fill="#38bdf8", font=("Segoe UI", 22, "bold"))
        elif telemetry.state == DroneState.HOVER:
            self.canvas.create_text(640, 150, text="HOVER", fill="#22c55e", font=("Segoe UI", 22, "bold"))
        elif telemetry.state == DroneState.LANDING:
            self.canvas.create_text(640, 150, text="LANDING", fill="#f59e0b", font=("Segoe UI", 22, "bold"))
        elif telemetry.state == DroneState.EMERGENCY:
            self.canvas.create_text(640, 150, text="EMERGENCY", fill="#ef4444", font=("Segoe UI", 22, "bold"))


def main() -> None:
    app = DroneWorldWindow()
    app.mainloop()
