#!/usr/bin/env python3

# ==========================================================
# Hospital ROS API Bridge
#
# 功能：
# 1. 提供 HTTP API 給 Backend 建立醫療任務
# 2. 將 HTTP Task request 轉成 JSON 字串
# 3. 發布到 ROS2 /hospital_task_request
# 4. 訂閱 /fleet_states
# 5. 提供目前機器人狀態給 HTTP API 查詢
# ==========================================================

import json
import threading
from typing import Optional

import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn


ROS_TASK_TOPIC_NAME = "/hospital_task_request"
ROS_FLEET_TOPIC_NAME = "/fleet_states"


# ==========================================================
# Task Request Model
# ==========================================================

class HospitalTaskRequest(BaseModel):
    """
    Backend 傳給 ROS Bridge 的標準 Task 格式
    """

    task_id: str

    task_type: str

    source: str

    destination: str

    priority: int = Field(
        default=1,
        ge=0,
        le=3,
    )

    required_capabilities: list[str] = Field(
        default_factory=list
    )

    note: Optional[str] = None


# ==========================================================
# ROS Bridge Node
# ==========================================================

class HospitalRosBridge(Node):

    def __init__(self):
        super().__init__("hospital_ros_api_bridge")

        # 將 Backend 的 Task 發布到 ROS2
        self.task_pub = self.create_publisher(
            String,
            ROS_TASK_TOPIC_NAME,
            10,
        )

        # 保存最近一次 /fleet_states
        self.latest_fleet = {
            "fleet": "",
            "robots": [],
        }

        # 訂閱 RMF fleet state
        self.create_subscription(
            FleetState,
            ROS_FLEET_TOPIC_NAME,
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info(
            "Hospital ROS API Bridge started"
        )

        self.get_logger().info(
            f"Publishing topic: {ROS_TASK_TOPIC_NAME}"
        )

        self.get_logger().info(
            f"Subscribing topic: {ROS_FLEET_TOPIC_NAME}"
        )

    # ======================================================
    # Publish Task
    # ======================================================

    def publish_hospital_task(
        self,
        task: HospitalTaskRequest,
    ):
        """
        將 HTTP Task request
        轉成 ROS2 String JSON
        發布到 /hospital_task_request
        """

        payload = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "source": task.source,
            "destination": task.destination,
            "priority": task.priority,
            "required_capabilities":
                task.required_capabilities,
        }

        if task.note:
            payload["note"] = task.note

        msg = String()

        msg.data = json.dumps(
            payload,
            ensure_ascii=False,
        )

        self.task_pub.publish(msg)

        self.get_logger().info(
            f"Published hospital task: {msg.data}"
        )

        return payload

    # ======================================================
    # Fleet State Callback
    # ======================================================

    def fleet_state_cb(self, msg: FleetState):

        robots = []

        for robot in msg.robots:

            mode = int(robot.mode.mode)

            task_id = robot.task_id or ""

            # ----------------------------------------------
            # 將 RMF mode 轉成人類可讀狀態
            # ----------------------------------------------

            if task_id:
                status = "執行任務中"
                mode_text = "執行任務中"
                current_task = f"任務中: {task_id}"

            elif mode == 1:
                status = "充電中"
                mode_text = "充電中"
                current_task = "充電中"

            elif mode == 2:
                status = "移動中"
                mode_text = "移動中"
                current_task = "移動中"

            else:
                status = "待命"
                mode_text = "待命"
                current_task = "待命中"

            robots.append({
                "rosName": robot.name,
                "name": robot.name,
                "model": robot.model,

                "status": status,

                "battery": int(
                    round(
                        float(robot.battery_percent) * 100
                    )
                ),

                "currentTask": current_task,

                "location":
                    robot.location.level_name,

                "x":
                    float(robot.location.x),

                "y":
                    float(robot.location.y),

                "yaw":
                    float(robot.location.yaw),

                "levelName":
                    robot.location.level_name,

                "mode":
                    mode,

                "modeText":
                    mode_text,

                "taskId":
                    task_id,
            })

        # ROS callback 與 HTTP endpoint
        # 不在同一時間執行
        # 因此將最新 fleet state 暫存在記憶體
        self.latest_fleet = {
            "fleet": msg.name,
            "robots": robots,
        }


# ==========================================================
# FastAPI
# ==========================================================

app = FastAPI(
    title="Hospital ROS API Bridge",
    description=(
        "HTTP API bridge for hospital tasks "
        "and robot states"
    ),
    version="0.3.0",
)


app.add_middleware(
    CORSMiddleware,

    # 開放所有來源
    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


ros_bridge_node = None


# ==========================================================
# Root
# ==========================================================

@app.get("/")
def root():

    return {
        "message":
            "Hospital ROS API Bridge is running",

        "taskTopic":
            ROS_TASK_TOPIC_NAME,

        "fleetTopic":
            ROS_FLEET_TOPIC_NAME,
    }


# ==========================================================
# Health Check
# ==========================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",

        "ros_task_topic":
            ROS_TASK_TOPIC_NAME,

        "ros_fleet_topic":
            ROS_FLEET_TOPIC_NAME,
    }


# ==========================================================
# Create Hospital Task
# ==========================================================

@app.post("/api/hospital/tasks")
def create_hospital_task(
    task: HospitalTaskRequest,
):

    if ros_bridge_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS bridge node is not ready",
        )

    # ----------------------------------------------
    # 驗證 task type
    # ----------------------------------------------

    valid_task_types = {
        "medicine_delivery",
        "specimen_delivery",
        "general_delivery",
        "waste_collection",
    }

    if task.task_type not in valid_task_types:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported task_type: "
                f"{task.task_type}"
            ),
        )

    # ----------------------------------------------
    # 驗證 capabilities
    # ----------------------------------------------

    valid_capabilities = {
        "navigation",
        "general_delivery",
        "medicine_delivery",
        "specimen_delivery",
        "manipulation",
    }

    invalid_capabilities = [
        capability
        for capability
        in task.required_capabilities
        if capability not in valid_capabilities
    ]

    if invalid_capabilities:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported capabilities: "
                + ", ".join(
                    invalid_capabilities
                )
            ),
        )

    payload = (
        ros_bridge_node
        .publish_hospital_task(task)
    )

    return {
        "success": True,

        "message":
            "Hospital task published to ROS topic",

        "topic":
            ROS_TASK_TOPIC_NAME,

        "task":
            payload,
    }


# ==========================================================
# Robot State API
# ==========================================================

@app.get("/api/hospital/robots")
def get_hospital_robots():

    if ros_bridge_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS bridge node is not ready",
        )

    return {
        "success": True,

        "source":
            ROS_FLEET_TOPIC_NAME,

        "data":
            ros_bridge_node.latest_fleet,
    }


# ==========================================================
# ROS Spin Thread
# ==========================================================

def spin_ros_node(node):
    rclpy.spin(node)


# ==========================================================
# Main
# ==========================================================

def main():

    global ros_bridge_node

    rclpy.init()

    ros_bridge_node = HospitalRosBridge()

    ros_thread = threading.Thread(
        target=spin_ros_node,
        args=(ros_bridge_node,),
        daemon=True,
    )

    ros_thread.start()

    uvicorn.run(
        app,

        # 接受所有網路介面
        host="0.0.0.0",

        # HTTP API port
        port=5050,
    )

    ros_bridge_node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()