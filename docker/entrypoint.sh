#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/humble/setup.bash
# Plugins built in the image, because the Humble debs no longer exist.
source /opt/gazebo_ros_ws/install/setup.bash
export GAZEBO_PLUGIN_PATH="/opt/gazebo_ros_ws/install/lib${GAZEBO_PLUGIN_PATH:+:$GAZEBO_PLUGIN_PATH}"

# DRONE_GUI=true also opens the Gazebo window. It needs the host graphics
# channel mounted into the container: see docker-compose.gui.yml.
gui="${DRONE_GUI:-false}"
if [[ "${gui}" == "true" ]]; then
  # No GPU is exposed to the container, so Ogre has to render in software.
  export LIBGL_ALWAYS_SOFTWARE=1
  export QT_X11_NO_MITSHM=1
  export OGRE_RTT_MODE="${OGRE_RTT_MODE:-Copy}"
fi

ros2 launch gazebo_ros gazebo.launch.py \
  world:=/app/gazebo/worlds/drone_lab.world \
  gui:="${gui}" \
  pause:=false &

# The tests read "the bridge answers" as "the world is ready", so hold the
# bridge back until Gazebo actually publishes the drone odometry.
for _ in $(seq 120); do
  if ros2 topic list 2>/dev/null | grep -qx '/drone/odom'; then
    break
  fi
  sleep 1
done

cd /app/src
exec python3 -u -m drone_simulator.ros.bridge_server
