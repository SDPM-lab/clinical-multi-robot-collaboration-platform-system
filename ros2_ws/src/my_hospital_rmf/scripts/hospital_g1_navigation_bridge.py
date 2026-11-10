#!/usr/bin/env python3

import math
import os
import yaml

import rclpy
from rclpy.node import Node

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


# ============================================================
# RMF / Hospital settings
# ============================================================

FLEET_NAME = "hospital_fleet"
MAP_NAME = "L1"

BATTERY_PERCENT = 99.0

# 10 Hz navigation + state update
CONTROL_PERIOD = 0.1


# ============================================================
# Simple waypoint follower settings
# ============================================================

# 距離 waypoint 小於這個值視為到達
ARRIVE_DISTANCE = 0.25

# 接近最後 waypoint 時進入低速靠近模式，
# 避免普通 TURN/BYPASS 在終點附近把 robot 帶走。
GOAL_APPROACH_DISTANCE = 0.75

# 最後靠近 waypoint 的最大速度
GOAL_APPROACH_MAX_SPEED = 0.12
GOAL_EMERGENCY_STOP_DISTANCE = 0.30

# 最後一個 waypoint 的朝向誤差
FINAL_YAW_TOLERANCE = 0.12

# 朝向誤差超過這個值時，先原地旋轉
ROTATE_FIRST_THRESHOLD = 0.30

# 比例控制(距離目標還多遠，就決定要給多大的前進速度)
LINEAR_KP = 0.7
ANGULAR_KP = 1.5

# 最大直線速度
MAX_LINEAR_SPEED = 0.7

# 最大角速度
MAX_ANGULAR_SPEED = 0.8

# 最小前進速度
MIN_LINEAR_SPEED = 0.06


# ============================================================
# LiDAR obstacle avoidance settings
# ============================================================

# 小於此距離開始減速
OBSTACLE_SLOW_DISTANCE = 0.8

# 小於此距離觸發避障
OBSTACLE_STOP_DISTANCE = 0.55

AVOID_TURN_ANGLE = math.radians(60.0)
AVOID_TURN_TOLERANCE = math.radians(8.0)
AVOID_FORWARD_DISTANCE = 1.2
AVOID_LINEAR_SPEED = 0.30
AVOID_EXTRA_TURN_ANGLE = math.radians(30.0)

# bypass 時與左右障礙物保持安全距離
SIDE_SAFE_DISTANCE = 0.45

# 側邊修正的角速度比例
SIDE_CORRECTION_KP = 2.0

# 側邊修正最大角速度，避免修正太劇烈
SIDE_MAX_ANGULAR_SPEED = 0.50

RECOVER_MIN_SIDE_CLEARANCE = 0.30

# bypass 時，安全後逐漸朝原本 waypoint 拉回
BYPASS_PATH_KP = 0.5

# 回原路線修正不能蓋過避障本身
BYPASS_PATH_MAX_ANGULAR_SPEED = 0.20

# ============================================================
# Robot-to-robot right-of-way
# ============================================================

# 多近時認為兩台 robot 可能發生局部衝突
ROBOT_CONFLICT_DISTANCE = 1.80

# 對方離開多遠後，讓行中的 robot 才恢復
ROBOT_RESUME_DISTANCE = 2.00

# 只判斷前方 ±60 度內的其他 robot
ROBOT_CONFLICT_ANGLE = math.radians(60.0)


# ============================================================
# Head-on reciprocal avoidance
# ============================================================

# 兩台朝向差超過 150 度，視為接近正面相遇
HEAD_ON_MIN_OPPOSITE_ANGLE = math.radians(150.0)

# 正面相遇時，兩台都往自己的右邊偏 25 度
HEAD_ON_TURN_ANGLE = math.radians(35.0)

# 小幅側移，不需要像一般障礙繞 1.2m
HEAD_ON_FORWARD_DISTANCE = 1.00

# 三段式 head-on：
# 先右斜移，再轉回原方向平行錯車
HEAD_ON_SHIFT_DISTANCE = 0.55

# 右側離牆太近時，不再繼續往右斜移
HEAD_ON_WALL_MIN_DISTANCE = 0.45

# 對方必須確實進入自己後方，才算完成錯車
HEAD_ON_BEHIND_MARGIN = 0.20

# 回到原本 lane 時允許的橫向誤差
HEAD_ON_LANE_TOLERANCE = 0.10

# 彼此距離拉開到這個程度，就開始回原 waypoint
HEAD_ON_CLEAR_DISTANCE = 1.40

# 正面會車速度
HEAD_ON_LINEAR_SPEED = 0.18

# 維持右偏方向的角速度上限
HEAD_ON_MAX_ANGULAR_SPEED = 0.30


# ============================================================
# Utility functions
# ============================================================

def clamp(value, low, high):
    return max(low, min(high, value))


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi

    while angle < -math.pi:
        angle += 2.0 * math.pi

    return angle


def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (
        q.w * q.z
        + q.x * q.y
    )

    cosy_cosp = 1.0 - 2.0 * (
        q.y * q.y
        + q.z * q.z
    )

    return math.atan2(
        siny_cosp,
        cosy_cosp,
    )


# ============================================================
# Per-robot runtime state
# ============================================================

class RobotRuntime:

    def __init__(
        self,
        robot_id,
        robot_type,
        spawn_x,
        spawn_y,
        spawn_yaw,
    ):
        self.robot_id = robot_id
        self.robot_type = robot_type

        # G1 出生時在醫院 map 的座標
        self.spawn_x = float(spawn_x)
        self.spawn_y = float(spawn_y)
        self.spawn_yaw = float(spawn_yaw)

        # diff_drive_controller odometry
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0

        self.received_odom = False

        # Gazebo ground-truth pose
        self.gt_x = 0.0
        self.gt_y = 0.0
        self.gt_yaw = 0.0
        self.received_ground_truth = False

        # LiDAR obstacle clearance
        self.received_scan = False

        self.front_clearance = math.inf
        self.left_clearance = math.inf
        self.right_clearance = math.inf

        # LiDAR debug information
        self.front_raw_min = math.inf
        self.front_close_count = 0
        self.front_beam_count = 0

        self.avoidance_state = "normal"
        self.avoidance_turn_direction = 0
        self.avoidance_target_yaw = 0.0
        self.avoidance_start_x = 0.0
        self.avoidance_start_y = 0.0

        # Robot-to-robot yielding
        self.yield_to_robot_id = None

        # 正面會車時正在避讓的另一台 robot
        self.head_on_robot_id = None

        # 正面會車開始前原本的行進方向
        # SHIFT 完成後會轉回此方向進行平行錯車
        self.head_on_original_yaw = 0.0

        # 正面會車開始時所在的原始 lane 基準點
        self.head_on_lane_anchor_x = 0.0
        self.head_on_lane_anchor_y = 0.0

        # 避免 20 Hz LiDAR log 洗版
        self.last_scan_log_time = -1.0e9

        # 最新 RMF PathRequest
        self.task_id = ""
        self.path = []
        self.current_target_index = 0

        self.seq = 0

        # 避免 completion log 重複
        self.was_navigating = False

    def update_odom(self, msg):
        self.odom_x = float(
            msg.pose.pose.position.x
        )

        self.odom_y = float(
            msg.pose.pose.position.y
        )

        self.odom_yaw = quaternion_to_yaw(
            msg.pose.pose.orientation
        )

        self.received_odom = True

    def update_ground_truth(self, msg):
        self.gt_x = float(
            msg.position.x
        )

        self.gt_y = float(
            msg.position.y
        )

        self.gt_yaw = quaternion_to_yaw(
            msg.orientation
        )

        self.received_ground_truth = True

    def map_pose(self):
        """
        取得目前在醫院 / RMF map 中的 pose。

        優先使用 Gazebo ground-truth pose。
        若尚未收到 ground truth，才 fallback 到
        spawn + diff_drive_controller odometry。
        """

        if self.received_ground_truth:
            return (
                self.gt_x,
                self.gt_y,
                self.gt_yaw,
            )

        c = math.cos(
            self.spawn_yaw
        )

        s = math.sin(
            self.spawn_yaw
        )

        map_x = (
            self.spawn_x
            + c * self.odom_x
            - s * self.odom_y
        )

        map_y = (
            self.spawn_y
            + s * self.odom_x
            + c * self.odom_y
        )

        map_yaw = normalize_angle(
            self.spawn_yaw
            + self.odom_yaw
        )

        return (
            map_x,
            map_y,
            map_yaw,
        )

    def receive_path(
        self,
        task_id,
        path,
    ):
        self.task_id = task_id
        self.path = list(path)
        self.current_target_index = 0

        # 新 PathRequest 進來時重置避障狀態
        self.avoidance_state = "normal"
        self.avoidance_turn_direction = 0
        self.avoidance_target_yaw = 0.0
        self.avoidance_start_x = 0.0
        self.avoidance_start_y = 0.0

        # Robot-to-robot yielding
        self.yield_to_robot_id = None

        self.head_on_robot_id = None

    def navigating(self):
        return (
            self.current_target_index
            < len(self.path)
        )

    def remaining_path(self):
        if not self.navigating():
            return []

        return self.path[
            self.current_target_index:
        ]


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

            self.cmd_publishers[
                robot_id
            ] = self.create_publisher(
                Twist,
                cmd_topic,
                10,
            )

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

        # --------------------------------------------------
        # LiDAR sectors
        #
        #            FRONT
        #          -20 ~ +20 deg
        #
        # RIGHT                  LEFT
        # -80 ~ -25 deg     +25 ~ +80 deg
        # --------------------------------------------------

        front_values = []
        left_values = []
        right_values = []

        front_limit = math.radians(10.0)

        side_inner = math.radians(25.0)
        side_outer = math.radians(80.0)

        for index, value in enumerate(
            msg.ranges
        ):
            distance = float(value)

            if not math.isfinite(
                distance
            ):
                continue

            if (
                distance < msg.range_min
                or
                distance > msg.range_max
            ):
                continue

            angle = (
                float(msg.angle_min)
                + index
                * float(msg.angle_increment)
            )

            # Front
            if abs(angle) <= front_limit:
                front_values.append(
                    distance
                )

            # Left
            elif (
                side_inner
                <= angle
                <= side_outer
            ):
                left_values.append(
                    distance
                )

            # Right
            elif (
                -side_outer
                <= angle
                <= -side_inner
            ):
                right_values.append(
                    distance
                )

        # LiDAR debug statistics
        robot.front_beam_count = len(
            front_values
        )

        robot.front_raw_min = (
            min(front_values)
            if front_values
            else math.inf
        )

        robot.front_close_count = sum(
            1
            for value in front_values
            if value <= OBSTACLE_STOP_DISTANCE
        )

        # Front clearance 使用 robust percentile，
        # 避免單一異常 LiDAR beam 直接觸發整套避障。
        #
        # 取排序後約 25th percentile：
        # 真正障礙物通常會同時佔據多條 beam，
        # 單點異常值則會被忽略。
        if front_values:
            sorted_front = sorted(
                front_values
            )

            front_index = int(
                0.25
                * (
                    len(sorted_front)
                    - 1
                )
            )

            robot.front_clearance = (
                sorted_front[
                    front_index
                ]
            )
        else:
            robot.front_clearance = math.inf

        robot.left_clearance = (
            min(left_values)
            if left_values
            else math.inf
        )

        robot.right_clearance = (
            min(right_values)
            if right_values
            else math.inf
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

        robot.receive_path(
            msg.task_id,
            msg.path,
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

        # 空 path = 停止
        if len(msg.path) == 0:
            self.stop_robot(
                msg.robot_name
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

        self.cmd_publishers[
            robot_id
        ].publish(msg)

    def find_robot_conflict(
        self,
        robot,
        x,
        y,
        yaw,
    ):
        """
        找出目前 robot 前方一定距離內，
        是否有另一台「正在導航」的 robot。

        回傳：
            other_robot
        或：
            None
        """

        closest_robot = None
        closest_distance = math.inf

        for other in self.robots.values():

            # 不跟自己比較
            if other.robot_id == robot.robot_id:
                continue

            # 對方還沒有 odom
            if not other.received_odom:
                continue

            # 只有兩台都正在移動時才使用讓行規則
            # 靜止 robot 還是當一般障礙物處理
            if not other.navigating():
                continue

            (
                other_x,
                other_y,
                _,
            ) = other.map_pose()

            dx = other_x - x
            dy = other_y - y

            distance = math.hypot(
                dx,
                dy,
            )

            if distance > ROBOT_CONFLICT_DISTANCE:
                continue

            direction_to_other = math.atan2(
                dy,
                dx,
            )

            angle_error = normalize_angle(
                direction_to_other - yaw
            )

            # 只處理前方 ±60 度內的 robot
            if abs(angle_error) > ROBOT_CONFLICT_ANGLE:
                continue

            if distance < closest_distance:
                closest_distance = distance
                closest_robot = other

        return closest_robot

    def is_head_on_conflict(
        self,
        robot,
        other,
        x,
        y,
        yaw,
    ):
        """
        判斷兩台正在移動的 robot 是否接近正面相遇。
        """

        if other is None:
            return False

        if not other.received_odom:
            return False

        if not other.navigating():
            return False

        (
            other_x,
            other_y,
            other_yaw,
        ) = other.map_pose()

        # --------------------------------------------
        # 1. 兩台朝向是否幾乎相反
        # --------------------------------------------

        heading_difference = abs(
            normalize_angle(
                other_yaw - yaw
            )
        )

        if (
            heading_difference
            < HEAD_ON_MIN_OPPOSITE_ANGLE
        ):
            return False

        # --------------------------------------------
        # 2. 我是不是也位於對方前方
        # --------------------------------------------

        direction_other_to_me = math.atan2(
            y - other_y,
            x - other_x,
        )

        other_front_error = normalize_angle(
            direction_other_to_me
            - other_yaw
        )

        if (
            abs(other_front_error)
            > ROBOT_CONFLICT_ANGLE
        ):
            return False

        return True

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

            turn_error = normalize_angle(
                robot.avoidance_target_yaw
                - yaw
            )

            # 已轉到避障方向
            if (
                abs(turn_error)
                <= AVOID_TURN_TOLERANCE
            ):
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

            angular = clamp(
                ANGULAR_KP
                * turn_error,
                -MAX_ANGULAR_SPEED,
                MAX_ANGULAR_SPEED,
            )

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

            side_clearance = math.inf

            # 如果原本是往左繞，障礙物通常會留在右側
            if robot.avoidance_turn_direction > 0:
                side_clearance = robot.right_clearance

            # 如果原本是往右繞，障礙物通常會留在左側
            elif robot.avoidance_turn_direction < 0:
                side_clearance = robot.left_clearance


            can_recover = (
                bypass_distance >= AVOID_FORWARD_DISTANCE
                and robot.front_clearance > OBSTACLE_SLOW_DISTANCE
                and side_clearance > RECOVER_MIN_SIDE_CLEARANCE
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

            bypass_linear = AVOID_LINEAR_SPEED
            bypass_angular = 0.0

            if robot.received_scan:

                left = robot.left_clearance
                right = robot.right_clearance

                side_too_close = (
                    left < SIDE_SAFE_DISTANCE
                    or right < SIDE_SAFE_DISTANCE
                )

                # ------------------------------------------------
                # 1. 側邊太近：安全優先
                # ------------------------------------------------

                if side_too_close:

                    # 側邊太近時減速
                    bypass_linear = 0.15

                    # 左邊比較近 -> 往右修
                    if left <= right:

                        correction = (
                            SIDE_SAFE_DISTANCE - left
                        )

                        bypass_angular = clamp(
                            -SIDE_CORRECTION_KP
                            * correction,
                            -SIDE_MAX_ANGULAR_SPEED,
                            SIDE_MAX_ANGULAR_SPEED,
                        )

                    # 右邊比較近 -> 往左修
                    else:

                        correction = (
                            SIDE_SAFE_DISTANCE - right
                        )

                        bypass_angular = clamp(
                            SIDE_CORRECTION_KP
                            * correction,
                            -SIDE_MAX_ANGULAR_SPEED,
                            SIDE_MAX_ANGULAR_SPEED,
                        )

                # ------------------------------------------------
                # 2. 左右都安全：
                #    開始朝原本 waypoint 的方向拉回
                # ------------------------------------------------

                else:

                    waypoint_yaw = math.atan2(
                        dy,
                        dx,
                    )

                    waypoint_error = normalize_angle(
                        waypoint_yaw - yaw
                    )

                    path_correction = clamp(
                        BYPASS_PATH_KP
                        * waypoint_error,
                        -BYPASS_PATH_MAX_ANGULAR_SPEED,
                        BYPASS_PATH_MAX_ANGULAR_SPEED,
                    )

                    bypass_angular += path_correction


            # 最後再限制一次角速度
            bypass_angular = clamp(
                bypass_angular,
                -SIDE_MAX_ANGULAR_SPEED,
                SIDE_MAX_ANGULAR_SPEED,
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

            recover_yaw = math.atan2(
                dy,
                dx,
            )

            recover_error = (
                normalize_angle(
                    recover_yaw
                    - yaw
                )
            )

            # 已重新面向原本 waypoint
            if (
                abs(recover_error)
                <= ROTATE_FIRST_THRESHOLD
            ):
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

            angular = clamp(
                ANGULAR_KP
                * recover_error,
                -MAX_ANGULAR_SPEED,
                MAX_ANGULAR_SPEED,
            )

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
                # 維持原本 deterministic YIELD。
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
        # Final waypoint reached:
        # align final yaw before declaring completion
        # ----------------------------------------------------

        if (
            is_last
            and
            distance <= ARRIVE_DISTANCE
        ):
            target_yaw = float(
                target.yaw
            )

            if math.isfinite(
                target_yaw
            ):
                final_yaw_error = (
                    normalize_angle(
                        target_yaw
                        - yaw
                    )
                )

                if (
                    abs(final_yaw_error)
                    > FINAL_YAW_TOLERANCE
                ):
                    angular = clamp(
                        ANGULAR_KP
                        * final_yaw_error,
                        -MAX_ANGULAR_SPEED,
                        MAX_ANGULAR_SPEED,
                    )

                    self.command_robot(
                        robot.robot_id,
                        0.0,
                        angular,
                    )

                    return

            # Position + final orientation both reached
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

        near_final_goal = (
            is_last
            and
            distance <= GOAL_APPROACH_DISTANCE
        )

        goal_emergency_obstacle = (
            near_final_goal
            and
            robot.received_scan
            and
            robot.front_clearance
            <= GOAL_EMERGENCY_STOP_DISTANCE
        )

        if (
            robot.avoidance_state == "normal"
            and
            robot.received_scan
            and
            robot.front_clearance
            <= OBSTACLE_STOP_DISTANCE
            and
            (
                not near_final_goal
                or goal_emergency_obstacle
            )
        ):

            robot.avoidance_start_x = x
            robot.avoidance_start_y = y

            # 哪邊比較空就往哪邊走
            if (
                robot.left_clearance
                >= robot.right_clearance
            ):
                robot.avoidance_turn_direction = 1

                direction_name = "LEFT"

            else:
                robot.avoidance_turn_direction = -1

                direction_name = "RIGHT"

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

        desired_yaw = math.atan2(
            dy,
            dx,
        )

        heading_error = (
            normalize_angle(
                desired_yaw
                - yaw
            )
        )

        angular = clamp(
            ANGULAR_KP
            * heading_error,
            -MAX_ANGULAR_SPEED,
            MAX_ANGULAR_SPEED,
        )

        # 若還沒朝向 waypoint，先原地轉
        if (
            abs(heading_error)
            > ROTATE_FIRST_THRESHOLD
        ):
            self.command_robot(
                robot.robot_id,
                0.0,
                angular,
            )

            return

        linear_limit = (
            MAX_LINEAR_SPEED
        )

        # 支援 RMF Location 的 approach speed limit
        if (
            target.obey_approach_speed_limit
            and
            target.approach_speed_limit > 0.0
        ):
            linear_limit = min(
                linear_limit,
                float(
                    target.approach_speed_limit
                ),
            )

        linear = min(
            linear_limit,
            LINEAR_KP * distance,
        )

        # 最後 waypoint 附近改成低速靠近，
        # 不再高速衝過目標後回頭修正。
        if (
            is_last
            and
            distance <= GOAL_APPROACH_DISTANCE
        ):
            linear = min(
                linear,
                GOAL_APPROACH_MAX_SPEED,
            )

        if (
            distance > ARRIVE_DISTANCE
            and
            linear < MIN_LINEAR_SPEED
        ):
            linear = min(
                MIN_LINEAR_SPEED,
                linear_limit,
            )

        # heading error 越大，前進速度稍微降低
        heading_scale = max(
            0.25,
            1.0
            - abs(heading_error)
            / ROTATE_FIRST_THRESHOLD,
        )

        linear *= heading_scale


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
        (
            map_x,
            map_y,
            map_yaw,
        ) = robot.map_pose()

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

            self.control_robot(
                robot
            )

            state = self.make_state(
                robot,
                now_msg,
            )

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
