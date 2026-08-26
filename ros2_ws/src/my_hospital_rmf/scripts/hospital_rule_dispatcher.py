#!/usr/bin/env python3

import json
import os
import time
import uuid
import yaml

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
)

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState
from rmf_task_msgs.msg import ApiRequest

from scheduler.models import (
    Task,
    RobotState,
)
from scheduler.capability_matcher import (
    capability_matching,
)
from scheduler.rule_based_scheduler import (
    RuleBasedScheduler,
)


NAV_GRAPH = os.path.join(
    get_package_share_directory("my_hospital_rmf"),
    "nav_graphs",
    "0.yaml",
)

MAP_NAME = "L1"
FLEET_NAME = "hospital_fleet"


# ==========================================================
# Robot capability 設定
#
# 第一版先放在這裡。
# 後續再搬到 fleet_config.yaml。
# ==========================================================

ROBOT_CAPABILITIES = {
    "hospital_robot_1": {
        "navigation",
        "medicine_delivery",
        "general_delivery",
    },
    "hospital_robot_2": {
        "navigation",
        "specimen_delivery",
        "general_delivery",
    },
    "hospital_robot_3": {
        "navigation",
        "general_delivery",
        "manipulation",
    },
}


def get_param_name(params):
    if isinstance(params, dict):
        return params.get("name")

    if isinstance(params, list):
        for item in params:
            if (
                isinstance(item, dict)
                and item.get("name")
            ):
                return item.get("name")

    return None


def load_waypoints(
    nav_graph_path,
    level_name,
):
    with open(
        nav_graph_path,
        "r",
    ) as f:
        data = yaml.safe_load(f)

    vertices = (
        data["levels"]
        [level_name]
        ["vertices"]
    )

    waypoints = {}

    for vertex in vertices:
        x = float(vertex[0])
        y = float(vertex[1])
        params = vertex[2]

        name = get_param_name(params)

        if name:
            waypoints[name] = (
                x,
                y,
            )

    return waypoints


class HospitalRuleDispatcher(Node):

    def __init__(self):
        super().__init__(
            "hospital_rule_dispatcher"
        )

        # ------------------------------------------
        # Waypoints
        # ------------------------------------------

        self.waypoints = load_waypoints(
            NAV_GRAPH,
            MAP_NAME,
        )

        # ------------------------------------------
        # Scheduler
        # ------------------------------------------

        self.scheduler = RuleBasedScheduler(
            self.waypoints
        )

        # ------------------------------------------
        # Robot State
        # ------------------------------------------

        self.robots = {}

        # ------------------------------------------
        # RMF Task Publisher
        # ------------------------------------------

        task_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.task_pub = self.create_publisher(
            ApiRequest,
            "/task_api_requests",
            task_qos,
        )

        # ------------------------------------------
        # Hospital Task Subscriber
        # ------------------------------------------

        self.create_subscription(
            String,
            "/hospital_task_request",
            self.task_request_cb,
            10,
        )

        # ------------------------------------------
        # Fleet State Subscriber
        # ------------------------------------------

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info(
            "Hospital dispatcher started"
        )

        self.get_logger().info(
            "Scheduler: rule_based"
        )

        self.get_logger().info(
            "Listening: "
            "/hospital_task_request"
        )

        self.get_logger().info(
            "Listening: /fleet_states"
        )

        self.get_logger().info(
            "Publishing: /task_api_requests"
        )

    # ======================================================
    # Fleet State
    # ======================================================

    def fleet_state_cb(
        self,
        msg: FleetState,
    ):
        if msg.name != FLEET_NAME:
            return

        for robot in msg.robots:

            task_id = (
                robot.task_id
                or ""
            )

            status = (
                "busy"
                if task_id
                else "idle"
            )

            robot_state = RobotState(
                robot_id=robot.name,

                fleet_name=msg.name,

                status=status,

                battery=float(
                    robot.battery_percent
                ),

                x=float(
                    robot.location.x
                ),

                y=float(
                    robot.location.y
                ),

                map_name=(
                    robot.location.level_name
                ),

                capabilities=(
                    ROBOT_CAPABILITIES.get(
                        robot.name,
                        {"navigation"},
                    )
                ),

                current_task=(
                    task_id
                    if task_id
                    else None
                ),

                available=(
                    not bool(task_id)
                ),
            )

            self.robots[
                robot.name
            ] = robot_state

    # ======================================================
    # Task Request
    # ======================================================

    def task_request_cb(
        self,
        msg: String,
    ):
        self.get_logger().info(
            "Received hospital task: "
            f"{msg.data}"
        )

        try:
            raw_task = json.loads(
                msg.data
            )

            # --------------------------------------
            # 建立標準 Task Model
            # --------------------------------------

            task = Task(
                task_id=(
                    raw_task["task_id"]
                ),

                task_type=(
                    raw_task["task_type"]
                ),

                source=(
                    raw_task["source"]
                ),

                destination=(
                    raw_task["destination"]
                ),

                priority=(
                    raw_task.get(
                        "priority",
                        1,
                    )
                ),

                required_capabilities=(
                    raw_task.get(
                        "required_capabilities",
                        [],
                    )
                ),
            )

            if not self.robots:
                self.get_logger().error(
                    "No fleet state "
                    "received yet"
                )
                return

            # --------------------------------------
            # RobotState dictionary
            # → list[RobotState]
            # --------------------------------------

            robots = list(
                self.robots.values()
            )

            # --------------------------------------
            # Capability Matching
            # --------------------------------------

            candidates = (
                capability_matching(
                    task.required_capabilities,
                    robots,
                )
            )

            if not candidates:
                self.get_logger().error(
                    "No robot satisfies "
                    "required capabilities"
                )
                return

            self.get_logger().info(
                "Candidate robots: "
                + ", ".join(
                    robot.robot_id
                    for robot
                    in candidates
                )
            )

            # --------------------------------------
            # Scheduler
            # --------------------------------------

            assignment = (
                self.scheduler.schedule(
                    task,
                    candidates,
                )
            )

            # --------------------------------------
            # Scheduler Result
            # --------------------------------------

            assignment_json = {
                "task_id":
                    assignment.task_id,

                "robot_id":
                    assignment.robot_id,

                "scheduler":
                    assignment.scheduler,

                "decision_status":
                    assignment.decision_status,

                "score":
                    assignment.score,
            }

            self.get_logger().info(
                "Assignment: "
                + json.dumps(
                    assignment_json,
                    ensure_ascii=False,
                )
            )

            # --------------------------------------
            # 無法派工
            # --------------------------------------

            if (
                assignment.decision_status
                != "assigned"
                or assignment.robot_id
                is None
            ):
                self.get_logger().error(
                    f"Task {task.task_id} "
                    "could not be assigned"
                )
                return

            # --------------------------------------
            # RMF 執行
            # --------------------------------------

            self.send_go_to_place(
                assignment.robot_id,
                task.destination,
                backend_task_id=(
                    task.task_id
                ),
            )

        except KeyError as e:
            self.get_logger().error(
                f"Missing task field: {e}"
            )

        except Exception as e:
            self.get_logger().error(
                "Failed to handle "
                f"task request: {e}"
            )

    # ======================================================
    # RMF Request Builder
    # ======================================================

    def send_go_to_place(
        self,
        robot_name,
        target,
        backend_task_id,
    ):
        if (
            target
            not in self.waypoints
        ):
            raise RuntimeError(
                "Unknown destination "
                f"waypoint: {target}"
            )

        now_ms = int(
            time.time() * 1000
        )

        task_json = {
            "type":
                "robot_task_request",

            "robot":
                robot_name,

            "fleet":
                FLEET_NAME,

            "request": {
                "category":
                    "compose",

                "description": {
                    "category":
                        "go_to_place",

                    "phases": [
                        {
                            "activity": {
                                "category":
                                    "go_to_place",

                                "description": {
                                    "one_of": [
                                        {
                                            "waypoint":
                                                target
                                        }
                                    ]
                                },
                            }
                        }
                    ],
                },

                "unix_millis_request_time":
                    now_ms,

                "unix_millis_earliest_start_time":
                    now_ms,

                "requester":
                    "hospital_rule_dispatcher",

                "fleet_name":
                    FLEET_NAME,
            },
        }

        request_id = (
            f"hospital_"
            f"{backend_task_id}_"
            f"{uuid.uuid4()}"
        )

        msg = ApiRequest()

        msg.request_id = request_id

        msg.json_msg = json.dumps(
            task_json
        )

        self.get_logger().info(
            "Sending RMF task "
            f"backend_task_id={backend_task_id}, "
            f"request_id={request_id}"
        )

        self.get_logger().info(
            msg.json_msg
        )

        self.task_pub.publish(msg)


def main():
    rclpy.init()

    node = HospitalRuleDispatcher()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()