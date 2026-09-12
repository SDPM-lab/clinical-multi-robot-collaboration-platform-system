#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler_v2.models import Task
from scheduler_v2.runtime import TaskProjection


# ==========================================================
# Priority Weights
# ==========================================================

DEFAULT_PRIORITY_WEIGHTS = {
    0: 1.0,   # Low
    1: 2.0,   # Normal
    2: 4.0,   # High
    3: 8.0,   # Emergency
}


# ==========================================================
# Reward Config
# ==========================================================

@dataclass(frozen=True)
class RewardConfig:

    # ----------------------------------------------
    # Objective weights
    # ----------------------------------------------

    waiting_weight: float = 1.0

    distance_weight: float = 0.25

    # ----------------------------------------------
    # Normalization references
    #
    # 不是 hard clipping threshold。
    #
    # x / (x + scale)
    # 會把非負數壓到 [0, 1)。
    # ----------------------------------------------

    waiting_scale_seconds: float = 300.0

    distance_scale_meters: float = 50.0


# ==========================================================
# Reward Components
# ==========================================================

@dataclass(frozen=True)
class RewardBreakdown:

    reward: float

    waiting_cost: float

    distance_cost: float

    normalized_waiting: float

    normalized_distance: float

    priority_weight: float


# ==========================================================
# Helpers
# ==========================================================

def bounded_normalize(
    value: float,
    scale: float,
) -> float:
    """
    將非負數轉成 [0, 1)。

        normalized = value / (value + scale)

    好處：
    - 不需要 hard clipping
    - 極端 workload 不會讓 reward 爆掉
    """

    value = max(
        0.0,
        float(value),
    )

    scale = float(scale)

    if scale <= 0.0:
        raise ValueError(
            "Normalization scale must "
            "be greater than 0"
        )

    return (
        value
        /
        (value + scale)
    )


def get_priority_weight(
    priority: int,
) -> float:

    try:

        return float(
            DEFAULT_PRIORITY_WEIGHTS[
                priority
            ]
        )

    except KeyError as exc:

        raise ValueError(
            "Unknown priority: "
            f"{priority}"
        ) from exc


# ==========================================================
# Assignment Reward
# ==========================================================

def calculate_assignment_reward(
    task: Task,
    projection: TaskProjection,
    config: RewardConfig = RewardConfig(),
) -> RewardBreakdown:
    """
    RL Initial Assignment Reward。

    目前只優化：

    1. Priority-aware projected waiting
    2. Distance to task source

    Capability / Battery Safety
    已由 Action Mask 作為 hard constraint，
    因此不重複放進 Reward。
    """

    normalized_waiting = (
        bounded_normalize(
            projection
            .workload_before_task,
            config
            .waiting_scale_seconds,
        )
    )

    normalized_distance = (
        bounded_normalize(
            projection
            .distance_to_source,
            config
            .distance_scale_meters,
        )
    )

    priority_weight = (
        get_priority_weight(
            task.priority
        )
    )

    waiting_cost = (
        config.waiting_weight
        *
        priority_weight
        *
        normalized_waiting
    )

    distance_cost = (
        config.distance_weight
        *
        normalized_distance
    )

    reward = -(
        waiting_cost
        +
        distance_cost
    )

    return RewardBreakdown(
        reward=float(reward),

        waiting_cost=float(
            waiting_cost
        ),

        distance_cost=float(
            distance_cost
        ),

        normalized_waiting=float(
            normalized_waiting
        ),

        normalized_distance=float(
            normalized_distance
        ),

        priority_weight=float(
            priority_weight
        ),
    )
