import copy
import os

import yaml

from ament_index_python.packages import (
    get_package_share_directory,
)

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    TimerAction,
)
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


# ============================================================
# Multi-robot Nav2
#
# Assumptions:
#
#   1. hospital.launch.py already provides:
#        - Gazebo
#        - 7 robots
#        - /map
#
#   2. Each robot already provides:
#        /hospital_robot_X/scan
#        /hospital_robot_X/diff_drive_controller/odom
#        hospital_robot_X/odom -> hospital_robot_X/base_link
#
#   3. Each g1_hospital_robot.launch.py already provides:
#        /hospital_robot_X/cmd_vel
#          -> twist_stamper
#          -> diff_drive_controller/cmd_vel
#
# This launch therefore ONLY starts Nav2 for each robot.
# ============================================================


def replace_robot_name(value, robot_name):
    """
    Recursively replace hospital_robot_1 in the original
    single-robot Nav2 configuration.
    """

    if isinstance(value, dict):
        return {
            key: replace_robot_name(
                val,
                robot_name,
            )
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            replace_robot_name(
                item,
                robot_name,
            )
            for item in value
        ]

    if isinstance(value, str):
        return value.replace(
            "hospital_robot_1",
            robot_name,
        )

    return value


def make_robot_params(
    template,
    robot_name,
    spawn,
    use_spawn_initial_pose,
):
    """
    Create a namespaced Nav2 parameter file for one robot.
    """

    config = copy.deepcopy(
        template
    )

    config = replace_robot_name(
        config,
        robot_name,
    )

    # --------------------------------------------------------
    # AMCL initial pose
    #
    # true:
    #   Full hospital startup.
    #   Robot is still at its Gazebo spawn pose.
    #
    # false:
    #   Nav2-only restart after the robot has moved.
    #   Do NOT reset AMCL back to the old spawn pose.
    #   AMCL will wait for /initialpose.
    # --------------------------------------------------------

    amcl_params = (
        config[
            "amcl"
        ][
            "ros__parameters"
        ]
    )

    if use_spawn_initial_pose:

        amcl_params[
            "set_initial_pose"
        ] = True

        initial_pose = (
            amcl_params[
                "initial_pose"
            ]
        )

        initial_pose["x"] = float(
            spawn["x"]
        )

        initial_pose["y"] = float(
            spawn["y"]
        )

        initial_pose["z"] = 0.0

        initial_pose["yaw"] = float(
            spawn.get(
                "yaw",
                0.0,
            )
        )

    else:

        amcl_params[
            "set_initial_pose"
        ] = False

    # --------------------------------------------------------
    # The Nav2 nodes run inside:
    #
    #   /hospital_robot_X
    #
    # ROS 2 parameter YAML therefore gets a namespace root.
    # --------------------------------------------------------

    namespaced_config = {
        robot_name: config
    }

    output_path = (
        f"/tmp/{robot_name}_nav2.yaml"
    )

    with open(
        output_path,
        "w",
    ) as f:
        yaml.safe_dump(
            namespaced_config,
            f,
            sort_keys=False,
        )

    return output_path


def make_nav2_stack(
    robot_name,
    params_file,
    delay,
):

    # ========================================================
    # Shared remappings
    #
    # map is global/shared among all seven robots.
    # cmd_vel must go to each robot's own twist_stamper.
    # ========================================================

    map_remap = [
        (
            "map",
            "/map",
        ),
        (
            f"/{robot_name}/map",
            "/map",
        ),
    ]

    cmd_vel_remaps = [
        (
            "cmd_vel",
            f"/{robot_name}/cmd_vel",
        ),
        (
            "/cmd_vel",
            f"/{robot_name}/cmd_vel",
        ),
    ]

    # ========================================================
    # AMCL
    # ========================================================

    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        namespace=robot_name,
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=map_remap,
    )

    # ========================================================
    # Planner
    # ========================================================

    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        namespace=robot_name,
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=map_remap,
    )

    # ========================================================
    # Controller
    # ========================================================

    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        namespace=robot_name,
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=cmd_vel_remaps,
    )

    # ========================================================
    # Behavior Server
    # ========================================================

    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        namespace=robot_name,
        output="screen",
        parameters=[
            params_file,
        ],
        remappings=cmd_vel_remaps,
    )

    # ========================================================
    # BT Navigator
    # ========================================================

    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        namespace=robot_name,
        output="screen",
        parameters=[
            params_file,
        ],
    )

    # ========================================================
    # Lifecycle Manager
    #
    # It is placed in the same namespace as its Nav2 nodes.
    # Relative node names therefore resolve to:
    #
    # /hospital_robot_X/amcl
    # /hospital_robot_X/planner_server
    # ...
    # ========================================================

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        namespace=robot_name,
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "autostart": True,
                "bond_timeout": 0.0,
                "node_names": [
                    "amcl",
                    "planner_server",
                    "controller_server",
                    "behavior_server",
                    "bt_navigator",
                ],
            }
        ],
    )

    # --------------------------------------------------------
    # Slight staggering reduces DDS / CPU startup spikes.
    # --------------------------------------------------------

    nav_nodes = TimerAction(
        period=delay,
        actions=[
            amcl,
            planner_server,
            controller_server,
            behavior_server,
            bt_navigator,
        ],
    )

    lifecycle = TimerAction(
        period=delay + 8.0,
        actions=[
            lifecycle_manager,
        ],
    )

    return [
        nav_nodes,
        lifecycle,
    ]



def launch_setup(context):

    pkg = get_package_share_directory(
        "my_hospital_rmf"
    )

    nav2_template_path = os.path.join(
        pkg,
        "config",
        "nav2_g1.yaml",
    )

    fleet_instances_path = os.path.join(
        pkg,
        "config",
        "fleet_instances.yaml",
    )

    with open(
        nav2_template_path,
        "r",
    ) as f:
        nav2_template = yaml.safe_load(
            f
        )

    with open(
        fleet_instances_path,
        "r",
    ) as f:
        fleet_config = yaml.safe_load(
            f
        )

    # ========================================================
    # AMCL initial pose mode
    #
    # true:
    #   Initialize AMCL from fleet spawn pose.
    #
    # false:
    #   Do not reset AMCL to spawn pose.
    #   Wait for /initialpose instead.
    # ========================================================

    use_spawn_initial_pose_arg = (
        LaunchConfiguration(
            "use_spawn_initial_pose"
        ).perform(context)
        .strip()
        .lower()
    )

    use_spawn_initial_pose = (
        use_spawn_initial_pose_arg
        in (
            "true",
            "1",
            "yes",
            "on",
        )
    )

    # ========================================================
    # robots launch argument
    #
    # Examples:
    #
    #   robots:=all
    #   robots:=2
    #   robots:=1,2,3
    #   robots:=hospital_robot_2
    #
    # Default = all enabled robots.
    # ========================================================

    robots_arg = (
        LaunchConfiguration(
            "robots"
        ).perform(context)
        .strip()
    )

    if not robots_arg:
        robots_arg = "all"

    selected = None

    if robots_arg.lower() != "all":

        selected = set()

        for item in robots_arg.split(","):

            item = item.strip()

            if not item:
                continue

            if item.isdigit():
                robot_name = (
                    f"hospital_robot_{int(item)}"
                )
            else:
                robot_name = item

            selected.add(
                robot_name
            )

    actions = []

    robot_index = 0

    launched_robots = []

    for robot_name, robot in (
        fleet_config[
            "robots"
        ].items()
    ):

        if not robot.get(
            "enabled",
            True,
        ):
            continue

        if (
            selected is not None
            and robot_name not in selected
        ):
            continue

        robot_index += 1

        launched_robots.append(
            robot_name
        )

        params_file = make_robot_params(
            nav2_template,
            robot_name,
            robot["spawn"],
            use_spawn_initial_pose,
        )

        # ----------------------------------------------------
        # Gradual startup
        #
        # selected robot 1:
        #   Nav2 nodes       5 s
        #   lifecycle       13 s
        #
        # selected robot 2:
        #   Nav2 nodes      20 s
        #   lifecycle       28 s
        #
        # etc.
        # ----------------------------------------------------

        delay = 5.0 + (
            15.0 * (
                robot_index - 1
            )
        )

        actions.extend(
            make_nav2_stack(
                robot_name,
                params_file,
                delay,
            )
        )

    print(
        "[g1_nav2_fleet] "
        "Selected robots: "
        + (
            ", ".join(
                launched_robots
            )
            if launched_robots
            else "<none>"
        )
    )

    if not launched_robots:
        raise RuntimeError(
            "No robots selected. "
            f"robots argument was: {robots_arg}"
        )

    return actions


def generate_launch_description():

    robots_arg = DeclareLaunchArgument(
        "robots",
        default_value="all",
        description=(
            "Nav2 robots to start. "
            "Examples: "
            "all | 2 | 1,2,3 | "
            "hospital_robot_2"
        ),
    )

    use_spawn_initial_pose_arg = DeclareLaunchArgument(
        "use_spawn_initial_pose",
        default_value="true",
        description=(
            "Initialize AMCL from each robot's Gazebo "
            "spawn pose. Use true for a fresh full-system "
            "startup. Use false when restarting Nav2 after "
            "robots have already moved."
        ),
    )

    setup = OpaqueFunction(
        function=launch_setup,
    )

    return LaunchDescription([
        robots_arg,
        use_spawn_initial_pose_arg,
        setup,
    ])
