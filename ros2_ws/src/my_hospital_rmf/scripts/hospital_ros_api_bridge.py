#!/usr/bin/env python3

import json
import threading
from typing import Optional

import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


ROS_TASK_TOPIC_NAME = "/hospital_task_request"
ROS_FLEET_TOPIC_NAME = "/fleet_states"


class HospitalTaskRequest(BaseModel):
    target: str
    priority: int = 1
    task_type: str = "go_to_place"
    note: Optional[str] = None


class HospitalRosBridge(Node):
    def __init__(self):
        super().__init__("hospital_ros_api_bridge")

        self.task_pub = self.create_publisher(
            String,
            ROS_TASK_TOPIC_NAME,
            10,
        )

        self.latest_fleet = {
            "fleet": "",
            "robots": [],
        }

        self.create_subscription(
            FleetState,
            ROS_FLEET_TOPIC_NAME,
            self.fleet_state_cb,
            10,
        )

        self.get_logger().info("Hospital ROS API Bridge started")
        self.get_logger().info(f"Publishing topic: {ROS_TASK_TOPIC_NAME}")
        self.get_logger().info(f"Subscribing topic: {ROS_FLEET_TOPIC_NAME}")

    def publish_hospital_task(self, task: HospitalTaskRequest):
        payload = {
            "target": task.target,
            "priority": task.priority,
            "task_type": task.task_type,
        }

        if task.note:
            payload["note"] = task.note

        msg = String()
        msg.data = json.dumps(payload)

        self.task_pub.publish(msg)

        self.get_logger().info(f"Published hospital task: {msg.data}")

        return payload

    def fleet_state_cb(self, msg: FleetState):
        robots = []

        for robot in msg.robots:
            mode = int(robot.mode.mode)
            task_id = robot.task_id or ""

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
                "battery": int(round(float(robot.battery_percent) * 100)),
                "currentTask": current_task,
                "location": robot.location.level_name,
                "x": float(robot.location.x),
                "y": float(robot.location.y),
                "yaw": float(robot.location.yaw),
                "levelName": robot.location.level_name,
                "mode": mode,
                "modeText": mode_text,
                "taskId": task_id,
            })

        self.latest_fleet = {
            "fleet": msg.name,
            "robots": robots,
        }


app = FastAPI(
    title="Hospital ROS API Bridge",
    description="HTTP API bridge for hospital tasks and robot states",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ros_bridge_node = None


@app.get("/")
def root():
    return {
        "message": "Hospital ROS API Bridge is running",
        "taskTopic": ROS_TASK_TOPIC_NAME,
        "fleetTopic": ROS_FLEET_TOPIC_NAME,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ros_task_topic": ROS_TASK_TOPIC_NAME,
        "ros_fleet_topic": ROS_FLEET_TOPIC_NAME,
    }


@app.post("/api/hospital/tasks")
def create_hospital_task(task: HospitalTaskRequest):
    if ros_bridge_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS bridge node is not ready",
        )

    if task.task_type != "go_to_place":
        raise HTTPException(
            status_code=400,
            detail="Only task_type='go_to_place' is supported now",
        )

    payload = ros_bridge_node.publish_hospital_task(task)

    return {
        "success": True,
        "message": "Hospital task published to ROS topic",
        "topic": ROS_TASK_TOPIC_NAME,
        "task": payload,
    }


@app.get("/api/hospital/robots")
def get_hospital_robots():
    if ros_bridge_node is None:
        raise HTTPException(
            status_code=500,
            detail="ROS bridge node is not ready",
        )

    return {
        "success": True,
        "source": ROS_FLEET_TOPIC_NAME,
        "data": ros_bridge_node.latest_fleet,
    }


def spin_ros_node(node):
    rclpy.spin(node)


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
        host="0.0.0.0",
        port=5050,
    )

    ros_bridge_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
