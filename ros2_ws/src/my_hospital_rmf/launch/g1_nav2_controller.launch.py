import os

from ament_index_python.packages import (
    get_package_share_directory,
)

from launch import LaunchDescription

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

    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        output="screen",
        arguments=[
            "--ros-args",
            "--log-level",
            "debug",
        ],
        parameters=[
            params_file,
        ],
        remappings=[
            (
                "/cmd_vel",
                "/hospital_robot_1/nav2_cmd_vel",
            ),
        ],
    )

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_controller",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "node_names": [
                    "controller_server",
                ],
            }
        ],
    )

    return LaunchDescription([
        controller_server,
        lifecycle_manager,
    ])
