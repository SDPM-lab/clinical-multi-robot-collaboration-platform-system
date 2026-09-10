#!/usr/bin/env python3

import math

from dataclasses import (
    dataclass,
)

from collections.abc import (
    Iterable,
    Mapping,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
    MIN_BATTERY_LEVEL,
    WEIGHTED_DISTANCE_WEIGHT,
    WEIGHTED_BATTERY_WEIGHT,
    WEIGHTED_WORKLOAD_WEIGHT,
    DISTANCE_NORMALIZATION_REFERENCE,
    WORKLOAD_NORMALIZATION_REFERENCE_SECONDS,
    BATTERY_DRAIN_PER_METER,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
    TaskProjection,
)

from scheduler_v2.projected_candidate_filter import (
    filter_projected_feasible_runtimes,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)


# ==========================================================
# Weighted Candidate Score
# ==========================================================

@dataclass(frozen=True)
class WeightedCandidateScore:
    """
    Weighted Heuristic 對單一 Candidate Robot
    的完整評分結果。

    保留 raw projection 與各項 normalized cost，
    方便：

    - Unit Test
    - Experiment logging
    - Dynamic Reassignment
    - 後續結果分析
    """

    robot: RobotState

    projection: TaskProjection

    distance_cost: float

    battery_cost: float

    workload_cost: float

    total_cost: float


# ==========================================================
# Normalization
# ==========================================================

def normalize_cost(
    value: float,
    reference: float,
) -> float:
    """
    將非負 cost 正規化至 0~1。

    Formula:

        normalized
        =
        min(value / reference, 1.0)

    reference 必須 > 0。
    """

    value = float(
        value
    )

    reference = float(
        reference
    )

    if value < 0.0:

        raise ValueError(
            "cost value cannot be negative"
        )

    if reference <= 0.0:

        raise ValueError(
            "normalization reference "
            "must be greater than 0"
        )

    return min(
        value / reference,
        1.0,
    )


# ==========================================================
# Weight Validation
# ==========================================================

def validate_weights(
    distance_weight: float,
    battery_weight: float,
    workload_weight: float,
) -> None:
    """
    Weighted Heuristic 的三個 weight：

    - 不可為負
    - 總和必須為 1.0
    """

    weights = (
        float(distance_weight),
        float(battery_weight),
        float(workload_weight),
    )

    if any(
        weight < 0.0
        for weight in weights
    ):

        raise ValueError(
            "Weighted heuristic weights "
            "cannot be negative"
        )

    if not math.isclose(
        sum(weights),
        1.0,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):

        raise ValueError(
            "Weighted heuristic weights "
            "must sum to 1.0"
        )


# ==========================================================
# Score One Candidate
# ==========================================================

def calculate_weighted_candidate_score(
    task: Task,
    runtime: RobotRuntimeState,
    places: Mapping[str, Place],
    current_time: float,
    distance_weight: float = (
        WEIGHTED_DISTANCE_WEIGHT
    ),
    battery_weight: float = (
        WEIGHTED_BATTERY_WEIGHT
    ),
    workload_weight: float = (
        WEIGHTED_WORKLOAD_WEIGHT
    ),
    distance_reference: float = (
        DISTANCE_NORMALIZATION_REFERENCE
    ),
    workload_reference: float = (
        WORKLOAD_NORMALIZATION_REFERENCE_SECONDS
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> WeightedCandidateScore:
    """
    計算單一 Candidate Robot 的 Weighted Cost。

    Distance：
        projected position -> task source

    BatteryCost：
        1 - battery

    Workload：
        task 開始前的 workload_before_task
    """

    validate_weights(
        distance_weight=distance_weight,
        battery_weight=battery_weight,
        workload_weight=workload_weight,
    )

    projection = (
        project_task_on_robot(
            task=task,
            runtime=runtime,
            places=places,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            service_time_seconds=(
                service_time_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    distance_cost = (
        normalize_cost(
            value=(
                projection
                .distance_to_source
            ),
            reference=(
                distance_reference
            ),
        )
    )

    # RobotState battery 已經統一為 0~1，
    # 因此 BatteryCost 本身已經正規化。
    battery_cost = (
        1.0
        -
        runtime.robot.battery
    )

    workload_cost = (
        normalize_cost(
            value=(
                projection
                .workload_before_task
            ),
            reference=(
                workload_reference
            ),
        )
    )

    total_cost = (
        distance_weight
        *
        distance_cost
        +
        battery_weight
        *
        battery_cost
        +
        workload_weight
        *
        workload_cost
    )

    return WeightedCandidateScore(
        robot=runtime.robot,
        projection=projection,
        distance_cost=distance_cost,
        battery_cost=battery_cost,
        workload_cost=workload_cost,
        total_cost=total_cost,
    )


# ==========================================================
# Score Feasible Candidates
# ==========================================================

def score_weighted_candidates(
    task: Task,
    runtimes: Iterable[RobotRuntimeState],
    places: Mapping[str, Place],
    current_time: float,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    distance_weight: float = (
        WEIGHTED_DISTANCE_WEIGHT
    ),
    battery_weight: float = (
        WEIGHTED_BATTERY_WEIGHT
    ),
    workload_weight: float = (
        WEIGHTED_WORKLOAD_WEIGHT
    ),
    distance_reference: float = (
        DISTANCE_NORMALIZATION_REFERENCE
    ),
    workload_reference: float = (
        WORKLOAD_NORMALIZATION_REFERENCE_SECONDS
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> list[WeightedCandidateScore]:
    """
    先使用共同 Candidate Filter，
    再對所有合法 Robot 計算 Weighted Cost。
    """

    validate_weights(
        distance_weight=distance_weight,
        battery_weight=battery_weight,
        workload_weight=workload_weight,
    )

    scores = []

    candidate_runtimes = (
        filter_projected_feasible_runtimes(
            task=task,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            battery_threshold=(
                battery_threshold
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    for runtime in candidate_runtimes:

        score = (
            calculate_weighted_candidate_score(
                task=task,
                runtime=runtime,
                places=places,
                current_time=current_time,
                distance_weight=(
                    distance_weight
                ),
                battery_weight=(
                    battery_weight
                ),
                workload_weight=(
                    workload_weight
                ),
                distance_reference=(
                    distance_reference
                ),
                workload_reference=(
                    workload_reference
                ),
                aging_interval_seconds=(
                    aging_interval_seconds
                ),
                service_time_seconds=(
                    service_time_seconds
                ),
                battery_drain_per_meter=(
                    battery_drain_per_meter
                ),
            )
        )

        scores.append(
            score
        )

    return scores


# ==========================================================
# Priority + Weighted Heuristic
# ==========================================================

def select_weighted_feasible_robot(
    task: Task,
    runtimes: Iterable[RobotRuntimeState],
    places: Mapping[str, Place],
    current_time: float,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    distance_weight: float = (
        WEIGHTED_DISTANCE_WEIGHT
    ),
    battery_weight: float = (
        WEIGHTED_BATTERY_WEIGHT
    ),
    workload_weight: float = (
        WEIGHTED_WORKLOAD_WEIGHT
    ),
    distance_reference: float = (
        DISTANCE_NORMALIZATION_REFERENCE
    ),
    workload_reference: float = (
        WORKLOAD_NORMALIZATION_REFERENCE_SECONDS
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
) -> RobotState | None:
    """
    Baseline 2：
    Priority + Weighted Heuristic

    在所有 Feasible Robots 中，
    選擇 Weighted Cost 最低者。

    Cost =
        wd * normalized_distance
        +
        wb * battery_cost
        +
        wl * normalized_workload

    Total Cost 完全相同時：
        robot_id 較小者優先。
    """

    scores = (
        score_weighted_candidates(
            task=task,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            battery_threshold=(
                battery_threshold
            ),
            distance_weight=(
                distance_weight
            ),
            battery_weight=(
                battery_weight
            ),
            workload_weight=(
                workload_weight
            ),
            distance_reference=(
                distance_reference
            ),
            workload_reference=(
                workload_reference
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            service_time_seconds=(
                service_time_seconds
            ),
        )
    )

    if not scores:

        return None

    best_score = min(
        scores,
        key=lambda score: (
            score.total_cost,
            score.robot.robot_id,
        ),
    )

    return best_score.robot