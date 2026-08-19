#!/usr/bin/env bash
set -e

cd ~/clinical-multi-robot-collaboration-platform-system

source /opt/ros/jazzy/setup.bash
source ~/rmf_ws/install/setup.bash

echo "[1/3] Generate Gazebo hospital map..."
ros2 run rmf_building_map_tools building_map_generator gazebo \
  ros2_ws/src/my_hospital_rmf/maps/hospital.building.yaml \
  ros2_ws/src/my_hospital_rmf/maps/hospital.world \
  ros2_ws/src/my_hospital_rmf/models

echo "[2/3] Generate nav graph overlay model..."
python3 ros2_ws/src/my_hospital_rmf/tools/generate_nav_overlay_model.py

echo "[3/3] Add nav overlay include to hospital.world..."
python3 - <<'PY'
from pathlib import Path

world_path = Path("ros2_ws/src/my_hospital_rmf/maps/hospital.world")
text = world_path.read_text(encoding="utf-8")

overlay_include = """    <include>
      <name>hospital_nav_overlay</name>
      <uri>model://hospital_nav_overlay</uri>
    </include>
"""

if "model://hospital_nav_overlay" in text:
    print("hospital_nav_overlay already exists")
else:
    marker = "    <rmf_charger_waypoints"
    if marker in text:
        text = text.replace(marker, overlay_include + marker)
    else:
        text = text.replace("  </world>", overlay_include + "  </world>")

    world_path.write_text(text, encoding="utf-8")
    print("Added hospital_nav_overlay to hospital.world")
PY

echo "Done."
