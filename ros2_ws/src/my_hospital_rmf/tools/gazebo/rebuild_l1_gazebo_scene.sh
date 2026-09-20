#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PKG_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REPO="$(cd -- "$PKG_ROOT/../../.." && pwd)"
TOOLS="$SCRIPT_DIR"
BUILDING="$PKG_ROOT/maps/L1.building.yaml"
WORLD="$PKG_ROOT/maps/L1.world"
MODELS="$PKG_ROOT/models"
NAV_GRAPHS="$PKG_ROOT/nav_graphs"
FLEET_CONFIG="$PKG_ROOT/config/fleet_config.yaml"
PROPS_CONFIG="$PKG_ROOT/config/props.yaml"
WITH_NAV_OVERLAY=true

if [[ "${1:-}" == "--without-nav-overlay" ]]; then
  WITH_NAV_OVERLAY=false
elif [[ "${1:-}" == "--help" ]]; then
  echo "Usage: $0 [--without-nav-overlay]"
  exit 0
elif [[ $# -gt 0 ]]; then
  echo "Unknown option: $1" >&2
  echo "Usage: $0 [--without-nav-overlay]" >&2
  exit 2
fi

for required_file in "$BUILDING" "$FLEET_CONFIG" "$PROPS_CONFIG"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Required input not found: $required_file" >&2
    exit 1
  fi
done

cd "$REPO"
set +u
source /opt/ros/jazzy/setup.bash
set -u

echo "[1/7] Generate L1 Gazebo world and building model..."
ros2 run rmf_building_map_tools building_map_generator gazebo \
  "$BUILDING" \
  "$WORLD" \
  "$MODELS"

echo "[2/7] Resolve OpenRobotics model URIs through Gazebo Fuel..."
python3 "$TOOLS/patch_fuel_uris.py"

echo "[3/7] Generate RMF navigation graphs..."
ros2 run rmf_building_map_tools building_map_generator nav \
  "$BUILDING" \
  "$NAV_GRAPHS"

if [[ "$WITH_NAV_OVERLAY" == true ]]; then
  echo "[4/7] Generate the optional Gazebo navigation overlay..."
  python3 "$TOOLS/generate_nav_overlay_model.py"

  echo "[5/7] Add the navigation overlay to L1.world..."
  python3 "$TOOLS/add_nav_overlay.py"
else
  echo "[4/7] Skip the optional Gazebo navigation overlay"
  echo "[5/7] No navigation overlay to add"
fi

echo "[6/7] Add robots declared in fleet_config.yaml..."
python3 "$TOOLS/add_fleet_robots.py"

echo "[7/7] Apply model replacements and scaling from props.yaml..."
python3 "$TOOLS/patch_props.py"

echo "Done."
echo "  L1.world       → maps/L1.world"
echo "  Gazebo models  → models/"
echo "  Robot nav graph  → nav_graphs/0.yaml"
echo "  Actor path graph → nav_graphs/1.yaml"
echo "  Robots         → from config/fleet_config.yaml"
echo "  Nav overlay    → $WITH_NAV_OVERLAY"
