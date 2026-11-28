import os
import yaml

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    TimerAction,
    RegisterEventHandler,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


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

    # --------------------------------------------------
    # Debug / performance test robot limit
    #
    # robots:=all  -> all enabled robots (default)
    # robots:=1    -> first enabled robot only
    # robots:=N    -> first N enabled robots
    # --------------------------------------------------

    robot_limit_raw = (
        LaunchConfiguration(
            "robots"
        ).perform(context).strip().lower()
    )

    if robot_limit_raw != "all":
        try:
            robot_limit = int(robot_limit_raw)
        except ValueError:
            raise RuntimeError(
                "robots must be 'all' or an integer >= 1"
            )

        if robot_limit < 1:
            raise RuntimeError(
                "robots must be >= 1"
            )

        if robot_limit > len(enabled_robots):
            raise RuntimeError(
                f"robots={robot_limit} exceeds "
                f"enabled fleet size={len(enabled_robots)}"
            )

        enabled_robots = enabled_robots[:robot_limit]

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

    # --------------------------------------------------
    # Fleet-level sequential controller startup
    #
    # Each G1 child launch only spawns the robot.
    # Controller spawners are created here and started
    # strictly one at a time:
    #
    # R1 JSB -> R1 Diff -> R2 JSB -> R2 Diff -> ...
    # --------------------------------------------------

    joint_spawners = []
    diff_spawners = []

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
                    "robot_model": LaunchConfiguration("robot_model"),
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

                    "start_controllers":
                        "false",
                }.items(),
            )
        )

        joint_spawners.append(
            Node(
                package="controller_manager",
                executable="spawner",
                namespace=robot_id,
                name="fleet_spawner_joint_state_broadcaster",
                output="screen",
                arguments=[
                    "joint_state_broadcaster",
                    "--controller-manager",
                    f"/{robot_id}/controller_manager",
                    "--controller-manager-timeout",
                    "120",
                    "--service-call-timeout",
                    "60",
                    "--switch-timeout",
                    "60",
                ],
                parameters=[{
                    "use_sim_time": True,
                }],
            )
        )

        diff_spawners.append(
            Node(
                package="controller_manager",
                executable="spawner",
                namespace=robot_id,
                name="fleet_spawner_diff_drive_controller",
                output="screen",
                arguments=[
                    "diff_drive_controller",
                    "--controller-manager",
                    f"/{robot_id}/controller_manager",
                    "--controller-manager-timeout",
                    "120",
                    "--service-call-timeout",
                    "60",
                    "--switch-timeout",
                    "60",
                ],
                parameters=[{
                    "use_sim_time": True,
                }],
            )
        )

    # --------------------------------------------------
    # Sequential controller event chain
    # --------------------------------------------------

    if joint_spawners:

        # Give Gazebo / gz_ros2_control time to create all
        # controller_manager services. Only the first spawner
        # needs a timer; all following spawners are event-driven.
        actions.append(
            TimerAction(
                period=15.0,
                actions=[
                    joint_spawners[0],
                ],
            )
        )

        for index in range(
            len(joint_spawners)
        ):

            # JSB_i finished -> DiffDrive_i
            actions.append(
                RegisterEventHandler(
                    OnProcessExit(
                        target_action=joint_spawners[index],
                        on_exit=[
                            diff_spawners[index],
                        ],
                    )
                )
            )

            # DiffDrive_i finished -> JSB_(i+1)
            if index + 1 < len(joint_spawners):
                actions.append(
                    RegisterEventHandler(
                        OnProcessExit(
                            target_action=diff_spawners[index],
                            on_exit=[
                                joint_spawners[index + 1],
                            ],
                        )
                    )
                )

    return actions


def generate_launch_description():

    return LaunchDescription([
        DeclareLaunchArgument(
            "robot_model",
            default_value="lightweight",
            choices=["full", "lightweight"],
        ),

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

        DeclareLaunchArgument(
            "robots",
            default_value="all",
            description=(
                "Number of enabled robots to launch. "
                "Use 'all' for the full fleet."
            ),
        ),

        OpaqueFunction(
            function=launch_setup
        ),
    ])
