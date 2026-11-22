#!/usr/bin/env python3

from __future__ import annotations

import json
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
        "reward_confirm_sweep27_"
        "w50_a30_q15_i05_"
        "seed7104_200k"
    )
    / "final_model.zip"
)


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

class HospitalPpoScheduler(Node):

    def __init__(self) -> None:

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

        self.model = MaskablePPO.load(
            str(MODEL_PATH),
            device="cpu",
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
            )
        )

        self.mask_builder = (
            ActionMaskBuilder(
                robot_ids=LOGICAL_ROBOT_IDS,
            )
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

        if task_id:
            return "busy"

        # Existing bridge interpretation:
        # mode 1 = charging
        if mode == 1:
            return "charging"

        # Moving without a task remains assignable.
        if mode == 2:
            return "busy"

        return "idle"

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

            if logical_id in self.charging_robots:
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


    def _scheduled_task_tick(
        self,
    ) -> None:

        if not self.pending_scheduled_tasks:
            return

        now = time.time()

        due_task_ids = [
            task_id
            for task_id, payload
            in self.pending_scheduled_tasks.items()
            if float(
                payload.get(
                    "scheduled_at",
                    0.0,
                )
            ) <= now
        ]

        for task_id in due_task_ids:

            payload = (
                self.pending_scheduled_tasks.pop(
                    task_id,
                    None,
                )
            )

            if payload is None:
                continue

            self.get_logger().info(
                "[SCHEDULED_TASK_DUE] "
                f"task={task_id}"
            )

            try:
                self._schedule_task(
                    payload
                )

            except Exception as exc:

                self.get_logger().error(
                    "Scheduled PPO task failed: "
                    f"task={task_id}, "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                self._publish_assignment_result(
                    task_id=task_id,
                    assigned=False,
                )


    def _task_callback(
        self,
        msg: String,
    ) -> None:

        payload = None

        try:

            payload = json.loads(
                msg.data
            )

            task_id = str(
                payload["task_id"]
            )

            scheduled_at = (
                payload.get(
                    "scheduled_at"
                )
            )

            if scheduled_at is not None:

                scheduled_at = float(
                    scheduled_at
                )

                if scheduled_at > time.time():

                    self.pending_scheduled_tasks[
                        task_id
                    ] = payload

                    self.get_logger().info(
                        "[SCHEDULED_TASK_WAITING] "
                        f"task={task_id}, "
                        f"scheduled_at="
                        f"{scheduled_at:.3f}, "
                        f"delay="
                        f"{scheduled_at - time.time():.1f}s"
                    )

                    return

            self._schedule_task(
                payload
            )

        except Exception as exc:

            self.get_logger().error(
                "PPO scheduling failed: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            if isinstance(payload, dict):
                task_id = payload.get(
                    "task_id"
                )

                if task_id:
                    self._publish_assignment_result(
                        task_id=str(task_id),
                        assigned=False,
                    )

    def _schedule_task(
        self,
        payload: dict,
    ) -> None:

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

        if observation.shape != (98,):
            raise RuntimeError(
                "Unexpected PPO observation "
                f"shape: {observation.shape}"
            )

        if mask.shape != (7,):
            raise RuntimeError(
                "Unexpected action mask "
                f"shape: {mask.shape}"
            )

        if not bool(
            np.any(mask)
        ):
            raise RuntimeError(
                "No feasible robot available "
                f"for task {task_id}"
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

        if running_task_id is None:

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
