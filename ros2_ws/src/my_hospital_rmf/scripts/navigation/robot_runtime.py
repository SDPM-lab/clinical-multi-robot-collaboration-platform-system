import math

from navigation.utils import (
    normalize_angle,
    quaternion_to_yaw,
)


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

        self.spawn_x = float(spawn_x)
        self.spawn_y = float(spawn_y)
        self.spawn_yaw = float(spawn_yaw)

        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0
        self.received_odom = False

        self.gt_x = 0.0
        self.gt_y = 0.0
        self.gt_yaw = 0.0
        self.received_ground_truth = False

        self.received_scan = False

        self.front_clearance = math.inf
        self.left_clearance = math.inf
        self.right_clearance = math.inf

        self.front_raw_min = math.inf
        self.front_close_count = 0
        self.front_beam_count = 0

        self.avoidance_state = "normal"
        self.avoidance_turn_direction = 0
        self.avoidance_target_yaw = 0.0
        self.avoidance_start_x = 0.0
        self.avoidance_start_y = 0.0

        self.yield_to_robot_id = None

        self.head_on_robot_id = None
        self.head_on_original_yaw = 0.0

        self.head_on_lane_anchor_x = 0.0
        self.head_on_lane_anchor_y = 0.0

        self.last_scan_log_time = -1.0e9

        self.task_id = ""
        self.path = []
        self.current_target_index = 0

        self.seq = 0
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

        self.avoidance_state = "normal"
        self.avoidance_turn_direction = 0
        self.avoidance_target_yaw = 0.0
        self.avoidance_start_x = 0.0
        self.avoidance_start_y = 0.0

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
