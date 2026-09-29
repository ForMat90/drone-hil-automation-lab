# Drone HIL Automation Lab

**End-to-end automated tests for a simulated drone flying in Gazebo, driven through ROS 2 and verified with Playwright.**

[Versione italiana](README.md) · [Getting started](#what-you-need-installed) · [How the pieces talk](#how-the-pieces-talk-to-each-other)

<!-- Replace with the demo GIF: Gazebo on the left, test terminal on the right. -->
![Demo: the drone flown by the automated tests in Gazebo](docs/demo.gif)

I run `npx playwright test` and the drone flies on its own inside the 3D scene: left, right, up, down, rotating — and every manoeuvre is checked by an assertion that verifies the command did what it promised.

### The interesting problem

Gazebo and ROS 2 run inside Linux (WSL) and communicate through ROS messages. Playwright runs on Windows and speaks HTTP. These two worlds cannot call each other directly, so I wrote a **bridge service** that exposes four APIs and translates them into ROS commands — the same approach used to make microservices written in different languages talk to each other.

```
npx playwright test  ──HTTP──▶  Python bridge (:8765)  ──ROS 2──▶  Gazebo
   (Windows, JS)                     (Linux/WSL)                  (3D drone)
```

### What this project demonstrates

- **A complete test pyramid**: fast unit tests on the flight logic, end-to-end tests against the running system.
- **Assertions on a physical system**: the checks verify a direction of movement rather than an exact value, because a physics simulation is never repeatable to the millimetre.
- **Cross-process, cross-language integration**: HTTP ⇄ ROS, Windows ⇄ Linux, JavaScript ⇄ Python.
- **Isolated tests**: the drone is recentred before each test and stopped when the suite ends.

### Stack

`Playwright` · `ROS 2 Humble` · `Gazebo 11` · `Python` · `JavaScript` · `pytest` · `WSL2`

---

The rest of this page is the practical guide: how to install everything, how to fly the drone by hand and how to run the tests.

---

## What you need installed

| What | Where it runs | What it is for |
|---|---|---|
| Windows 10/11 with WSL2 + Ubuntu 22.04 | — | running Linux inside Windows |
| ROS 2 Humble + Gazebo 11 | inside Ubuntu 22.04 | the 3D world and the drone |
| Python 3.10+ | Windows | the fast logic tests |
| Node.js | Windows | the Playwright automated tests |

First-time Gazebo/ROS installation (only once):

```powershell
wsl --install -d Ubuntu-22.04
wsl -d Ubuntu-22.04 -u root -- bash -lc "bash /mnt/c/Drone-HIL-Automation-Lab/scripts/install_real_gazebo.sh"
```

Test dependencies (only once):

```powershell
cd C:\Drone-HIL-Automation-Lab
npm install
python -m pip install -r requirements.txt
```

The detailed ROS/Gazebo guide is in [docs/REAL_GAZEBO_SETUP.md](docs/REAL_GAZEBO_SETUP.md).

---

## 1) Start Gazebo (always the first step)

```powershell
cd C:\Drone-HIL-Automation-Lab
.\scripts\run_gazebo_windows.ps1
```

The 3D window opens with the drone, the grass, the trees, the warehouse and the orange fence.
Keep this terminal open: closing it closes Gazebo.

---

## 2) Fly the drone by hand

In a **second terminal**:

```powershell
cd C:\Drone-HIL-Automation-Lab
.\scripts\run_manual_control_windows.ps1
```

Keys:

| Key | What it does |
|---|---|
| `w` / `s` | forward / backward |
| `a` / `d` | left / right |
| `r` / `f` | up / down |
| `q` / `e` | rotate in place (yaw) |
| `x` | stop |
| `Ctrl+C` | quit manual control |

There is **no browser and no web address** here: the program reads the key and sends it straight to Gazebo.

If the drone leaves the area or climbs too high, it is automatically brought back to the centre.

---

## 3) Automated tests (the drone flies on its own)

Leave Gazebo open and **close manual control** (`Ctrl+C`): if both are running they compete for the commands and the drone behaves erratically.

In a third terminal:

```powershell
cd C:\Drone-HIL-Automation-Lab
npx playwright test
```

Watch the Gazebo window: the drone starts moving by itself — left, right, forward, backward, up, down, and rotating.
The terminal shows the list of tests with ✓ or ✗.

When the suite ends the drone is stopped and recentred. **Gazebo stays open**: you close it whenever you want.

Useful commands:

```powershell
npx playwright test                          # all tests
npx playwright test -g "A:"                  # only the A command test
npx playwright test --reporter=html          # browsable report
```

---

## 4) Fast logic tests (unit tests)

These **do not open Gazebo** and take less than a second:

```powershell
cd C:\Drone-HIL-Automation-Lab
python -m pytest tests/test_drone_simulator.py
```

---

## How the pieces talk to each other

This is the part that confuses people the most, so let's take it slowly.

The problem: **Gazebo and ROS run inside Linux (WSL) and speak "ROS"**, while **Playwright runs on Windows and speaks HTTP**. Two different worlds, two different languages. They cannot call each other directly.

The solution is the same one used between microservices: put **a small service with an API** in the middle. That service is [scripts/drone_web_control.py](scripts/drone_web_control.py): it receives HTTP requests and forwards them to ROS.

```
  npx playwright test            (Windows, JavaScript)
            │
            │  HTTP calls
            ▼
  http://127.0.0.1:8765          <-- an API we wrote ourselves
  scripts/drone_web_control.py   (Linux/WSL, Python)
            │
            │  ROS messages
            ▼
  Gazebo: the drone moves
```

### The APIs the tests use

| Call | What it is for |
|---|---|
| `POST /api/hold` with `{ "command": "a" }` | hold the command down (like holding the key) |
| `POST /api/release` | release the command: the drone slows down and stops |
| `GET /api/pose` | read where the drone is (x, y, z, speed, rotation) |
| `POST /api/reset` | put the drone back in the centre |

A test, step by step:

1. the test calls `POST /api/hold` with `a`;
2. the service translates it and publishes a leftward force on the ROS topic `/drone/gazebo_ros_force`;
3. Gazebo applies the force and the drone moves;
4. every 0.2 seconds the test calls `GET /api/pose` and records the position;
5. after 5 seconds it calls `POST /api/release`;
6. it checks the collected samples: "did it actually go left?" If yes, the test passes.

### Two important points

- **Playwright does not open any browser here.** Playwright is normally used to test websites by clicking buttons; in this project it is used purely as a tool that makes API calls and writes the assertions. The result is not read from a page — it is visible in Gazebo and in the position numbers.
- **`http://127.0.0.1:8765` is not "the drone's website".** It is only the bridge between Windows and Linux. Opening it in a browser shows a small page with buttons, handy for manual poking, but the automated tests do not use it: they call the APIs directly.
- The bridge service **starts on its own** when you run the tests (started by [e2e/global-setup.js](e2e/global-setup.js)). To start it manually: `.\scripts\run_web_control_windows.ps1`.

---

## What the tests actually verify

### Automated tests against Gazebo — [e2e/drone-commands.spec.js](e2e/drone-commands.spec.js)

Before every test the drone is recentred, so one test cannot skew the next one.
Each command is held down for **5 seconds**: long enough to see the movement with your own eyes in the 3D window.

| Test | What it checks |
|---|---|
| A: left for 5s and return to centre | the drone moves left; at the end of the run it comes back to the centre |
| D: right for 5s | it moves right |
| W: forward for 5s | it moves forward |
| S: backward for 5s | it moves backward |
| R: up for 5s | it climbs |
| F: down for 5s | it descends |
| release: the drone stops | after releasing the command the speed drops to nearly zero and it does not keep sliding |
| Q and E change the yaw | the drone rotates in place |

### Unit tests — [tests/test_drone_simulator.py](tests/test_drone_simulator.py)

They check the pure logic, without Gazebo: drone states (idle, armed, take-off, hover, landing, emergency), take-off, landing, emergency stop, the area limits, and the fact that a held command stops on release.

---

## Key files

| Path | What it is for |
|---|---|
| [scripts/run_gazebo_windows.ps1](scripts/run_gazebo_windows.ps1) | opens Gazebo from a Windows terminal |
| [scripts/run_manual_control_windows.ps1](scripts/run_manual_control_windows.ps1) | starts keyboard piloting |
| [scripts/manual_drone_control.py](scripts/manual_drone_control.py) | reads the keys and sends forces to ROS |
| [scripts/drone_web_control.py](scripts/drone_web_control.py) | the bridge: HTTP API ⇄ ROS, port 8765 |
| [scripts/run_web_control_windows.ps1](scripts/run_web_control_windows.ps1) | starts the bridge manually (usually not needed) |
| [scripts/gazebo_boundary_guard.py](scripts/gazebo_boundary_guard.py) | recentres the drone if it leaves the area |
| [e2e/drone-commands.spec.js](e2e/drone-commands.spec.js) | the automated tests and their assertions |
| [e2e/drone-api.js](e2e/drone-api.js) | reusable helpers: hold, read pose, reset |
| [e2e/global-setup.js](e2e/global-setup.js) | before the tests: find or start the bridge |
| [e2e/global-teardown.js](e2e/global-teardown.js) | after the tests: stop the drone |
| [playwright.config.js](playwright.config.js) | test configuration (timeout, ordering, reporter) |
| [tests/test_drone_simulator.py](tests/test_drone_simulator.py) | logic unit tests |
| [src/drone_simulator/flight_control.py](src/drone_simulator/flight_control.py) | command forces, top speed, braking, area limits |
| [src/drone_simulator/simulator.py](src/drone_simulator/simulator.py) | the drone logic used by the unit tests |
| [gazebo/worlds/drone_lab.world](gazebo/worlds/drone_lab.world) | the 3D world: drone, trees, warehouse, fence |
| [scripts/run_gazebo_3d.sh](scripts/run_gazebo_3d.sh) | the Linux script that actually launches Gazebo |

To change how fast or how responsive the drone feels, edit **a single file**: `src/drone_simulator/flight_control.py`. The same settings apply to both manual flight and the tests.

---

## Extras

**Automatic area guard** (optional, third terminal):

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "source /opt/ros/humble/setup.bash; python3 /mnt/c/Drone-HIL-Automation-Lab/scripts/gazebo_boundary_guard.py"
```

**Older movement test** (checks forward motion only, with Gazebo open):

```powershell
.\scripts\run_movement_test_windows.ps1
```

**Lightweight 2D simulator** (Python window, no Gazebo, handy for trying out the logic):

```powershell
python run_simulator.py
```

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The tests say Gazebo is not running | start `.\scripts\run_gazebo_windows.ps1` first and wait for the 3D window |
| The Gazebo window closes immediately with a graphics error | run the script again: it kills leftover processes on startup |
| The drone does not respond to keys | Gazebo is not running, or you are typing in the wrong terminal |
| The drone behaves oddly during the tests | manual control is still open: close it with `Ctrl+C` |
| Playwright asks to install a browser | not needed: these tests do not use a browser. Make sure you run `npx playwright test` from the project folder |

---

## Notes on the tests and possible improvements

**How the tests are built, in short.** They do not check an exact number, because a physics simulation never produces the same result twice. They check a **direction**: after holding `a`, the drone must have moved left by at least a few dozen centimetres. This keeps them stable and cheap to maintain. The position is sampled throughout the movement, not only at the end, so a test does not fail if the drone gets recentred in the meantime.

Things that would make the project stronger:

- **A deliberately failing test**, to prove the assertions really work and do not always pass.
- **Collision tests**: verify the drone does not fly through the warehouse or the trees.
- **Landing-pad tests**, with a tolerance on accuracy.
- **Stored reports**: keep the results of each run (`npx playwright test --reporter=html`) to compare over time.
- **CI execution**: today a machine with Gazebo running is required; Gazebo can also run headless (`gui:=false`) on a server.
- **A single startup command** that opens Gazebo, the bridge and the tests in sequence, for people who do not want to juggle three terminals.
- **A real autopilot (PX4/SITL)** if simulating the flight firmware ever becomes necessary: more realistic, but much heavier to install.
