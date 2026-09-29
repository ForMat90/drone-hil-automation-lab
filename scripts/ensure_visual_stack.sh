#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export PYTHONPATH="${repo_root}/src:${PYTHONPATH:-}"

mkdir -p "${repo_root}/.run"

if ! pgrep -x gzserver >/dev/null 2>&1; then
  nohup bash "${repo_root}/scripts/run_gazebo_3d.sh" \
    > "${repo_root}/.run/gazebo.log" 2>&1 &
  echo $! > "${repo_root}/.run/gazebo.pid"
fi

if ! pgrep -f "scripts/drone_web_control.py" >/dev/null 2>&1; then
  nohup python3 "${repo_root}/scripts/drone_web_control.py" \
    > "${repo_root}/.run/web_control.log" 2>&1 &
  echo $! > "${repo_root}/.run/web_control.pid"
fi

for _ in $(seq 1 60); do
  if python3 - <<'PY'
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8765/api/pose", timeout=1)
PY
  then
    echo "Gazebo + pannello comandi pronti su http://127.0.0.1:8765"
    exit 0
  fi
  sleep 1
done

echo "Timeout: Gazebo/ROS o il pannello web non sono partiti. Vedi .run/*.log" >&2
exit 1
