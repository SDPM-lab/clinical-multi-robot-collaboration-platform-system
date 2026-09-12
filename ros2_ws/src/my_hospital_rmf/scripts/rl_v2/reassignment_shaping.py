#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler_v2.runtime import (
    TaskProjection,
)

from rl_v2.reward import (
    get_priority_weight,
)


# ==========================================================
# Configuration
# ==========================================================

@dataclass(frozen=True)
class ReassignmentShapingConfig:

    # ------------------------------------------------------
    # Projected Waiting
    #
    # 與目前 Long-Horizon Reward
    # 使用相同 300 秒 normalization。
    # ------------------------------------------------------

    waiting_scale: float = 300.0

    # ------------------------------------------------------
    # Projected Distance
    #
    # 與目前 System Reward：
    #
    # distance_weight = 0.25
    # distance_scale  = 50
    #
    # 保持相同語意。
    # ------------------------------------------------------

    distance_weight: float = 0.25
    distance_scale: float = 50.0

    # ------------------------------------------------------
    # Shaping Weight
    #
    # Shaping 只負責提供 immediate learning signal。
    # 真正的 Long-Horizon System Reward
    # 仍然是主要目標。
    # ------------------------------------------------------

    shaping_weight: float = 0.25


# ==========================================================
# Breakdown
# ==========================================================

@dataclass(frozen=True)
class ReassignmentShapingBreakdown:

    current_projected_cost: float

    selected_projected_cost: float

    raw_improvement: float

    shaping_reward: float


# ==========================================================
# Projected Cost
# ==========================================================

def calculate_projected_task_cost(
    priority: int,
    projection: TaskProjection,
    config: (
        ReassignmentShapingConfig
    ) = ReassignmentShapingConfig(),
) -> float:
    """
    計算某 Task 如果留在 / 移到指定 Robot，
    預估需要承擔的局部成本。

    ProjectedCost =
        priority_weight
        * projected_waiting / 300

        +

        0.25
        * distance_to_source / 50

    注意：

    workload_before_task：
        Task 真正開始執行以前，
        預估還要等待的 workload。

    distance_to_source：
        輪到 Task 時，
        Robot projected position
        到 Task source 的距離。
    """

    if config.waiting_scale <= 0.0:

        raise ValueError(
            "waiting_scale must be > 0"
        )

    if config.distance_scale <= 0.0:

        raise ValueError(
            "distance_scale must be > 0"
        )

    if config.distance_weight < 0.0:

        raise ValueError(
            "distance_weight cannot be negative"
        )

    if config.shaping_weight < 0.0:

        raise ValueError(
            "shaping_weight cannot be negative"
        )

    priority_weight = (
        get_priority_weight(
            priority
        )
    )

    waiting_cost = (
        priority_weight
        *
        projection.workload_before_task
        /
        config.waiting_scale
    )

    distance_cost = (
        config.distance_weight
        *
        projection.distance_to_source
        /
        config.distance_scale
    )

    return float(
        waiting_cost
        +
        distance_cost
    )


# ==========================================================
# Reassignment Improvement
# ==========================================================

def calculate_reassignment_shaping(
    priority: int,
    current_projection: TaskProjection,
    selected_projection: TaskProjection,
    config: (
        ReassignmentShapingConfig
    ) = ReassignmentShapingConfig(),
) -> ReassignmentShapingBreakdown:
    """
    Immediate projected-improvement shaping。

    若 Stay：
        shaping = 0

    若 Reassign：

        improvement =
            current projected cost
            -
            selected projected cost

    因此：

        新 Robot 比較好
            -> improvement > 0

        新 Robot 比較差
            -> improvement < 0

    最後：

        shaping_reward =
            shaping_weight
            * improvement
    """

    current_cost = (
        calculate_projected_task_cost(
            priority=priority,
            projection=(
                current_projection
            ),
            config=config,
        )
    )

    selected_cost = (
        calculate_projected_task_cost(
            priority=priority,
            projection=(
                selected_projection
            ),
            config=config,
        )
    )

    # ------------------------------------------------------
    # Stay
    #
    # 不管浮點 projection 是否有微小誤差，
    # 同 Robot 就定義成 0。
    # ------------------------------------------------------

    if (
        current_projection.robot_id
        ==
        selected_projection.robot_id
    ):

        raw_improvement = 0.0
        shaping_reward = 0.0

    else:

        raw_improvement = (
            current_cost
            -
            selected_cost
        )

        shaping_reward = (
            config.shaping_weight
            *
            raw_improvement
        )

    return (
        ReassignmentShapingBreakdown(
            current_projected_cost=(
                float(
                    current_cost
                )
            ),

            selected_projected_cost=(
                float(
                    selected_cost
                )
            ),

            raw_improvement=(
                float(
                    raw_improvement
                )
            ),

            shaping_reward=(
                float(
                    shaping_reward
                )
            ),
        )
    )
