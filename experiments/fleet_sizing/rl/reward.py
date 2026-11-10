from __future__ import annotations

from dataclasses import dataclass

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
)


# ============================================================
# Default Reward Configuration
# ============================================================


@dataclass(frozen=True)
class RewardConfig:

    # Assignment-time shaping
    approach_weight: float = 0.30
    queue_weight: float = 0.15
    imbalance_weight: float = 0.05

    # Realized outcome
    waiting_weight: float = 0.50

    # Normalization scales
    approach_scale_s: float = 600.0
    waiting_scale_s: float = 600.0
    tasks_ahead_scale: float = 10.0

    # Priority importance
    low_priority_weight: float = 1.0
    normal_priority_weight: float = 1.5
    high_priority_weight: float = 2.5
    emergency_priority_weight: float = 4.0


DEFAULT_REWARD_CONFIG = RewardConfig()


# ============================================================
# Reward Breakdown
# ============================================================


@dataclass(frozen=True)
class AssignmentRewardBreakdown:

    normalized_approach: float
    normalized_tasks_ahead: float
    load_imbalance: float

    approach_penalty: float
    queue_penalty: float
    imbalance_penalty: float

    total_reward: float


@dataclass(frozen=True)
class WaitingRewardBreakdown:

    waiting_time_s: float
    normalized_waiting: float
    priority_weight: float
    waiting_penalty: float

    total_reward: float


# ============================================================
# Helpers
# ============================================================


def normalize_nonnegative(
    value: float,
    scale: float,
) -> float:

    value = float(value)
    scale = float(scale)

    if value < 0.0:
        raise ValueError(
            "value must be non-negative"
        )

    if scale <= 0.0:
        raise ValueError(
            "scale must be positive"
        )

    return min(
        value / scale,
        1.0,
    )


def validate_unit_interval(
    value: float,
    *,
    name: str,
) -> float:

    value = float(value)

    if not (
        0.0
        <= value
        <= 1.0
    ):
        raise ValueError(
            f"{name} must be in [0, 1]"
        )

    return value


# ============================================================
# Priority
# ============================================================


def get_priority_weight(
    priority: int,
    config: RewardConfig = (
        DEFAULT_REWARD_CONFIG
    ),
) -> float:

    mapping = {
        PRIORITY_LOW:
        config.low_priority_weight,

        PRIORITY_NORMAL:
        config.normal_priority_weight,

        PRIORITY_HIGH:
        config.high_priority_weight,

        PRIORITY_EMERGENCY:
        config.emergency_priority_weight,
    }

    if priority not in mapping:
        raise ValueError(
            f"Unsupported priority: "
            f"{priority}"
        )

    return float(
        mapping[
            priority
        ]
    )


# ============================================================
# Assignment-time Reward
# ============================================================


def calculate_assignment_reward(
    *,
    projected_approach_time_s: float,
    tasks_ahead_count: int,
    post_assignment_load_imbalance: float,
    config: RewardConfig = (
        DEFAULT_REWARD_CONFIG
    ),
) -> AssignmentRewardBreakdown:

    normalized_approach = (
        normalize_nonnegative(
            projected_approach_time_s,
            config.approach_scale_s,
        )
    )

    normalized_tasks_ahead = (
        normalize_nonnegative(
            float(
                tasks_ahead_count
            ),
            config.tasks_ahead_scale,
        )
    )

    load_imbalance = (
        validate_unit_interval(
            post_assignment_load_imbalance,
            name=(
                "post_assignment_load_imbalance"
            ),
        )
    )

    approach_penalty = (
        config.approach_weight
        * normalized_approach
    )

    queue_penalty = (
        config.queue_weight
        * normalized_tasks_ahead
    )

    imbalance_penalty = (
        config.imbalance_weight
        * load_imbalance
    )

    total_reward = -(
        approach_penalty
        + queue_penalty
        + imbalance_penalty
    )

    return AssignmentRewardBreakdown(
        normalized_approach=(
            normalized_approach
        ),

        normalized_tasks_ahead=(
            normalized_tasks_ahead
        ),

        load_imbalance=(
            load_imbalance
        ),

        approach_penalty=(
            approach_penalty
        ),

        queue_penalty=(
            queue_penalty
        ),

        imbalance_penalty=(
            imbalance_penalty
        ),

        total_reward=(
            total_reward
        ),
    )


# ============================================================
# Realized Waiting Reward
# ============================================================


def calculate_waiting_reward(
    *,
    waiting_time_s: float,
    priority: int,
    config: RewardConfig = (
        DEFAULT_REWARD_CONFIG
    ),
) -> WaitingRewardBreakdown:

    normalized_waiting = (
        normalize_nonnegative(
            waiting_time_s,
            config.waiting_scale_s,
        )
    )

    priority_weight = (
        get_priority_weight(
            priority,
            config,
        )
    )

    waiting_penalty = (
        config.waiting_weight
        * normalized_waiting
        * priority_weight
    )

    return WaitingRewardBreakdown(
        waiting_time_s=float(
            waiting_time_s
        ),

        normalized_waiting=(
            normalized_waiting
        ),

        priority_weight=(
            priority_weight
        ),

        waiting_penalty=(
            waiting_penalty
        ),

        total_reward=-(
            waiting_penalty
        ),
    )