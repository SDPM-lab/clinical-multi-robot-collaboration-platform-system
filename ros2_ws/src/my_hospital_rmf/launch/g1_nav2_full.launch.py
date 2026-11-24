import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    TimerAction,
)
from launch.launch_description_sources import (
    PythonLaunchDescriptionSource,
)

from launch_ros.actions import Node


def generate_launch_description():

    pkg = get_package_share_directory(
        "my_hospital_rmf"
    )

    params_file = os.path.join(
        pkg,
        "config",
        "nav2_g1.yaml",
    )

    map_yaml = os.path.join(
        pkg,
        "maps",
        "L1_nav2_live.yaml",
    )

    # ==================================================
    # G1 + Gazebo + ros2_control
    # ==================================================

    g1_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg,
                "launch",
                "g1_hospital_robot.launch.py",
            )
        ),
        launch_arguments={
            "instance_name": "hospital_robot_1",
            "robot_type": "clean",
            "start_world": "true",
        }.items(),
    )

    # ==================================================
    # Map Server
    # ==================================================

    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[
            {
                "yaml_filename": map_yaml,
                "use_sim_time": True,
            }
        ],
    )

    # ==================================================
    # AMCL
    # ==================================================

    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        output="screen",
        parameters=[
            params_file,
        ],
    )

    # ==================================================
    # Planner Server
    # ==================================================

    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        output="screen",
        parameters=[
            params_file,
        ],
    )

    # ==================================================
    # Controller Server
    # ==================================================

    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=[
            (
                "/cmd_vel",
                "/hospital_robot_1/cmd_vel",
            ),
        ],
    )

    # ==================================================
    # Behavior Server
    # ==================================================

    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=[
            (
                "/cmd_vel",
                "/hospital_robot_1/cmd_vel",
            ),
        ],
    )

    # ==================================================
    # BT Navigator
    # ==================================================

    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        output="screen",
        parameters=[
            params_file,
        ],
    )

    # ==================================================
    # Lifecycle Manager
    # ==================================================

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "bond_timeout": 0.0,
                "node_names": [
                    "map_server",
                    "amcl",
                    "planner_server",
                    "controller_server",
                    "behavior_server",
                    "bt_navigator",
                ],
            }
        ],
    )

    # ==================================================
    # Wait for G1 / Gazebo / ros2_control first
    # ==================================================

    nav2_stack = TimerAction(
        period=60.0,
        actions=[
            map_server,
            amcl,
            planner_server,
            controller_server,
            behavior_server,
            bt_navigator,
            lifecycle_manager,
        ],
    )

    return LaunchDescription([
        g1_launch,
        nav2_stack,
    ])
