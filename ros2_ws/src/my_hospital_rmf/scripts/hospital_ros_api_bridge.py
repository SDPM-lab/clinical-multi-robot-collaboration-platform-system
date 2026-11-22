#!/usr/bin/env python3

from __future__ import annotations

import json
import threading
from typing import List, Optional

import rclpy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rclpy.node import Node
from rmf_fleet_msgs.msg import FleetState
from std_msgs.msg import String
import uvicorn


ROS_TASK_TOPIC_NAME = "/hospital_task_request"
ROS_FLEET_TOPIC_NAME = "/fleet_states"

VALID_TASK_TYPES = {
    "waste_transport",
    "clothes_collection",
    "specimen_delivery",
    "medication_delivery",
    "ward_service",
}

VALID_CAPABILITIES = VALID_TASK_TYPES


class HospitalTaskRequest(BaseModel):
    task_id: str

    task_type: str

    source: str
    destination: str

    priority: int = Field(
        ge=0,
        le=3,
    )

    required_capabilities: List[str] = []

    created_at: Optional[float] = None

    scheduled_at: Optional[float] = None

    note: Optional[str] = None


class HospitalRosApiBridge(Node):

    def __init__(self) -> None:

        super().__init__(
            "hospital_ros_api_bridge"
        )

        self.task_publisher = (
            self.create_publisher(
                String,
                ROS_TASK_TOPIC_NAME,
                10,
            )
        )

        self.fleet_subscription = (
            self.create_subscription(
                FleetState,
                ROS_FLEET_TOPIC_NAME,
                self._fleet_state_callback,
                10,
            )
        )

        self.latest_fleets = {}

        self.get_logger().info(
            "Hospital ROS API Bridge initialized"
        )

        self.get_logger().info(
            f"Publishing tasks: "
            f"{ROS_TASK_TOPIC_NAME}"
        )

        self.get_logger().info(
            f"Listening fleet states: "
            f"{ROS_FLEET_TOPIC_NAME}"
        )

    def publish_task(
        self,
        task: HospitalTaskRequest,
    ) -> dict:

        payload = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "source": task.source,
            "destination": task.destination,
            "priority": task.priority,
            "required_capabilities": (
                task.required_capabilities
            ),
            "created_at": task.created_at,
            "scheduled_at": task.scheduled_at,
            "note": task.note,
        }

        msg = String()

        msg.data = json.dumps(
            payload,
            ensure_ascii=False,
        )

        self.task_publisher.publish(
            msg
        )

        self.get_logger().info(
            "Published hospital task: "
            f"{task.task_id} "
            f"({task.task_type}) "
            f"{task.source} -> "
            f"{task.destination}"
        )

        return payload

    def _fleet_state_callback(
        self,
        msg: FleetState,
    ) -> None:

        robots = []

        for robot in msg.robots:

            mode = int(
                robot.mode.mode
            )

            task_id = (
                str(robot.task_id).strip()
            )

            if mode == 1:
                status = "充電中"
                mode_text = "充電中"
                current_task = "充電中"

            elif mode == 2:
                if task_id:
                    status = "執行任務中"
                    mode_text = "執行任務中"
                    current_task = (
                        f"任務中: {task_id}"
                    )
                else:
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
                        float(
                            robot.battery_percent
                        )
                    )
                ),

                "batterySoc": float(
                    robot.battery_percent
                ),

                "currentTask": (
                    current_task
                ),

                "x": float(
                    robot.location.x
                ),

                "y": float(
                    robot.location.y
                ),

                "yaw": float(
                    robot.location.yaw
                ),

                "levelName": (
                    robot.location.level_name
                ),

                "mode": mode,

                "modeText": mode_text,

                "taskId": task_id,
            })

        self.latest_fleets[
            msg.name
        ] = {
            "fleet": msg.name,
            "robots": robots,
        }


app = FastAPI(
    title="Hospital ROS API Bridge",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ros_bridge_node: (
    HospitalRosApiBridge
    | None
) = None


@app.get("/")
def root():

    return {
        "message":
            "Hospital ROS API Bridge "
            "is running",

        "taskTopic":
            ROS_TASK_TOPIC_NAME,

        "fleetTopic":
            ROS_FLEET_TOPIC_NAME,
    }


@app.get("/api/health")
def health():

    return {
        "status": "ok",

        "ros_task_topic":
            ROS_TASK_TOPIC_NAME,

        "ros_fleet_topic":
            ROS_FLEET_TOPIC_NAME,
    }


@app.post("/api/hospital/tasks")
def create_hospital_task(
    task: HospitalTaskRequest,
):

    if ros_bridge_node is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "ROS bridge node "
                "is not ready"
            ),
        )

    if (
        task.task_type
        not in VALID_TASK_TYPES
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported task_type: "
                f"{task.task_type}"
            ),
        )

    invalid_capabilities = [
        capability
        for capability
        in task.required_capabilities
        if capability
        not in VALID_CAPABILITIES
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
        ros_bridge_node.publish_task(
            task
        )
    )

    return {
        "success": True,

        "message":
            "Hospital task published "
            "to ROS topic",

        "topic":
            ROS_TASK_TOPIC_NAME,

        "task":
            payload,
    }


@app.get("/api/hospital/robots")
def get_hospital_robots():

    if ros_bridge_node is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "ROS bridge node "
                "is not ready"
            ),
        )

    return {
        "success": True,
        "source": (
            ROS_FLEET_TOPIC_NAME
        ),
        "data": (
            ros_bridge_node
            .latest_fleets
        ),
    }


def spin_ros_node(
    node: HospitalRosApiBridge,
) -> None:

    rclpy.spin(node)


def main() -> None:

    global ros_bridge_node

    rclpy.init()

    ros_bridge_node = (
        HospitalRosApiBridge()
    )

    ros_thread = threading.Thread(
        target=spin_ros_node,
        args=(ros_bridge_node,),
        daemon=True,
    )

    ros_thread.start()

    try:

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=5050,
            log_level="info",
        )

    finally:

        ros_bridge_node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
