# Gazebo 11 + ROS 2 Humble + the HTTP bridge in one headless image, so the
# flight environment is identical on any machine and needs no WSL setup.
FROM ros:humble-ros-base-jammy

# ros-humble-gazebo-ros-pkgs was removed from packages.ros.org after Gazebo
# Classic reached end of life, so apt-get exits 100. Gazebo 11 itself is still
# in Ubuntu 22.04; the two plugins this world loads are built from the humble
# branch of gazebo_ros_pkgs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gazebo \
        libgazebo-dev \
        git \
        python3-colcon-common-extensions \
        python3-rosdep \
    && rosdep init || true \
    && rosdep update \
    && git clone --depth 1 --branch humble \
        https://github.com/ros-simulation/gazebo_ros_pkgs.git /tmp/gazebo_ros_pkgs \
    && rosdep install --from-paths /tmp/gazebo_ros_pkgs --ignore-src -y --rosdistro humble \
    && mkdir -p /opt/gazebo_ros_ws/src \
    && mv /tmp/gazebo_ros_pkgs /opt/gazebo_ros_ws/src/gazebo_ros_pkgs \
    && bash -c "source /opt/ros/humble/setup.bash \
        && cd /opt/gazebo_ros_ws \
        && colcon build --merge-install --cmake-args -DCMAKE_BUILD_TYPE=Release" \
    && rm -rf /opt/gazebo_ros_ws/build /opt/gazebo_ros_ws/log /opt/gazebo_ros_ws/src /var/lib/apt/lists/*

# Keep DDS discovery inside the container, and never reach for the online model
# database: the world only uses sun and ground_plane, which ship with Gazebo.
ENV ROS_LOCALHOST_ONLY=1 \
    GAZEBO_MODEL_DATABASE_URI=""

WORKDIR /app
COPY gazebo ./gazebo
COPY src ./src
COPY docker/entrypoint.sh /usr/local/bin/drone-entrypoint
RUN chmod +x /usr/local/bin/drone-entrypoint

EXPOSE 8765
CMD ["/usr/local/bin/drone-entrypoint"]
