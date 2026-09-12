#!/usr/bin/env python3

import numpy as np

from scheduler_v2.runtime import (
    TaskProjection,
)

from rl_v2.reassignment_shaping import (
    ReassignmentShapingConfig,
    calculate_reassignment_shaping,
)


def make_projection(
    robot_id: str,
    workload: float,
    distance: float,
):

    return TaskProjection(
        robot_id=robot_id,

        projected_x=0.0,
        projected_y=0.0,
        projected_map_name="L1",

        workload_before_task=(
            workload
        ),

        distance_to_source=(
            distance
        ),

        queue_length_before_task=0,

        task_ids_before=(),

        projected_battery_before_task=1.0,

        expected_task_battery_consumption=0.0,

        projected_battery_after_task=1.0,
    )


# ==========================================================
# Stay
# ==========================================================

def test_stay_has_zero_shaping():

    current = make_projection(
        robot_id="R1",
        workload=120.0,
        distance=10.0,
    )

    selected = make_projection(
        robot_id="R1",
        workload=120.0,
        distance=10.0,
    )

    result = (
        calculate_reassignment_shaping(
            priority=1,
            current_projection=current,
            selected_projection=selected,
        )
    )

    assert np.isclose(
        result.shaping_reward,
        0.0,
    )

    assert np.isclose(
        result.raw_improvement,
        0.0,
    )


# ==========================================================
# Better Robot
# ==========================================================

def test_better_robot_has_positive_shaping():

    current = make_projection(
        robot_id="R1",
        workload=180.0,
        distance=20.0,
    )

    selected = make_projection(
        robot_id="R2",
        workload=60.0,
        distance=10.0,
    )

    result = (
        calculate_reassignment_shaping(
            priority=1,
            current_projection=current,
            selected_projection=selected,
        )
    )

    assert (
        result.raw_improvement
        >
        0.0
    )

    assert (
        result.shaping_reward
        >
        0.0
    )


# ==========================================================
# Worse Robot
# ==========================================================

def test_worse_robot_has_negative_shaping():

    current = make_projection(
        robot_id="R1",
        workload=60.0,
        distance=10.0,
    )

    selected = make_projection(
        robot_id="R2",
        workload=180.0,
        distance=20.0,
    )

    result = (
        calculate_reassignment_shaping(
            priority=1,
            current_projection=current,
            selected_projection=selected,
        )
    )

    assert (
        result.raw_improvement
        <
        0.0
    )

    assert (
        result.shaping_reward
        <
        0.0
    )


# ==========================================================
# Priority Effect
# ==========================================================

def test_emergency_waiting_improvement_is_stronger_than_low():

    current = make_projection(
        robot_id="R1",
        workload=180.0,
        distance=10.0,
    )

    selected = make_projection(
        robot_id="R2",
        workload=60.0,
        distance=10.0,
    )

    low = (
        calculate_reassignment_shaping(
            priority=0,
            current_projection=current,
            selected_projection=selected,
        )
    )

    emergency = (
        calculate_reassignment_shaping(
            priority=3,
            current_projection=current,
            selected_projection=selected,
        )
    )

    assert (
        emergency.shaping_reward
        >
        low.shaping_reward
    )

    assert (
        emergency.raw_improvement
        >
        low.raw_improvement
    )


# ==========================================================
# Default Weight
# ==========================================================

def test_default_shaping_weight_is_quarter():

    current = make_projection(
        robot_id="R1",
        workload=300.0,
        distance=0.0,
    )

    selected = make_projection(
        robot_id="R2",
        workload=0.0,
        distance=0.0,
    )

    result = (
        calculate_reassignment_shaping(
            priority=0,
            current_projection=current,
            selected_projection=selected,
            config=(
                ReassignmentShapingConfig(
                    shaping_weight=0.25,
                )
            ),
        )
    )

    # Low Priority weight = 1
    #
    # current cost:
    #     300 / 300 = 1
    #
    # selected cost:
    #     0
    #
    # improvement:
    #     1
    #
    # shaping:
    #     0.25 * 1 = 0.25

    assert np.isclose(
        result.raw_improvement,
        1.0,
    )

    assert np.isclose(
        result.shaping_reward,
        0.25,
    )
