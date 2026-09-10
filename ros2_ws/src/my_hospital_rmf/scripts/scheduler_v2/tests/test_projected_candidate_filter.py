#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projected_candidate_filter import (
    calculate_projected_battery_after_queue,
    is_projected_feasible_runtime,
    filter_projected_feasible_runtimes,
)


# ==========================================================
# Helpers
# ==========================================================

def make_places():

    return {
        "A": Place(
            "A",
            0.0,
            0.0,
            "L1",
        ),

        "B": Place(
            "B",
            10.0,
            0.0,
            "L1",
        ),

        "C": Place(
            "C",
            20.0,
            0.0,
            "L1",
        ),

        "D": Place(
            "D",
            30.0,
            0.0,
            "L1",
        ),
    }


def make_robot(
    robot_id: str = "R1",
    battery: float = 0.80,
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status=status,
        battery=battery,
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities={
            "navigation",
            "general_delivery",
        },
        available=True,
    )


def make_task(
    task_id: str,
    priority: int,
    source: str,
    destination: str,
    created_at: float = 0.0,
) -> Task:

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source=source,
        destination=destination,
        priority=priority,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=created_at,
    )


# ==========================================================
# Simple Safe Task
# ==========================================================

def test_projected_task_is_safe():

    runtime = RobotRuntimeState(
        robot=make_robot(
            battery=0.50
        )
    )

    task = make_task(
        task_id="T1",
        priority=1,
        source="A",
        destination="B",
    )

    assert (
        is_projected_feasible_runtime(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
            battery_threshold=0.20,
            battery_drain_per_meter=0.01,
        )
        is True
    )


# ==========================================================
# Current Battery Is Safe But Task Is Not
# ==========================================================

def test_current_battery_safe_but_projected_task_unsafe():

    runtime = RobotRuntimeState(
        robot=make_robot(
            battery=0.25
        )
    )

    task = make_task(
        task_id="T1",
        priority=1,
        source="A",
        destination="B",
    )

    # Current:
    # 0.25 >= 0.20
    #
    # Task:
    # 10m * 0.01 = 0.10
    #
    # After:
    # 0.15 < 0.20
    assert (
        is_projected_feasible_runtime(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
            battery_threshold=0.20,
            battery_drain_per_meter=0.01,
        )
        is False
    )


# ==========================================================
# Exact Threshold
# ==========================================================

def test_projected_battery_exactly_at_threshold_is_safe():

    runtime = RobotRuntimeState(
        robot=make_robot(
            battery=0.30
        )
    )

    task = make_task(
        task_id="T1",
        priority=1,
        source="A",
        destination="B",
    )

    # 0.30 - 0.10 = 0.20
    assert (
        is_projected_feasible_runtime(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
            battery_threshold=0.20,
            battery_drain_per_meter=0.01,
        )
        is True
    )


# ==========================================================
# Whole Queue Safety
# ==========================================================

def test_new_task_cannot_make_existing_queue_unsafe():

    old_low = make_task(
        task_id="LOW",
        priority=0,
        source="B",
        destination="C",
        created_at=0.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=3,
        source="A",
        destination="B",
        created_at=10.0,
    )

    runtime = RobotRuntimeState(
        robot=make_robot(
            battery=0.39
        ),
        waiting_tasks=[
            old_low,
        ],
    )

    # Queue after Priority ordering:
    #
    # EMERGENCY:
    # A -> B = 10m = 0.10
    #
    # LOW:
    # B -> C = 10m = 0.10
    #
    # Emergency 自己做完：
    # 0.39 - 0.10 = 0.29
    # 看起來安全。
    #
    # 但完整 Queue：
    # 0.39 - 0.20 = 0.19
    #
    # 所以不可接受 Emergency
    # 到這台 Robot。
    assert (
        is_projected_feasible_runtime(
            task=emergency,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            battery_threshold=0.20,
            battery_drain_per_meter=0.01,
        )
        is False
    )


# ==========================================================
# Queue Battery Value
# ==========================================================

def test_projected_battery_after_queue():

    first = make_task(
        task_id="T1",
        priority=2,
        source="A",
        destination="B",
    )

    second = make_task(
        task_id="T2",
        priority=1,
        source="B",
        destination="C",
    )

    runtime = RobotRuntimeState(
        robot=make_robot(
            battery=0.80
        ),
        waiting_tasks=[
            first,
        ],
    )

    remaining = (
        calculate_projected_battery_after_queue(
            task=second,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
            battery_drain_per_meter=0.01,
        )
    )

    # A -> B = 10m
    # B -> C = 10m
    #
    # total consumption = 0.20
    assert (
        remaining
        ==
        pytest.approx(
            0.60
        )
    )


# ==========================================================
# Common Candidate Restrictions
# ==========================================================

def test_projected_filter_still_respects_robot_status():

    task = make_task(
        task_id="T1",
        priority=1,
        source="A",
        destination="B",
    )

    valid = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            battery=0.80,
        )
    )

    offline = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            battery=0.80,
            status="offline",
        )
    )

    candidates = (
        filter_projected_feasible_runtimes(
            task=task,
            runtimes=[
                valid,
                offline,
            ],
            places=make_places(),
            current_time=0.0,
            battery_drain_per_meter=0.01,
        )
    )

    assert [
        runtime.robot.robot_id
        for runtime
        in candidates
    ] == [
        "R1",
    ]