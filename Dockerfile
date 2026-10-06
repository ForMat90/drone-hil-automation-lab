# Gazebo 11 + ROS 2 Humble + the HTTP bridge in one headless image, so the
# flight environment is identical on any machine and needs no WSL setup.
FROM ros:humble-ros-base-jammy

# ros-humble-gazebo-ros-pkgs was removed from packages.ros.org after Gazebo
# Classic reached end of life, so apt-get exits 100. Gazebo 11 itself is still
# in Ubuntu 22.04. Tag 3.9.0 is the last gazebo_ros_pkgs release shipped for Humble.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gazebo \
        libgazebo-dev \
        git \
        python3-colcon-common-extensions \
        python3-rosdep \
    && (rosdep init || true) \
    && rosdep update \
    && git clone --depth 1 --branch 3.9.0 \
        https://github.com/ros-simulation/gazebo_ros_pkgs.git /opt/gazebo_ros_ws/src/gazebo_ros_pkgs \
    && rosdep install --from-paths /opt/gazebo_ros_ws/src --ignore-src -y --rosdistro humble \
    && rm -rf /var/lib/apt/lists/*

# The world only loads libgazebo_ros_force.so and libgazebo_ros_p3d.so.
# Building every plugin in the package is what stalled Docker.
ENV GAZEBO_PLUGIN_PATH=/opt/gazebo_ros_ws/install/lib
RUN bash -c "source /opt/ros/humble/setup.bash \
    && cd /opt/gazebo_ros_ws \
    && export CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 \
    && colcon build --merge-install --parallel-workers 1 \
        --packages-select gazebo_dev gazebo_msgs gazebo_ros \
        --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    && source /opt/gazebo_ros_ws/install/setup.bash \
    && cmake -S /opt/gazebo_ros_ws/src/gazebo_ros_pkgs/gazebo_plugins -B /tmp/gzplug \
        -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    && cmake --build /tmp/gzplug --target gazebo_ros_force gazebo_ros_p3d -j1 \
    && cp /tmp/gzplug/libgazebo_ros_force.so /tmp/gzplug/libgazebo_ros_p3d.so /opt/gazebo_ros_ws/install/lib/" \
    && rm -rf /opt/gazebo_ros_ws/build /opt/gazebo_ros_ws/log /opt/gazebo_ros_ws/src /tmp/gzplug

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
