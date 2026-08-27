#!/usr/bin/env python3

import json
import os
import time
import uuid
import yaml

from collections import deque

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
from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)
from scheduler.robot_selection.rule_based_scheduler import (
    RuleBasedScheduler,
)
from scheduler.task_selection.fcfs_scheduler import (
    FCFSScheduler,
)
from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)


NAV_GRAPH = os.path.join(
    get_package_share_directory("my_hospital_rmf"),
    "nav_graphs",
    "0.yaml",
)

MAP_NAME = "L1"
FLEET_NAME = "hospital_fleet"


# ==========================================================
# Robot Capability 設定
#
# 第一版先放在程式中。
# 後續可以再搬到 fleet_config.yaml。
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


# ==========================================================
# Navigation Graph Helper
# ==========================================================

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


# ==========================================================
# Hospital Dispatcher
# ==========================================================

class HospitalRuleDispatcher(Node):

    def __init__(self):

        super().__init__(
            "hospital_rule_dispatcher"
        )

        # ==================================================
        # Waypoints
        # ==================================================

        self.waypoints = load_waypoints(
            NAV_GRAPH,
            MAP_NAME,
        )

        # ==================================================
        # Robot Scheduler Selector
        # ==================================================

        self.declare_parameter(
            "robot_scheduler",
            "rule_based",
        )

        self.robot_scheduler_name = (
            self.get_parameter(
                "robot_scheduler"
            )
            .get_parameter_value()
            .string_value
        )

        if self.robot_scheduler_name == "nearest":
            self.robot_scheduler = (
                NearestScheduler(
                    self.waypoints
                )
            )

        elif self.robot_scheduler_name == "rule_based":
            self.robot_scheduler = (
                RuleBasedScheduler(
                    self.waypoints
                )
            )

        else:
            raise RuntimeError(
                "Unknown robot scheduler: "
                f"{self.robot_scheduler_name}"
            )


        # ==================================================
        # Task Scheduler Selector
        # ==================================================

        self.declare_parameter(
            "task_scheduler",
            "fcfs",
        )

        self.task_scheduler_name = (
            self.get_parameter(
                "task_scheduler"
            )
            .get_parameter_value()
            .string_value
        )

        if self.task_scheduler_name == "fcfs":
            self.task_scheduler = (
                FCFSScheduler()
            )

        elif self.task_scheduler_name == "priority":
            self.task_scheduler = (
                PriorityScheduler()
            )

        else:
            raise RuntimeError(
                "Unknown task scheduler: "
                f"{self.task_scheduler_name}"
            )

        # ==================================================
        # Robot States
        # ==================================================

        self.robots = {}

        # ==================================================
        # Pending Task Queue
        #
        # 任務收到後不再立即派工，
        # 而是先放進 Queue。
        # ==================================================

        self.pending_tasks = deque()

        # 每 0.5 秒檢查一次 Queue
        self.task_queue_timer = (
            self.create_timer(
                0.5,
                self.process_task_queue,
            )
        )

        # ==================================================
        # RMF Task Publisher
        # ==================================================

        task_qos = QoSProfile(
            history=(
                HistoryPolicy.KEEP_LAST
            ),

            depth=10,

            reliability=(
                ReliabilityPolicy.RELIABLE
            ),

            durability=(
                DurabilityPolicy.TRANSIENT_LOCAL
            ),
        )

        self.task_pub = (
            self.create_publisher(
                ApiRequest,
                "/task_api_requests",
                task_qos,
            )
        )

        # ==================================================
        # Hospital Task Subscriber
        # ==================================================

        self.create_subscription(
            String,
            "/hospital_task_request",
            self.task_request_cb,
            10,
        )

        # ==================================================
        # Fleet State Subscriber
        # ==================================================

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_state_cb,
            10,
        )

        # ==================================================
        # Startup Log
        # ==================================================

        self.get_logger().info(
            "Hospital dispatcher started"
        )

        self.get_logger().info(
            "Robot scheduler: "
            f"{self.robot_scheduler_name}"
        )

        self.get_logger().info(
            "Task scheduler: "
            f"{self.task_scheduler_name}"
        )

        self.get_logger().info(
            "Task queue processor started"
        )

        self.get_logger().info(
            "Listening: "
            "/hospital_task_request"
        )

        self.get_logger().info(
            "Listening: "
            "/fleet_states"
        )

        self.get_logger().info(
            "Publishing: "
            "/task_api_requests"
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

                robot_id=(
                    robot.name
                ),

                fleet_name=(
                    msg.name
                ),

                status=(
                    status
                ),

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
    # Incoming Task
    #
    # 現在只做：
    #
    # JSON
    # ↓
    # Task Model
    # ↓
    # Pending Queue
    #
    # 不在 callback 裡直接派工。
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

            # --------------------------------------
            # Task → Pending Queue
            # --------------------------------------

            self.pending_tasks.append(
                task
            )

            self.get_logger().info(
                "Task queued: "
                f"task_id={task.task_id}, "
                f"priority={task.priority}, "
                "queue_size="
                f"{len(self.pending_tasks)}"
            )

        except KeyError as e:

            self.get_logger().error(
                "Missing task field: "
                f"{e}"
            )

        except json.JSONDecodeError as e:

            self.get_logger().error(
                "Invalid task JSON: "
                f"{e}"
            )

        except Exception as e:

            self.get_logger().error(
                "Failed to queue "
                f"task request: {e}"
            )

    # ======================================================
    # Task Queue Processor
    #
    # 現階段：
    #
    # deque.popleft()
    #
    # 本身就是 FIFO。
    #
    # 下一步做 FCFS / Priority 時，
    # 這裡會改成：
    #
    # task_selector.select(...)
    # ======================================================

    def process_task_queue(self):

        if not self.pending_tasks:
            return

        if not self.robots:
            return

        # ======================================================
        # Task Selection
        # ======================================================

        task = self.task_scheduler.select(
            self.pending_tasks
        )

        if task is None:
            return

        robots = list(
            self.robots.values()
        )

        # ======================================================
        # Capability Matching
        # ======================================================

        capability_candidates = (
            capability_matching(
                task.required_capabilities,
                robots,
            )
        )

        if not capability_candidates:
            return

        # ======================================================
        # Availability Filtering
        # ======================================================

        available_candidates = [
            robot
            for robot in capability_candidates
            if robot.available
        ]

        if not available_candidates:
            return

        self.get_logger().info(
            "Processing queued task: "
            f"task_id={task.task_id}, "
            f"task_scheduler="
            f"{self.task_scheduler_name}, "
            f"queue_size="
            f"{len(self.pending_tasks)}"
        )

        self.get_logger().info(
            "Candidate robots: "
            + ", ".join(
                robot.robot_id
                for robot
                in available_candidates
            )
        )

        try:

            # ==================================================
            # Robot Scheduler
            # ==================================================

            assignment = (
                self.robot_scheduler.schedule(
                    task,
                    available_candidates,
                )
            )

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

            if (
                assignment.decision_status
                != "assigned"
                or assignment.robot_id
                is None
            ):
                return

            # ==================================================
            # 成功派工才移除被選中的 Task
            # ==================================================

            self.pending_tasks.remove(
                task
            )

            dispatched_task = task

            self.get_logger().info(
                "Task dequeued: "
                f"task_id={dispatched_task.task_id}, "
                "remaining_queue="
                f"{len(self.pending_tasks)}"
            )

            # ==================================================
            # Reserve Robot
            # ==================================================

            selected_robot = (
                self.robots.get(
                    assignment.robot_id
                )
            )

            if selected_robot:

                selected_robot.available = False
                selected_robot.status = ("busy")
                selected_robot.current_task = (
                    task.task_id
                )

            # ==================================================
            # Send to RMF
            # ==================================================

            self.send_go_to_place(
                assignment.robot_id,
                task.destination,
                backend_task_id=(
                    task.task_id
                ),
            )

        except Exception as e:

            self.get_logger().error(
                "Failed to process "
                f"task {task.task_id}: {e}"
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

        msg.request_id = (
            request_id
        )

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

        # 只發布一次
        self.task_pub.publish(
            msg
        )


# ==========================================================
# Main
# ==========================================================

def main():

    rclpy.init()

    node = (
        HospitalRuleDispatcher()
    )

    try:

        rclpy.spin(
            node
        )

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()