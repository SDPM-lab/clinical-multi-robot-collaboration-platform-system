#!/usr/bin/env bash

set -e

PROJECT_ROOT="$HOME/clinical-multi-robot-collaboration-platform-system"

echo "========================================"
echo " Starting Hospital RMF System"
echo "========================================"

source "$PROJECT_ROOT/scripts/hospital_env.sh"

echo
echo "[1/2] Checking leftover processes..."

if pgrep -f "gz sim server" >/dev/null \
  || pgrep -f "hospital_fleet_adapter" >/dev/null \
  || pgrep -f "rmf_task_dispatcher" >/dev/null; then

    echo "Old Hospital processes detected."
    echo "Cleaning them first..."

    "$PROJECT_ROOT/scripts/stop_hospital.sh"
fi

echo
echo "[2/2] Launching Hospital simulation..."

cd "$PROJECT_ROOT/ros2_ws"

exec ros2 launch my_hospital_rmf hospital.launch.py \
  use_sim_time:=true