# Apre la finestra 3D di Gazebo con il mondo del drone. Va lanciato per primo.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxRepo = '/mnt/' + $repo.Substring(0, 1).ToLower() + $repo.Substring(2).Replace('\', '/')
wsl.exe -d Ubuntu-22.04 -- bash -lc "pkill -x gzclient >/dev/null 2>&1 || true; pkill -x gzserver >/dev/null 2>&1 || true; source /opt/ros/humble/setup.bash; bash '$linuxRepo/scripts/run_gazebo_3d.sh'"
