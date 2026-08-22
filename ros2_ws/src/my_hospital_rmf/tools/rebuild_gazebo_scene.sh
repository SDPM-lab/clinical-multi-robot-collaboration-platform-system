#!/usr/bin/env bash
set -e

REPO=~/clinical-multi-robot-collaboration-platform-system
TOOLS=$REPO/ros2_ws/src/my_hospital_rmf/tools

cd "$REPO"
source /opt/ros/jazzy/setup.bash

echo "[1/5] Generate Gazebo hospital map..."
ros2 run rmf_building_map_tools building_map_generator gazebo \
  ros2_ws/src/my_hospital_rmf/maps/hospital.building.yaml \
  ros2_ws/src/my_hospital_rmf/maps/hospital.world \
  ros2_ws/src/my_hospital_rmf/models

echo "[2/5] Patch model:// URIs → Fuel URIs..."
python3 "$TOOLS/patch_fuel_uris.py"

echo "[3/5] Generate nav graph overlay model..."
python3 "$TOOLS/generate_nav_overlay_model.py"

echo "[4/5] Patch hospital.world: nav overlay + robots..."
python3 "$TOOLS/patch_world.py"

echo "[5/5] Generate nav graphs..."
ros2 run rmf_building_map_tools building_map_generator nav \
  ros2_ws/src/my_hospital_rmf/maps/hospital.building.yaml \
  ros2_ws/src/my_hospital_rmf/nav_graphs

echo "[+]   Patch hospital.world: extra props from props.yaml..."
python3 "$TOOLS/patch_props.py"

echo "Done."
echo "  hospital.world → maps/hospital.world"
echo "  Gazebo models  → models/"
echo "  Nav graphs     → nav_graphs/0.yaml"
echo "  Robots         → from config/fleet_config.yaml"
