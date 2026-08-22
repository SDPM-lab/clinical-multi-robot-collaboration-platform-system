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
install(PROGRAMS scripts/hospital_ros_api_bridge.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_ros_api_bridge)
install(PROGRAMS scripts/hospital_rosbridge_ws_adapter.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_rosbridge_ws_adapter)
install(PROGRAMS scripts/hospital_rule_dispatcher.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_rule_dispatcher)
install(PROGRAMS scripts/hospital_cleanup_gazebo_runtime.py
  DESTINATION lib/${PROJECT_NAME} RENAME hospital_cleanup_gazebo_runtime)
install(PROGRAMS tools/sync_gazebo_to_traffic_editor.py
  DESTINATION lib/${PROJECT_NAME} RENAME sync_gazebo_to_traffic_editor)

ament_package()
