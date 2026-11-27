#!/usr/bin/env bash
set -eo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
hospital_dir=${HOSPITAL_WORKSPACE_ROOT:-"$project_dir"}
if [[ -z "$hospital_dir" || ! -r "$hospital_dir/ros2_ws/install/setup.bash" ]]; then
    echo 'Set HOSPITAL_WORKSPACE_ROOT to the built backend project directory.' >&2
    exit 1
fi

cd "$hospital_dir"
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
export DISPLAY="${DISPLAY:-:99}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-101}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export CYCLONEDDS_URI="${HOSPITAL_CYCLONEDDS_URI:-file://$hospital_dir/ros2_ws/src/my_hospital_rmf/config/cyclonedds_7robots.xml}"
export GZ_PARTITION="${HOSPITAL_GZ_PARTITION:-hospital_vnc_$$_$(date +%s)}"
xdpyinfo >/dev/null

package_dir=$(ros2 pkg prefix --share my_hospital_rmf)
export GZ_SIM_RESOURCE_PATH="$package_dir/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
printf 'ROS package: %s\nGazebo partition: %s\n' "$package_dir" "$GZ_PARTITION"

gui_pid=
ros2 launch my_hospital_rmf hospital.launch.py robots:="${HOSPITAL_ROBOTS:-7}" launch_gazebo_gui:=false launch_rviz:=false "$@" &
launch_pid=$!
cleanup() {
    if [[ -n "$gui_pid" ]]; then
        kill -TERM "$gui_pid" 2>/dev/null || true
        wait "$gui_pid" 2>/dev/null || true
    fi
    kill -INT "$launch_pid" 2>/dev/null || true
    wait "$launch_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for ((attempt=0; attempt<75; attempt++)); do
    if ! kill -0 "$launch_pid" 2>/dev/null; then
        wait "$launch_pid"
        exit
    fi
    services=$(timeout 3s gz service -l || true)
    if [[ "$services" == *'/world/sim_world/control'* ]]; then
        bash "$project_dir/scripts/open-gazebo-vnc.sh" &
        gui_pid=$!
        wait -n "$launch_pid" "$gui_pid"
        exit
    fi
    sleep 1
done
echo 'Gazebo world service did not become available.' >&2
exit 1
