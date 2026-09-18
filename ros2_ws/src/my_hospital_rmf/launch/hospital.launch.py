from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, ExecuteProcess,
    RegisterEventHandler
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LifecycleNode
from ament_index_python.packages import get_package_prefix, get_package_share_directory
import os


def generate_launch_description():

    pkg = get_package_share_directory("my_hospital_rmf")
    world_file = os.path.join(pkg, "maps", "hospital.world")
    nav_graph  = os.path.join(pkg, "nav_graphs", "0.yaml")
    map_yaml   = os.path.join(pkg, "maps", "hospital_map.yaml")
    fleet_cfg  = os.path.join(pkg, "config", "fleet_config.yaml")
    rviz_cfg   = os.path.join(pkg, "rviz", "hospital.rviz")
    cleanup_executable = os.path.join(
        get_package_prefix("my_hospital_rmf"),
        "lib", "my_hospital_rmf", "hospital_cleanup_gazebo_runtime"
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false",
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
    launch_rviz_arg = DeclareLaunchArgument(
        "launch_rviz", default_value="true",
        description="是否啟動 RViz2"
    )
    use_sim_time = LaunchConfiguration("use_sim_time")
    server_uri   = LaunchConfiguration("server_uri")
    launch_gazebo = LaunchConfiguration("launch_gazebo")
    launch_rviz   = LaunchConfiguration("launch_rviz")

    # ── Gz Sim（Gazebo Harmonic）────────────────────────────────
    gz_sim = ExecuteProcess(
        cmd=["gz", "sim", world_file, "--verbose"],
        additional_env={
            # Keep model paths inherited from the shell (including the source
            # workspace used by Traffic Editor) and add the installed models.
            "GZ_SIM_RESOURCE_PATH": os.pathsep.join(filter(None, [
                os.path.join(pkg, "models"),
                os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
            ]))
        },
        output="screen",
        condition=IfCondition(launch_gazebo),
        # Let the Gazebo Ruby wrapper stop its GUI and server children in order.
        # ROS launch escalates only if graceful shutdown does not finish in time.
        sigterm_timeout="10.0",
        sigkill_timeout="5.0",
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
    # use_sim_time=true 時加入 -sim，與 hospital.launch.xml 保持一致。
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

    # ── 模擬機器人狀態發布者 ──────────────────────────────────────
    fake_robot = Node(
        package="my_hospital_rmf",
        executable="hospital_fake_robot_state_publisher",
        output="screen",
    )

    # ── WebSocket 推播（port 9090）───────────────────────────────
    ws_adapter = Node(
        package="my_hospital_rmf",
        executable="hospital_rosbridge_ws_adapter",
        output="screen",
    )

    # ── HTTP API Bridge（port 5050）──────────────────────────────
    api_bridge = Node(
        package="my_hospital_rmf",
        executable="hospital_ros_api_bridge",
        output="screen",
    )

    # ── Scheduler v2 任務派遣 ──────────────────────────────────────
    scheduler_dispatcher = Node(
        package="my_hospital_rmf",
        executable="hospital_scheduler_dispatcher_v2",
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
    gazebo_exit_cleanup = RegisterEventHandler(
        OnProcessExit(
            target_action=gz_sim,
            on_exit=[
                ExecuteProcess(cmd=[cleanup_executable], output="screen"),
            ],
        )
    )

    # ── 啟動順序說明 ──────────────────────────────────────────────
    # LaunchDescription 裡的項目會依序「登記」，但節點是並行啟動的，
    # 不會等前一個完全 ready 才啟動下一個。
    # 順序：參數宣告 → 模擬器/視覺化 → RMF 核心 → 自定義節點 → 地圖
    return LaunchDescription([
        use_sim_time_arg,
        server_uri_arg,
        launch_gazebo_arg,
        launch_rviz_arg,
        gz_sim,
        rviz2,
        # RMF 核心
        traffic_schedule,
        traffic_blockade,
        # state_aggregator,
        fleet_manager,
        hospital_fleet_adapter_sim,
        hospital_fleet_adapter_real,
        # Door infrastructure
        door_supervisor,
        fake_door,
        # 自定義節點
        fake_robot,
        ws_adapter,
        api_bridge,
        scheduler_dispatcher,
        # 地圖
        map_server,
        lifecycle_manager,
        rosbridge,
        # gz sim 完全退出後才清理 runtime logs
        gazebo_exit_cleanup,
    ])
