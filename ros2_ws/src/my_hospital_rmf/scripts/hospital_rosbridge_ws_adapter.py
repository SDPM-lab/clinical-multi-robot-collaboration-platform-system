#!/usr/bin/env python3

import asyncio
import json
import threading
from copy import deepcopy

import rclpy
from rclpy.node import Node
from rmf_fleet_msgs.msg import FleetState

import websockets


FLEET_TOPIC = "/fleet_states"
WS_HOST = "0.0.0.0"
WS_PORT = 9090


class FleetStateWsAdapter(Node):
    def __init__(self):
        super().__init__("hospital_rosbridge_ws_adapter")

        self.latest_msg = None
        self.ws_clients = set()
        self.loop = None

        self.create_subscription(
            FleetState,
            FLEET_TOPIC,
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info(f"Subscribed to {FLEET_TOPIC}")
        self.get_logger().info(f"Will serve rosbridge-like websocket on ws://localhost:{WS_PORT}")

    def fleet_state_cb(self, msg: FleetState):
        self.latest_msg = self.fleet_state_to_rosbridge_json(msg)

        if self.loop and self.ws_clients:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_latest(),
                self.loop,
            )

    def fleet_state_to_rosbridge_json(self, msg: FleetState):
        robots = []

        for robot in msg.robots:
            robots.append({
                "name": robot.name,
                "model": robot.model,
                "task_id": robot.task_id,
                "mode": {
                    "mode": int(robot.mode.mode),
                    "mode_request_id": int(robot.mode.mode_request_id),
                },
                "battery_percent": float(robot.battery_percent) * 100.0,
                "location": {
                    "t": {
                        "sec": int(robot.location.t.sec),
                        "nanosec": int(robot.location.t.nanosec),
                    },
                    "x": float(robot.location.x),
                    "y": float(robot.location.y),
                    "yaw": float(robot.location.yaw),
                    "obey_approach_speed_limit": bool(robot.location.obey_approach_speed_limit),
                    "approach_speed_limit": float(robot.location.approach_speed_limit),
                    "level_name": robot.location.level_name,
                    "index": int(robot.location.index),
                },
                "path": [],
            })

        return {
            "op": "publish",
            "topic": FLEET_TOPIC,
            "msg": {
                "name": msg.name,
                "robots": robots,
            },
        }

    async def broadcast_latest(self):
        if self.latest_msg is None:
            return

        data = json.dumps(self.latest_msg)

        dead_clients = []
        for ws in list(self.ws_clients):
            try:
                await ws.send(data)
            except Exception:
                dead_clients.append(ws)

        for ws in dead_clients:
            self.ws_clients.discard(ws)

    async def handle_client(self, websocket):
        self.ws_clients.add(websocket)
        self.get_logger().info("Web client connected")

        try:
            if self.latest_msg is not None:
                await websocket.send(json.dumps(self.latest_msg))

            async for message in websocket:
                try:
                    request = json.loads(message)
                except Exception:
                    continue

                op = request.get("op", "")
                topic = request.get("topic", "")

                if op == "subscribe":
                    self.get_logger().info(f"Client subscribed to {topic}")

                    if topic == FLEET_TOPIC and self.latest_msg is not None:
                        await websocket.send(json.dumps(self.latest_msg))

                    if topic == "/robot_nearest_waypoint":
                        # 學長後端會訂閱這個 topic，但目前不是必要功能。
                        # 這裡先接受訂閱，不回資料，避免影響主流程。
                        pass

        finally:
            self.ws_clients.discard(websocket)
            self.get_logger().info("Web client disconnected")


def spin_ros(node):
    rclpy.spin(node)


async def run_ws_server(node):
    node.loop = asyncio.get_running_loop()

    async with websockets.serve(node.handle_client, WS_HOST, WS_PORT):
        node.get_logger().info(f"WebSocket adapter started at ws://localhost:{WS_PORT}")
        await asyncio.Future()


def main():
    rclpy.init()

    node = FleetStateWsAdapter()

    ros_thread = threading.Thread(
        target=spin_ros,
        args=(node,),
        daemon=True,
    )
    ros_thread.start()

    try:
        asyncio.run(run_ws_server(node))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
