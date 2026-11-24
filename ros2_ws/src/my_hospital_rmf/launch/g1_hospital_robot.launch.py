import os
import xml.etree.ElementTree as ET
import yaml

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    TimerAction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node

from ros_gz_sim.actions import GzServer
from launch.actions import ExecuteProcess
from ros_gz_bridge.actions import RosGzBridge

from robot_common_launch import get_ros2_control_robot_description


ROBOT_MODEL = "agibot_g1"


def make_controller_yaml(instance_name):
    config = {
        f"/{instance_name}/controller_manager": {
            "ros__parameters": {
                "update_rate": 30,
                "joint_state_broadcaster": {
                    "type": "joint_state_broadcaster/JointStateBroadcaster"
                },
                "diff_drive_controller": {
                    "type": "diff_drive_controller/DiffDriveController"
                },
            }
        },

        f"/{instance_name}/diff_drive_controller": {
            "ros__parameters": {
                "update_rate": 15,

                "left_wheel_names": ["left_wheel_joint"],
                "right_wheel_names": ["right_wheel_joint"],

                "wheel_separation": 0.373,
                "wheel_radius": 0.07948,

                "linear.x.has_velocity_limits": True,
                "linear.x.max_velocity": 1.0,

                "angular.z.has_velocity_limits": True,
                "angular.z.max_velocity": 5.0,

                "enable_odom_tf": True,

                # 多機器人時避免 frame 意義混淆
                "odom_frame_id": "odom",
                "base_frame_id": "base_link",
            }
        },
    }

    path = f"/tmp/{instance_name}_g1_controllers.yaml"

    with open(path, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    return path


def patch_robot_description(
    robot_description,
    instance_name,
    controller_yaml,
):
    root = ET.fromstring(robot_description)

    # --------------------------------------------------
    # gz_ros2_control namespace / controller config
    # --------------------------------------------------
    found_control = False

    for plugin in root.iter("plugin"):
        if (
            plugin.attrib.get("name")
            == "gz_ros2_control::GazeboSimROS2ControlPlugin"
        ):
            found_control = True

            ros = plugin.find("ros")
            if ros is None:
                ros = ET.SubElement(plugin, "ros")

            namespace = ros.find("namespace")
            if namespace is None:
                namespace = ET.SubElement(
                    ros,
                    "namespace",
                )

            namespace.text = f"/{instance_name}"

            parameters = plugin.find("parameters")
            if parameters is None:
                parameters = ET.SubElement(
                    plugin,
                    "parameters",
                )

            parameters.text = controller_yaml

    if not found_control:
        raise RuntimeError(
            "找不到 gz_ros2_control::GazeboSimROS2ControlPlugin"
        )

    # --------------------------------------------------
    # Per-robot LiDAR topic / frame
    # --------------------------------------------------
    found_lidar = False

    for gazebo in root.iter("gazebo"):
        if gazebo.attrib.get("reference") != "scan":
            continue

        for sensor in list(gazebo.findall("sensor")):
            if sensor.attrib.get("type") != "gpu_lidar":
                continue

            found_lidar = True

            # Keep scan updates frequent enough for AMCL and local obstacle clearing.
            topic = sensor.find("topic")
            if topic is None:
                topic = ET.SubElement(
                    sensor,
                    "topic",
                )

            topic.text = f"/{instance_name}/scan"

            frame = sensor.find("gz_frame_id")
            if frame is None:
                frame = ET.SubElement(
                    sensor,
                    "gz_frame_id",
                )

            frame.text = f"{instance_name}/scan"

            update_rate = sensor.find("update_rate")

            if update_rate is None:
                update_rate = ET.SubElement(
                    sensor,
                    "update_rate",
                )

            update_rate.text = "10"

            # Reduce horizontal LiDAR rays:
            # 180 -> 90 for Gazebo performance testing.
            samples = sensor.find(
                "./lidar/scan/horizontal/samples"
            )

            if samples is None:
                raise RuntimeError(
                    "找不到 gpu_lidar horizontal samples"
                )

            samples.text = "90"

            always_on = sensor.find("always_on")

            if always_on is None:
                always_on = ET.SubElement(
                    sensor,
                    "always_on",
                )

            always_on.text = "true"

    if not found_lidar:
        raise RuntimeError(
            "找不到 AgiBot G1 gpu_lidar sensor"
        )

    return ET.tostring(
        root,
        encoding="unicode",
    )


def launch_setup(context, *args, **kwargs):

    instance_name = context.launch_configurations["instance_name"]
    robot_type = context.launch_configurations["robot_type"].lower()

    start_controllers = (
        context.launch_configurations["start_controllers"]
        .strip()
        .lower()
        in ("true", "1", "yes", "on")
    )

    x = context.launch_configurations["x"]
    y = context.launch_configurations["y"]
    z = context.launch_configurations["z"]
    yaw = context.launch_configurations["yaw"]

    start_world = (
        context.launch_configurations["start_world"]
        .strip()
        .lower()
        in ("true", "1", "yes")
    )

    # --------------------------------------------------
    # Robot Type / Capability validation
    # --------------------------------------------------

    profiles_path = os.path.join(
        get_package_share_directory("my_hospital_rmf"),
        "config",
        "robot_profiles.yaml",
    )

    with open(profiles_path, "r") as f:
        profiles = yaml.safe_load(f)

    robot_types = profiles.get("robot_types", {})

    if robot_type not in robot_types:
        raise RuntimeError(
            f"Unknown robot_type '{robot_type}'. "
            f"Available: {list(robot_types.keys())}"
        )

    capabilities = robot_types[robot_type]["capabilities"]

    print("=" * 70)
    print(f"Hospital Robot Instance : {instance_name}")
    print(f"Robot Type              : {robot_type}")
    print(f"Robot Model             : {ROBOT_MODEL}")
    print(f"Capabilities            : {capabilities}")
    print(f"Spawn                    : ({x}, {y}, {z}), yaw={yaw}")
    print("=" * 70)

    # --------------------------------------------------
    # Controller configuration
    # --------------------------------------------------

    controller_yaml = make_controller_yaml(instance_name)

    # --------------------------------------------------
    # Generate G1 URDF
    # --------------------------------------------------

    robot_description = get_ros2_control_robot_description(
        ROBOT_MODEL,
        robot_type="",
        hardware="gz",
        launch_configurations={},
    )

    if robot_description is None:
        raise RuntimeError("Failed generating G1 robot_description")

    robot_description = patch_robot_description(
        robot_description,
        instance_name,
        controller_yaml,
    )

    nodes = []

    # --------------------------------------------------
    # Gazebo world only needs to start once
    # --------------------------------------------------

    if start_world:

        models_path = os.path.join(
            get_package_share_directory("my_hospital_rmf"),
            "models",
        )
        os.environ["GZ_SIM_RESOURCE_PATH"] = os.pathsep.join(filter(None, [
            models_path,
            os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
        ]))

        world_path = os.path.join(


            get_package_share_directory("my_hospital_rmf"),


            "maps",


            "L1.world",


        )

        gz_server = ExecuteProcess(
            cmd=[
                "gz",
                "sim",
                "-s",
                "-r",
                world_path,
                "--verbose",
            ],
            output="screen",
        )

        gz_bridge_config = os.path.join(
            get_package_share_directory("my_hospital_rmf"),
            "config",
            "hospital_gz_bridge.yaml",
        )

        gz_bridge = RosGzBridge(
            bridge_name="ros_gz_bridge",
            config_file=gz_bridge_config,
            create_own_container=False,
            use_composition=False,
        )

        nodes.extend([
            gz_server,
            gz_bridge,
        ])

    # --------------------------------------------------
    # Robot State Publisher
    # --------------------------------------------------

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace=instance_name,
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True,
            "publish_frequency": 100.0,

            # 之後多台 G1 時避免 TF frame 撞名
            "frame_prefix": f"{instance_name}/",
        }],
    )

    # --------------------------------------------------
    # Spawn robot
    # --------------------------------------------------

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name=f"spawn_{instance_name}",
        output="screen",
        arguments=[
            "-topic",
            f"/{instance_name}/robot_description",

            "-name",
            instance_name,

            "-allow_renaming",
            "false",

            "-x", x,
            "-y", y,
            "-z", z,
            "-Y", yaw,
        ],
    )

    # --------------------------------------------------
    # Controllers
    # --------------------------------------------------

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        namespace=instance_name,
        name="spawner_joint_state_broadcaster",
        output="screen",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            f"/{instance_name}/controller_manager",
            "--controller-manager-timeout",
            "60",
            "--service-call-timeout",
            "30",
            "--switch-timeout",
            "30",
        ],
        parameters=[{"use_sim_time": True}],
    )

    diff_drive_controller = Node(
        package="controller_manager",
        executable="spawner",
        namespace=instance_name,
        name="spawner_diff_drive_controller",
        output="screen",
        arguments=[
            "diff_drive_controller",
            "--controller-manager",
            f"/{instance_name}/controller_manager",
            "--controller-manager-timeout",
            "60",
            "--service-call-timeout",
            "30",
            "--switch-timeout",
            "30",
        ],
        parameters=[{"use_sim_time": True}],
    )

    # --------------------------------------------------
    # Twist -> TwistStamped
    # --------------------------------------------------

    twist_stamper = Node(
        package="twist_stamper",
        executable="twist_stamper",
        namespace=instance_name,
        name="twist_stamper",
        output="screen",
        remappings=[
            ("cmd_vel_in", "cmd_vel"),
            ("cmd_vel_out", "diff_drive_controller/cmd_vel"),
        ],
        parameters=[{
            "frame_id": f"{instance_name}/base_link",
            "use_sim_time": True,
        }],
    )

    # --------------------------------------------------
    # Stagger controller startup between robots
    #
    # ros2_control spawners use a shared lock. Starting many
    # robot controllers at the same time can cause some
    # spawners to fail, leaving controllers unloaded or
    # unconfigured.
    # --------------------------------------------------

    try:
        robot_number = int(
            instance_name.rsplit("_", 1)[1]
        )
    except (ValueError, IndexError):
        robot_number = 1

    controller_slot = max(
        0,
        robot_number - 1,
    )

    joint_controller_delay = (
        12.0
        + controller_slot * 30.0
    )

    diff_controller_delay = (
        16.0
        + controller_slot * 30.0
    )

    self_spawn_delay = (
        3.0 if start_world else 1.0
    )

    print(
        f"[{instance_name}] "
        f"spawn={self_spawn_delay:.1f}s, "
        f"joint_controller={joint_controller_delay:.1f}s, "
        f"diff_controller={diff_controller_delay:.1f}s"
    )

    nodes.extend([
        robot_state_publisher,
        twist_stamper,

        TimerAction(
            period=self_spawn_delay,
            actions=[spawn_robot],
        ),
    ])

    if start_controllers:
        nodes.extend([
            TimerAction(
                period=joint_controller_delay,
                actions=[
                    joint_state_broadcaster,
                ],
            ),

            RegisterEventHandler(
                OnProcessExit(
                    target_action=joint_state_broadcaster,
                    on_exit=[
                        diff_drive_controller,
                    ],
                )
            ),
        ])

    return nodes


def generate_launch_description():

    return LaunchDescription([

        DeclareLaunchArgument(
            "start_controllers",
            default_value="true",
            description=(
                "Whether this robot starts its own "
                "ros2_control spawners."
            ),
        ),

        DeclareLaunchArgument(
            "instance_name",
            default_value="hospital_robot_1",
        ),

        DeclareLaunchArgument(
            "robot_type",
            default_value="clean",
            description="clean | medical | ward",
        ),

        DeclareLaunchArgument(
            "x",
            default_value="9.0",
        ),

        DeclareLaunchArgument(
            "y",
            default_value="-18.0",
        ),

        DeclareLaunchArgument(
            "z",
            default_value="0.2",
        ),

        DeclareLaunchArgument(
            "yaw",
            default_value="0.0",
        ),

        DeclareLaunchArgument(
            "start_world",
            default_value="true",
            description="Only the first robot should start Gazebo world",
        ),

        OpaqueFunction(function=launch_setup),
    ])
