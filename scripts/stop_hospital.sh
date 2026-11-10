#!/usr/bin/env bash

echo "========================================"
echo " Stopping Hospital RMF System"
echo "========================================"

# --------------------------------------------------
# 1. Stop main hospital launch process
# --------------------------------------------------
echo "[1/4] Stopping main launch..."

pkill -TERM -f "ros2 launch my_hospital_rmf hospital.launch.py" \
  2>/dev/null || true

sleep 2


# --------------------------------------------------
# 2. Stop Hospital / RMF processes
#    Also cleans orphaned processes
# --------------------------------------------------
echo "[2/4] Stopping RMF / Hospital nodes..."

pkill -TERM -f "/my_hospital_rmf/hospital_fleet_adapter" \
  2>/dev/null || true

pkill -TERM -f "rmf_demos_fleet_adapter/fleet_manager" \
  2>/dev/null || true

pkill -TERM -f "rmf_task_ros2/rmf_task_dispatcher" \
  2>/dev/null || true

pkill -TERM -f "/my_hospital_rmf/hospital_g1_navigation_bridge" \
  2>/dev/null || true

pkill -TERM -f "/my_hospital_rmf/hospital_rosbridge_ws_adapter" \
  2>/dev/null || true

pkill -TERM -f "/my_hospital_rmf/hospital_fake_door_adapter" \
  2>/dev/null || true

pkill -TERM -f "rmf_traffic_schedule" \
  2>/dev/null || true

pkill -TERM -f "rmf_traffic_blockade" \
  2>/dev/null || true

sleep 2


# --------------------------------------------------
# 3. Stop Gazebo
# --------------------------------------------------
echo "[3/4] Stopping Gazebo..."

pkill -TERM -f "gz sim server" 2>/dev/null || true
pkill -TERM -f "gz sim gui" 2>/dev/null || true
pkill -TERM -f "gzserver" 2>/dev/null || true
pkill -TERM -f "gzclient" 2>/dev/null || true

sleep 2


# --------------------------------------------------
# Force kill leftovers
# --------------------------------------------------
pkill -KILL -f "ros2 launch my_hospital_rmf hospital.launch.py" \
  2>/dev/null || true

pkill -KILL -f "/my_hospital_rmf/hospital_fleet_adapter" \
  2>/dev/null || true

pkill -KILL -f "rmf_demos_fleet_adapter/fleet_manager" \
  2>/dev/null || true

pkill -KILL -f "rmf_task_ros2/rmf_task_dispatcher" \
  2>/dev/null || true

pkill -KILL -f "/my_hospital_rmf/hospital_g1_navigation_bridge" \
  2>/dev/null || true

pkill -KILL -f "/my_hospital_rmf/hospital_rosbridge_ws_adapter" \
  2>/dev/null || true

pkill -KILL -f "/my_hospital_rmf/hospital_fake_door_adapter" \
  2>/dev/null || true

pkill -KILL -f "rmf_traffic_schedule" \
  2>/dev/null || true

pkill -KILL -f "rmf_traffic_blockade" \
  2>/dev/null || true

pkill -KILL -f "gz sim server" 2>/dev/null || true
pkill -KILL -f "gz sim gui" 2>/dev/null || true


# --------------------------------------------------
# 4. Verification
# --------------------------------------------------
echo "[4/4] Checking remaining processes..."
echo

REMAINING=$(pgrep -af \
"hospital.launch.py|hospital_fleet_adapter|fleet_manager|rmf_task_dispatcher|hospital_g1_navigation_bridge|hospital_rosbridge_ws_adapter|hospital_fake_door_adapter|rmf_traffic_schedule|rmf_traffic_blockade|gz sim server|gz sim gui" \
|| true)

if [ -z "$REMAINING" ]; then
    echo "OK: Hospital RMF system completely stopped."
else
    echo "WARNING: Some related processes are still running:"
    echo "$REMAINING"
fi

echo
echo "========================================"
echo " Hospital RMF Stop Finished"
echo "========================================"