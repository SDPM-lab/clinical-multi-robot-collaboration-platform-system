#!/usr/bin/env python3

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemRewardConfig:

    waiting_weight: float = 1.0
    distance_weight: float = 0.25

    waiting_scale: float = 300.0
    distance_scale: float = 50.0

    failure_penalty: float = 10.0

    # 只有真正發生 Robot migration 才扣。
    # Stay 不扣。
    reassignment_penalty: float = 0.0


@dataclass(frozen=True)
class SystemRewardBreakdown:

    reward: float

    weighted_waiting_delta: float
    travel_distance_delta: float
    failed_task_delta: int
    reassignment_delta: int

    waiting_cost: float
    distance_cost: float
    failure_cost: float
    reassignment_cost: float


def calculate_system_reward(
    weighted_waiting_delta: float,
    travel_distance_delta: float,
    failed_task_delta: int,
    reassignment_delta: int = 0,
    config: SystemRewardConfig = SystemRewardConfig(),
) -> SystemRewardBreakdown:
    """
    計算兩次 RL Decision 之間
    系統真正產生的成本。

    Reward =
        - priority-weighted actual waiting cost
        - actual travel distance cost
        - failed task penalty
        - actual reassignment penalty

    注意：
    - 不使用 projected waiting
    - Stay 的 reassignment_delta = 0
    - 真正 Robot migration 的 reassignment_delta = 1
    """

    weighted_waiting_delta = float(
        weighted_waiting_delta
    )

    travel_distance_delta = float(
        travel_distance_delta
    )

    failed_task_delta = int(
        failed_task_delta
    )

    reassignment_delta = int(
        reassignment_delta
    )

    # ======================================================
    # Validation
    # ======================================================

    if weighted_waiting_delta < 0.0:

        raise ValueError(
            "weighted_waiting_delta "
            "cannot be negative"
        )

    if travel_distance_delta < 0.0:

        raise ValueError(
            "travel_distance_delta "
            "cannot be negative"
        )

    if failed_task_delta < 0:

        raise ValueError(
            "failed_task_delta "
            "cannot be negative"
        )

    if reassignment_delta < 0:

        raise ValueError(
            "reassignment_delta "
            "cannot be negative"
        )

    if config.waiting_scale <= 0.0:

        raise ValueError(
            "waiting_scale must be > 0"
        )

    if config.distance_scale <= 0.0:

        raise ValueError(
            "distance_scale must be > 0"
        )

    if config.reassignment_penalty < 0.0:

        raise ValueError(
            "reassignment_penalty "
            "cannot be negative"
        )

    # ======================================================
    # Cost Components
    # ======================================================

    waiting_cost = (
        config.waiting_weight
        *
        weighted_waiting_delta
        /
        config.waiting_scale
    )

    distance_cost = (
        config.distance_weight
        *
        travel_distance_delta
        /
        config.distance_scale
    )

    failure_cost = (
        config.failure_penalty
        *
        failed_task_delta
    )

    reassignment_cost = (
        config.reassignment_penalty
        *
        reassignment_delta
    )

    # ======================================================
    # Reward
    # ======================================================

    reward = -(
        waiting_cost
        +
        distance_cost
        +
        failure_cost
        +
        reassignment_cost
    )

    return SystemRewardBreakdown(
        reward=float(
            reward
        ),

        weighted_waiting_delta=(
            weighted_waiting_delta
        ),

        travel_distance_delta=(
            travel_distance_delta
        ),

        failed_task_delta=(
            failed_task_delta
        ),

        reassignment_delta=(
            reassignment_delta
        ),

        waiting_cost=float(
            waiting_cost
        ),

        distance_cost=float(
            distance_cost
        ),

        failure_cost=float(
            failure_cost
        ),

        reassignment_cost=float(
            reassignment_cost
        ),
    )
