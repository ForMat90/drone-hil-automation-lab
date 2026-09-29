# Real 3D Gazebo drone simulator setup

This is the real path to a proper 3D drone simulator. It is heavier than the local Tkinter version, but it is the correct setup if you want a Gazebo-like environment and real flight testing.

Important:
- the current WSL environment is Ubuntu 26.04 and does not expose a supported Gazebo/ROS package set for this workflow
- the correct and reproducible setup is Ubuntu 22.04 LTS + ROS 2 Humble + Gazebo
- this guide is intended for a clean Linux environment, ideally inside WSL2

## 1) Install WSL2 and Ubuntu 22.04

On Windows PowerShell as Administrator:

```powershell
wsl --install
wsl --list --online
wsl --install -d Ubuntu-22.04
```

Per trasferire il progetto su un altro PC, copia o clona il repository, mantenendo la cartella `gazebo/worlds` e gli script in `scripts`. Non serve installare ROS o Gazebo dentro Windows: vengono installati nella distribuzione Ubuntu 22.04.

Then open the Ubuntu 22.04 shell and run:

```bash
lsb_release -a
```

Expected: Ubuntu 22.04 LTS.

## 2) Update the system

```bash
sudo apt update
sudo apt upgrade -y
```

If you do not have a sudo password, use the root session first:

```bash
sudo -i
```

or, during setup, run the installer commands as root.

## 3) Install basic tools

```bash
sudo apt install -y curl gnupg software-properties-common ca-certificates lsb-release
```

## 4) Add the ROS 2 package source

```bash
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list
```

## 5) Install ROS 2 Humble

```bash
sudo apt update
sudo apt install -y ros-humble-desktop
```

Then load ROS in each terminal:

```bash
source /opt/ros/humble/setup.bash
```

Add it to your shell startup:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 6) Install Gazebo and ROS Gazebo integration

```bash
sudo apt install -y gazebo ros-humble-gazebo-ros-pkgs ros-humble-gazebo-plugins ros-humble-gazebo-ros2-control
```

Then verify the installation:

```bash
gazebo --version
ros2 pkg list | grep gazebo
```

## 7) Launch the simulator

From the repository, start the included 3D world:

```bash
cd /mnt/c/Drone-HIL-Automation-Lab
source /opt/ros/humble/setup.bash
bash scripts/run_gazebo_3d.sh
```

The world contains a ground plane, landing pad, trees, a warehouse and a drone model. For a quick black-box test, keep Gazebo open and run in a second terminal:

```bash
source /opt/ros/humble/setup.bash
cd /mnt/c/Drone-HIL-Automation-Lab
python3 tests/gazebo_smoke_test.py
```

The smoke test checks that the drone model is loaded and that Gazebo publishes its odometry at 3 m. The movement test applies a controlled force and verifies a positive X displacement. To drive the drone manually, run `python3 scripts/manual_drone_control.py` in a second terminal. Keys are `w/s`, `a/d`, `r/f` and `q/e`.

The current keyboard control is direct force control, with a 20 x 16 m visible area and a 1-8 m altitude envelope. It is not a complete flight controller. Stabilized flight, assisted takeoff/landing and collision avoidance require PX4/SITL or a dedicated ROS 2 controller. PX4 Position mode is the real-world reference: centered sticks hold position, while parameters limit acceleration, velocity and vertical speed.

Run `python3 scripts/gazebo_boundary_guard.py` in a separate terminal to enforce the envelope continuously, even when the keyboard controller is closed.

## 8) Modify the simulator and tests

- `gazebo/worlds/drone_lab.world`: visual world and drone model.
- The world includes a visible 20 x 16 m boundary; `reset_world` restores the drone to its initial center pose.
- `tests/gazebo_smoke_test.py`: integration commands sent to the running Gazebo instance.
- `scripts/manual_drone_control.py`: keyboard force controller with boundary recovery.
- `src/drone_simulator/simulator.py`: offline flight state machine.
- `tests/test_drone_simulator.py`: offline unit tests.

## 9) Optional: PX4 SITL integration

If you want a proper drone controller in Gazebo:

```bash
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
make px4_sitl_default gazebo
```

This is the real drone-cockpit workflow for flight simulation.

## 10) Why this is the correct path

This setup is the real 3D simulator flow:
- actual 3D world rendering
- drone model support
- realistic spatial movement
- testable flight logic
- industrial-style simulation stack

It is heavier than the simple Tkinter version, but it is the one that matches the Gazebo 3D requirement.
