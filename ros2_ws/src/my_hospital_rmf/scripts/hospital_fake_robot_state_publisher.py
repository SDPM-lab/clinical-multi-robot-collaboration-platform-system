#!/usr/bin/env python3

import math
import yaml
import rclpy
from rclpy.node import Node

from rmf_fleet_msgs.msg import RobotState, RobotMode, Location, PathRequest


NAV_GRAPH = "/home/asus/rmf_custom_ws/src/my_hospital_rmf/nav_graphs/0.yaml"
FLEET_NAME = "hospital_fleet"
MAP_NAME = "L1"

MOVE_SPEED = 0.6
ARRIVE_DISTANCE = 0.15
TIMER_PERIOD = 0.2
BATTERY_PERCENT = 0.99


ROBOT_STARTS = {
    "hospital_robot_1": "charging_station_junction",
    "hospital_robot_2": "storage_junction",
}


def get_param_name(params):
    if isinstance(params, dict):
        return params.get("name")

    if isinstance(params, list):
        for item in params:
            if isinstance(item, dict) and item.get("name"):
                return item.get("name")

    return None


def find_waypoint_xy(nav_graph_path, level_name, waypoint_name):
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
    def __init__(self, name, start_waypoint):
        self.name = name
        self.start_waypoint = start_waypoint

        self.x, self.y = find_waypoint_xy(
            NAV_GRAPH,
            MAP_NAME,
            start_waypoint,
        )

        self.yaw = 0.0
        self.seq = 0
        self.task_id = ""
        self.path = []
        self.current_target_index = 0
        self.is_moving = False

    def receive_path(self, task_id, path):
        self.task_id = task_id
        self.path = list(path)
        self.current_target_index = 0
        self.is_moving = len(self.path) > 0

    def move_one_step(self):
        if not self.is_moving or self.current_target_index >= len(self.path):
            self.is_moving = False
            return

        target = self.path[self.current_target_index]

        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < ARRIVE_DISTANCE:
            self.x = target.x
            self.y = target.y
            self.yaw = target.yaw
            self.current_target_index += 1

            if self.current_target_index >= len(self.path):
                self.is_moving = False
                self.path = []

            return

        step = MOVE_SPEED * TIMER_PERIOD
        ratio = min(step / distance, 1.0)

        self.x += dx * ratio
        self.y += dy * ratio
        self.yaw = math.atan2(dy, dx)

    def make_state_msg(self, now_msg):
        msg = RobotState()

        msg.name = self.name
        msg.model = FLEET_NAME
        msg.task_id = self.task_id
        msg.seq = self.seq
        self.seq += 1

        msg.mode = RobotMode()

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

        if self.is_moving:
            msg.path = self.path[self.current_target_index:]
        else:
            msg.path = []

        return msg


class HospitalFakeRobotStatePublisher(Node):
    def __init__(self):
        super().__init__("hospital_fake_robot_state_publisher")

        self.state_pub = self.create_publisher(RobotState, "/robot_state", 10)

        self.path_sub = self.create_subscription(
            PathRequest,
            "/robot_path_requests",
            self.path_request_cb,
            10,
        )

        self.robots = {}

        for robot_name, start_waypoint in ROBOT_STARTS.items():
            robot = FakeRobot(robot_name, start_waypoint)
            self.robots[robot_name] = robot

            self.get_logger().info(
                f"{robot_name} start at {start_waypoint}: "
                f"x={robot.x}, y={robot.y}"
            )

        self.timer = self.create_timer(TIMER_PERIOD, self.on_timer)

    def path_request_cb(self, msg):
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
        now_msg = self.get_clock().now().to_msg()

        for robot in self.robots.values():
            was_moving = robot.is_moving

            robot.move_one_step()

            if was_moving and not robot.is_moving:
                self.get_logger().info(
                    f"{robot.name} task {robot.task_id} completed"
                )

            msg = robot.make_state_msg(now_msg)
            self.state_pub.publish(msg)


def main():
    rclpy.init()
    node = HospitalFakeRobotStatePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
