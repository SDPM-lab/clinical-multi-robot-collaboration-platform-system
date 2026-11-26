from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    RegisterEventHandler,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, LifecycleNode
from ament_index_python.packages import get_package_prefix, get_package_share_directory
import os


def generate_launch_description():

    pkg = get_package_share_directory("my_hospital_rmf")
    world_file = os.path.join(pkg, "maps", "L1.world")
    nav_graph  = os.path.join(pkg, "nav_graphs", "0.yaml")
    map_yaml   = os.path.join(
        pkg,
        "maps",
        "L1_nav2_live.yaml",
    )
    fleet_cfg  = os.path.join(pkg, "config", "fleet_config.yaml")
    rviz_cfg   = os.path.join(pkg, "rviz", "hospital.rviz")
    cleanup_executable = os.path.join(
        get_package_prefix("my_hospital_rmf"),
        "lib", "my_hospital_rmf", "hospital_cleanup_gazebo_runtime"
    )

    g1_fleet_launch = os.path.join(
        pkg,
        "launch",
        "hospital_g1_fleet.launch.py",
    )

    g1_nav2_fleet_launch = os.path.join(
        pkg,
        "launch",
        "g1_nav2_fleet.launch.py",
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="true",
        description="跟 Gazebo 一起用時設 true，單跑真實機器人設 false"
    )
    server_uri_arg = DeclareLaunchArgument(
        "server_uri", default_value="",
        description="RMF API Server URI（選填）"
    )
    launch_gazebo_arg = DeclareLaunchArgument(
        "launch_gazebo", default_value="true",
        description="是否啟動 Gz Sim 模擬器"
    )

    launch_gazebo_gui_arg = DeclareLaunchArgument(
        "launch_gazebo_gui",
        default_value="true",
        description="是否啟動 Gazebo GUI；false 時使用 server-only 模式"
    )
    launch_rviz_arg = DeclareLaunchArgument(
        "launch_rviz", default_value="true",
        description="是否啟動 RViz2"
    )

    robots_arg = DeclareLaunchArgument(
        "robots",
        default_value="all",
        description=(
            "Number of enabled G1 robots to launch; "
            "use 'all' for the full fleet"
        ),
    )

    use_sim_time = LaunchConfiguration("use_sim_time")
    server_uri   = LaunchConfiguration("server_uri")
    launch_gazebo = LaunchConfiguration("launch_gazebo")
    launch_gazebo_gui = LaunchConfiguration("launch_gazebo_gui")
    launch_rviz   = LaunchConfiguration("launch_rviz")
    robots        = LaunchConfiguration("robots")

    # hospital.launch.py interprets robots as a COUNT:
    #   1 -> robot 1
    #   2 -> robots 1,2
    #   3 -> robots 1,2,3
    #
    # g1_nav2_fleet.launch.py instead interprets numeric values
    # as explicit robot IDs, so convert the count here.
    nav2_robots = PythonExpression([
        "'all' if '", robots, "' == 'all' else "
        "','.join(str(i) for i in range(1, int('",
        robots,
        "') + 1))"
    ])

    # ── Gz Sim（Gazebo Harmonic）────────────────────────────────
    gz_sim_gui = ExecuteProcess(
        cmd=["gz", "sim", "-r", world_file, "--verbose"],
        additional_env={
            # Keep model paths inherited from the shell (including the source
            # workspace used by Traffic Editor) and add the installed models.
            "GZ_SIM_RESOURCE_PATH": os.pathsep.join(filter(None, [
                os.path.join(pkg, "models"),
                os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
            ]))
        },
        output="screen",
        condition=IfCondition(
            PythonExpression([
                "'", launch_gazebo, "' == 'true' and '",
                launch_gazebo_gui, "' == 'true'"
            ])
        ),
        sigterm_timeout="10.0",
        sigkill_timeout="5.0",
    )

    gz_sim_server = ExecuteProcess(
        cmd=["gz", "sim", "-s", "-r", world_file, "--verbose"],
        additional_env={
            "GZ_SIM_RESOURCE_PATH": os.pathsep.join(filter(None, [
                os.path.join(pkg, "models"),
                os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
            ]))
        },
        output="screen",
        condition=IfCondition(
            PythonExpression([
                "'", launch_gazebo, "' == 'true' and '",
                launch_gazebo_gui, "' == 'false'"
            ])
        ),
        sigterm_timeout="10.0",
        sigkill_timeout="5.0",
    )

    # ── Gazebo /clock → ROS 2 ─────────────────────────────────
    # G1 的 gz_ros2_control / controller_manager 使用模擬時間，
    # 正式 hospital launch 必須提供 ROS /clock。
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="hospital_clock_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"
        ],
        output="screen",
        condition=IfCondition(launch_gazebo),
    )

    # ── Gazebo LiDAR → ROS 2 ───────────────────────────────────
    lidar_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="hospital_lidar_bridge",
        arguments=[
            "/hospital_robot_1/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_2/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_3/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_4/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_5/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_6/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/hospital_robot_7/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        output="screen",
        condition=IfCondition(launch_gazebo),
    )

    # ── G1 Fleet ────────────────────────────────────────────────
    # Gazebo 已由 hospital.launch.py 啟動，因此所有 G1 只負責 spawn。
    g1_fleet = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            g1_fleet_launch
        ),
        launch_arguments={
            # Use the same Gazebo startup path that is already
            # proven to work when hospital_g1_fleet.launch.py
            # is launched manually.
            "start_world": "true",
            "robots": robots,
        }.items(),
        condition=IfCondition(launch_gazebo),
    )

    # 正式醫院 world 較大，先給 Gazebo 幾秒初始化再 spawn G1。
    g1_fleet_delayed = TimerAction(
        period=5.0,
        actions=[
            g1_fleet,
        ],
    )

    # ── G1 Nav2 Fleet ───────────────────────────────────────────
    #
    # hospital.launch.py already owns the shared /map_server,
    # therefore Nav2 must not start another map server.
    #
    # Delay Nav2 until Gazebo and G1 controllers are available.
    g1_nav2_fleet = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            g1_nav2_fleet_launch
        ),
        launch_arguments={
            "robots": nav2_robots,
            "start_map_server": "false",
            "use_spawn_initial_pose": "true",
        }.items(),
        condition=IfCondition(
            launch_gazebo
        ),
    )

    g1_nav2_fleet_delayed = TimerAction(
        # G1 fleet starts at t=5s, then its controllers are
        # brought up sequentially:
        # R1 JSB -> R1 Diff -> R2 JSB -> R2 Diff.
        # Wait until that chain has completed before Nav2 starts.
        period=80.0,
        actions=[
            g1_nav2_fleet,
        ],
    )

    # ── RViz2（自動載入醫院地圖設定）────────────────────────────
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_cfg],
        condition=IfCondition(launch_rviz),
    )

    # ── RMF Traffic Schedule（路徑規劃核心）─────────────────────
    traffic_schedule = Node(
        package="rmf_traffic_ros2",
        executable="rmf_traffic_schedule",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ── RMF Blockade（碰撞協調）──────────────────────────────────
    traffic_blockade = Node(
        package="rmf_traffic_ros2",
        executable="rmf_traffic_blockade",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # ── RMF Task Dispatcher（任務競標與派工）──────────────────────
    task_dispatcher = Node(
        package="rmf_task_ros2",
        executable="rmf_task_dispatcher",
        name="rmf_dispatcher_node",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── Robot State Aggregator（/robot_state → /fleet_states
    # state_aggregator = Node(
    #     package="rmf_fleet_adapter",
    #     executable="robot_state_aggregator",
    #     output="screen",
    #     parameters=[{
    #         "use_sim_time": use_sim_time,
    #         "fleet_name": "hospital_fleet",
    #         "robot_prefix": "hospital",
    #     }],
    # )

    # ── Hospital Fleet Manager ───────────────────────────────────
    fleet_manager = Node(
        package="rmf_demos_fleet_adapter",
        executable="fleet_manager",
        output="both",
        arguments=[
            "--config_file", fleet_cfg,
            "--nav_graph", nav_graph,
        ],
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── Hospital Fleet Adapter ───────────────────────────────────
    # use_sim_time=true 時加入 -sim，啟用模擬模式。
    hospital_fleet_adapter_sim = Node(
        package="my_hospital_rmf",
        executable="hospital_fleet_adapter",
        output="both",
        arguments=[
            "-c", fleet_cfg,
            "-n", nav_graph,
            "-sim",
        ],
        parameters=[{
            "use_sim_time": use_sim_time,
            "server_uri": server_uri,
        }],
        condition=IfCondition(use_sim_time),
    )

    hospital_fleet_adapter_real = Node(
        package="my_hospital_rmf",
        executable="hospital_fleet_adapter",
        output="both",
        arguments=[
            "-c", fleet_cfg,
            "-n", nav_graph,
        ],
        parameters=[{
            "use_sim_time": use_sim_time,
            "server_uri": server_uri,
        }],
        condition=UnlessCondition(use_sim_time),
    )

    # ── RMF Door Supervisor ───────────────────────────────────────
    door_supervisor = Node(
        package="rmf_fleet_adapter",
        executable="door_supervisor",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── 模擬門設備 ────────────────────────────────────────────────
    fake_door = Node(
        package="my_hospital_rmf",
        executable="hospital_fake_door_adapter",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── G1 真實導航橋 ────────────────────────────────────────────
    # RMF /robot_path_requests
    #   -> Nav2 NavigateThroughPoses
    #   -> G1 motion
    # TF map -> base_link
    #   -> RMF /robot_state
    g1_navigation_bridge = Node(
        package="my_hospital_rmf",
        executable="hospital_g1_navigation_bridge",
        name="hospital_g1_navigation_bridge",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── PPO Scheduler ───────────────────────────────────────────
    #
    # The PPO runtime dependencies (sb3_contrib,
    # stable_baselines3, etc.) live in the project .venv_rl.
    # Run the source scheduler explicitly with that interpreter
    # instead of the system Python used by ros2 Node executables.
    project_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                get_package_prefix(
                    "my_hospital_rmf"
                )
            )
        )
    )

    ppo_python = os.path.join(
        project_root,
        ".venv_rl",
        "bin",
        "python",
    )

    ppo_script = os.path.join(
        project_root,
        "ros2_ws",
        "src",
        "my_hospital_rmf",
        "scripts",
        "hospital_ppo_scheduler.py",
    )

    ppo_scheduler = ExecuteProcess(
        cmd=[
            ppo_python,
            ppo_script,
        ],
        output="screen",
        additional_env={
            "HOSPITAL_SCHEDULING_ONLY": "",
        },
    )

    # ── ROS API Bridge ──────────────────────────────────────────
    ros_api_bridge = Node(
        package="my_hospital_rmf",
        executable="hospital_ros_api_bridge",
        name="hospital_ros_api_bridge",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    # ── WebSocket 推播（port 9090）───────────────────────────────
    ws_adapter = Node(
        package="my_hospital_rmf",
        executable="hospital_rosbridge_ws_adapter",
        output="screen",
    )

    # ── 地圖發布（/map topic）────────────────────────────────────
    map_server = LifecycleNode(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        namespace="",
        output="screen",
        parameters=[{
            "yaml_filename": map_yaml,
            "use_sim_time": use_sim_time,
        }],
    )

    # ── Lifecycle Manager（讓 map_server 進入 active 狀態）───────
    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_map",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "autostart": True, # # 啟動後自動幫 map_server 執行 configure+activate
            "node_names": ["map_server"], ## 要管理哪些 Lifecycle Node
        }],
    )

    # ── Rosbridge WebSocket Server（port 9091，供前端 roslib）────
    rosbridge = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[{"port": 9091}],
    )

    # ── Gazebo 關閉後清理 runtime logs ───────────────────────────
    # 不額外 pkill；避免和 gz sim 自己的 GUI → Server 關閉流程競爭。
    gazebo_gui_exit_cleanup = RegisterEventHandler(
        OnProcessExit(
            target_action=gz_sim_gui,
            on_exit=[
                ExecuteProcess(
                    cmd=[cleanup_executable],
                    output="screen",
                ),
            ],
        )
    )

    gazebo_server_exit_cleanup = RegisterEventHandler(
        OnProcessExit(
            target_action=gz_sim_server,
            on_exit=[
                ExecuteProcess(
                    cmd=[cleanup_executable],
                    output="screen",
                ),
            ],
        )
    )

    # ============================================================
    # Phased full-system startup
    #
    # Phase 1:
    #   t=5s   Gazebo + G1 fleet + ros2_control
    #
    # Phase 2:
    #   t=70s  shared map
    #   t=80s  Nav2 fleet
    #
    # Phase 3:
    #   t=115s RMF core
    #
    # Phase 4:
    #   t=125s RMF fleet integration / doors / navigation bridge
    #
    # Phase 5:
    #   t=135s PPO / API / WebSocket / RViz
    # ============================================================

    map_phase = TimerAction(
        period=70.0,
        actions=[
            map_server,
            lifecycle_manager,
        ],
    )

    rmf_core_phase = TimerAction(
        period=115.0,
        actions=[
            traffic_schedule,
            traffic_blockade,
            task_dispatcher,
        ],
    )

    rmf_integration_phase = TimerAction(
        period=125.0,
        actions=[
            fleet_manager,
            hospital_fleet_adapter_sim,
            hospital_fleet_adapter_real,
            door_supervisor,
            fake_door,
            g1_navigation_bridge,
        ],
    )

    application_phase = TimerAction(
        period=135.0,
        actions=[
            ppo_scheduler,
            ros_api_bridge,
            ws_adapter,
            rosbridge,
            rviz2,
        ],
    )

    # ── 啟動順序說明 ──────────────────────────────────────────────
    # LaunchDescription 裡的項目會依序「登記」，但節點是並行啟動的，
    # 不會等前一個完全 ready 才啟動下一個。
    # 順序：參數宣告 → 模擬器/視覺化 → RMF 核心 → 自定義節點 → 地圖
    # RMF mutex group resource management
    mutex_group_supervisor = Node(
        package="rmf_fleet_adapter",
        executable="mutex_group_supervisor",
        name="mutex_group_supervisor",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
        }],
    )

    return LaunchDescription([
        use_sim_time_arg,
        server_uri_arg,
        launch_gazebo_arg,
        launch_gazebo_gui_arg,
        launch_rviz_arg,
        robots_arg,

        mutex_group_supervisor,

        # Phase 1
        g1_fleet_delayed,

        # Phase 2
        map_phase,
        g1_nav2_fleet_delayed,

        # Phase 3
        rmf_core_phase,

        # Phase 4
        rmf_integration_phase,

        # Phase 5
        application_phase,
    ])
