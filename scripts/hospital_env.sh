#!/usr/bin/env bash

PROJECT_ROOT="$HOME/clinical-multi-robot-collaboration-platform-system"
ROS_WS="$PROJECT_ROOT/ros2_ws"

source /opt/ros/jazzy/setup.bash
source "$ROS_WS/install/setup.bash"

export ROS_DOMAIN_ID=22
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>200</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'

# Keep Gazebo Transport on the local machine.
export GZ_IP=127.0.0.1

export GZ_SIM_RESOURCE_PATH="$ROS_WS/src/my_hospital_rmf/models:$GZ_SIM_RESOURCE_PATH"

echo "========================================"
echo " Hospital RMF Environment Loaded"
echo " PROJECT_ROOT=$PROJECT_ROOT"
echo " ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo " RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
echo "========================================"