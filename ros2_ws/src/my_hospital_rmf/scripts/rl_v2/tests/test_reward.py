#!/usr/bin/env python3

from scheduler_v2.models import Task
from scheduler_v2.runtime import (
    TaskProjection,
)

from rl_v2.reward import (
    bounded_normalize,
    calculate_assignment_reward,
)


def make_task(
    priority: int,
) -> Task:

    return Task(
        task_id="T_TEST",
        task_type="medicine_delivery",
        source="pharmacy",
        destination="ward_a",
        priority=priority,
        required_capabilities={
            "navigation",
            "medicine_delivery",
        },
    )


def make_projection(
    workload: float,
    distance: float,
) -> TaskProjection:

    return TaskProjection(
        robot_id="hospital_robot_1",
        projected_x=0.0,
        projected_y=0.0,
        projected_map_name="L1",
        workload_before_task=workload,
        distance_to_source=distance,
        queue_length_before_task=0,
        task_ids_before=(),
        projected_battery_before_task=0.8,
        expected_task_battery_consumption=0.1,
        projected_battery_after_task=0.7,
    )


def test_bounded_normalize():

    assert bounded_normalize(
        0.0,
        300.0,
    ) == 0.0

    assert 0.0 < bounded_normalize(
        300.0,
        300.0,
    ) < 1.0


def test_more_waiting_is_worse():

    task = make_task(
        priority=1
    )

    short = (
        calculate_assignment_reward(
            task,
            make_projection(
                workload=10.0,
                distance=10.0,
            ),
        )
    )

    long = (
        calculate_assignment_reward(
            task,
            make_projection(
                workload=300.0,
                distance=10.0,
            ),
        )
    )

    assert (
        long.reward
        <
        short.reward
    )


def test_emergency_waiting_is_penalized_more():

    projection = (
        make_projection(
            workload=120.0,
            distance=10.0,
        )
    )

    low = (
        calculate_assignment_reward(
            make_task(priority=0),
            projection,
        )
    )

    emergency = (
        calculate_assignment_reward(
            make_task(priority=3),
            projection,
        )
    )

    assert (
        emergency.reward
        <
        low.reward
    )


def test_more_distance_is_worse():

    task = make_task(
        priority=1
    )

    near = (
        calculate_assignment_reward(
            task,
            make_projection(
                workload=20.0,
                distance=5.0,
            ),
        )
    )

    far = (
        calculate_assignment_reward(
            task,
            make_projection(
                workload=20.0,
                distance=50.0,
            ),
        )
    )

    assert (
        far.reward
        <
        near.reward
    )
