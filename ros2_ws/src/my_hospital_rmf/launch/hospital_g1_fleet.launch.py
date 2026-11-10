import os
import yaml

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def as_bool(value):
    return str(value).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def launch_setup(context, *args, **kwargs):

    package_share = get_package_share_directory(
        "my_hospital_rmf"
    )

    models_path = os.path.join(
        package_share,
        "models",
    )

    existing_resource_path = os.environ.get(
        "GZ_SIM_RESOURCE_PATH",
        "",
    )

    resource_paths = [
        models_path,
    ]

    if existing_resource_path:
        resource_paths.append(existing_resource_path)

    os.environ["GZ_SIM_RESOURCE_PATH"] = os.pathsep.join(
        resource_paths
    )

    print(
        "GZ_SIM_RESOURCE_PATH =",
        os.environ["GZ_SIM_RESOURCE_PATH"],
    )

    fleet_path = os.path.join(
        package_share,
        "config",
        "fleet_instances.yaml",
    )

    robot_launch_path = os.path.join(
        package_share,
        "launch",
        "g1_hospital_robot.launch.py",
    )

    # --------------------------------------------------
    # 外部決定 fleet 是否負責啟動 Gazebo world
    # --------------------------------------------------

    fleet_start_world = as_bool(
        LaunchConfiguration(
            "start_world"
        ).perform(context)
    )

    fleet_config = load_yaml(
        fleet_path
    )

    robots = fleet_config.get(
        "robots",
        {},
    )

    enabled_robots = []

    for robot_id, config in robots.items():

        if config.get(
            "enabled",
            True,
        ):
            enabled_robots.append(
                (robot_id, config)
            )

    if not enabled_robots:
        raise RuntimeError(
            "fleet_instances.yaml 裡沒有 enabled robot"
        )

    actions = []

    actions.append(
        LogInfo(
            msg=[
                "\n========================================\n",
                "Hospital G1 Fleet\n",
                f"Enabled robots: {len(enabled_robots)}\n",
                f"Fleet starts world: {fleet_start_world}\n",
                "========================================"
            ]
        )
    )

    for index, (
        robot_id,
        config,
    ) in enumerate(enabled_robots):

        robot_type = config.get(
            "type"
        )

        if not robot_type:
            raise RuntimeError(
                f"{robot_id}: missing type"
            )

        model = config.get(
            "model",
            "agibot_g1",
        )

        if model != "agibot_g1":
            raise RuntimeError(
                f"{robot_id}: unsupported model "
                f"'{model}' in G1 fleet launcher"
            )

        spawn = config.get(
            "spawn",
            {},
        )

        x = str(
            spawn.get("x", 0.0)
        )

        y = str(
            spawn.get("y", 0.0)
        )

        z = str(
            spawn.get("z", 0.2)
        )

        yaw = str(
            spawn.get("yaw", 0.0)
        )

        # --------------------------------------------------
        # fleet 本身負責 world 時：
        #   只有第一台 G1 啟動 world
        #
        # fleet_start_world=false 時：
        #   所有 G1 都只 spawn，不再啟動第二套 Gazebo
        # --------------------------------------------------

        robot_start_world = (
            fleet_start_world
            and
            index == 0
        )

        start_world = (
            "true"
            if robot_start_world
            else "false"
        )

        actions.append(
            LogInfo(
                msg=[
                    f"[Fleet] {robot_id}",
                    f" | type={robot_type}",
                    f" | spawn=({x}, {y}, {z})",
                    f" | start_world={start_world}",
                ]
            )
        )

        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    robot_launch_path
                ),
                launch_arguments={
                    "instance_name":
                        robot_id,

                    "robot_type":
                        robot_type,

                    "x":
                        x,

                    "y":
                        y,

                    "z":
                        z,

                    "yaw":
                        yaw,

                    "start_world":
                        start_world,
                }.items(),
            )
        )

    return actions


def generate_launch_description():

    return LaunchDescription([

        DeclareLaunchArgument(
            "start_world",
            default_value="true",
            description=(
                "Whether this fleet launcher "
                "should start Gazebo world. "
                "Set false when included by "
                "hospital.launch.py."
            ),
        ),

        OpaqueFunction(
            function=launch_setup
        ),
    ])
