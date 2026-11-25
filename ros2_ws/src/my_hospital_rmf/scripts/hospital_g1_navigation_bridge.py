#!/usr/bin/env python3

import math
import os
import yaml

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateThroughPoses
from geometry_msgs.msg import PoseStamped

from tf2_ros import Buffer, TransformListener

from ament_index_python.packages import get_package_share_directory

from geometry_msgs.msg import Twist
from geometry_msgs.msg import Pose
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

from rmf_fleet_msgs.msg import (
    RobotState,
    RobotMode,
    Location,
    PathRequest,
)

from navigation.utils import (
    clamp,
    normalize_angle,
)

from navigation.robot_runtime import RobotRuntime

from navigation.traffic_avoidance import (
    find_robot_conflict,
    is_head_on_conflict,
)

from navigation.obstacle_avoidance import (
    analyze_lidar_scan,
    compute_turn_command,
    can_recover_from_bypass,
    compute_bypass_command,
    compute_recover_command,
    should_trigger_obstacle_avoidance,
    choose_avoidance_direction,
)

from navigation.path_follower import (
    compute_normal_tracking_command,
    compute_final_goal_command,
)

from navigation.config import (
    CONTROL_PERIOD,
    ARRIVE_DISTANCE,
    GOAL_APPROACH_DISTANCE,
    GOAL_APPROACH_MAX_SPEED,
    GOAL_EMERGENCY_STOP_DISTANCE,
    FINAL_YAW_TOLERANCE,
    ROTATE_FIRST_THRESHOLD,
    LINEAR_KP,
    ANGULAR_KP,
    MAX_LINEAR_SPEED,
    MAX_ANGULAR_SPEED,
    MIN_LINEAR_SPEED,
    OBSTACLE_SLOW_DISTANCE,
    OBSTACLE_STOP_DISTANCE,
    AVOID_TURN_ANGLE,
    AVOID_TURN_TOLERANCE,
    AVOID_FORWARD_DISTANCE,
    AVOID_LINEAR_SPEED,
    AVOID_EXTRA_TURN_ANGLE,
    SIDE_SAFE_DISTANCE,
    SIDE_CORRECTION_KP,
    SIDE_MAX_ANGULAR_SPEED,
    RECOVER_MIN_SIDE_CLEARANCE,
    BYPASS_PATH_KP,
    BYPASS_PATH_MAX_ANGULAR_SPEED,
    ROBOT_CONFLICT_DISTANCE,
    ROBOT_RESUME_DISTANCE,
    ROBOT_CONFLICT_ANGLE,
    HEAD_ON_MIN_OPPOSITE_ANGLE,
    HEAD_ON_TURN_ANGLE,
    HEAD_ON_FORWARD_DISTANCE,
    HEAD_ON_SHIFT_DISTANCE,
    HEAD_ON_WALL_MIN_DISTANCE,
    HEAD_ON_BEHIND_MARGIN,
    HEAD_ON_LANE_TOLERANCE,
    HEAD_ON_CLEAR_DISTANCE,
    HEAD_ON_LINEAR_SPEED,
    HEAD_ON_MAX_ANGULAR_SPEED,
)


# ============================================================
# RMF / Hospital settings
# ============================================================

FLEET_NAME = "hospital_fleet"
MAP_NAME = "L1"

BATTERY_PERCENT = 99.0


# ============================================================
# Main bridge
# ============================================================

class HospitalG1NavigationBridge(Node):

    def __init__(self):

        super().__init__(
            "hospital_g1_navigation_bridge"
        )

        package_share = (
            get_package_share_directory(
                "my_hospital_rmf"
            )
        )

        fleet_instances_path = os.path.join(
            package_share,
            "config",
            "fleet_instances.yaml",
        )

        with open(
            fleet_instances_path,
            "r",
            encoding="utf-8",
        ) as f:

            config = (
                yaml.safe_load(f)
                or {}
            )

        robot_configs = config.get(
            "robots",
            {},
        )

        if not robot_configs:
            raise RuntimeError(
                "No robots found in fleet_instances.yaml"
            )

        self.robots = {}
        self.cmd_publishers = {}
        self.scan_subscriptions = {}

        # ----------------------------------------------------
        # Nav2 action clients
        #
        # Each robot has its own NavigateThroughPoses server:
        #
        # /hospital_robot_X/navigate_through_poses
        # ----------------------------------------------------

        self.nav_clients = {}
        self.nav_goal_handles = {}

        # ----------------------------------------------------
        # TF
        #
        # Nav2 operates in the map frame. RMF RobotState must
        # therefore report the same map-frame robot pose.
        # ----------------------------------------------------

        self.tf_buffer = Buffer()

        self.tf_listener = TransformListener(
            self.tf_buffer,
            self,
        )

        # Last RMF request signature per robot.
        # Used to ignore duplicate PathRequest messages.
        self.last_path_signatures = {}

        # ----------------------------------------------------
        # RMF state output
        # ----------------------------------------------------

        self.state_pub = self.create_publisher(
            RobotState,
            "/robot_state",
            10,
        )

        # ----------------------------------------------------
        # RMF path input
        # ----------------------------------------------------

        self.path_sub = self.create_subscription(
            PathRequest,
            "/robot_path_requests",
            self.path_request_callback,
            10,
        )

        # ----------------------------------------------------
        # Create one runtime + odom subscriber + cmd_vel
        # publisher per enabled robot
        # ----------------------------------------------------

        for robot_id, info in robot_configs.items():

            if not info.get(
                "enabled",
                True,
            ):
                continue

            spawn = info.get(
                "spawn",
                {},
            )

            robot = RobotRuntime(
                robot_id=robot_id,
                robot_type=info.get(
                    "type",
                    "unknown",
                ),
                spawn_x=spawn.get(
                    "x",
                    0.0,
                ),
                spawn_y=spawn.get(
                    "y",
                    0.0,
                ),
                spawn_yaw=spawn.get(
                    "yaw",
                    0.0,
                ),
            )

            self.robots[
                robot_id
            ] = robot

            odom_topic = (
                f"/{robot_id}"
                "/diff_drive_controller"
                "/odom"
            )

            cmd_topic = (
                f"/{robot_id}/cmd_vel"
            )

            scan_topic = (
                f"/{robot_id}/scan"
            )

            ground_truth_topic = (
                f"/model/{robot_id}/pose"
            )

            self.create_subscription(
                Odometry,
                odom_topic,
                lambda msg, rid=robot_id:
                    self.odom_callback(
                        rid,
                        msg,
                    ),
                10,
            )

            self.create_subscription(
                Pose,
                ground_truth_topic,
                lambda msg, rid=robot_id:
                    self.ground_truth_callback(
                        rid,
                        msg,
                    ),
                10,
            )

            self.scan_subscriptions[
                robot_id
            ] = self.create_subscription(
                LaserScan,
                scan_topic,
                lambda msg, rid=robot_id:
                    self.scan_callback(
                        rid,
                        msg,
                    ),
                10,
            )

            # ------------------------------------------------
            # Nav2 owns base motion for every robot.
            #
            # The RMF bridge must NOT publish cmd_vel directly,
            # otherwise it would compete with Nav2's controller.
            # ------------------------------------------------

            self.nav_clients[
                robot_id
            ] = ActionClient(
                self,
                NavigateThroughPoses,
                f"/{robot_id}/navigate_through_poses",
            )

            self.nav_goal_handles[
                robot_id
            ] = None

            self.get_logger().info(
                f"{robot_id}: "
                f"type={robot.robot_type}, "
                f"spawn=("
                f"{robot.spawn_x}, "
                f"{robot.spawn_y}, "
                f"{robot.spawn_yaw}), "
                f"odom={odom_topic}, "
                f"scan={scan_topic}, "
                f"cmd={cmd_topic}"
            )

        self.timer = self.create_timer(
            CONTROL_PERIOD,
            self.on_timer,
        )

        self.get_logger().info(
            "Hospital G1 Navigation Bridge ready"
        )

    # ========================================================
    # ROS callbacks
    # ========================================================

    def odom_callback(
        self,
        robot_id,
        msg,
    ):
        robot = self.robots.get(
            robot_id
        )

        if robot is None:
            return

        robot.update_odom(
            msg
        )



    def ground_truth_callback(
        self,
        robot_id,
        msg,
    ):
        robot = self.robots.get(
            robot_id
        )

        if robot is None:
            return

        robot.update_ground_truth(
            msg
        )

    def scan_callback(
        self,
        robot_id,
        msg,
    ):
        robot = self.robots.get(
            robot_id
        )

        if robot is None:
            return

        scan = analyze_lidar_scan(
            msg
        )

        robot.front_beam_count = (
            scan["front_beam_count"]
        )

        robot.front_raw_min = (
            scan["front_raw_min"]
        )

        robot.front_close_count = (
            scan["front_close_count"]
        )

        robot.front_clearance = (
            scan["front_clearance"]
        )

        robot.left_clearance = (
            scan["left_clearance"]
        )

        robot.right_clearance = (
            scan["right_clearance"]
        )

        robot.received_scan = True

        # --------------------------------------------------
        # Debug log：每台 robot 最多每 2 秒一次
        # --------------------------------------------------

        now_s = (
            self.get_clock()
            .now()
            .nanoseconds
            / 1.0e9
        )

        if (
            now_s
            - robot.last_scan_log_time
            >= 2.0
        ):
            robot.last_scan_log_time = (
                now_s
            )

            self.get_logger().info(
                f"[LIDAR] {robot.robot_id} "
                f"front="
                f"{robot.front_clearance:.2f}m, "
                f"left="
                f"{robot.left_clearance:.2f}m, "
                f"right="
                f"{robot.right_clearance:.2f}m"
            )

    def _nav_switch_state(self, robot_id):

        if not hasattr(self, "_nav_switch_states"):
            self._nav_switch_states = {}

        return self._nav_switch_states.setdefault(
            robot_id,
            {
                "generation": 0,
                "active": None,
                "pending": None,
                "cancel_requested": False,
            }
        )


    def _apply_pending_nav_path(self, robot_id):

        state = self._nav_switch_state(robot_id)

        if state["active"] is not None:
            return

        msg = state["pending"]

        if msg is None:
            return

        state["pending"] = None

        robot = self.robots.get(robot_id)

        if robot is None:
            return

        robot.receive_path(
            msg.task_id,
            msg.path,
        )

        if not msg.path:

            robot.current_target_index = 0
            robot.path = []

            self.stop_robot(robot_id)

            self.get_logger().info(
                f"[NAV_STOPPED] robot={robot_id}"
            )

            return

        self.get_logger().info(
            f"[NAV_PATH_APPLIED] "
            f"robot={robot_id}, task_id={msg.task_id}"
        )

        self.send_nav2_path(robot)


    def cancel_nav2_goal(self, robot_id):

        state = self._nav_switch_state(robot_id)

        generation = state["active"]

        if generation is None:
            return

        goal_handle = self.nav_goal_handles.get(
            robot_id
        )

        if goal_handle is None:
            return

        if state["cancel_requested"]:
            return

        state["cancel_requested"] = True

        self.get_logger().info(
            f"[NAV_CANCEL_REQUEST] "
            f"robot={robot_id}, generation={generation}"
        )

        try:

            future = goal_handle.cancel_goal_async()

            future.add_done_callback(
                lambda f, rid=robot_id, gen=generation:
                    self.nav_cancel_done_callback(
                        rid, gen, f
                    )
            )

        except Exception as exc:

            state["cancel_requested"] = False

            self.get_logger().error(
                f"[NAV_CANCEL_ERROR] "
                f"robot={robot_id}: {exc}"
            )


    def nav_cancel_done_callback(
        self,
        robot_id,
        generation,
        future,
    ):

        state = self._nav_switch_state(robot_id)

        if state["active"] != generation:
            return

        try:

            response = future.result()

            count = len(response.goals_canceling)

            self.get_logger().info(
                f"[NAV_CANCEL_RESPONSE] "
                f"robot={robot_id}, "
                f"generation={generation}, "
                f"goals_canceling={count}"
            )

            if count == 0:

                self.get_logger().warning(
                    f"{robot_id}: cancellation not "
                    "confirmed; waiting for terminal result"
                )

        except Exception as exc:

            self.get_logger().error(
                f"[NAV_CANCEL_ERROR] "
                f"robot={robot_id}: {exc}"
            )

        # Never clear the active goal here.
        # Wait for the terminal action result.


    def send_nav2_path(
        self,
        robot,
    ):
        """Send the current RMF path to this robot's Nav2."""

        client = self.nav_clients.get(
            robot.robot_id
        )

        if client is None:
            self.get_logger().error(
                f"{robot.robot_id}: "
                "Nav2 action client not found"
            )
            return

        if not robot.path:
            return

        if not client.server_is_ready():
            self.get_logger().warning(
                f"{robot.robot_id}: "
                "NavigateThroughPoses server is not ready"
            )
            return

        goal = NavigateThroughPoses.Goal()

        goal.poses = []

        for point in robot.path:

            pose = PoseStamped()

            pose.header.frame_id = "map"
            pose.header.stamp = (
                self.get_clock()
                .now()
                .to_msg()
            )

            pose.pose.position.x = float(
                point.x
            )

            pose.pose.position.y = float(
                point.y
            )

            yaw = float(
                point.yaw
            )

            pose.pose.orientation.z = (
                math.sin(yaw / 2.0)
            )

            pose.pose.orientation.w = (
                math.cos(yaw / 2.0)
            )

            goal.poses.append(
                pose
            )

        self.get_logger().info(
            f"{robot.robot_id}: "
            f"sending {len(goal.poses)} poses "
            "to Nav2"
        )


        state = self._nav_switch_state(
            robot.robot_id
        )

        if state["active"] is not None:
            return

        state["generation"] += 1

        generation = state["generation"]

        state["active"] = generation
        state["cancel_requested"] = False

        self.get_logger().info(
            f"[NAV_GOAL_SENT] "
            f"robot={robot.robot_id}, "
            f"generation={generation}"
        )

        try:

            future = client.send_goal_async(goal)

            future.add_done_callback(
                lambda f, rid=robot.robot_id, gen=generation:
                    self.nav_goal_response_callback(
                        rid, gen, f
                    )
            )

        except Exception as exc:

            self.get_logger().error(
                f"[NAV_SEND_ERROR] "
                f"robot={robot.robot_id}: {exc}"
            )


    def nav_goal_response_callback(
        self,
        robot_id,
        generation,
        future,
    ):

        state = self._nav_switch_state(robot_id)

        try:

            goal_handle = future.result()

        except Exception as exc:

            self.get_logger().error(
                f"[NAV_RESPONSE_ERROR] "
                f"robot={robot_id}: {exc}"
            )

            return

        if state["active"] != generation:

            if goal_handle.accepted:
                goal_handle.cancel_goal_async()

            return

        if not goal_handle.accepted:

            state["active"] = None
            state["cancel_requested"] = False

            self.nav_goal_handles[robot_id] = None

            self.get_logger().error(
                f"[NAV_GOAL_REJECTED] "
                f"robot={robot_id}, "
                f"generation={generation}"
            )

            self._apply_pending_nav_path(robot_id)

            return

        self.nav_goal_handles[robot_id] = goal_handle

        self.get_logger().info(
            f"[NAV_GOAL_ACCEPTED] "
            f"robot={robot_id}, "
            f"generation={generation}"
        )

        result_future = goal_handle.get_result_async()

        result_future.add_done_callback(
            lambda f, rid=robot_id, gen=generation:
                self.nav_result_callback(
                    rid, gen, f
                )
        )

        if state["pending"] is not None:

            self.cancel_nav2_goal(robot_id)


    def nav_result_callback(
        self,
        robot_id,
        generation,
        future,
    ):

        state = self._nav_switch_state(robot_id)

        if state["active"] != generation:

            self.get_logger().info(
                f"[NAV_STALE_RESULT_IGNORED] "
                f"robot={robot_id}, "
                f"generation={generation}"
            )

            return

        robot = self.robots.get(robot_id)

        if robot is None:
            return

        try:

            wrapped_result = future.result()

        except Exception as exc:

            self.get_logger().error(
                f"[NAV_RESULT_ERROR] "
                f"robot={robot_id}: {exc}"
            )

            return

        if wrapped_result.status not in (4, 5, 6):

            self.get_logger().error(
                f"[NAV_NONTERMINAL_RESULT] "
                f"robot={robot_id}, "
                f"status={wrapped_result.status}"
            )

            return

        self.get_logger().info(
            f"[NAV_TERMINAL] "
            f"robot={robot_id}, "
            f"generation={generation}, "
            f"status={wrapped_result.status}"
        )

        state["active"] = None
        state["cancel_requested"] = False

        self.nav_goal_handles[robot_id] = None

        if state["pending"] is not None:

            self.get_logger().info(
                f"[NAV_SWITCH_READY] "
                f"robot={robot_id}"
            )

            self._apply_pending_nav_path(robot_id)

            return

        status = wrapped_result.status
        result = wrapped_result.result

        if (
            status == 4
            and result.error_code == 0
        ):
            completed_task = (
                robot.task_id
            )

            robot.current_target_index = (
                len(robot.path)
            )

            robot.path = []

            self.get_logger().info(
                f"{robot_id} completed path "
                f"task_id={completed_task} "
                "through Nav2"
            )

            return

        # Nav2 has reached a terminal state, even if it failed
        # or was cancelled. Do not leave RobotState stuck in
        # MODE_MOVING forever.
        robot.current_target_index = (
            len(robot.path)
        )

        robot.path = []

        self.get_logger().error(
            f"{robot_id}: "
            f"Nav2 navigation failed "
            f"status={status}, "
            f"error_code={result.error_code}, "
            f"error_msg={result.error_msg}; "
            "runtime path cleared"
        )


    def path_request_callback(
        self,
        msg,
    ):
        if msg.fleet_name != FLEET_NAME:
            return

        robot = self.robots.get(
            msg.robot_name
        )

        if robot is None:
            self.get_logger().warning(
                f"Unknown robot in PathRequest: "
                f"{msg.robot_name}"
            )
            return

        # 目前系統只有 L1。
        # 如果未來加入電梯 / 多樓層，再擴充 map transition。
        for point in msg.path:
            if (
                point.level_name
                and
                point.level_name != MAP_NAME
            ):
                self.get_logger().error(
                    f"{msg.robot_name}: "
                    f"unsupported level "
                    f"{point.level_name}"
                )
                self.stop_robot(
                    msg.robot_name
                )
                return

        # ----------------------------------------------------
        # Ignore duplicate RMF PathRequest messages.
        #
        # RMF may publish the same request more than once.
        # Re-sending the same Nav2 goal would unnecessarily
        # cancel and restart navigation.
        # ----------------------------------------------------

        path_signature = (
            msg.task_id,
            tuple(
                (
                    round(float(point.x), 4),
                    round(float(point.y), 4),
                    round(float(point.yaw), 4),
                    point.level_name,
                    int(point.index),
                )
                for point in msg.path
            ),
        )

        previous_signature = (
            self.last_path_signatures.get(
                msg.robot_name
            )
        )

        if previous_signature == path_signature:
            self.get_logger().info(
                f"{msg.robot_name}: "
                "duplicate PathRequest ignored"
            )
            return

        self.last_path_signatures[
            msg.robot_name
        ] = path_signature

        # ----------------------------------------------------
        # A genuinely new RMF PathRequest supersedes the
        # previous Nav2 navigation goal.
        # ----------------------------------------------------


        state = self._nav_switch_state(
            msg.robot_name
        )

        state["pending"] = msg

        if state["active"] is not None:

            self.get_logger().info(
                f"[NAV_SWITCH_PENDING] "
                f"robot={msg.robot_name}, "
                f"task_id={msg.task_id}, "
                f"active_generation={state['active']}"
            )

            self.cancel_nav2_goal(
                msg.robot_name
            )

        else:

            self._apply_pending_nav_path(
                msg.robot_name
            )

        self.get_logger().info(
            f"{msg.robot_name} received "
            f"PathRequest: "
            f"task_id={msg.task_id}, "
            f"points={len(msg.path)}"
        )

        for i, p in enumerate(
            msg.path
        ):
            self.get_logger().info(
                f"  point {i}: "
                f"x={p.x:.3f}, "
                f"y={p.y:.3f}, "
                f"yaw={p.yaw:.3f}, "
                f"level={p.level_name}, "
                f"index={p.index}"
            )

    # ========================================================
    # Navigation control
    # ========================================================

    def stop_robot(
        self,
        robot_id,
    ):
        pub = self.cmd_publishers.get(
            robot_id
        )

        if pub is None:
            return

        pub.publish(
            Twist()
        )

    def command_robot(
        self,
        robot_id,
        linear,
        angular,
    ):
        msg = Twist()

        msg.linear.x = float(
            linear
        )

        msg.angular.z = float(
            angular
        )

        pub = self.cmd_publishers.get(
            robot_id
        )

        if pub is None:
            return

        pub.publish(msg)

    def find_robot_conflict(
        self,
        robot,
        x,
        y,
        yaw,
    ):
        return find_robot_conflict(
            self.robots,
            robot,
            x,
            y,
            yaw,
        )

    def is_head_on_conflict(
        self,
        robot,
        other,
        x,
        y,
        yaw,
    ):
        return is_head_on_conflict(
            robot,
            other,
            x,
            y,
            yaw,
        )

    def control_robot(
        self,
        robot,
    ):
        if not robot.received_odom:
            return

        # ----------------------------------------------------
        # No active path
        # ----------------------------------------------------

        if not robot.navigating():
            self.stop_robot(
                robot.robot_id
            )
            return

        (
            x,
            y,
            yaw,
        ) = robot.map_pose()

        # ----------------------------------------------------
        # Skip already-reached intermediate points
        # ----------------------------------------------------

        while robot.navigating():

            target = robot.path[
                robot.current_target_index
            ]

            dx = float(target.x) - x
            dy = float(target.y) - y

            distance = math.hypot(
                dx,
                dy,
            )

            is_last = (
                robot.current_target_index
                == len(robot.path) - 1
            )

            # 中間 waypoint 到達
            if (
                distance
                <= ARRIVE_DISTANCE
                and
                not is_last
            ):
                self.get_logger().info(
                    f"{robot.robot_id} reached "
                    f"waypoint "
                    f"{robot.current_target_index}"
                )

                robot.current_target_index += 1
                continue

            break

        if not robot.navigating():
            self.stop_robot(
                robot.robot_id
            )
            return

        target = robot.path[
            robot.current_target_index
        ]

        dx = float(target.x) - x
        dy = float(target.y) - y

        distance = math.hypot(
            dx,
            dy,
        )

        is_last = (
            robot.current_target_index
            == len(robot.path) - 1
        )

        # ====================================================
        # Obstacle avoidance state machine
        # ====================================================


        # ----------------------------------------------------
        # YIELD
        # ----------------------------------------------------

        if robot.avoidance_state == "yield":

            other = self.robots.get(
                robot.yield_to_robot_id
            )

            # 對方不存在或已經沒有 odom
            if (
                other is None
                or
                not other.received_odom
            ):
                robot.avoidance_state = "normal"
                robot.yield_to_robot_id = None
                return

            (
                other_x,
                other_y,
                _,
            ) = other.map_pose()

            robot_distance = math.hypot(
                other_x - x,
                other_y - y,
            )

            # 對方已經離開安全距離
            if robot_distance >= ROBOT_RESUME_DISTANCE:

                self.get_logger().info(
                    f"[YIELD] {robot.robot_id} "
                    f"{other.robot_id} cleared "
                    f"distance={robot_distance:.2f}m "
                    f"-> resume"
                )

                robot.avoidance_state = "normal"
                robot.yield_to_robot_id = None

                self.stop_robot(
                    robot.robot_id
                )

                return

            # 還沒離開，持續停車
            self.stop_robot(
                robot.robot_id
            )

            return

        # ----------------------------------------------------
        # STATIONARY ROBOT WAIT
        #
        # 前方 robot 沒有正在導航時，
        # 先短暫等待，避免只是暫時停頓就立刻繞行。
        #
        # 若持續阻擋約 1 秒，轉入既有 generic
        # turn -> bypass -> recover 流程。
        # ----------------------------------------------------

        if robot.avoidance_state == "stationary_wait":

            other = self.robots.get(
                robot.stationary_robot_id
            )

            # 對方消失、沒有 pose，或已經開始移動：
            # 回到 normal，下一個 control cycle
            # 重新判斷交通狀況。
            if (
                other is None
                or not other.received_odom
                or other.navigating()
            ):
                robot.avoidance_state = "normal"
                robot.stationary_robot_id = None
                robot.stationary_wait_ticks = 0

                self.stop_robot(
                    robot.robot_id
                )

                return

            (
                other_x,
                other_y,
                _,
            ) = other.map_pose()

            other_distance = math.hypot(
                other_x - x,
                other_y - y,
            )

            # 已經不再阻擋
            if other_distance >= ROBOT_RESUME_DISTANCE:
                robot.avoidance_state = "normal"
                robot.stationary_robot_id = None
                robot.stationary_wait_ticks = 0

                self.stop_robot(
                    robot.robot_id
                )

                return

            robot.stationary_wait_ticks += 1

            # CONTROL_PERIOD = 0.1，
            # 10 ticks 約等於 1 秒。
            if robot.stationary_wait_ticks < 10:
                self.stop_robot(
                    robot.robot_id
                )
                return

            # 確認對方持續靜止且仍在前方：
            #
            # 不使用 generic turn/bypass。
            # 改用既有的 lane-based passing：
            #
            # head_on_turn
            # -> head_on_shift
            # -> head_on_parallel_turn
            # -> head_on_parallel
            # -> head_on_return_turn
            # -> head_on_return
            # -> recover
            #
            # 雖然 state 名稱叫 head_on，
            # 這裡實際上是重用它的幾何錯車流程。

            robot.head_on_robot_id = (
                other.robot_id
            )

            # 優先使用 RMF segment 本身的方向，
            # 不直接使用 robot 當下可能已有誤差的 yaw。
            if (
                robot.segment_anchor_x is not None
                and
                robot.segment_anchor_y is not None
            ):
                lane_dx = (
                    float(target.x)
                    - robot.segment_anchor_x
                )

                lane_dy = (
                    float(target.y)
                    - robot.segment_anchor_y
                )

                lane_length = math.hypot(
                    lane_dx,
                    lane_dy,
                )

                if lane_length > 1.0e-6:
                    lane_yaw = math.atan2(
                        lane_dy,
                        lane_dx,
                    )
                else:
                    lane_yaw = yaw

                robot.head_on_lane_anchor_x = (
                    robot.segment_anchor_x
                )

                robot.head_on_lane_anchor_y = (
                    robot.segment_anchor_y
                )

            else:
                lane_yaw = yaw

                robot.head_on_lane_anchor_x = x
                robot.head_on_lane_anchor_y = y

            robot.head_on_original_yaw = lane_yaw

            # 與既有 head-on 規則一致：
            # 先往自己的右側偏移。
            robot.avoidance_target_yaw = (
                normalize_angle(
                    lane_yaw
                    - HEAD_ON_TURN_ANGLE
                )
            )

            robot.stationary_robot_id = None
            robot.stationary_wait_ticks = 0

            robot.avoidance_state = (
                "head_on_turn"
            )

            self.get_logger().warning(
                f"[STATIONARY] {robot.robot_id} "
                f"blocked by {other.robot_id} "
                f"distance={other_distance:.2f}m "
                f"-> lane-based pass"
            )

            self.stop_robot(
                robot.robot_id
            )

            return


        # ----------------------------------------------------
        # HEAD-ON TURN
        #
        # 正面相遇：
        # 先往自己的右側轉 HEAD_ON_TURN_ANGLE。
        # ----------------------------------------------------

        if robot.avoidance_state == "head_on_turn":

            turn_error = normalize_angle(
                robot.avoidance_target_yaw
                - yaw
            )

            if (
                abs(turn_error)
                <= AVOID_TURN_TOLERANCE
            ):
                robot.avoidance_state = (
                    "head_on_shift"
                )

                # Ground Truth 座標：
                # 從真正開始右移的位置計算 shift distance。
                robot.avoidance_start_x = x
                robot.avoidance_start_y = y

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"turn complete -> shift"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            angular = clamp(
                ANGULAR_KP
                * turn_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return


        # ----------------------------------------------------
        # HEAD-ON SHIFT
        #
        # 沿右偏方向只移動一小段。
        # 目的只是取得橫向間距，
        # 不再像舊版本一路斜著 PASS。
        # ----------------------------------------------------

        if robot.avoidance_state == "head_on_shift":

            shift_dx = (
                x
                - robot.avoidance_start_x
            )

            shift_dy = (
                y
                - robot.avoidance_start_y
            )

            shift_distance = math.hypot(
                shift_dx,
                shift_dy,
            )

            right_too_close = (
                robot.received_scan
                and
                robot.right_clearance
                <= HEAD_ON_WALL_MIN_DISTANCE
            )

            shift_complete = (
                shift_distance
                >= HEAD_ON_SHIFT_DISTANCE
            )

            # 已取得足夠側向空間，
            # 或右側已經太靠牆：
            # 不再往右擠，開始轉回原行進方向。
            if (
                shift_complete
                or right_too_close
            ):
                robot.avoidance_state = (
                    "head_on_parallel_turn"
                )

                robot.avoidance_target_yaw = (
                    robot.head_on_original_yaw
                )

                reason = (
                    "distance"
                    if shift_complete
                    else "right_wall"
                )

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"shift complete -> parallel_turn "
                    f"reason={reason} "
                    f"shift={shift_distance:.2f}m "
                    f"right={robot.right_clearance:.2f}m"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            # 保持 35 度右偏方向
            heading_error = normalize_angle(
                robot.avoidance_target_yaw
                - yaw
            )

            angular = clamp(
                ANGULAR_KP
                * heading_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            # 越靠近右牆，速度越低
            linear = HEAD_ON_LINEAR_SPEED

            if (
                robot.received_scan
                and
                robot.right_clearance
                < SIDE_SAFE_DISTANCE
            ):
                linear = min(
                    linear,
                    0.12,
                )

            self.command_robot(
                robot.robot_id,
                linear,
                angular,
            )

            return


        # ----------------------------------------------------
        # HEAD-ON PARALLEL TURN
        #
        # 側移完成後，重新轉回正面相遇前的行進方向。
        # ----------------------------------------------------

        if (
            robot.avoidance_state
            == "head_on_parallel_turn"
        ):

            turn_error = normalize_angle(
                robot.head_on_original_yaw
                - yaw
            )

            if (
                abs(turn_error)
                <= AVOID_TURN_TOLERANCE
            ):
                robot.avoidance_state = (
                    "head_on_parallel"
                )

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"parallel heading reached -> pass"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            angular = clamp(
                ANGULAR_KP
                * turn_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return


        # ----------------------------------------------------
        # HEAD-ON PARALLEL
        #
        # 已經位於右側的平行軌道。
        # 保持原本方向向前，直到：
        #
        # 1. 與對方距離 >= HEAD_ON_CLEAR_DISTANCE
        # 2. 對方確實已經位於自己後方
        #
        # 才可以 recover。
        # ----------------------------------------------------

        if (
            robot.avoidance_state
            == "head_on_parallel"
        ):

            other = self.robots.get(
                robot.head_on_robot_id
            )

            other_distance = math.inf
            other_forward = math.inf

            other_has_pose = False

            if other is not None:
                other_has_pose = (
                    other.received_ground_truth
                    or other.received_odom
                )

            if (
                other is not None
                and other_has_pose
            ):
                (
                    other_x,
                    other_y,
                    _,
                ) = other.map_pose()

                rel_x = (
                    other_x - x
                )

                rel_y = (
                    other_y - y
                )

                other_distance = math.hypot(
                    rel_x,
                    rel_y,
                )

                # 把「對方相對位置」投影到
                # 自己原本的前進方向。
                #
                # > 0：對方還在前面
                # < 0：對方已經通過、位於後方
                other_forward = (
                    math.cos(
                        robot.head_on_original_yaw
                    )
                    * rel_x
                    +
                    math.sin(
                        robot.head_on_original_yaw
                    )
                    * rel_y
                )

            passed_other = (
                other_forward
                <= -HEAD_ON_BEHIND_MARGIN
            )

            clear_enough = (
                other_distance
                >= HEAD_ON_CLEAR_DISTANCE
            )

            if (
                passed_other
                and clear_enough
            ):
                robot.avoidance_state = (
                    "head_on_return_turn"
                )

                # 往左斜回原本 lane
                robot.avoidance_target_yaw = (
                    normalize_angle(
                        robot.head_on_original_yaw
                        + HEAD_ON_TURN_ANGLE
                    )
                )

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"parallel pass complete -> return_turn "
                    f"robot_distance={other_distance:.2f}m "
                    f"forward={other_forward:.2f}m"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            # ------------------------------------------------
            # 平行通過時：
            # 仍然持續保持原始 heading。
            # ------------------------------------------------

            heading_error = normalize_angle(
                robot.head_on_original_yaw
                - yaw
            )

            angular = clamp(
                ANGULAR_KP
                * heading_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            linear = HEAD_ON_LINEAR_SPEED

            if robot.received_scan:

                left = robot.left_clearance
                right = robot.right_clearance

                # 右牆太近 -> 往左修
                if (
                    right
                    < SIDE_SAFE_DISTANCE
                ):
                    correction = (
                        SIDE_SAFE_DISTANCE
                        - right
                    )

                    angular += clamp(
                        SIDE_CORRECTION_KP
                        * correction,
                        0.0,
                        HEAD_ON_MAX_ANGULAR_SPEED,
                    )

                    linear = min(
                        linear,
                        0.14,
                    )

                # 左側太近 -> 往右修
                elif (
                    left
                    < SIDE_SAFE_DISTANCE
                ):
                    correction = (
                        SIDE_SAFE_DISTANCE
                        - left
                    )

                    angular -= clamp(
                        SIDE_CORRECTION_KP
                        * correction,
                        0.0,
                        HEAD_ON_MAX_ANGULAR_SPEED,
                    )

                    linear = min(
                        linear,
                        0.14,
                    )

            angular = clamp(
                angular,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            self.command_robot(
                robot.robot_id,
                linear,
                angular,
            )

            return


        # ----------------------------------------------------
        # HEAD-ON RETURN TURN
        #
        # 已經錯車完成。
        # 現在往左轉，準備回到正面相遇前的原始 lane。
        # ----------------------------------------------------

        if (
            robot.avoidance_state
            == "head_on_return_turn"
        ):

            turn_error = normalize_angle(
                robot.avoidance_target_yaw
                - yaw
            )

            if (
                abs(turn_error)
                <= AVOID_TURN_TOLERANCE
            ):
                robot.avoidance_state = (
                    "head_on_return"
                )

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"return heading reached -> return"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            angular = clamp(
                ANGULAR_KP
                * turn_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return


        # ----------------------------------------------------
        # HEAD-ON RETURN
        #
        # 以 Ground Truth 計算目前距離原始 lane
        # 還有多少橫向偏移。
        #
        # lateral_offset:
        #   0      = 已回原 lane
        #   < 0    = 位於原 lane 右側
        #   > 0    = 已超過原 lane 左側
        # ----------------------------------------------------

        if (
            robot.avoidance_state
            == "head_on_return"
        ):

            anchor_dx = (
                x
                - robot.head_on_lane_anchor_x
            )

            anchor_dy = (
                y
                - robot.head_on_lane_anchor_y
            )

            lateral_offset = (
                -math.sin(
                    robot.head_on_original_yaw
                )
                * anchor_dx
                +
                math.cos(
                    robot.head_on_original_yaw
                )
                * anchor_dy
            )

            # 已回到原始 lane，
            # 或已經稍微跨過中心線：
            # 不再繼續左移。
            lane_rejoined = (
                lateral_offset
                >= -HEAD_ON_LANE_TOLERANCE
            )

            if lane_rejoined:

                robot.avoidance_state = (
                    "recover"
                )

                robot.head_on_robot_id = None

                self.get_logger().info(
                    f"[HEADON] {robot.robot_id} "
                    f"lane rejoined -> recover "
                    f"lateral_offset="
                    f"{lateral_offset:.2f}m"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            # 保持左斜回線方向
            heading_error = normalize_angle(
                robot.avoidance_target_yaw
                - yaw
            )

            angular = clamp(
                ANGULAR_KP
                * heading_error,
                -HEAD_ON_MAX_ANGULAR_SPEED,
                HEAD_ON_MAX_ANGULAR_SPEED,
            )

            linear = HEAD_ON_LINEAR_SPEED

            # 回線時若左側已經太近，
            # 降低速度，避免左側撞牆。
            if (
                robot.received_scan
                and
                robot.left_clearance
                < SIDE_SAFE_DISTANCE
            ):
                linear = min(
                    linear,
                    0.12,
                )

            self.command_robot(
                robot.robot_id,
                linear,
                angular,
            )

            return


        # ----------------------------------------------------
        # TURN
        # ----------------------------------------------------

        if robot.avoidance_state == "turn":

            turn_reached, angular = (
                compute_turn_command(
                    yaw,
                    robot.avoidance_target_yaw,
                )
            )

            # 已轉到避障方向
            if turn_reached:
                robot.avoidance_state = (
                    "bypass"
                )

                self.get_logger().info(
                    f"[AVOID] {robot.robot_id} "
                    f"turn complete -> bypass"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return

        # ----------------------------------------------------
        # BYPASS
        # ----------------------------------------------------

        if robot.avoidance_state == "bypass":

            bypass_dx = (
                x
                - robot.avoidance_start_x
            )

            bypass_dy = (
                y
                - robot.avoidance_start_y
            )

            bypass_distance = math.hypot(
                bypass_dx,
                bypass_dy,
            )

            # 繞行途中前面又出現障礙
            # 再往原本選定的方向多轉 30 度
            if (
                robot.received_scan
                and
                robot.front_clearance
                <= OBSTACLE_STOP_DISTANCE
            ):
                robot.avoidance_target_yaw = (
                    normalize_angle(
                        yaw
                        +
                        robot.avoidance_turn_direction
                        * AVOID_EXTRA_TURN_ANGLE
                    )
                )

                robot.avoidance_state = (
                    "turn"
                )

                self.get_logger().warning(
                    f"[AVOID] {robot.robot_id} "
                    f"obstacle during bypass, "
                    f"turn more"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            # ------------------------------------------------
            # 確認真的已經繞過障礙，才開始 recover
            # ------------------------------------------------

            (
                can_recover,
                side_clearance,
            ) = can_recover_from_bypass(
                robot,
                bypass_distance,
            )

            if can_recover:

                robot.avoidance_state = "recover"

                self.get_logger().info(
                    f"[AVOID] {robot.robot_id} "
                    f"bypass complete -> recover "
                    f"distance={bypass_distance:.2f}m "
                    f"front={robot.front_clearance:.2f}m "
                    f"side={side_clearance:.2f}m"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            # ------------------------------------------------
            # bypass 時保持左右安全距離
            # 同時在安全時逐漸朝原本 waypoint 拉回
            # ------------------------------------------------

            (
                bypass_linear,
                bypass_angular,
            ) = compute_bypass_command(
                robot,
                dx,
                dy,
                yaw,
            )

            self.command_robot(
                robot.robot_id,
                bypass_linear,
                bypass_angular,
            )

            return

        # ----------------------------------------------------
        # RECOVER
        # ----------------------------------------------------

        if robot.avoidance_state == "recover":

            (
                recovered,
                angular,
            ) = compute_recover_command(
                dx,
                dy,
                yaw,
            )

            # 已重新面向原本 waypoint
            if recovered:
                robot.avoidance_state = (
                    "normal"
                )

                robot.avoidance_turn_direction = 0

                self.get_logger().info(
                    f"[AVOID] {robot.robot_id} "
                    f"recover complete -> normal"
                )

                self.stop_robot(
                    robot.robot_id
                )

                return

            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return

        # ----------------------------------------------------
        # NORMAL -> robot-to-robot conflict
        # ----------------------------------------------------

        if robot.avoidance_state == "normal":

            conflict_robot = self.find_robot_conflict(
                robot,
                x,
                y,
                yaw,
            )

            if conflict_robot is not None:

                # ====================================================
                # Case 0:
                # 前方是靜止 robot
                #
                # 不使用 robot ID yield，
                # 先進 stationary_wait。
                # ====================================================

                if not conflict_robot.navigating():
                    robot.avoidance_state = (
                        "stationary_wait"
                    )

                    robot.stationary_robot_id = (
                        conflict_robot.robot_id
                    )

                    robot.stationary_wait_ticks = 0

                    self.get_logger().warning(
                        f"[STATIONARY] "
                        f"{robot.robot_id} "
                        f"blocked by "
                        f"{conflict_robot.robot_id} "
                        f"-> wait"
                    )

                    self.stop_robot(
                        robot.robot_id
                    )

                    return

                # ====================================================
                # Case 1:
                # 兩台正面相遇
                #
                # 不使用 YIELD。
                # 兩台都往「自己的右邊」小幅避讓。
                # ====================================================

                if self.is_head_on_conflict(
                    robot,
                    conflict_robot,
                    x,
                    y,
                    yaw,
                ):

                    robot.avoidance_state = (
                        "head_on_turn"
                    )

                    robot.head_on_robot_id = (
                        conflict_robot.robot_id
                    )

                    # 記住正面相遇前原本的前進方向。
                    # 右移完成後會重新轉回這個方向。
                    robot.head_on_original_yaw = yaw

                    # 記住原本 lane 的基準點。
                    # 後續會用 Ground Truth 判斷
                    # 是否已經回到原本路線。
                    robot.head_on_lane_anchor_x = x
                    robot.head_on_lane_anchor_y = y

                    # 右轉 = yaw 減少
                    robot.avoidance_target_yaw = (
                        normalize_angle(
                            yaw
                            - HEAD_ON_TURN_ANGLE
                        )
                    )

                    self.get_logger().warning(
                        f"[HEADON] {robot.robot_id} "
                        f"meet "
                        f"{conflict_robot.robot_id} "
                        f"-> keep RIGHT"
                    )

                    self.stop_robot(
                        robot.robot_id
                    )

                    return

                # ====================================================
                # Case 2:
                # 不是正面相遇
                #
                # 如果對方是靜止 robot，
                # 目前正在移動的 robot 一律停車讓路。
                #
                # 如果雙方都正在導航，
                # 才使用原本 deterministic YIELD。
                # ====================================================

                current_number = int(
                    robot.robot_id.rsplit(
                        "_",
                        1,
                    )[-1]
                )

                other_number = int(
                    conflict_robot.robot_id.rsplit(
                        "_",
                        1,
                    )[-1]
                )

                # ID 較大的 robot 讓路
                if current_number > other_number:

                    robot.avoidance_state = "yield"

                    robot.yield_to_robot_id = (
                        conflict_robot.robot_id
                    )

                    self.get_logger().warning(
                        f"[YIELD] {robot.robot_id} "
                        f"yield to "
                        f"{conflict_robot.robot_id}"
                    )

                    self.stop_robot(
                        robot.robot_id
                    )

                    return
        # ----------------------------------------------------
        # Final waypoint reached
        # ----------------------------------------------------

        final_result = compute_final_goal_command(
            target,
            distance,
            yaw,
            is_last,
        )

        if final_result is not None:
            (
                final_status,
                final_linear,
                final_angular,
            ) = final_result

            if final_status == "rotate":
                self.command_robot(
                    robot.robot_id,
                    final_linear,
                    final_angular,
                )
                return

            if final_status == "complete":
                self.stop_robot(
                    robot.robot_id
                )

                completed_task = (
                    robot.task_id
                )

                robot.current_target_index = (
                    len(robot.path)
                )

                robot.path = []

                self.get_logger().info(
                    f"{robot.robot_id} "
                    f"completed path "
                    f"task_id={completed_task}"
                )

                return

        # ----------------------------------------------------
        # NORMAL -> obstacle detected
        # ----------------------------------------------------

        if should_trigger_obstacle_avoidance(
            robot,
            distance,
            is_last,
        ):

            robot.avoidance_start_x = x
            robot.avoidance_start_y = y

            (
                robot.avoidance_turn_direction,
                direction_name,
            ) = choose_avoidance_direction(
                robot
            )

            robot.avoidance_target_yaw = (
                normalize_angle(
                    yaw
                    +
                    robot.avoidance_turn_direction
                    * AVOID_TURN_ANGLE
                )
            )

            robot.avoidance_state = "turn"

            self.get_logger().warning(
                f"[AVOID] {robot.robot_id} "
                f"pos=({x:.2f},{y:.2f}) "
                f"target=({float(target.x):.2f},"
                f"{float(target.y):.2f}) "
                f"target_dist={distance:.2f}m "
                f"yaw={yaw:.2f} "
                f"front={robot.front_clearance:.2f}m "
                f"raw_min={robot.front_raw_min:.2f}m "
                f"close_beams="
                f"{robot.front_close_count}/"
                f"{robot.front_beam_count} "
                f"left={robot.left_clearance:.2f}m "
                f"right={robot.right_clearance:.2f}m "
                f"choose={direction_name}"
            )

            self.stop_robot(
                robot.robot_id
            )

            return

        # ----------------------------------------------------
        # Normal waypoint tracking
        # ----------------------------------------------------

        linear, angular = (
            compute_normal_tracking_command(
                target,
                dx,
                dy,
                distance,
                yaw,
                is_last,
                robot_x=x,
                robot_y=y,
                segment_anchor_x=(
                    robot.segment_anchor_x
                ),
                segment_anchor_y=(
                    robot.segment_anchor_y
                ),
            )
        )

        # ----------------------------------------------------
        # LiDAR front obstacle handling
        # ----------------------------------------------------

        if robot.received_scan:

            # 前方障礙物接近：依距離逐漸減速
            if robot.front_clearance < OBSTACLE_SLOW_DISTANCE:

                obstacle_scale = (
                    (
                        robot.front_clearance
                        - OBSTACLE_STOP_DISTANCE
                    )
                    /
                    (
                        OBSTACLE_SLOW_DISTANCE
                        - OBSTACLE_STOP_DISTANCE
                    )
                )

                obstacle_scale = clamp(
                    obstacle_scale,
                    0.20,
                    1.0,
                )

                linear *= obstacle_scale

        self.command_robot(
            robot.robot_id,
            linear,
            angular,
        )

    # ========================================================
    # RobotState
    # ========================================================

    def make_state(
        self,
        robot,
        now_msg,
    ):
        # Nav2 uses TF map -> base_link as its authoritative
        # map-frame pose. RMF must use the same pose, otherwise
        # RMF may consider the robot lost even when Nav2 has
        # successfully reached its goal.
        try:
            transform = self.tf_buffer.lookup_transform(
                "map",
                f"{robot.robot_id}/base_link",
                rclpy.time.Time(),
            )

            translation = (
                transform.transform.translation
            )

            rotation = (
                transform.transform.rotation
            )

            map_x = float(
                translation.x
            )

            map_y = float(
                translation.y
            )

            map_yaw = math.atan2(
                2.0 * (
                    rotation.w * rotation.z
                    + rotation.x * rotation.y
                ),
                1.0 - 2.0 * (
                    rotation.y * rotation.y
                    + rotation.z * rotation.z
                ),
            )

        except Exception as exc:
            # RMF RobotState must always be expressed in the
            # Nav2/RMF map frame. The Gazebo ground-truth pose
            # (/model/<robot>/pose) is not guaranteed to use the
            # same frame, so publishing it as a fallback can make
            # RMF believe the robot is far away from the graph.
            #
            # Wait until map -> base_link is available instead.
            self.get_logger().debug(
                f"{robot.robot_id}: "
                "RMF state skipped; map TF not ready: "
                f"{exc}"
            )
            return None

        msg = RobotState()

        msg.name = (
            robot.robot_id
        )

        msg.model = (
            FLEET_NAME
        )

        # PathRequest 規格要求帶回最新 task_id
        msg.task_id = (
            robot.task_id
        )

        msg.seq = (
            robot.seq
        )

        robot.seq += 1

        msg.mode = RobotMode()

        if robot.navigating():
            msg.mode.mode = (
                RobotMode.MODE_MOVING
            )
        else:
            msg.mode.mode = (
                RobotMode.MODE_IDLE
            )

        msg.location = Location()

        msg.location.t = (
            now_msg
        )

        msg.location.x = float(
            map_x
        )

        msg.location.y = float(
            map_y
        )

        msg.location.yaw = float(
            map_yaw
        )

        msg.location.level_name = (
            MAP_NAME
        )

        msg.battery_percent = (
            BATTERY_PERCENT
        )

        msg.path = (
            robot.remaining_path()
        )

        return msg

    # ========================================================
    # Main periodic loop
    # ========================================================

    def on_timer(self):

        now_msg = (
            self
            .get_clock()
            .now()
            .to_msg()
        )

        for robot in (
            self.robots.values()
        ):

            if not robot.received_odom:
                continue

            # Navigation commands are handled by Nav2.
            # This bridge only translates RMF paths and
            # publishes RobotState.

            state = self.make_state(
                robot,
                now_msg,
            )

            if state is None:
                continue

            self.state_pub.publish(
                state
            )


def main(args=None):

    rclpy.init(
        args=args
    )

    node = (
        HospitalG1NavigationBridge()
    )

    try:
        rclpy.spin(
            node
        )

    except KeyboardInterrupt:
        pass

    finally:

        # 程式關閉時保證所有 G1 停車
        for robot_id in (
            node.robots.keys()
        ):
            node.stop_robot(
                robot_id
            )

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
