#!/usr/bin/env python3
# ========================================
#
# 【用途】
#   模擬醫院機器人的移動行為，在沒有真實硬體時提供假的機器人狀態，
#   讓整個 RMF 系統可以正常測試與開發。
#
# 【ROS2 話題】
#   發佈：/robot_state      (rmf_fleet_msgs/RobotState)  — 每台機器人的位置與模式
#   訂閱：/robot_path_requests (rmf_fleet_msgs/PathRequest) — 接收 RMF 下發的路徑指令
#
# 【運作流程】
#   1. 從 nav_graph YAML 讀取各路點座標
#   2. 每隔 TIMER_PERIOD 秒更新一次機器人位置（模擬勻速移動）
#   3. 到達目標路點後繼續下一個，直到路徑走完
#   4. 持續發佈 /robot_state 讓 Fleet Adapter 知道機器人在哪裡
# ========================================

import math
import os
import yaml
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory

from rmf_fleet_msgs.msg import RobotState, RobotMode, Location, PathRequest


# 導航圖路徑（記錄所有路點名稱與 XY 座標）
NAV_GRAPH = os.path.join(get_package_share_directory("my_hospital_rmf"), "nav_graphs", "0.yaml")
FLEET_NAME = "hospital_fleet"
MAP_NAME = "L1"

MOVE_SPEED = 0.6       # 機器人移動速度（公尺/秒）
ARRIVE_DISTANCE = 0.15 # 距離目標點小於此值視為「到達」（公尺）
TIMER_PERIOD = 0.2     # 狀態更新頻率（秒）
BATTERY_PERCENT = 0.99 # 固定電量（模擬用，不做電量消耗）


# 各機器人的初始停靠路點
ROBOT_STARTS = {
    "hospital_robot_1": "charging_station_junction",
    "hospital_robot_2": "storage_junction",
}


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


def find_waypoint_xy(nav_graph_path, level_name, waypoint_name):
    """在 YAML 導航圖中找到指定路點名稱的 (x, y) 座標。"""
    with open(nav_graph_path, "r") as f:
        data = yaml.safe_load(f)

    vertices = data["levels"][level_name]["vertices"]

    for vertex in vertices:
        x = float(vertex[0])
        y = float(vertex[1])
        params = vertex[2]

        name = get_param_name(params)

        if name == waypoint_name:
            return x, y

    raise RuntimeError(f"Cannot find waypoint: {waypoint_name}")


class FakeRobot:
    """單台模擬機器人的狀態與移動邏輯。"""

    def __init__(self, name, start_waypoint):
        self.name = name
        self.start_waypoint = start_waypoint

        # 從導航圖取得初始座標
        self.x, self.y = find_waypoint_xy(
            NAV_GRAPH,
            MAP_NAME,
            start_waypoint,
        )

        self.yaw = 0.0
        self.seq = 0           # 狀態訊息的序號（每次發佈遞增）
        self.task_id = ""      # 目前執行的任務 ID（空字串表示閒置）
        self.path = []         # 待走的路點清單
        self.current_target_index = 0
        self.is_moving = False

    def receive_path(self, task_id, path):
        """收到新路徑指令時重設移動狀態。"""
        self.task_id = task_id
        self.path = list(path)
        self.current_target_index = 0
        self.is_moving = len(self.path) > 0

    def move_one_step(self):
        """每個 timer tick 往目標路點移動一步。
        到達當前路點後自動切換到下一個，全部走完則停止。"""
        if not self.is_moving or self.current_target_index >= len(self.path):
            self.is_moving = False
            return

        target = self.path[self.current_target_index]

        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # 距離夠近視為到達，切換到下一個路點
        if distance < ARRIVE_DISTANCE:
            self.x = target.x
            self.y = target.y
            self.yaw = target.yaw
            self.current_target_index += 1

            if self.current_target_index >= len(self.path):
                self.is_moving = False
                self.path = []

            return

        # 依速度計算本次移動步長，沿直線前進
        step = MOVE_SPEED * TIMER_PERIOD
        ratio = min(step / distance, 1.0)

        self.x += dx * ratio
        self.y += dy * ratio
        self.yaw = math.atan2(dy, dx) #計算當前朝向角度（弧度制，-pi~pi）

    def make_state_msg(self, now_msg):
        """把目前狀態打包成 RobotState 訊息準備發佈。"""
        msg = RobotState()

        msg.name = self.name
        msg.model = FLEET_NAME
        msg.task_id = self.task_id
        msg.seq = self.seq
        self.seq += 1

        msg.mode = RobotMode()

        # 移動中用 MODE_MOVING，停止則 MODE_IDLE
        if self.is_moving:
            msg.mode.mode = RobotMode.MODE_MOVING
        else:
            msg.mode.mode = RobotMode.MODE_IDLE

        msg.location = Location()
        msg.location.t = now_msg
        msg.location.x = float(self.x)
        msg.location.y = float(self.y)
        msg.location.yaw = float(self.yaw)
        msg.location.level_name = MAP_NAME

        msg.battery_percent = BATTERY_PERCENT

        # 只回報尚未走到的路點（已走過的不需要）
        if self.is_moving:
            msg.path = self.path[self.current_target_index:]
        else:
            msg.path = []

        return msg


class HospitalFakeRobotStatePublisher(Node):
    """ROS2 節點：管理所有模擬機器人並定時發佈它們的狀態。"""

    def __init__(self):
        super().__init__("hospital_fake_robot_state_publisher")

        # 發佈每台機器人的即時狀態
        self.state_pub = self.create_publisher(RobotState, "/robot_state", 10)

        # 訂閱 RMF Fleet Adapter 下發的路徑指令
        self.path_sub = self.create_subscription(
            PathRequest,
            "/robot_path_requests",
            self.path_request_cb,
            10,
        )

        self.robots = {}

        # 依照 ROBOT_STARTS 建立各台模擬機器人
        for robot_name, start_waypoint in ROBOT_STARTS.items():
            robot = FakeRobot(robot_name, start_waypoint)
            self.robots[robot_name] = robot

            self.get_logger().info(
                f"{robot_name} start at {start_waypoint}: "
                f"x={robot.x}, y={robot.y}"
            )

        # 定時器：每 TIMER_PERIOD 秒更新位置並發佈狀態
        self.timer = self.create_timer(TIMER_PERIOD, self.on_timer)

    def path_request_cb(self, msg):
        """收到路徑指令時，找到對應機器人並交給它執行。
        若 fleet_name 不符或機器人不存在則忽略。"""
        if msg.fleet_name != FLEET_NAME:
            return

        robot = self.robots.get(msg.robot_name)

        if robot is None:
            return

        robot.receive_path(msg.task_id, msg.path)

        self.get_logger().info(
            f"{msg.robot_name} received path request: "
            f"task_id={msg.task_id}, path_points={len(msg.path)}"
        )

        for i, p in enumerate(msg.path):
            self.get_logger().info(
                f"  {msg.robot_name} point {i}: "
                f"level={p.level_name}, x={p.x:.2f}, y={p.y:.2f}, yaw={p.yaw:.2f}"
            )

    def on_timer(self):
        """每個 tick 讓所有機器人移動一步，並發佈最新狀態。"""
        now_msg = self.get_clock().now().to_msg()

        for robot in self.robots.values():
            was_moving = robot.is_moving

            robot.move_one_step()

            # 剛完成任務時記錄 log
            if was_moving and not robot.is_moving:
                self.get_logger().info(
                    f"{robot.name} task {robot.task_id} completed"
                )

            msg = robot.make_state_msg(now_msg) # 打包 RobotState
            self.state_pub.publish(msg) # 發布移動後的狀態


def main():
    rclpy.init()
    node = HospitalFakeRobotStatePublisher()
    rclpy.spin(node) #在 __init__全部跑完之後才執行
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
