#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
import os
import math
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
)

from rmf_fleet_msgs.msg import FleetState
from rmf_task_msgs.msg import ApiRequest
from std_msgs.msg import String


# ============================================================
# Project paths
# ============================================================

THIS_FILE = Path(__file__).resolve()


def find_project_root() -> Path:

    candidates = []

    # 1. Current working directory and its parents.
    cwd = Path.cwd().resolve()

    candidates.append(cwd)
    candidates.extend(cwd.parents)

    # 2. Installed/source executable location and its parents.
    candidates.append(THIS_FILE.parent)
    candidates.extend(THIS_FILE.parents)

    for candidate in candidates:

        if (
            candidate
            / "experiments"
            / "fleet_sizing"
        ).is_dir():

            return candidate

    raise RuntimeError(
        "Could not locate project root containing "
        "experiments/fleet_sizing. "
        f"cwd={cwd}, executable={THIS_FILE}"
    )


PROJECT_ROOT = find_project_root()

FLEET_SIZING_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
)

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(FLEET_SIZING_DIR),
    )

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# ============================================================
# RL / experiment imports
# ============================================================

from models import RobotState, TaskState

from nav_graph import NavGraph

from travel_time import TravelTimeModel

from rl.observation import (
    BATTERY_LAYOUT,
    LOCATIONS,
    ObservationEncoder,
)

from rl.action_mask import (
    ActionMaskBuilder,
)


try:
    from sb3_contrib import MaskablePPO
except ImportError as exc:
    raise RuntimeError(
        "sb3_contrib is not available. "
        "Run this scheduler from the same Python "
        "environment used for PPO training."
    ) from exc


# ============================================================
# Constants
# ============================================================

TASK_TOPIC = "/hospital_task_request"
FLEET_TOPIC = "/fleet_states"

PPO_ASSIGNMENT_TOPIC = "/hospital_ppo_assignment"

RMF_TASK_API_TOPIC = "/task_api_requests"
RMF_FLEET_NAME = "hospital_fleet"

RMF_COMPLETION_TOPIC = "/hospital_rmf_activity_completed"

CHARGING_WAYPOINT = "charging_station_2"

BATTERY_CHARGE_TRIGGER_SOC = 0.25

BATTERY_RESUME_SOC = 0.80
BATTERY_FULL_CHARGE_TIME_S = 2.0 * 60.0 * 60.0
BATTERY_CHARGE_RATE_PER_SECOND = 1.0 / BATTERY_FULL_CHARGE_TIME_S

TEST_CHARGING_DURATION_S = 10.0

MODEL_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "models"
    / (
        "reward_confirm_nav2_sweep12_"
        "w40_a35_q15_i10_"
        "seed7101_200k"
    )
    / "final_model.zip"
)


FORMAL_MODEL_SHA256 = (
    "1972295e176e6907d3bee4d01b301fa"
    "10526dac40dca38a5e867fe1a63825d07"
)

FORMAL_MODEL_SEED = 7101
FORMAL_OBSERVATION_SIZE = 98
FORMAL_ACTION_COUNT = 7
FORMAL_TRAINING_TIMESTEPS = 200192
FORMAL_APPROACH_SCALE_S = 600.0
FLEET_STATE_MAX_AGE_S = 30.0

LOGICAL_ROBOT_IDS = (
    "C01",
    "C02",
    "M01",
    "M02",
    "W01",
    "W02",
    "W03",
)


LOGICAL_TO_RMF = {
    "C01": "hospital_robot_1",
    "C02": "hospital_robot_2",
    "M01": "hospital_robot_3",
    "M02": "hospital_robot_4",
    "W01": "hospital_robot_5",
    "W02": "hospital_robot_6",
    "W03": "hospital_robot_7",
}


RMF_TO_LOGICAL = {
    rmf_name: logical_id
    for logical_id, rmf_name
    in LOGICAL_TO_RMF.items()
}


ROBOT_TYPES = {
    "C01": "clean",
    "C02": "clean",

    "M01": "medical",
    "M02": "medical",

    "W01": "ward",
    "W02": "ward",
    "W03": "ward",
}


ROBOT_CAPABILITIES = {
    "clean": [
        "waste_transport",
        "clothes_collection",
    ],

    "medical": [
        "specimen_delivery",
        "medication_delivery",
    ],

    "ward": [
        "medication_delivery",
        "ward_service",
    ],
}


VALID_TASK_TYPES = {
    "waste_transport",
    "clothes_collection",
    "specimen_delivery",
    "medication_delivery",
    "ward_service",
}


# ============================================================
# Scheduler Node
# ============================================================

class WaitForAvailableRobot(Exception):
    """A compatible robot is temporarily unavailable."""


class HospitalPpoScheduler(Node):

    def __init__(self) -> None:

        from rclpy.qos import (
            QoSProfile,
            ReliabilityPolicy,
            DurabilityPolicy,
        )

        super().__init__(
            "hospital_ppo_scheduler"
        )

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"PPO model not found: "
                f"{MODEL_PATH}"
            )

        self.get_logger().info(
            f"Loading PPO model: "
            f"{MODEL_PATH}"
        )

        model_sha256 = hashlib.sha256(
            MODEL_PATH.read_bytes()
        ).hexdigest()

        if model_sha256 != FORMAL_MODEL_SHA256:
            raise RuntimeError(
                "Formal PPO model SHA256 mismatch: "
                f"expected={FORMAL_MODEL_SHA256}, "
                f"actual={model_sha256}"
            )

        self.model = MaskablePPO.load(
            str(MODEL_PATH),
            device="cpu",
        )

        if self.model.seed != FORMAL_MODEL_SEED:
            raise RuntimeError(
                f"Unexpected PPO seed: {self.model.seed}"
            )

        if (
            self.model.observation_space.shape
            != (FORMAL_OBSERVATION_SIZE,)
        ):
            raise RuntimeError(
                "Unexpected PPO observation space: "
                f"{self.model.observation_space}"
            )

        if self.model.action_space.n != FORMAL_ACTION_COUNT:
            raise RuntimeError(
                "Unexpected PPO action space: "
                f"{self.model.action_space}"
            )

        if (
            self.model.num_timesteps
            != FORMAL_TRAINING_TIMESTEPS
        ):
            raise RuntimeError(
                "Unexpected PPO training timesteps: "
                f"{self.model.num_timesteps}"
            )

        self.get_logger().info(
            "[FORMAL_PPO_MODEL_VERIFIED] "
            f"seed={self.model.seed}, "
            f"sha256={model_sha256}, "
            f"observation={self.model.observation_space}, "
            f"action={self.model.action_space}, "
            f"timesteps={self.model.num_timesteps}, "
            "device=cpu"
        )

        self.nav_graph = NavGraph()

        self.travel_model = (
            TravelTimeModel(
                nav_graph=self.nav_graph
            )
        )

        self.observation_encoder = (
            ObservationEncoder(
                robot_ids=LOGICAL_ROBOT_IDS,
                layout=BATTERY_LAYOUT,
                approach_time_scale_s=FORMAL_APPROACH_SCALE_S,
            )
        )

        self.mask_builder = (
            ActionMaskBuilder(
                robot_ids=LOGICAL_ROBOT_IDS,
            )
        )

        if (
            self.observation_encoder.observation_size
            != FORMAL_OBSERVATION_SIZE
        ):
            raise RuntimeError("Observation encoder size mismatch")

        if self.mask_builder.action_count != FORMAL_ACTION_COUNT:
            raise RuntimeError("Action mask size mismatch")

        self.get_logger().info(
            "[PPO_RUNTIME_CONFIGURATION] "
            f"approach_scale_s="
            f"{self.observation_encoder.approach_time_scale_s}, "
            f"routes={len(self.travel_model.route_stats)}, "
            f"effective_speed_mps="
            f"{self.travel_model.effective_speed_mps}, "
            f"route_summary={self.travel_model.summary_csv_path}, "
            f"nav_graph={self.nav_graph.yaml_path}"
        )

        # ----------------------------------------------------
        # Optional battery test mode.
        #
        # OFF by default. When enabled, the robot selected for
        # a Hospital Task is treated as SOC=0.20 after assignment.
        # This is only for validating battery-aware runtime logic.
        # ----------------------------------------------------

        self.test_force_low_battery = (
            os.environ.get(
                "HOSPITAL_TEST_FORCE_LOW_BATTERY",
                "0",
            )
            == "1"
        )

        # Scheduling-only mode:
        # PPO makes the assignment and publishes the result to Backend,
        # but does not dispatch the task to RMF/navigation.
        self.scheduling_only = (
            os.environ.get(
                "HOSPITAL_SCHEDULING_ONLY",
                "0",
            )
            == "1"
        )

        self.get_logger().info(
            "Scheduling-only mode: "
            f"{self.scheduling_only}"
        )

        self.test_low_battery_robots = set()

        # Latest physical FleetState snapshot.
        self.latest_robot_data: Dict[
            str,
            dict,
        ] = {}

        # Runtime scheduler-side task state.
        self.tasks_by_id: Dict[
            str,
            TaskState,
        ] = {}

        # Tasks received from Backend but not yet due.
        # Key = Backend hospital task_id
        self.pending_scheduled_tasks: Dict[
            str,
            dict,
        ] = {}

        # Currently executing Hospital Task.
        #
        # IMPORTANT:
        # This uses our Hospital task_id, NOT RMF's
        # internal task_id.
        self.running_task_ids: Dict[
            str,
            str | None,
        ] = {
            robot_id: None
            for robot_id
            in LOGICAL_ROBOT_IDS
        }

        # Track whether the active Hospital Task has reached
        # its source waypoint before allowing final completion.
        self.source_reached: Dict[
            str,
            bool,
        ] = {
            robot_id: False
            for robot_id
            in LOGICAL_ROBOT_IDS
        }

        # Future Hospital Tasks assigned by PPO.
        self.queued_task_ids: Dict[
            str,
            List[str],
        ] = {
            robot_id: []
            for robot_id
            in LOGICAL_ROBOT_IDS
        }

        # True while robot is travelling back to charger.
        self.returning_to_charge: Dict[
            str,
            bool,
        ] = {
            robot_id: False
            for robot_id
            in LOGICAL_ROBOT_IDS
        }

        self.charging_robots = set()

        self.charging_start_time_s = {}
        self.charging_end_time_s = {}
        self.charging_start_soc = {}

        self.runtime_battery_soc_override = {}

        self.charging_timer = self.create_timer(
            1.0,
            self._charging_tick,
        )

        self.scheduled_task_timer = self.create_timer(
            1.0,
            self._scheduled_task_tick,
        )

        rmf_task_qos = QoSProfile(
            depth=100
        )

        rmf_task_qos.reliability = (
            ReliabilityPolicy.RELIABLE
        )

        rmf_task_qos.durability = (
            DurabilityPolicy.TRANSIENT_LOCAL
        )

        self.rmf_task_publisher = (
            self.create_publisher(
                ApiRequest,
                RMF_TASK_API_TOPIC,
                rmf_task_qos,
            )
        )

        self.assignment_publisher = (
            self.create_publisher(
                String,
                PPO_ASSIGNMENT_TOPIC,
                10,
            )
        )

        self.create_subscription(
            FleetState,
            FLEET_TOPIC,
            self._fleet_state_callback,
            10,
        )

        self.create_subscription(
            String,
            TASK_TOPIC,
            self._task_callback,
            10,
        )

        self.create_subscription(
            String,
            RMF_COMPLETION_TOPIC,
            self._activity_completed_callback,
            10,
        )

        self.get_logger().info(
            "Hospital PPO Scheduler ready"
        )

        self.get_logger().info(
            "Action mapping: "
            "0=C01/robot_1, "
            "1=C02/robot_2, "
            "2=M01/robot_3, "
            "3=M02/robot_4, "
            "4=W01/robot_5, "
            "5=W02/robot_6, "
            "6=W03/robot_7"
        )

        # Return-to-parking runtime state.
        self.parking_operations = {}

        from rmf_task_msgs.msg import ApiResponse

        self.parking_api_subscription = (
            self.create_subscription(
                ApiResponse,
                "/task_api_responses",
                self._parking_api_response_callback,
                100,
            )
        )


        from action_msgs.msg import GoalStatusArray

        self.parking_nav_status = {}
        self.parking_nav_subscriptions = []

        parking_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        for rid in LOGICAL_ROBOT_IDS:

            robot_name = LOGICAL_TO_RMF[rid]

            for action_name in (
                "navigate_through_poses",
                "navigate_to_pose",
            ):

                topic = (
                    f"/{robot_name}/"
                    f"{action_name}/_action/status"
                )

                subscription = self.create_subscription(
                    GoalStatusArray,
                    topic,
                    lambda msg, logical_id=rid, action=action_name:
                        self._parking_nav_status_callback(
                            logical_id,
                            action,
                            msg,
                        ),
                    parking_qos,
                )

                self.parking_nav_subscriptions.append(
                    subscription
                )

        self.parking_settlement_timer = (
            self.create_timer(
                1.0,
                self._parking_settlement_tick,
            )
        )

    # ========================================================
    # Fleet state
    # ========================================================

    def _fleet_state_callback(
        self,
        msg: FleetState,
    ) -> None:

        for robot in msg.robots:

            if (
                robot.name
                not in RMF_TO_LOGICAL
            ):
                continue

            logical_id = (
                RMF_TO_LOGICAL[
                    robot.name
                ]
            )

            task_id = (
                str(
                    robot.task_id
                )
                .strip()
            )

            mode = int(
                robot.mode.mode
            )

            status = (
                self._convert_rmf_status(
                    mode=mode,
                    task_id=task_id,
                )
            )

            battery_soc = float(
                robot.battery_percent
            )

            # Defensive handling in case the source reports
            # battery in 0..100 instead of 0..1.
            if battery_soc > 1.0:
                battery_soc /= 100.0

            battery_soc = min(
                max(
                    battery_soc,
                    0.0,
                ),
                1.0,
            )

            self.latest_robot_data[
                logical_id
            ] = {
                "rmf_name": robot.name,

                "x": float(
                    robot.location.x
                ),

                "y": float(
                    robot.location.y
                ),

                "yaw": float(
                    robot.location.yaw
                ),

                "level_name": (
                    robot.location
                    .level_name
                ),

                "task_id": (
                    task_id
                    if task_id
                    else None
                ),

                "status": status,

                "rmf_mode": mode,

                "path_length": len(robot.path),

                "received_at": time.monotonic(),

                "fleet_stamp": (
                    int(robot.location.t.sec),
                    int(robot.location.t.nanosec),
                ),

                "battery_soc": (
                    battery_soc
                ),
            }

    @staticmethod
    def _convert_rmf_status(
        *,
        mode: int,
        task_id: str,
    ) -> str:


        if mode in (5, 8):
            return "error"

        if mode == 1:
            return "charging"

        if task_id:
            return "busy"

        if mode == 0:
            return "idle"

        return "busy"

    # ========================================================
    # Nearest waypoint
    # ========================================================

    def _nearest_waypoint(
        self,
        x: float,
        y: float,
    ) -> str:

        if not (
            self.nav_graph
            .waypoints_by_name
        ):
            raise RuntimeError(
                "Nav graph has no named waypoints"
            )

        canonical_waypoints = [
            self.nav_graph
            .waypoints_by_name[name]
            for name in LOCATIONS
            if name in (
                self.nav_graph
                .waypoints_by_name
            )
        ]

        if not canonical_waypoints:
            raise RuntimeError(
                "No PPO canonical locations "
                "exist in nav graph"
            )

        waypoint = min(
            canonical_waypoints,
            key=lambda item: math.hypot(
                float(x) - item.x,
                float(y) - item.y,
            ),
        )

        return waypoint.name

    # ========================================================
    # Runtime RobotState conversion
    # ========================================================

    def _get_runtime_battery_soc(
        self,
        logical_robot_id,
    ):
        if (
            logical_robot_id
            in self.runtime_battery_soc_override
        ):
            return float(
                self.runtime_battery_soc_override[
                    logical_robot_id
                ]
            )

        if (
            self.test_force_low_battery
            and logical_robot_id
            in self.test_low_battery_robots
        ):
            return 0.16

        data = self.latest_robot_data[
            logical_robot_id
        ]

        return float(
            data["battery_soc"]
        )


    def _ensure_scheduling_only_robot_data(
        self,
    ) -> None:
        # Scheduling-only fallback.
        #
        # When Gazebo / RMF is not running, provide deterministic
        # robot snapshots so the original 98-D PPO observation and
        # 7-D action mask can still be constructed.
        #
        # Real /fleet_states data always overwrites these values
        # when it becomes available.

        if not self.nav_graph.waypoints_by_name:
            raise RuntimeError(
                "Nav graph has no named waypoints"
            )

        fallback_waypoint = next(
            iter(
                self.nav_graph
                .waypoints_by_name
                .values()
            )
        )

        demo_locations = {
            "C01": "charging_station_2",
            "C02": "nurse_station",
            "M01": "pharmacy",
            "M02": "lab",
            "W01": "ward_a_2",
            "W02": "ward_b_2",
            "W03": "consult_1_2",
        }

        added = []

        for logical_id in LOGICAL_ROBOT_IDS:

            if logical_id in self.latest_robot_data:
                continue

            waypoint_name = demo_locations[
                logical_id
            ]

            waypoint = (
                self.nav_graph
                .waypoints_by_name
                .get(
                    waypoint_name,
                    fallback_waypoint,
                )
            )

            self.latest_robot_data[
                logical_id
            ] = {
                "rmf_name": (
                    LOGICAL_TO_RMF[
                        logical_id
                    ]
                ),
                "x": float(waypoint.x),
                "y": float(waypoint.y),
                "yaw": 0.0,
                "level_name": "L1",
                "task_id": None,
                "status": (
                    "idle"
                    if self.scheduling_only
                    else "offline"
                ),
                "battery_soc": 1.0,
            }

            added.append(
                logical_id
            )

        if added:
            mode_label = (
                "SCHEDULING_ONLY_DEMO_FLEET"
                if self.scheduling_only
                else "OFFLINE_FLEET_PLACEHOLDERS"
            )

            self.get_logger().info(
                f"[{mode_label}] "
                "initialized="
                + ",".join(added)
            )


    def _build_robot_states(
        self,
    ) -> List[RobotState]:

        self._ensure_scheduling_only_robot_data()

        missing = [
            robot_id
            for robot_id
            in LOGICAL_ROBOT_IDS
            if robot_id
            not in self.latest_robot_data
        ]

        if missing:
            raise RuntimeError(
                "Fleet state incomplete. "
                "Missing robots: "
                + ", ".join(missing)
            )

        robots: List[
            RobotState
        ] = []

        for logical_id in (
            LOGICAL_ROBOT_IDS
        ):

            data = (
                self.latest_robot_data[
                    logical_id
                ]
            )

            robot_type = (
                ROBOT_TYPES[
                    logical_id
                ]
            )

            current_location = (
                self._nearest_waypoint(
                    data["x"],
                    data["y"],
                )
            )

            # IMPORTANT:
            # PPO must use the Hospital Scheduler task ID,
            # not RMF's internal task_id.
            current_task_id = (
                self.running_task_ids[
                    logical_id
                ]
            )

            queue = list(
                self.queued_task_ids[
                    logical_id
                ]
            )

            runtime_status = (
                data["status"]
            )

            received_at = data.get("received_at")

            fleet_state_stale = (
                not self.scheduling_only
                and (
                    received_at is None
                    or time.monotonic() - received_at
                        > FLEET_STATE_MAX_AGE_S
                )
            )

            if fleet_state_stale:
                # Exclude stale robots from new assignments.
                # Do not clear their running tasks, queues,
                # parking operations or charging state.
                status = "offline"

            elif logical_id in self.charging_robots:
                status = "charging"

            elif self.returning_to_charge[
                logical_id
            ]:
                status = "returning_to_charge"

            elif (
                current_task_id is not None
                or queue
            ):
                status = "busy"

            elif logical_id in self.parking_operations:

                operation = self.parking_operations[logical_id]

                if (
                    operation["phase"] in (
                        "requesting",
                        "returning",
                    )
                    and runtime_status in ("idle", "busy")
                    and data.get("rmf_mode") in (0, 2, 6)
                    and time.monotonic()
                        - data.get("received_at", 0.0) <= FLEET_STATE_MAX_AGE_S
                    and self._get_runtime_battery_soc(
                        logical_id
                    ) >= BATTERY_CHARGE_TRIGGER_SOC
                    and (
                        not data.get("task_id")
                        or data.get("task_id") in (
                            operation["request_id"],
                            operation["rmf_task_id"],
                        )
                    )
                ):
                    status = "idle"

                else:
                    status = "busy"

            else:
                status = runtime_status

            # Active Hospital Task destination.
            #
            # This field is critical for the duration-free
            # projection used during PPO training:
            #
            # active task exists
            # -> projection starts from active task destination
            current_task_destination = None

            if current_task_id is not None:
                current_task = (
                    self.tasks_by_id.get(
                        current_task_id
                    )
                )

                if current_task is not None:
                    current_task_destination = (
                        current_task.destination
                    )

            # Future location is the location after all
            # currently known scheduled work.
            future_location = (
                current_location
            )

            if queue:
                last_task_id = queue[-1]

                last_task = (
                    self.tasks_by_id.get(
                        last_task_id
                    )
                )

                if last_task is not None:
                    future_location = (
                        last_task.destination
                    )

            elif current_task_id is not None:
                current_task = (
                    self.tasks_by_id.get(
                        current_task_id
                    )
                )

                if current_task is not None:
                    future_location = (
                        current_task.destination
                    )

            robot = RobotState(
                robot_id=logical_id,

                robot_type=robot_type,

                capabilities=list(
                    ROBOT_CAPABILITIES[
                        robot_type
                    ]
                ),

                current_location=(
                    current_location
                ),

                status=(
                    status
                ),

                current_task_id=(
                    current_task_id
                ),

                current_task_destination=(
                    current_task_destination
                ),

                queued_task_ids=queue,

                available_time_s=0.0,

                future_location=(
                    future_location
                ),

                battery_soc=(
                    self._get_runtime_battery_soc(
                        logical_id
                    )
                ),
            )

            robots.append(
                robot
            )

        return robots

    # ========================================================
    # Travel time
    # ========================================================

    def _travel_time(
        self,
        source: str,
        destination: str,
    ) -> float:

        return float(
            self.travel_model
            .get_travel_time_mean(
                source,
                destination,
            )
        )

    # ========================================================
    # RMF targeted dispatch
    # ========================================================

    def _dispatch_rmf_task(
        self,
        *,
        task: TaskState,
        rmf_robot_name: str,
    ) -> str:

        request_id = (
            f"ppo_{task.task_id}_"
            f"{int(time.time() * 1000)}"
        )

        payload = {
            "type": "robot_task_request",

            "robot": rmf_robot_name,

            "fleet": RMF_FLEET_NAME,

            "request": {
                "category": "compose",

                "description": {
                    "category":
                        "hospital_ppo_task",

                    "detail": (
                        f"{task.task_type}: "
                        f"{task.source} -> "
                        f"{task.destination}"
                    ),

                    "phases": [
                        {
                            "activity": {
                                "category":
                                    "go_to_place",

                                "description":
                                    task.source,
                            }
                        },

                        {
                            "activity": {
                                "category":
                                    "go_to_place",

                                "description":
                                    task.destination,
                            }
                        },
                    ],
                },
            },
        }

        msg = ApiRequest()

        msg.request_id = (
            request_id
        )

        msg.json_msg = json.dumps(
            payload,
            separators=(",", ":"),
        )

        self.rmf_task_publisher.publish(
            msg
        )

        self.get_logger().info(
            "RMF task dispatched: "
            f"request_id={request_id}, "
            f"robot={rmf_robot_name}, "
            f"{task.source} -> "
            f"{task.destination}"
        )

        return request_id


    def _publish_assignment_result(
        self,
        *,
        task_id: str,
        assigned: bool,
        rmf_robot_name: str | None = None,
    ) -> None:

        payload = {
            "task_id": task_id,
            "status": 3 if assigned else 4,
        }

        if assigned:
            if not rmf_robot_name:
                raise ValueError(
                    "rmf_robot_name is required "
                    "for successful assignment"
                )

            payload["assignment"] = {
                "is_assigned": True,
                "expected_robot_name": (
                    rmf_robot_name
                ),
            }

        msg = String()

        msg.data = json.dumps(
            payload,
            separators=(",", ":"),
        )

        self.assignment_publisher.publish(
            msg
        )

        self.get_logger().info(
            "[PPO_ASSIGNMENT_PUBLISHED] "
            f"task={task_id}, "
            f"assigned={assigned}, "
            f"robot={rmf_robot_name}"
        )


    # ========================================================
    # Incoming task
    # ========================================================

    def _start_hospital_task(
        self,
        *,
        logical_robot_id: str,
        task: TaskState,
    ) -> None:

        rmf_robot_name = (
            LOGICAL_TO_RMF[
                logical_robot_id
            ]
        )

        if logical_robot_id in self.parking_operations:

            raise RuntimeError(
                "Cannot dispatch hospital task while "
                "parking operation is unresolved"
            )

        now = time.time()

        self.running_task_ids[
            logical_robot_id
        ] = task.task_id

        self.source_reached[
            logical_robot_id
        ] = False

        if self.test_force_low_battery:
            self.test_low_battery_robots.add(
                logical_robot_id
            )

            self.get_logger().warning(
                "[TEST_BATTERY_OVERRIDE] "
                f"robot="
                f"{LOGICAL_TO_RMF[logical_robot_id]}, "
                "soc=0.160"
            )

        self.returning_to_charge[
            logical_robot_id
        ] = False

        task.status = "active"

        if task.start_time_s is None:
            task.start_time_s = now

        request_id = (
            self._dispatch_rmf_task(
                task=task,
                rmf_robot_name=(
                    rmf_robot_name
                ),
            )
        )

        self.get_logger().info(
            "[TASK_STARTED] "
            f"task={task.task_id}, "
            f"robot={rmf_robot_name}, "
            f"request_id={request_id}"
        )


    def _dispatch_return_to_charge(
        self,
        logical_robot_id: str,
    ) -> None:

        rmf_robot_name = (
            LOGICAL_TO_RMF[
                logical_robot_id
            ]
        )

        request_id = (
            f"charge_"
            f"{rmf_robot_name}_"
            f"{int(time.time() * 1000)}"
        )

        payload = {
            "type": "robot_task_request",

            "robot": rmf_robot_name,

            "fleet": RMF_FLEET_NAME,

            "request": {
                "category": "compose",

                "description": {
                    "category":
                        "return_to_charge",

                    "detail":
                        CHARGING_WAYPOINT,

                    "phases": [
                        {
                            "activity": {
                                "category":
                                    "go_to_place",

                                "description":
                                    CHARGING_WAYPOINT,
                            }
                        },
                    ],
                },
            },
        }

        msg = ApiRequest()

        msg.request_id = request_id

        msg.json_msg = json.dumps(
            payload,
            separators=(",", ":"),
        )

        self.returning_to_charge[
            logical_robot_id
        ] = True

        self.rmf_task_publisher.publish(
            msg
        )

        self.get_logger().info(
            "[RETURN_TO_CHARGE] "
            f"robot={rmf_robot_name}, "
            f"destination="
            f"{CHARGING_WAYPOINT}"
        )


    def _start_charging(
        self,
        logical_robot_id,
    ):
        if logical_robot_id in self.charging_robots:
            return

        start_soc = self._get_runtime_battery_soc(
            logical_robot_id
        )

        if start_soc >= BATTERY_RESUME_SOC:
            self.get_logger().info(
                "[CHARGE_NOT_REQUIRED] "
                f"robot={LOGICAL_TO_RMF[logical_robot_id]}, "
                f"soc={start_soc:.3f}"
            )

            self._start_next_or_charge(
                logical_robot_id
            )
            return

        now_s = time.time()

        if self.test_force_low_battery:
            charging_duration_s = (
                TEST_CHARGING_DURATION_S
            )
        else:
            required_soc = (
                BATTERY_RESUME_SOC
                - start_soc
            )

            charging_duration_s = (
                required_soc
                / BATTERY_CHARGE_RATE_PER_SECOND
            )

        self.test_low_battery_robots.discard(
            logical_robot_id
        )

        self.runtime_battery_soc_override[
            logical_robot_id
        ] = start_soc

        self.charging_robots.add(
            logical_robot_id
        )

        self.charging_start_time_s[
            logical_robot_id
        ] = now_s

        self.charging_end_time_s[
            logical_robot_id
        ] = (
            now_s
            + charging_duration_s
        )

        self.charging_start_soc[
            logical_robot_id
        ] = start_soc

        self.get_logger().info(
            "[CHARGING_STARTED] "
            f"robot={LOGICAL_TO_RMF[logical_robot_id]}, "
            f"start_soc={start_soc:.3f}, "
            f"target_soc={BATTERY_RESUME_SOC:.3f}, "
            f"duration_s={charging_duration_s:.1f}"
        )


    def _charging_tick(
        self,
    ):
        if not self.charging_robots:
            return

        now_s = time.time()

        for logical_robot_id in list(
            self.charging_robots
        ):
            start_time_s = (
                self.charging_start_time_s[
                    logical_robot_id
                ]
            )

            end_time_s = (
                self.charging_end_time_s[
                    logical_robot_id
                ]
            )

            start_soc = (
                self.charging_start_soc[
                    logical_robot_id
                ]
            )

            duration_s = max(
                end_time_s - start_time_s,
                1e-6,
            )

            progress = min(
                1.0,
                max(
                    0.0,
                    (
                        now_s - start_time_s
                    )
                    / duration_s,
                ),
            )

            current_soc = (
                start_soc
                + (
                    BATTERY_RESUME_SOC
                    - start_soc
                )
                * progress
            )

            self.runtime_battery_soc_override[
                logical_robot_id
            ] = current_soc

            if now_s < end_time_s:
                continue

            self.runtime_battery_soc_override[
                logical_robot_id
            ] = BATTERY_RESUME_SOC

            self.charging_robots.discard(
                logical_robot_id
            )

            self.charging_start_time_s.pop(
                logical_robot_id,
                None,
            )

            self.charging_end_time_s.pop(
                logical_robot_id,
                None,
            )

            self.charging_start_soc.pop(
                logical_robot_id,
                None,
            )

            self.get_logger().info(
                "[CHARGING_COMPLETED] "
                f"robot={LOGICAL_TO_RMF[logical_robot_id]}, "
                f"soc={BATTERY_RESUME_SOC:.3f}"
            )

            self._start_next_or_charge(
                logical_robot_id
            )


    def _start_next_or_charge(
        self,
        logical_robot_id: str,
    ) -> None:

        if logical_robot_id in self.parking_operations:
            return

        if logical_robot_id in self.charging_robots:
            return

        # --------------------------------------------------
        # Match training-time battery behavior.
        #
        # After an active task completes:
        #
        # 1. Low battery has priority over queued work.
        # 2. Otherwise execute the next queued task.
        # 3. If no queued work exists, remain idle.
        # --------------------------------------------------

        battery_soc = (
            self._get_runtime_battery_soc(
                logical_robot_id
            )
        )

        if (
            battery_soc
            < BATTERY_CHARGE_TRIGGER_SOC
        ):
            self.get_logger().info(
                "[LOW_BATTERY] "
                f"robot="
                f"{LOGICAL_TO_RMF[logical_robot_id]}, "
                f"soc={battery_soc:.3f}, "
                f"trigger="
                f"{BATTERY_CHARGE_TRIGGER_SOC:.3f}"
            )

            self._dispatch_return_to_charge(
                logical_robot_id
            )

            return

        queue = (
            self.queued_task_ids[
                logical_robot_id
            ]
        )

        if queue:

            next_task_id = (
                queue.pop(0)
            )

            next_task = (
                self.tasks_by_id[
                    next_task_id
                ]
            )

            self.get_logger().info(
                "[QUEUE_POP] "
                f"robot="
                f"{LOGICAL_TO_RMF[logical_robot_id]}, "
                f"next_task={next_task_id}, "
                f"remaining_queue={list(queue)}"
            )

            self._start_hospital_task(
                logical_robot_id=(
                    logical_robot_id
                ),
                task=next_task,
            )

            return

        self.get_logger().info(
            "[ROBOT_IDLE] "
            f"robot="
            f"{LOGICAL_TO_RMF[logical_robot_id]}, "
            f"soc={battery_soc:.3f}, "
            "queue=[]"
        )


        if not self.scheduling_only:

            self._dispatch_return_to_parking(
                logical_robot_id
            )


    def _activity_completed_callback(
        self,
        msg: String,
    ) -> None:

        try:
            payload = json.loads(
                msg.data
            )

        except Exception as exc:
            self.get_logger().error(
                "Invalid completion event: "
                f"{exc}"
            )
            return

        rmf_robot_name = str(
            payload.get(
                "robot_id",
                "",
            )
        )

        destination = str(
            payload.get(
                "destination",
                "",
            )
        )

        if (
            rmf_robot_name
            not in RMF_TO_LOGICAL
        ):
            return

        logical_robot_id = (
            RMF_TO_LOGICAL[
                rmf_robot_name
            ]
        )

        # ----------------------------------------------
        # Return-to-charge completion
        # ----------------------------------------------

        parking = self.parking_operations.get(
            logical_robot_id
        )

        if parking is not None:

            if destination == parking["waypoint"]:

                parking["arrival_event_at"] = time.monotonic()

                self.get_logger().info(
                    "[PARKING_ARRIVAL_EVENT] "
                    f"robot={rmf_robot_name}, "
                    f"destination={destination}"
                )

            # Parking events are not hospital task events.
            return

        if self.returning_to_charge[
            logical_robot_id
        ]:

            if (
                destination
                == CHARGING_WAYPOINT
            ):
                self.returning_to_charge[
                    logical_robot_id
                ] = False

                self.get_logger().info(
                    "[CHARGE_STATION_REACHED] "
                    f"robot={rmf_robot_name}"
                )

                self._start_charging(
                    logical_robot_id
                )

            return

        # ----------------------------------------------
        # Hospital task completion
        # ----------------------------------------------

        task_id = (
            self.running_task_ids[
                logical_robot_id
            ]
        )

        if task_id is None:
            return

        task = (
            self.tasks_by_id.get(
                task_id
            )
        )

        if task is None:
            self.get_logger().error(
                "Running task missing from "
                f"tasks_by_id: {task_id}"
            )
            return

        # --------------------------------------------------
        # Hospital task phase tracking
        #
        # A valid Hospital Task must complete:
        # current location -> source -> destination
        #
        # Reaching the final destination is only accepted
        # after the source phase has completed.
        # --------------------------------------------------

        if (
            destination == task.source
            and not self.source_reached[
                logical_robot_id
            ]
        ):
            self.source_reached[
                logical_robot_id
            ] = True

            self.get_logger().info(
                "[SOURCE_REACHED] "
                f"task={task.task_id}, "
                f"robot={rmf_robot_name}, "
                f"source={destination}"
            )

            return

        if destination != task.destination:
            return

        if not self.source_reached[
            logical_robot_id
        ]:
            self.get_logger().warning(
                "[DESTINATION_IGNORED_BEFORE_SOURCE] "
                f"task={task.task_id}, "
                f"robot={rmf_robot_name}, "
                f"destination={destination}"
            )

            return

        now = time.time()

        task.status = "completed"
        task.completion_time_s = now

        self.running_task_ids[
            logical_robot_id
        ] = None

        self.source_reached[
            logical_robot_id
        ] = False

        self.get_logger().info(
            "[TASK_COMPLETED] "
            f"task={task.task_id}, "
            f"robot={rmf_robot_name}, "
            f"destination={destination}"
        )

        self._start_next_or_charge(
            logical_robot_id
        )


    def _scheduled_task_tick(self) -> None:
        now = time.time()
        due_tasks = sorted(
            (
                (task_id, payload)
                for task_id, payload in self.pending_scheduled_tasks.items()
                if payload["scheduled_at"] <= now
            ),
            key=lambda entry: entry[1]["scheduled_at"],
        )
        for task_id, payload in due_tasks:
            try:
                self._schedule_task(payload)
            except WaitForAvailableRobot:
                continue
            except Exception as exc:
                self.get_logger().error(
                    f"Scheduled PPO task failed: task={task_id}, "
                    f"{type(exc).__name__}: {exc}"
                )
                self._publish_assignment_result(task_id=task_id, assigned=False)
            self.pending_scheduled_tasks.pop(task_id)

    def _task_callback(self, msg: String) -> None:
        payload = None
        try:
            payload = json.loads(msg.data)
            task_id = str(payload["task_id"])
            if task_id in self.pending_scheduled_tasks or task_id in self.tasks_by_id:
                return
            scheduled_at = payload.get("scheduled_at")
            if scheduled_at is None:
                scheduled_at = time.time()
            payload["scheduled_at"] = float(scheduled_at)
            if not np.isfinite(payload["scheduled_at"]):
                raise ValueError("scheduled_at must be finite")
            self.pending_scheduled_tasks[task_id] = payload
            self.get_logger().info(
                f"[SCHEDULED_TASK_WAITING] task={task_id}, "
                f"scheduled_at={payload['scheduled_at']:.3f}"
            )
        except Exception as exc:
            self.get_logger().error(f"PPO scheduling failed: {type(exc).__name__}: {exc}")
            if isinstance(payload, dict) and payload.get("task_id"):
                self._publish_assignment_result(
                    task_id=str(payload["task_id"]), assigned=False
                )

    def _schedule_task(self, payload: dict) -> None:

        task_id = str(
            payload["task_id"]
        )

        task_type = str(
            payload["task_type"]
        )

        source = str(
            payload["source"]
        )

        destination = str(
            payload["destination"]
        )

        priority = int(
            payload["priority"]
        )

        if (
            task_type
            not in VALID_TASK_TYPES
        ):
            raise ValueError(
                "Unsupported task type: "
                f"{task_type}"
            )

        if not (
            self.nav_graph
            .has_waypoint(source)
        ):
            raise ValueError(
                "Unknown source waypoint: "
                f"{source}"
            )

        if not (
            self.nav_graph
            .has_waypoint(destination)
        ):
            raise ValueError(
                "Unknown destination waypoint: "
                f"{destination}"
            )

        current_time_s = time.time()

        created_at = (
            payload.get(
                "created_at"
            )
        )

        scheduled_at = (
            payload.get(
                "scheduled_at"
            )
        )

        if scheduled_at is not None:
            arrival_time_s = float(
                scheduled_at
            )

        elif created_at is not None:
            arrival_time_s = float(
                created_at
            )

        else:
            arrival_time_s = (
                current_time_s
            )

        task = TaskState(
            task_id=task_id,

            task_type=task_type,

            source=source,

            destination=destination,

            priority=priority,

            arrival_time_s=(
                arrival_time_s
            ),

            # PPO observation is duration-free.
            # Runtime does not provide future realized
            # service duration to the scheduler.
            service_time_s=0.0,
        )

        self.tasks_by_id[
            task_id
        ] = task

        robots = (
            self._build_robot_states()
        )

        mask = (
            self.mask_builder
            .build(
                task=task,

                robots=robots,

                enable_battery_model=True,

                tasks_by_id=(
                    self.tasks_by_id
                ),

                current_time_s=(
                    current_time_s
                ),

                travel_time_fn=(
                    self._travel_time
                ),
            )
        )

        # ----------------------------------------------------
        # Runtime RMF availability filter
        #
        # Training/baseline experiments allow assigning a new
        # task to a busy robot so that it can be queued.
        #
        # The current real RMF integration dispatches each
        # assignment immediately as a robot_task_request.
        # Therefore a robot that is already busy must not be
        # selected again until its current task is completed.
        #
        # Offline robots are also explicitly excluded here.
        # ----------------------------------------------------

        temporarily_unavailable = ("busy", "charging", "returning_to_charge")
        if not self.scheduling_only:
            for index, robot in enumerate(robots):
                runtime_status = (
                    str(robot.status)
                    .strip()
                    .lower()
                )

                if runtime_status in (*temporarily_unavailable, "offline", "error"):
                    mask[index] = False

        if mask.shape != (7,):
            raise RuntimeError(
                "Unexpected action mask "
                f"shape: {mask.shape}"
            )

        if not bool(
            np.any(mask)
        ):
            if not self.scheduling_only and any(
                task.task_type in robot.capabilities
                and str(robot.status).strip().lower() in temporarily_unavailable
                for robot in robots
            ):
                self.tasks_by_id.pop(task_id)
                raise WaitForAvailableRobot()
            raise RuntimeError(
                "No feasible robot available "
                f"for task {task_id}"
            )

        observation = (
            self.observation_encoder
            .encode(
                task=task,

                robots=robots,

                tasks_by_id=(
                    self.tasks_by_id
                ),

                current_time_s=(
                    current_time_s
                ),

                travel_time_fn=(
                    self._travel_time
                ),
            )
        )

        if observation.shape != (98,):
            raise RuntimeError(
                "Unexpected PPO observation "
                f"shape: {observation.shape}"
            )

        self.get_logger().info(
            "[PPO_STATE_BEGIN]"
        )

        for robot in robots:
            self.get_logger().info(
                "[PPO_STATE] "
                f"robot={robot.robot_id}, "
                f"current_location={robot.current_location}, "
                f"current_task_id={robot.current_task_id}, "
                f"current_task_destination="
                f"{robot.current_task_destination}, "
                f"queue={list(robot.queued_task_ids)}, "
                f"future_location={robot.future_location}, "
                f"status={robot.status}, "
                f"battery_soc={robot.battery_soc:.3f}"
            )

        self.get_logger().info(
            "[PPO_STATE_END]"
        )

        if not self.model.observation_space.contains(
            observation
        ):
            raise RuntimeError(
                "Observation is outside the formal PPO space"
            )

        action, _ = (
            self.model.predict(
                observation,

                action_masks=mask,

                deterministic=True,
            )
        )

        action = int(
            action
        )

        if not bool(
            mask[action]
        ):
            raise RuntimeError(
                "PPO selected infeasible "
                f"action {action}"
            )

        logical_robot_id = (
            LOGICAL_ROBOT_IDS[
                action
            ]
        )

        rmf_robot_name = (
            LOGICAL_TO_RMF[
                logical_robot_id
            ]
        )

        mask_text = [
            int(value)
            for value in mask.tolist()
        ]

        self.get_logger().info(
            "================================"
        )

        self.get_logger().info(
            f"Task: {task_id}"
        )

        self.get_logger().info(
            f"Type: {task_type}"
        )

        self.get_logger().info(
            f"Route: "
            f"{source} -> {destination}"
        )

        self.get_logger().info(
            f"Priority: {priority}"
        )

        self.get_logger().info(
            f"Observation shape: "
            f"{observation.shape}"
        )

        self.get_logger().info(
            f"Action mask: {mask_text}"
        )

        self.get_logger().info(
            f"PPO action: {action}"
        )

        self.get_logger().info(
            "Selected logical robot: "
            f"{logical_robot_id}"
        )

        self.get_logger().info(
            "Selected RMF robot: "
            f"{rmf_robot_name}"
        )

        self.get_logger().info(
            "================================"
        )

        task.assigned_robot = (
            logical_robot_id
        )

        task.assignment_time_s = (
            current_time_s
        )

        # In scheduling-only mode, stop after PPO assignment.
        # Backend receives /hospital_ppo_assignment and can update
        # assignedRobot/status without involving RMF/navigation.
        if self.scheduling_only:

            task.status = "assigned"

            # Keep the assignment as scheduler-side workload so
            # subsequent PPO decisions can see that this robot
            # already has pending work, even though RMF execution
            # is disabled.
            self.queued_task_ids[
                logical_robot_id
            ].append(
                task_id
            )

            self._publish_assignment_result(
                task_id=task_id,
                assigned=True,
                rmf_robot_name=rmf_robot_name,
            )

            self.get_logger().info(
                "[SCHEDULING_ONLY_ASSIGNED] "
                f"task={task_id}, "
                f"robot={rmf_robot_name}"
            )

            return

        running_task_id = (
            self.running_task_ids[
                logical_robot_id
            ]
        )

        if logical_robot_id in self.parking_operations:

            self.queued_task_ids[
                logical_robot_id
            ].append(task_id)

            task.status = "queued"

            self.get_logger().info(
                "[PPO_ASSIGN_PARKING_PREEMPT] "
                f"task={task_id}, "
                f"robot={rmf_robot_name}"
            )

            self._request_parking_cancel(
                logical_robot_id
            )

            # The queued task reserves this robot.
            # Do not dispatch until parking is settled.

        elif running_task_id is None:

            self._start_hospital_task(
                logical_robot_id=(
                    logical_robot_id
                ),
                task=task,
            )

            self.get_logger().info(
                "[PPO_ASSIGN_IMMEDIATE] "
                f"task={task_id}, "
                f"robot={rmf_robot_name}"
            )

        else:

            self.queued_task_ids[
                logical_robot_id
            ].append(
                task_id
            )

            task.status = "queued"

            self.get_logger().info(
                "[PPO_ASSIGN_QUEUED] "
                f"task={task_id}, "
                f"robot={rmf_robot_name}, "
                f"running={running_task_id}, "
                f"queue="
                f"{self.queued_task_ids[logical_robot_id]}"
            )

        self._publish_assignment_result(
            task_id=task_id,
            assigned=True,
            rmf_robot_name=rmf_robot_name,
        )


    def _parking_waypoint(self, logical_robot_id):

        parking_by_rmf = {
            "hospital_robot_1": ("parking_clean_1", 16.4, -12.1),
            "hospital_robot_2": ("parking_clean_2", 16.4, -10.7),
            "hospital_robot_3": ("parking_medical_1", 25.0, -19.4),
            "hospital_robot_4": ("parking_medical_2", 25.0, -20.7),
            "hospital_robot_5": ("parking_ward_1", 11.4, -19.4),
            "hospital_robot_6": ("parking_ward_2", 11.4, -20.7),
            "hospital_robot_7": ("parking_ward_3", 11.4, -22.0),
        }

        return parking_by_rmf[
            LOGICAL_TO_RMF[logical_robot_id]
        ]


    def _is_at_parking(self, logical_robot_id):

        data = self.latest_robot_data.get(
            logical_robot_id
        )

        if data is None:
            return False

        waypoint, x, y = self._parking_waypoint(
            logical_robot_id
        )

        distance = (
            (float(data["x"]) - x) ** 2
            + (float(data["y"]) - y) ** 2
        ) ** 0.5

        return distance <= 0.35


    def _dispatch_return_to_parking(
        self,
        logical_robot_id,
    ):

        if self.scheduling_only:
            return

        if logical_robot_id in self.parking_operations:
            return

        if logical_robot_id in self.charging_robots:
            return

        if self.returning_to_charge[logical_robot_id]:
            return

        if self.running_task_ids[logical_robot_id] is not None:
            return

        if self.queued_task_ids[logical_robot_id]:
            return

        if self._get_runtime_battery_soc(
            logical_robot_id
        ) < BATTERY_CHARGE_TRIGGER_SOC:
            return

        if self._is_at_parking(logical_robot_id):

            self.get_logger().info(
                "[PARKING_ALREADY_REACHED] "
                f"robot={LOGICAL_TO_RMF[logical_robot_id]}"
            )

            return

        waypoint, _, _ = self._parking_waypoint(
            logical_robot_id
        )

        rmf_robot_name = LOGICAL_TO_RMF[
            logical_robot_id
        ]

        request_id = (
            f"parking_{rmf_robot_name}_"
            f"{time.time_ns()}"
        )

        payload = {
            "type": "robot_task_request",
            "robot": rmf_robot_name,
            "fleet": RMF_FLEET_NAME,
            "request": {
                "category": "compose",
                "description": {
                    "category": "return_to_parking",
                    "detail": waypoint,
                    "phases": [
                        {
                            "activity": {
                                "category": "go_to_place",
                                "description": waypoint,
                            }
                        }
                    ],
                },
            },
        }

        operation = {
            "request_id": request_id,
            "rmf_task_id": None,
            "waypoint": waypoint,
            "phase": "requesting",
            "cancel_request_id": None,
            "cancel_accepted": False,
            "created_at": time.monotonic(),
            "seen_rmf_task": False,
            "idle_samples": 0,
            "last_idle_stamp": None,
            "idle_position": None,
            "timeout_reported": False,
        }

        self.parking_operations[
            logical_robot_id
        ] = operation

        msg = ApiRequest()
        msg.request_id = request_id
        msg.json_msg = json.dumps(payload)

        self.rmf_task_publisher.publish(msg)

        self.get_logger().info(
            "[RETURN_TO_PARKING_REQUEST] "
            f"robot={rmf_robot_name}, "
            f"waypoint={waypoint}, "
            f"request_id={request_id}"
        )


    def _request_parking_cancel(
        self,
        logical_robot_id,
    ):

        operation = self.parking_operations.get(
            logical_robot_id
        )

        if operation is None:
            return

        if operation["cancel_request_id"] is not None:
            return

        if operation["phase"] in (
            "failed",
            "cancel_failed",
        ):
            return

        if operation["rmf_task_id"] is None:

            operation["phase"] = "preempt_pending"

            return

        request_id = (
            f"parking_cancel_"
            f"{LOGICAL_TO_RMF[logical_robot_id]}_"
            f"{time.time_ns()}"
        )

        payload = {
            "type": "cancel_task_request",
            "task_id": operation["rmf_task_id"],
            "labels": [
                "preempt_return_to_parking"
            ],
        }

        operation["cancel_request_id"] = request_id
        operation["phase"] = "canceling"
        operation["cancel_requested_at"] = time.monotonic()

        msg = ApiRequest()
        msg.request_id = request_id
        msg.json_msg = json.dumps(payload)

        self.rmf_task_publisher.publish(msg)

        self.get_logger().info(
            "[PARKING_CANCEL_REQUEST] "
            f"robot={LOGICAL_TO_RMF[logical_robot_id]}, "
            f"rmf_task_id={operation['rmf_task_id']}"
        )


    def _parking_api_response_callback(
        self,
        msg,
    ):

        if msg.type != 2:
            return

        operation = None
        logical_robot_id = None

        for rid, item in self.parking_operations.items():

            if msg.request_id in (
                item["request_id"],
                item["cancel_request_id"],
            ):
                operation = item
                logical_robot_id = rid
                break

        if operation is None:
            return

        try:
            data = json.loads(msg.json_msg)
        except Exception as exc:

            self.get_logger().error(
                f"[PARKING_INVALID_RESPONSE] {exc}"
            )

            return

        robot = LOGICAL_TO_RMF[
            logical_robot_id
        ]

        if msg.request_id == operation["request_id"]:

            if operation["rmf_task_id"] is not None:
                return

            booking = (
                data.get("state", {})
                .get("booking", {})
            )

            rmf_task_id = booking.get("id")

            if (
                data.get("success") is False
                or not rmf_task_id
            ):

                operation["phase"] = (
                    "rejected"
                    if data.get("success") is False
                    else "failed"
                )

                self.get_logger().error(
                    "[PARKING_REQUEST_FAILED] "
                    f"robot={robot}, response={data}"
                )

                return

            operation["rmf_task_id"] = str(
                rmf_task_id
            )

            should_cancel = (
                operation["phase"] == "preempt_pending"
                or bool(
                    self.queued_task_ids[
                        logical_robot_id
                    ]
                )
            )

            operation["phase"] = "returning"

            self.get_logger().info(
                "[PARKING_REQUEST_ACCEPTED] "
                f"robot={robot}, "
                f"rmf_task_id={rmf_task_id}"
            )

            if should_cancel:

                self._request_parking_cancel(
                    logical_robot_id
                )

            return

        if msg.request_id == operation["cancel_request_id"]:

            if operation["cancel_accepted"]:
                return

            if data.get("success") is True:

                operation["cancel_accepted"] = True
                operation["cancel_accepted_at"] = time.monotonic()
                operation["phase"] = "waiting_stop"

                self.get_logger().info(
                    "[PARKING_CANCEL_ACCEPTED] "
                    f"robot={robot}"
                )

            else:

                operation["phase"] = "cancel_failed"

                self.get_logger().error(
                    "[PARKING_CANCEL_FAILED] "
                    f"robot={robot}, response={data}"
                )


    def _parking_nav_status_callback(
        self,
        logical_robot_id,
        action_name,
        msg,
    ):

        self.parking_nav_status[
            (logical_robot_id, action_name)
        ] = {
            "received_at": time.monotonic(),

            # 1=ACCEPTED, 2=EXECUTING, 3=CANCELING
            "active": any(
                int(goal.status) in (1, 2, 3)
                for goal in msg.status_list
            ),
        }


    def _parking_settlement_tick(self):

        if self.scheduling_only:
            return

        now = time.monotonic()

        for rid, operation in list(
            self.parking_operations.items()
        ):

            robot_name = LOGICAL_TO_RMF[rid]

            data = self.latest_robot_data.get(rid)

            if data is None:
                continue

            if now - data.get("received_at", 0.0) > FLEET_STATE_MAX_AGE_S:

                operation["idle_samples"] = 0
                operation["idle_position"] = None

                continue

            current_rmf_task = data.get("task_id")

            if (
                current_rmf_task
                and current_rmf_task in (
                    operation["request_id"],
                    operation["rmf_task_id"],
                )
            ):

                operation["seen_rmf_task"] = True

            phase = operation["phase"]

            # Do not release an operation when its result
            # is unknown or cancellation is unresolved.
            cancellation_ready = (
                phase == "waiting_stop"
                and operation["cancel_accepted"]
            )

            arrival_ready = (
                phase in ("returning", "cancel_failed")
                and operation["rmf_task_id"] is not None
                and self._is_at_parking(rid)
                and (
                    operation["seen_rmf_task"]
                    or "arrival_event_at" in operation
                )
            )

            if not cancellation_ready and not arrival_ready:

                if (
                    now - operation["created_at"] > 1800.0
                    and not operation["timeout_reported"]
                ):

                    operation["timeout_reported"] = True

                    self.get_logger().error(
                        "[PARKING_OPERATION_UNRESOLVED] "
                        f"robot={robot_name}, "
                        f"phase={phase}"
                    )

                continue

            through_status = self.parking_nav_status.get(
                (rid, "navigate_through_poses")
            )

            single_status = self.parking_nav_status.get(
                (rid, "navigate_to_pose")
            )

            # The bridge uses NavigateThroughPoses.
            # Require positive evidence that its action
            # has reached a non-active state.
            if through_status is None:
                continue

            nav_active = (
                through_status["active"]
                or (
                    single_status is not None
                    and single_status["active"]
                )
            )

            if cancellation_ready:

                evidence_after = operation[
                    "cancel_requested_at"
                ]

            else:

                evidence_after = operation["created_at"]

            fleet_fresh = (
                data["received_at"] >= evidence_after
            )

            nav_fresh = (
                through_status["received_at"]
                >= evidence_after
            )

            idle_confirmed = (
                data.get("rmf_mode") == 0
                and not current_rmf_task
                and data.get("path_length") == 0
                and data.get("level_name") == "L1"
                and not nav_active
                and fleet_fresh
                and nav_fresh
            )

            if not idle_confirmed:

                operation["idle_samples"] = 0
                operation["idle_position"] = None

                continue

            stamp = data.get("fleet_stamp")

            if stamp == operation["last_idle_stamp"]:
                continue

            operation["last_idle_stamp"] = stamp

            position = (
                float(data["x"]),
                float(data["y"]),
            )

            previous = operation["idle_position"]

            if previous is not None:

                displacement = (
                    (position[0] - previous[0]) ** 2
                    + (position[1] - previous[1]) ** 2
                ) ** 0.5

                if displacement > 0.05:

                    operation["idle_samples"] = 0

            operation["idle_position"] = position
            operation["idle_samples"] += 1

            if operation["idle_samples"] < 2:
                continue

            reason = (
                "canceled"
                if cancellation_ready
                else "arrived"
            )

            self.parking_operations.pop(rid)

            self.get_logger().info(
                "[PARKING_SETTLED] "
                f"robot={robot_name}, "
                f"reason={reason}, "
                f"queue={self.queued_task_ids[rid]}"
            )

            # Preserve the original charging priority.
            # If a new task is queued, it will be started
            # by _start_next_or_charge.
            self._start_next_or_charge(rid)

            # Do not dispatch a new hospital task here.
            # An API response does not prove Nav2 has stopped.


def main() -> None:

    rclpy.init()

    node = HospitalPpoScheduler()

    try:
        rclpy.spin(
            node
        )

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
