#!/usr/bin/env python3
# =======================================================
#
# 【用途】
#   醫院任務調度器：接收來自前端的任務請求，依照規則自動挑選
#   最適合的機器人，再將標準 RMF 任務指令發給 Open-RMF 系統執行。
#
# 【ROS2 話題】
#   訂閱：/hospital_task_request  (std_msgs/String, JSON)
#           前端透過 hospital_ros_api_bridge 送來的任務請求
#   訂閱：/fleet_states           (rmf_fleet_msgs/FleetState)
#           持續更新每台機器人的位置、電量、任務狀態
#   發佈：/task_api_requests      (rmf_task_msgs/ApiRequest)
#           RMF 標準任務 API，由 Task Manager 接手執行
#
# 【選機器人邏輯 (choose_robot)】
#   分數 = 距目標距離 + 忙碌懲罰(1000) + 低電懲罰(500)
#   分數最低者勝出，確保優先派閒置且距離近的機器人。
#
# 【發送任務流程】
#   send_go_to_place → 組出 RMF compose/go_to_place JSON
#   → 連發 5 次（每次間隔 0.2s）確保 Transient Local 訂閱者收到
# =======================================================

import json
import math
import os
import time
import uuid
import yaml

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState
from rmf_task_msgs.msg import ApiRequest


NAV_GRAPH = os.path.join(get_package_share_directory("my_hospital_rmf"), "nav_graphs", "0.yaml")
MAP_NAME = "L1"
FLEET_NAME = "hospital_fleet"


def get_param_name(params):
    """從 nav_graph vertex 的 params 欄位中取出路點名稱。
    params 可能是 dict 或 list，兩種格式都相容。"""
    if isinstance(params, dict):
        return params.get("name")

    if isinstance(params, list):
        for item in params:
            if isinstance(item, dict) and item.get("name"):
                return item.get("name")

    return None


def load_waypoints(nav_graph_path, level_name):
    """從 YAML 導航圖載入所有命名路點，回傳 {名稱: (x, y)} 字典。"""
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
            waypoints[name] = (x, y) #{"charging_station": (10.5, 3.2),"pharmacy":(20.0, 12.0),}

    return waypoints


class HospitalRuleDispatcher(Node):
    """ROS2 節點：以規則式評分挑選機器人並發送 RMF 任務。"""

    def __init__(self):
        super().__init__("hospital_rule_dispatcher")

        # 載入導航圖路點（用於計算機器人到目標的距離）
        self.waypoints = load_waypoints(NAV_GRAPH, MAP_NAME)
        self.robots = {}  # 快取最新的艦隊狀態 {robot_name: {...}}

        # /task_api_requests 必須用 TRANSIENT_LOCAL 確保 RMF Task Manager
        # 即使晚訂閱也能收到訊息（Reliable + Transient Local）
        task_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL, #就算訂閱者比發布者晚啟動，也能收到之前發過的訊息
        )

        self.task_pub = self.create_publisher(
            ApiRequest,
            "/task_api_requests",
            task_qos,
        )

        # 接收前端透過 hospital_ros_api_bridge 送來的任務請求（JSON 字串）
        self.create_subscription(
            String,
            "/hospital_task_request",
            self.task_request_cb,
            10,
        )

        # 持續監聽艦隊狀態以更新每台機器人的位置與忙碌情況
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
        """更新快取中的機器人狀態，只處理屬於本艦隊的訊息。"""
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
        """依評分規則從艦隊中挑出最適合執行任務的機器人。

        評分 = 距目標距離 + 忙碌懲罰(1000) + 低電懲罰(500)
        分數最低者勝出。
        """
        if target not in self.waypoints:
            raise RuntimeError(f"Unknown target waypoint: {target}")

        target_x, target_y = self.waypoints[target]

        best_robot = None
        best_score = float("inf")

        for robot_name, state in self.robots.items():
            dx = state["x"] - target_x
            dy = state["y"] - target_y
            distance = math.sqrt(dx * dx + dy * dy)

            # 正在執行任務的機器人加大懲罰，避免搶佔已在工作的機器人
            busy_penalty = 1000.0 if state["task_id"] else 0.0
            # 電量低於 20% 加懲罰，優先留給緊急任務
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
        """收到任務請求時，解析 JSON、選機器人、發送 RMF 任務。

        目前只支援 task_type = "go_to_place"。
        """
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
        """組出符合 RMF Task API 格式的 go_to_place 任務並發佈。

        使用 compose + go_to_place 的巢狀結構，指定機器人與目標路點。
        連發 5 次（間隔 200ms）以確保 Transient Local 訂閱者不遺漏。
        """
        now_ms = int(time.time() * 1000) #取得毫秒數,RMF Task API 規定時間要用毫秒整數格式

        task_json = {
            "type": "robot_task_request",
            "robot": robot_name,
            "fleet": FLEET_NAME,
            "request": {
                "category": "compose", #由多個phrase組成的任務
                "description": {
                    "category": "go_to_place",
                    "phases": [
                        {
                            "activity": {
                                "category": "go_to_place",
                                "description": {
                                    "one_of": [ # 告訴 RMF 目標是這幾個路點其中一個都可以
                                        {
                                            "waypoint": target
                                        }
                                    ]
                                },
                            }
                        }
                    ],
                },
                "unix_millis_request_time": now_ms, #任務建立時間
                "unix_millis_earliest_start_time": now_ms,  #最早可以開始的時間（立即）
                "requester": "hospital_rule_dispatcher",  #是誰發的任務
                "fleet_name": FLEET_NAME, #再次指定機隊
            },
        }

        request_id = "hospital_rule_" + str(uuid.uuid4()) #產生唯一的任務ID,避免重複,例如:a3f2c1d4-8b9e-4f2a-b3c1-d4e5f6a7b8c9                                               

        msg = ApiRequest() # ApiRequest 永遠只有兩個欄位
        msg.request_id = request_id
        msg.json_msg = json.dumps(task_json)

        self.get_logger().info(f"Sending RMF task request_id={request_id}")
        self.get_logger().info(msg.json_msg)

        # 連發 5 次確保 RMF Task Manager 收到（Transient Local 訂閱者可能晚啟動）
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
