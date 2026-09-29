#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script as root: wsl -d Ubuntu -u root" >&2
  exit 1
fi

if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo "Detected: $NAME $VERSION_ID"
fi

if [ "${VERSION_ID:-}" != "22.04" ]; then
  echo "WARNING: Gazebo/ROS 2 Humble is best supported on Ubuntu 22.04 LTS."
  echo "This script is intended for a clean Ubuntu 22.04 environment."
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl gnupg software-properties-common ca-certificates lsb-release

curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" > /etc/apt/sources.list.d/ros2.list

apt-get update
apt-get install -y ros-humble-desktop

apt-get install -y gazebo ros-humble-gazebo-ros-pkgs ros-humble-gazebo-plugins ros-humble-gazebo-ros2-control

printf "\nSetup complete. Load ROS with:\n"
printf "  source /opt/ros/humble/setup.bash\n"
printf "\nStart Gazebo with:\n"
printf "  gazebo\n"
printf "\nOr with ROS launch:\n"
printf "  source /opt/ros/humble/setup.bash\n"
printf "  ros2 launch gazebo_ros gz_sim.launch.py\n"
