#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
BUILDING="${REPO_ROOT}/ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml"
OUTPUT="${REPO_ROOT}/ros2_ws/src/my_hospital_rmf/nav_graphs_generated"

set +u
source /opt/ros/jazzy/setup.bash
set -u
ros2 run rmf_building_map_tools building_map_generator nav "${BUILDING}" "${OUTPUT}"
python3 "${SCRIPT_DIR}/convert-rmf-navigation.py"
