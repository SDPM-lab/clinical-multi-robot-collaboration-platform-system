#!/usr/bin/env python3

import json
import math
import time
import uuid
import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState
from rmf_task_msgs.msg import ApiRequest


NAV_GRAPH = "/home/asus/rmf_custom_ws/src/my_hospital_rmf/nav_graphs/0.yaml"
MAP_NAME = "L1"
FLEET_NAME = "hospital_fleet"


def get_param_name(params):
    if isinstance(params, dict):
        return params.get("name")

    if isinstance(params, list):
        for item in params:
            if isinstance(item, dict) and item.get("name"):
                return item.get("name")

    return None


def load_waypoints(nav_graph_path, level_name):
    with open(nav_graph_path, "r") as f:
        data = yaml.safe_load(f)

    vertices = data["levels"][level_name]["vertices"]

    waypoints = {}

    for vertex in vertices:
        x = float(vertex[0])
        y = float(vertex[1])
        params = vertex[2]

        name = get_param_name(params)

        if name:
            waypoints[name] = (x, y)

    return waypoints


class HospitalRuleDispatcher(Node):
    def __init__(self):
        super().__init__("hospital_rule_dispatcher")

        self.waypoints = load_waypoints(NAV_GRAPH, MAP_NAME)
        self.robots = {}

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

        self.create_subscription(
            String,
            "/hospital_task_request",
            self.task_request_cb,
            10,
        )

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info("Hospital rule dispatcher started")
        self.get_logger().info("Listening: /hospital_task_request")
        self.get_logger().info("Listening: /fleet_states")
        self.get_logger().info("Publishing: /task_api_requests")

    def fleet_state_cb(self, msg):
        if msg.name != FLEET_NAME:
            return

        for robot in msg.robots:
            self.robots[robot.name] = {
                "x": robot.location.x,
                "y": robot.location.y,
                "battery": robot.battery_percent,
                "mode": robot.mode.mode,
                "task_id": robot.task_id,
            }

    def choose_robot(self, target):
        if target not in self.waypoints:
            raise RuntimeError(f"Unknown target waypoint: {target}")

        target_x, target_y = self.waypoints[target]

        best_robot = None
        best_score = float("inf")

        for robot_name, state in self.robots.items():
            dx = state["x"] - target_x
            dy = state["y"] - target_y
            distance = math.sqrt(dx * dx + dy * dy)

            busy_penalty = 1000.0 if state["task_id"] else 0.0
            battery_penalty = 500.0 if state["battery"] < 0.2 else 0.0

            score = distance + busy_penalty + battery_penalty

            self.get_logger().info(
                f"candidate={robot_name}, distance={distance:.2f}, "
                f"battery={state['battery']:.2f}, task_id='{state['task_id']}', "
                f"score={score:.2f}"
            )

            if score < best_score:
                best_score = score
                best_robot = robot_name

        if best_robot is None:
            raise RuntimeError("No robot available")

        return best_robot

    def task_request_cb(self, msg):
        self.get_logger().info(f"Received hospital task: {msg.data}")

        try:
            task = json.loads(msg.data)
            target = task["target"]
            priority = task.get("priority", 1)
            task_type = task.get("task_type", "go_to_place")

            if task_type != "go_to_place":
                self.get_logger().error(f"Unsupported task_type: {task_type}")
                return

            if not self.robots:
                self.get_logger().error("No fleet state received yet")
                return

            selected_robot = self.choose_robot(target)

            self.get_logger().info(
                f"Selected robot: {selected_robot} for target: {target}, priority={priority}"
            )

            self.send_go_to_place(selected_robot, target)

        except Exception as e:
            self.get_logger().error(f"Failed to handle task request: {e}")

    def send_go_to_place(self, robot_name, target):
        now_ms = int(time.time() * 1000)

        task_json = {
            "type": "robot_task_request",
            "robot": robot_name,
            "fleet": FLEET_NAME,
            "request": {
                "category": "compose",
                "description": {
                    "category": "go_to_place",
                    "phases": [
                        {
                            "activity": {
                                "category": "go_to_place",
                                "description": {
                                    "one_of": [
                                        {
                                            "waypoint": target
                                        }
                                    ]
                                },
                            }
                        }
                    ],
                },
                "unix_millis_request_time": now_ms,
                "unix_millis_earliest_start_time": now_ms,
                "requester": "hospital_rule_dispatcher",
                "fleet_name": FLEET_NAME,
            },
        }

        request_id = "hospital_rule_" + str(uuid.uuid4())

        msg = ApiRequest()
        msg.request_id = request_id
        msg.json_msg = json.dumps(task_json)

        self.get_logger().info(f"Sending RMF task request_id={request_id}")
        self.get_logger().info(msg.json_msg)

        for _ in range(5):
            self.task_pub.publish(msg)
            time.sleep(0.2)


def main():
    rclpy.init()
    node = HospitalRuleDispatcher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
