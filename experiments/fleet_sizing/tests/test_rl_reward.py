from __future__ import annotations

import pytest

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
)

from experiments.fleet_sizing.rl.reward import (
    DEFAULT_REWARD_CONFIG,
    RewardConfig,
    calculate_assignment_reward,
    calculate_waiting_reward,
    get_priority_weight,
    normalize_nonnegative,
)


# ============================================================
# Normalization
# ============================================================


def test_normalize_zero():

    assert (
        normalize_nonnegative(
            0.0,
            600.0,
        )
        == pytest.approx(
            0.0
        )
    )


def test_normalize_half():

    assert (
        normalize_nonnegative(
            300.0,
            600.0,
        )
        == pytest.approx(
            0.5
        )
    )


def test_normalize_is_clipped_to_one():

    assert (
        normalize_nonnegative(
            1200.0,
            600.0,
        )
        == pytest.approx(
            1.0
        )
    )


def test_negative_value_rejected():

    with pytest.raises(
        ValueError
    ):
        normalize_nonnegative(
            -1.0,
            600.0,
        )


def test_nonpositive_scale_rejected():

    with pytest.raises(
        ValueError
    ):
        normalize_nonnegative(
            1.0,
            0.0,
        )


# ============================================================
# Priority Weights
# ============================================================


def test_low_priority_weight():

    assert (
        get_priority_weight(
            PRIORITY_LOW
        )
        == pytest.approx(
            1.0
        )
    )


def test_normal_priority_weight():

    assert (
        get_priority_weight(
            PRIORITY_NORMAL
        )
        == pytest.approx(
            1.5
        )
    )


def test_high_priority_weight():

    assert (
        get_priority_weight(
            PRIORITY_HIGH
        )
        == pytest.approx(
            2.5
        )
    )


def test_emergency_priority_weight():

    assert (
        get_priority_weight(
            PRIORITY_EMERGENCY
        )
        == pytest.approx(
            4.0
        )
    )


def test_priority_weights_are_monotonic():

    values = [
        get_priority_weight(
            PRIORITY_LOW
        ),
        get_priority_weight(
            PRIORITY_NORMAL
        ),
        get_priority_weight(
            PRIORITY_HIGH
        ),
        get_priority_weight(
            PRIORITY_EMERGENCY
        ),
    ]

    assert (
        values
        == sorted(values)
    )


def test_unknown_priority_rejected():

    with pytest.raises(
        ValueError
    ):
        get_priority_weight(
            999
        )


# ============================================================
# Assignment Reward
# ============================================================


def test_zero_assignment_cost_has_zero_reward():

    result = (
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=0.0,
        )
    )

    assert (
        result.total_reward
        == pytest.approx(
            0.0
        )
    )


def test_assignment_reward_is_negative():

    result = (
        calculate_assignment_reward(
            projected_approach_time_s=300.0,
            tasks_ahead_count=2,
            post_assignment_load_imbalance=0.5,
        )
    )

    assert (
        result.total_reward
        < 0.0
    )


def test_more_approach_is_worse():

    near = (
        calculate_assignment_reward(
            projected_approach_time_s=100.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=0.0,
        )
    )

    far = (
        calculate_assignment_reward(
            projected_approach_time_s=500.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=0.0,
        )
    )

    assert (
        far.total_reward
        < near.total_reward
    )


def test_more_tasks_ahead_is_worse():

    low_queue = (
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=1,
            post_assignment_load_imbalance=0.0,
        )
    )

    high_queue = (
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=5,
            post_assignment_load_imbalance=0.0,
        )
    )

    assert (
        high_queue.total_reward
        < low_queue.total_reward
    )


def test_more_imbalance_is_worse():

    balanced = (
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=0.0,
        )
    )

    imbalanced = (
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=1.0,
        )
    )

    assert (
        imbalanced.total_reward
        < balanced.total_reward
    )


def test_invalid_imbalance_rejected():

    with pytest.raises(
        ValueError
    ):
        calculate_assignment_reward(
            projected_approach_time_s=0.0,
            tasks_ahead_count=0,
            post_assignment_load_imbalance=1.5,
        )


# ============================================================
# Waiting Reward
# ============================================================


def test_zero_waiting_has_zero_penalty():

    result = (
        calculate_waiting_reward(
            waiting_time_s=0.0,
            priority=(
                PRIORITY_EMERGENCY
            ),
        )
    )

    assert (
        result.total_reward
        == pytest.approx(
            0.0
        )
    )


def test_more_waiting_is_worse():

    short_wait = (
        calculate_waiting_reward(
            waiting_time_s=60.0,
            priority=(
                PRIORITY_NORMAL
            ),
        )
    )

    long_wait = (
        calculate_waiting_reward(
            waiting_time_s=300.0,
            priority=(
                PRIORITY_NORMAL
            ),
        )
    )

    assert (
        long_wait.total_reward
        < short_wait.total_reward
    )


def test_emergency_waiting_is_penalized_more():

    normal = (
        calculate_waiting_reward(
            waiting_time_s=120.0,
            priority=(
                PRIORITY_NORMAL
            ),
        )
    )

    emergency = (
        calculate_waiting_reward(
            waiting_time_s=120.0,
            priority=(
                PRIORITY_EMERGENCY
            ),
        )
    )

    assert (
        emergency.total_reward
        < normal.total_reward
    )


def test_priority_does_not_affect_assignment_shaping():

    first = (
        calculate_assignment_reward(
            projected_approach_time_s=200.0,
            tasks_ahead_count=2,
            post_assignment_load_imbalance=0.25,
        )
    )

    second = (
        calculate_assignment_reward(
            projected_approach_time_s=200.0,
            tasks_ahead_count=2,
            post_assignment_load_imbalance=0.25,
        )
    )

    assert (
        first
        == second
    )


# ============================================================
# Custom Configuration
# ============================================================


def test_custom_reward_weights_work():

    config = RewardConfig(
        approach_weight=1.0,
        queue_weight=0.0,
        imbalance_weight=0.0,
        waiting_weight=0.0,
    )

    result = (
        calculate_assignment_reward(
            projected_approach_time_s=300.0,
            tasks_ahead_count=9,
            post_assignment_load_imbalance=1.0,
            config=config,
        )
    )

    assert (
        result.total_reward
        == pytest.approx(
            -0.5
        )
    )


def test_default_weights_sum_to_one():

    total = (
        DEFAULT_REWARD_CONFIG
        .approach_weight

        + DEFAULT_REWARD_CONFIG
        .queue_weight

        + DEFAULT_REWARD_CONFIG
        .imbalance_weight

        + DEFAULT_REWARD_CONFIG
        .waiting_weight
    )

    assert (
        total
        == pytest.approx(
            1.0
        )
    )