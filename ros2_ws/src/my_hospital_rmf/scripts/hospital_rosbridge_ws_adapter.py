#!/usr/bin/env python3
# =================================================
# 【用途】
#   將 ROS2 的 /fleet_states 訊息橋接到 WebSocket，
#   讓前端網頁（或其他 WebSocket 客戶端）不需要安裝 ROS2
#   就能即時收到機器人艦隊狀態。
#
# 【ROS2 話題】
#   訂閱：/fleet_states (rmf_fleet_msgs/FleetState)
#
# 【WebSocket】
#   監聽：ws://0.0.0.0:9090
#   格式：模仿 rosbridge_suite 的 JSON 協議
#         { "op": "publish", "topic": "/fleet_states", "msg": {...} }
#
# 【運作流程】
#   1. ROS2 執行緒持續接收 /fleet_states 並快取最新一筆
#   2. asyncio 執行緒跑 WebSocket Server，管理所有連線的客戶端
#   3. 每次收到新訊息就廣播給所有已連線客戶端
#   4. 新客戶端連線時立即推送一次最新狀態（避免等待下一次發佈）

 # ┌──────┬────────────────────┬────────────────────────────────┐
 # │      │ ros_api_bridge.py  │    rosbridge_ws_adapter.py     │
 # ├──────┼────────────────────┼────────────────────────────────┤
 # │ 協定 │ HTTP（前端主動問） │ WebSocket（伺服器主動推）      │
 # ├──────┼────────────────────┼────────────────────────────────┤
 # │ 適合 │ 一次性查詢         │ 即時更新（機器人位置持續推送） │
 # └──────┴────────────────────┴────────────────────────────────┘
# ====================================================

# Python 的非同步執行套件,讓你在單一 thread裡同時處理多件事，專門用來處理「等待」的情況（網路、IO）。像是多客戶連線
import json
import asyncio 
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
    """ROS2 節點：訂閱艦隊狀態並透過 WebSocket 廣播給前端。"""

    def __init__(self):
        super().__init__("hospital_rosbridge_ws_adapter")

        self.latest_msg = None      # 快取最近一筆 FleetState（JSON 格式）
        self.ws_clients = set()     # 目前所有已連線的 WebSocket 客戶端
        self.loop = None            # asyncio event loop（在 ws server 啟動後設定）表示「WebSocket server還沒啟動，地址還不知道」

        self.create_subscription(
            FleetState,
            FLEET_TOPIC,
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info(f"Subscribed to {FLEET_TOPIC}")
        self.get_logger().info(f"Will serve rosbridge-like websocket on ws://localhost:{WS_PORT}")

    def fleet_state_cb(self, msg: FleetState):
        """收到新的 FleetState 時更新快取並廣播給所有客戶端。"""
        self.latest_msg = self.fleet_state_to_rosbridge_json(msg)

        # 若 event loop 已啟動且有客戶端，才觸發廣播
        # Thread A 收到 FleetState，透過地址投遞任務給 Thread B
        if self.loop and self.ws_clients:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_latest(), # 要執行的任務
                self.loop, # 投遞到哪裡（Thread B 的地址）
            )

    def fleet_state_to_rosbridge_json(self, msg: FleetState):
        """將 ROS2 FleetState 訊息轉成符合 rosbridge 協議的 JSON 字典。
        電量從 0~1 轉為 0~100 百分比格式。"""
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

        return {  # rosbridge 協議格式
            "op": "publish",
            "topic": FLEET_TOPIC,
            "msg": {
                "name": msg.name,
                "robots": robots,
            },
        }

    async def broadcast_latest(self):
        """將最新 FleetState 廣播給所有連線中的客戶端。
        發送失敗的客戶端視為已斷線，從集合中移除。"""
        if self.latest_msg is None:
            return

        data = json.dumps(self.latest_msg) # 把快取資料轉成 JSON 字串

        dead_clients = []
        for ws in list(self.ws_clients):
            try:
                await ws.send(data)
            except Exception:
                dead_clients.append(ws)

        for ws in dead_clients:
            self.ws_clients.discard(ws)

    async def handle_client(self, websocket): #每個新連線都會有自己的 websocket物件
        """處理單一 WebSocket 客戶端的連線生命週期。

        連線時：立即推送最新狀態（若已有快取）。
        持續監聽客戶端訊息：處理 subscribe 指令。
        斷線時：從客戶端集合移除。
        """
        self.ws_clients.add(websocket)
        self.get_logger().info("Web client connected")

        try:
            # 新連線立即推送最新狀態，不必等下一次 /fleet_states 發佈
            if self.latest_msg is not None:
                await websocket.send(json.dumps(self.latest_msg))

            async for message in websocket:
                try:
                    request = json.loads(message) # 把收到的字串解析成 dict
                except Exception:
                    continue

                op = request.get("op", "")
                topic = request.get("topic", "")

                if op == "subscribe":
                    self.get_logger().info(f"Client subscribed to {topic}")

                    # 客戶端重新訂閱 fleet_states 時補推一次最新資料
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
    """在獨立執行緒中跑 ROS2 spin，避免阻塞 asyncio event loop。"""
    rclpy.spin(node)


async def run_ws_server(node):
    """啟動 WebSocket Server 並記錄 event loop 供 ROS2 callback 使用。"""
    # Thread B 啟動時，把自己的地址存起來
    node.loop = asyncio.get_running_loop()

    async with websockets.serve(node.handle_client, WS_HOST, WS_PORT): #在背景監聽，每次有新客戶端連線就自動呼叫
        node.get_logger().info(f"WebSocket adapter started at ws://localhost:{WS_PORT}")
        await asyncio.Future()  # 永久等待，直到程式被中斷


def main():
    rclpy.init()

    node = FleetStateWsAdapter()

    # ROS2 spin 跑在背景執行緒，WebSocket Server 跑在主執行緒的 asyncio loop
    ros_thread = threading.Thread(
        target=spin_ros,
        args=(node,),
        daemon=True,
    )
    ros_thread.start()

    try:
        asyncio.run(run_ws_server(node)) #啟動一個 event loop，在裡面跑非同步的東西
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
