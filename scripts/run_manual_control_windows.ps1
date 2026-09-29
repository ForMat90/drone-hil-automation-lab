# Pilotaggio manuale del drone con la tastiera (Gazebo deve essere gia aperto).
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + $repo.Substring(2).Replace('\', '/')
# Lanciato da src/ cosi "python3 -m" trova il pacchetto senza toccare il PYTHONPATH di ROS.
wsl.exe -d Ubuntu-22.04 -- bash -lc "source /opt/ros/humble/setup.bash; cd '$linuxRepo/src'; python3 -m drone_simulator.ros.manual_control"
