# Avvia a mano il bridge HTTP/ROS. Di solito non serve: lo avviano i test Playwright.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + $repo.Substring(2).Replace('\', '/')
wsl.exe -d Ubuntu-22.04 -- bash -lc "source /opt/ros/humble/setup.bash; cd '$linuxRepo/src'; python3 -u -m drone_simulator.ros.bridge_server"
