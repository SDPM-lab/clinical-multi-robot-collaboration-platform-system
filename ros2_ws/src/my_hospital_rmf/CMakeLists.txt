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
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
