# Gazebo 11 + ROS 2 Humble + the HTTP bridge in one headless image, so the
# flight environment is identical on any machine and needs no WSL setup.
FROM ros:humble-ros-base-jammy

# gazebo_ros_pkgs brings Gazebo 11 and the force/p3d plugins the world loads.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ros-humble-gazebo-ros-pkgs \
    && rm -rf /var/lib/apt/lists/*

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
