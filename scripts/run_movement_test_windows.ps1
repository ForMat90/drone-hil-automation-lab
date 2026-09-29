$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + $repo.Substring(2).Replace('\', '/')
wsl.exe -d Ubuntu-22.04 -- bash -lc "source /opt/ros/humble/setup.bash; python3 '$linuxRepo/tests/gazebo_movement_test.py'"
