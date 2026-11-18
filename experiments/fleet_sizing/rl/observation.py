from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np

from experiments.fleet_sizing.baseline.common import (
    evaluate_feasible_placement_candidates,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Constants
# ============================================================

TASK_TYPES = (
    "waste_transport",
    "clothes_collection",
    "specimen_delivery",
    "medication_delivery",
    "ward_service",
)

SUPPORTED_PRIORITIES = (
    0,  # Low
    1,  # Normal
    2,  # High
    3,  # Emergency
)

# Fixed known hospital navigation locations used by the
# fleet-sizing / scheduling simulator.
LOCATIONS = (
    "charging_station_2",

    "ward_a_2",
    "ward_b_2",

    "consult_1_2",
    "consult_2_2",
    "consult_3_2",

    "nurse_station",
    "blood_draw",

    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",

    "waste_return_2",
    "clothes_return_2",

    "pharmacy",
    "lab",
)

EXPECTED_ROBOT_COUNT = 7

APPROACH_TIME_SCALE_S = 600.0
LOAD_SCALE = 10.0
TASKS_AHEAD_SCALE = 10.0


TravelTimeFunction = Callable[
    [str, str],
    float,
]


# ============================================================
# Observation Layout
# ============================================================


@dataclass(frozen=True)
class ObservationLayout:

    task_type_size: int

    priority_size: int

    source_size: int

    destination_size: int

    robot_feature_size: int

    robot_count: int

    global_feature_size: int

    include_battery_features: bool = False

    @property
    def task_feature_size(
        self,
    ) -> int:

        return (
            self.task_type_size
            + self.priority_size
            + self.source_size
            + self.destination_size
        )

    @property
    def total_size(
        self,
    ) -> int:

        return (
            self.task_feature_size
            + (
                self.robot_feature_size
                * self.robot_count
            )
            + self.global_feature_size
        )


DEFAULT_LAYOUT = ObservationLayout(
    task_type_size=len(
        TASK_TYPES
    ),
    priority_size=len(
        SUPPORTED_PRIORITIES
    ),
    source_size=len(
        LOCATIONS
    ),
    destination_size=len(
        LOCATIONS
    ),
    robot_feature_size=6,
    robot_count=(
        EXPECTED_ROBOT_COUNT
    ),
    global_feature_size=1,
)

BATTERY_LAYOUT = ObservationLayout(
    task_type_size=len(
        TASK_TYPES
    ),
    priority_size=len(
        SUPPORTED_PRIORITIES
    ),
    source_size=len(
        LOCATIONS
    ),
    destination_size=len(
        LOCATIONS
    ),
    robot_feature_size=8,
    robot_count=(
        EXPECTED_ROBOT_COUNT
    ),
    global_feature_size=1,
)

def test_battery_observation_layout_size():

    assert (
        BATTERY_LAYOUT.total_size
        == 98
    )


# ============================================================
# Basic Encoding
# ============================================================


def one_hot(
    value,
    categories: Sequence,
) -> list[float]:

    if value not in categories:

        raise ValueError(
            f"Unsupported value "
            f"{value!r}; expected "
            f"one of {categories!r}"
        )

    return [
        1.0
        if value == category
        else 0.0
        for category in categories
    ]


def normalize_nonnegative(
    value: float,
    scale: float,
) -> float:

    value = float(
        value
    )

    scale = float(
        scale
    )

    if value < 0.0:

        raise ValueError(
            "value must be "
            "non-negative"
        )

    if scale <= 0.0:

        raise ValueError(
            "scale must be positive"
        )

    return min(
        value / scale,
        1.0,
    )


# ============================================================
# Robot State Helpers
# ============================================================


def robot_capability_match(
    robot: RobotState,
    task: TaskState,
) -> float:

    return float(
        task.task_type
        in robot.capabilities
    )


def robot_is_assignable(
    robot: RobotState,
) -> float:

    return float(
        str(
            robot.status
        )
        .strip()
        .lower()
        in {
            "idle",
            "busy",
        }
    )


def robot_is_busy(
    robot: RobotState,
) -> float:

    return float(
        robot.current_task_id
        is not None
    )


def robot_battery_unavailable(
    robot: RobotState,
) -> float:

    return float(
        str(
            robot.status
        )
        .strip()
        .lower()
        in {
            "charging",
            "returning_to_charge",
        }
    )


def observable_load(
    robot: RobotState,
) -> int:

    return (
        int(
            robot.current_task_id
            is not None
        )
        + len(
            robot.queued_task_ids
        )
    )


def calculate_load_imbalance(
    robots: Iterable[
        RobotState
    ],
) -> float:

    loads = [
        float(
            observable_load(
                robot
            )
        )
        for robot in robots
    ]

    if not loads:

        return 0.0

    maximum = max(
        loads
    )

    if maximum <= 0.0:

        return 0.0

    normalized = [
        value / maximum
        for value in loads
    ]

    return (
        max(normalized)
        - min(normalized)
    )


# ============================================================
# Observation Encoder
# ============================================================


class ObservationEncoder:

    def __init__(
        self,
        robot_ids: Sequence[str],
        layout: ObservationLayout = (
            DEFAULT_LAYOUT
        ),
        approach_time_scale_s: float = (
            APPROACH_TIME_SCALE_S
        ),
    ) -> None:

        self.robot_ids = tuple(
            robot_ids
        )

        self.layout = layout

        self.approach_time_scale_s = float(
            approach_time_scale_s
        )

        if self.approach_time_scale_s <= 0.0:
            raise ValueError(
                "approach_time_scale_s must be > 0"
            )

        if (
            len(
                self.robot_ids
            )
            != self.layout.robot_count
        ):

            raise ValueError(
                "ObservationEncoder expects "
                f"{self.layout.robot_count} "
                "robots, got "
                f"{len(self.robot_ids)}"
            )

        if (
            len(
                set(
                    self.robot_ids
                )
            )
            != len(
                self.robot_ids
            )
        ):

            raise ValueError(
                "robot_ids must be unique"
            )

    @property
    def observation_size(
        self,
    ) -> int:

        return (
            self.layout.total_size
        )

    def encode(
        self,
        *,
        task: TaskState,
        robots: Iterable[
            RobotState
        ],
        tasks_by_id: dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn: (
            TravelTimeFunction
        ),
    ) -> np.ndarray:

        robot_list = list(
            robots
        )

        robot_by_id = {
            robot.robot_id:
            robot
            for robot
            in robot_list
        }

        if (
            set(
                robot_by_id
            )
            != set(
                self.robot_ids
            )
        ):

            raise ValueError(
                "Robot set does not match "
                "ObservationEncoder "
                "robot_ids"
            )

        vector: list[
            float
        ] = []

        # ----------------------------------------------------
        # Incoming Task
        # ----------------------------------------------------

        vector.extend(
            one_hot(
                task.task_type,
                TASK_TYPES,
            )
        )

        vector.extend(
            one_hot(
                task.priority,
                SUPPORTED_PRIORITIES,
            )
        )

        vector.extend(
            one_hot(
                task.source,
                LOCATIONS,
            )
        )

        vector.extend(
            one_hot(
                task.destination,
                LOCATIONS,
            )
        )

        # ----------------------------------------------------
        # Duration-free Placement Evaluation
        # ----------------------------------------------------

        evaluations = (
            evaluate_feasible_placement_candidates(
                robots=robot_list,

                task=task,

                tasks_by_id=(
                    tasks_by_id
                ),

                current_time_s=(
                    current_time_s
                ),

                travel_time_fn=(
                    travel_time_fn
                ),
            )
        )

        evaluation_by_robot = {
            evaluation.robot_id:
            evaluation

            for evaluation
            in evaluations
        }

        # ----------------------------------------------------
        # Per-Robot Features
        # ----------------------------------------------------

        for robot_id in (
            self.robot_ids
        ):

            robot = (
                robot_by_id[
                    robot_id
                ]
            )

            evaluation = (
                evaluation_by_robot.get(
                    robot_id
                )
            )

            capability = (
                robot_capability_match(
                    robot,
                    task,
                )
            )

            assignable = (
                robot_is_assignable(
                    robot
                )
            )

            busy = (
                robot_is_busy(
                    robot
                )
            )

            battery_soc = float(
                robot.battery_soc
            )

            battery_unavailable = (
                robot_battery_unavailable(
                    robot
                )
            )

            load = (
                normalize_nonnegative(
                    observable_load(
                        robot
                    ),
                    LOAD_SCALE,
                )
            )

            if (
                evaluation
                is None
            ):

                projected_approach = (
                    0.0
                )

                tasks_ahead = (
                    0.0
                )

            else:

                projected_approach = (
                    normalize_nonnegative(
                        evaluation
                        .projected_approach_time_s,

                        self.approach_time_scale_s,
                    )
                )

                tasks_ahead = (
                    normalize_nonnegative(
                        evaluation
                        .tasks_ahead_count,

                        TASKS_AHEAD_SCALE,
                    )
                )

            robot_features = [
                capability,
                assignable,
                busy,
                load,
                projected_approach,
                tasks_ahead,
            ]

            if (
                self.layout.robot_feature_size
                == 8
            ):

                robot_features.extend(
                    [
                        battery_soc,
                        battery_unavailable,
                    ]
                )

            vector.extend(
                robot_features
            )

        # ----------------------------------------------------
        # Global Feature
        # ----------------------------------------------------

        vector.append(
            calculate_load_imbalance(
                robot_list
            )
        )

        observation = (
            np.asarray(
                vector,
                dtype=np.float32,
            )
        )

        if (
            observation.shape
            != (
                self.observation_size,
            )
        ):

            raise RuntimeError(
                "Unexpected observation "
                f"shape: "
                f"{observation.shape}; "
                "expected "
                f"({self.observation_size},)"
            )

        if not np.all(
            np.isfinite(
                observation
            )
        ):

            raise RuntimeError(
                "Observation contains "
                "non-finite values"
            )

        return observation