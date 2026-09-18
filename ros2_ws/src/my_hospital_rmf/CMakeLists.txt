cmake_minimum_required(VERSION 3.8)
project(my_hospital_rmf)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    maps
    nav_graphs
    config
    models
    rviz
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS scripts/hospital_fake_robot_state_publisher.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_fake_robot_state_publisher)

install(PROGRAMS scripts/hospital_fake_door_adapter.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_fake_door_adapter)

install(PROGRAMS scripts/hospital_ros_api_bridge.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_ros_api_bridge)

install(PROGRAMS scripts/hospital_rosbridge_ws_adapter.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_rosbridge_ws_adapter)

install(PROGRAMS scripts/hospital_rule_dispatcher.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_rule_dispatcher)

install(PROGRAMS scripts/hospital_scheduler_dispatcher_v2.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_scheduler_dispatcher_v2)

install(PROGRAMS scripts/hospital_cleanup_gazebo_runtime.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_cleanup_gazebo_runtime)

install(PROGRAMS tools/sync_gazebo_to_traffic_editor.py
  DESTINATION lib/${PROJECT_NAME} RENAME sync_gazebo_to_traffic_editor)

install(
  DIRECTORY scripts/scheduler/
  DESTINATION lib/${PROJECT_NAME}/scheduler
  FILES_MATCHING
    PATTERN "*.py"
)


# Scheduler v2 Python modules
install(
  DIRECTORY scripts/scheduler_v2/
  DESTINATION lib/${PROJECT_NAME}/scheduler_v2
  FILES_MATCHING
    PATTERN "*.py"
)

# RL v2 Python modules
install(
  DIRECTORY scripts/rl_v2/
  DESTINATION lib/${PROJECT_NAME}/rl_v2
  FILES_MATCHING
    PATTERN "*.py"
)

# Frozen RL models used by the formal scheduler
install(
  FILES
    scripts/rl_v2/models/long_horizon_ppo_102k_seed42.zip
    scripts/rl_v2/models/reassignment_ppo_shaping025_102k_seed42.zip
  DESTINATION share/${PROJECT_NAME}/rl_v2/models
)


install(PROGRAMS scripts/hospital_fleet_adapter.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_fleet_adapter)

ament_package()