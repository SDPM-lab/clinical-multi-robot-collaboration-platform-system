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

        # Stationary robot blocker
        self.stationary_robot_id = None
        self.stationary_wait_ticks = 0

        self.head_on_robot_id = None
        self.head_on_original_yaw = 0.0

        self.head_on_lane_anchor_x = 0.0
        self.head_on_lane_anchor_y = 0.0

        self.last_scan_log_time = -1.0e9

        self.task_id = ""
        self.path = []
        self.current_target_index = 0

        # RMF lane tracking state
        #
        # PathRequest 的第 0 點通常是 robot 當下位置，
        # 不一定是 nav graph lane 的真正起點。
        #
        # 因此保留上一個 RMF goal，讓下一段路徑可以
        # 以前一個 waypoint 作為 lane anchor。
        self.segment_anchor_x = None
        self.segment_anchor_y = None

        self.last_rmf_goal_x = None
        self.last_rmf_goal_y = None

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
        new_path = list(path)

        previous_task_id = self.task_id
        duplicate_path = False

        self.task_id = task_id

        if new_path:
            first_x = float(new_path[0].x)
            first_y = float(new_path[0].y)

            new_goal_x = float(new_path[-1].x)
            new_goal_y = float(new_path[-1].y)

            # 如果上一個 RMF goal 與這次 PathRequest 起點很接近，
            # 代表這通常是同一條 RMF route 的下一個 segment。
            #
            # 使用上一個 RMF waypoint 當 lane anchor，
            # 而不是使用已經可能偏離 lane 的 robot current pose。
            if (
                self.last_rmf_goal_x is not None
                and
                self.last_rmf_goal_y is not None
            ):
                anchor_distance = math.hypot(
                    first_x - self.last_rmf_goal_x,
                    first_y - self.last_rmf_goal_y,
                )

                goal_change = math.hypot(
                    new_goal_x - self.last_rmf_goal_x,
                    new_goal_y - self.last_rmf_goal_y,
                )

                # goal_change 很小通常是 RMF 重送同一段 path。
                # 這時保留既有 anchor，不重新建立斜線。
                if (
                    task_id == previous_task_id
                    and
                    goal_change <= 0.10
                    and
                    self.segment_anchor_x is not None
                    and
                    self.segment_anchor_y is not None
                ):
                    duplicate_path = True

                elif anchor_distance <= 0.75:
                    self.segment_anchor_x = (
                        self.last_rmf_goal_x
                    )
                    self.segment_anchor_y = (
                        self.last_rmf_goal_y
                    )

                else:
                    self.segment_anchor_x = first_x
                    self.segment_anchor_y = first_y

            else:
                self.segment_anchor_x = first_x
                self.segment_anchor_y = first_y

            self.last_rmf_goal_x = new_goal_x
            self.last_rmf_goal_y = new_goal_y

        else:
            self.segment_anchor_x = None
            self.segment_anchor_y = None

        self.path = new_path

        # RMF 重送同一段 path 時，
        # 不要中斷正在執行的 avoidance maneuver。
        if duplicate_path:
            if self.path:
                self.current_target_index = (
                    len(self.path) - 1
                )
            else:
                self.current_target_index = 0

        else:
            self.current_target_index = 0

            self.avoidance_state = "normal"
            self.avoidance_turn_direction = 0
            self.avoidance_target_yaw = 0.0
            self.avoidance_start_x = 0.0
            self.avoidance_start_y = 0.0

            self.yield_to_robot_id = None

            self.stationary_robot_id = None
            self.stationary_wait_ticks = 0

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
