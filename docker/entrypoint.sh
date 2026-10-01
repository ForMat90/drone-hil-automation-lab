#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash

# Headless: gzserver only. The world has no camera sensors and the drone flies
# with gravity off, so the physics the tests measure is the same as with the GUI.
ros2 launch gazebo_ros gazebo.launch.py \
  world:=/app/gazebo/worlds/drone_lab.world \
  gui:=false \
  pause:=false &

# The tests read "the bridge answers" as "the world is ready", so hold the
# bridge back until Gazebo actually publishes the drone odometry.
for _ in $(seq 90); do
  if ros2 topic list 2>/dev/null | grep -qx '/drone/odom'; then
    break
  fi
  sleep 1
done

cd /app/src
exec python3 -u -m drone_simulator.ros.bridge_server
