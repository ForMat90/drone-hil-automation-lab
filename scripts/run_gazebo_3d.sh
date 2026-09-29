#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash

# A previous crashed GUI leaves gzserver running and the next client dies immediately.
pkill -x gzclient >/dev/null 2>&1 || true
pkill -x gzserver >/dev/null 2>&1 || true
sleep 1

# Software GL (llvmpipe) is what triggers the Ogre AxisAlignedBox assert in WSLg.
# Use the WSLg GPU path unless the user explicitly forces software rendering.
if [[ "${LIBGL_ALWAYS_SOFTWARE:-}" == "1" ]]; then
  export LIBGL_ALWAYS_SOFTWARE=1
else
  unset LIBGL_ALWAYS_SOFTWARE
fi
export QT_X11_NO_MITSHM=1
export OGRE_RTT_MODE="${OGRE_RTT_MODE:-Copy}"

ros2 launch gazebo_ros gazebo.launch.py \
  world:="${repo_root}/gazebo/worlds/drone_lab.world" \
  pause:=false
