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

from scheduler_v2.robot_selection.dynamic_weighted import (
    build_reassignment_runtime_views,
    evaluate_dynamic_weighted_reassignment,
    should_reassign,
)


# ==========================================================
# Helpers
# ==========================================================

def make_places():

    return {
        "SOURCE": Place(
            "SOURCE",
            0.0,
            0.0,
            "L1",
        ),

        "DESTINATION": Place(
            "DESTINATION",
            10.0,
            0.0,
            "L1",
        ),
    }


def make_robot(
    robot_id: str,
    battery: float,
    status: str = "idle",
    capabilities: set[str] | None = None,
) -> RobotState:

    if capabilities is None:

        capabilities = {
            "navigation",
            "general_delivery",
        }

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status=status,
        battery=battery,
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities=capabilities,
        available=True,
    )


def make_waiting_task(
    priority: int = 1,
) -> Task:

    return Task(
        task_id="TARGET",
        task_type="general_delivery",
        source="SOURCE",
        destination="DESTINATION",
        priority=priority,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        status="assigned",
        assigned_robot="R1",
        created_at=0.0,
    )


# ==========================================================
# Hysteresis
# ==========================================================

def test_should_reassign_when_improvement_is_large():

    assert (
        should_reassign(
            current_cost=0.50,
            alternative_cost=0.40,
            minimum_improvement=0.05,
        )
        is True
    )


def test_should_not_reassign_at_exact_threshold():

    assert (
        should_reassign(
            current_cost=0.50,
            alternative_cost=0.45,
            minimum_improvement=0.05,
        )
        is False
    )


def test_negative_hysteresis_rejected():

    with pytest.raises(
        ValueError
    ):

        should_reassign(
            current_cost=0.50,
            alternative_cost=0.40,
            minimum_improvement=-0.01,
        )


# ==========================================================
# Runtime View
# ==========================================================

def test_runtime_view_removes_target_without_mutating_original():

    task = make_waiting_task()

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.80,
        ),
        waiting_tasks=[
            task,
        ],
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=0.80,
        )
    )

    views = (
        build_reassignment_runtime_views(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
        )
    )

    # Evaluation view 已移除 TARGET。
    assert all(
        queued.task_id
        !=
        "TARGET"
        for runtime
        in views
        for queued
        in runtime.waiting_tasks
    )

    # 原本 Runtime 不可被修改。
    assert [
        queued.task_id
        for queued
        in r1.waiting_tasks
    ] == [
        "TARGET",
    ]

    assert (
        task.assigned_robot
        ==
        "R1"
    )


# ==========================================================
# Clear Reassignment
# ==========================================================

def test_dynamic_weighted_reassigns_when_improvement_is_large():

    task = make_waiting_task()

    # R1 / R2 距離、workload 都相同。
    #
    # 唯一主要差異：
    # R1 battery = 0.50
    # R2 battery = 1.00
    #
    # Battery Cost：
    #
    # R1 = (1 - .50) * .30 = .15
    # R2 = 0
    #
    # improvement > 0.05
    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.50,
        ),
        waiting_tasks=[
            task,
        ],
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=1.00,
        )
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            minimum_improvement=0.05,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.previous_robot
        ==
        "R1"
    )

    assert (
        result.selected_robot
        ==
        "R2"
    )

    assert (
        result.changed
        is True
    )

    assert (
        result.reason
        ==
        "improved"
    )


# ==========================================================
# Hysteresis Stay
# ==========================================================

def test_dynamic_weighted_stays_when_improvement_is_small():

    task = make_waiting_task()

    # Battery Cost 差：
    #
    # R1 battery .80
    # → .20 * .30 = .06
    #
    # R2 battery .90
    # → .10 * .30 = .03
    #
    # improvement ≈ .03
    #
    # < hysteresis .05
    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.80,
        ),
        waiting_tasks=[
            task,
        ],
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=0.90,
        )
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            minimum_improvement=0.05,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R1"
    )

    assert (
        result.changed
        is False
    )

    assert (
        result.reason
        ==
        "below_hysteresis"
    )


# ==========================================================
# Current Best
# ==========================================================

def test_dynamic_weighted_stays_when_current_is_best():

    task = make_waiting_task()

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=1.00,
        ),
        waiting_tasks=[
            task,
        ],
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=0.60,
        )
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R1"
    )

    assert (
        result.changed
        is False
    )

    assert (
        result.reason
        ==
        "current_best"
    )


# ==========================================================
# Capability Safety
# ==========================================================

def test_dynamic_weighted_excludes_infeasible_alternative():

    task = make_waiting_task()

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.60,
        ),
        waiting_tasks=[
            task,
        ],
    )

    # Battery 很漂亮，
    # 但缺 general_delivery。
    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=1.00,
            capabilities={
                "navigation",
            },
        )
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R1"
    )

    assert (
        result.reason
        ==
        "no_alternative"
    )


# ==========================================================
# Running Task
# ==========================================================

def test_running_task_cannot_be_reassigned():

    task = make_waiting_task()

    task.status = "running"

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.80,
            status="busy",
        ),
        running_task=task,
        running_remaining_time=10.0,
    )

    with pytest.raises(
        ValueError
    ):

        build_reassignment_runtime_views(
            task=task,
            runtimes=[
                r1,
            ],
        )


# ==========================================================
# Current Robot Becomes Infeasible
# ==========================================================

def test_current_infeasible_forces_reassignment():

    task = make_waiting_task()

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.80,
            status="offline",
        ),
        waiting_tasks=[
            task,
        ],
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=0.80,
        )
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R2"
    )

    assert (
        result.changed
        is True
    )

    assert (
        result.current_cost
        is None
    )

    assert (
        result.reason
        ==
        "current_infeasible"
    )


def test_emergency_does_not_move_to_later_start_robot():

    task = make_waiting_task(
        priority=3,
    )

    # ------------------------------------------------------
    # R1：
    #
    # Battery 較差，
    # 所以 Weighted Cost 較高。
    #
    # 但沒有 Running Task，
    # Emergency 可以立即開始。
    # ------------------------------------------------------

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.50,
        ),
        waiting_tasks=[
            task,
        ],
    )

    # ------------------------------------------------------
    # R2：
    #
    # Battery 非常好，
    # Weighted Cost 有機會更低。
    #
    # 但是正在執行不可搶占的 Running Task，
    # 所以 TARGET 必須多等 100 秒。
    # ------------------------------------------------------

    running_task = Task(
        task_id="RUNNING",
        task_type="general_delivery",
        source="SOURCE",
        destination="SOURCE",
        priority=1,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        status="running",
        assigned_robot="R2",
        created_at=0.0,
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=1.00,
            status="busy",
        ),
        running_task=(
            running_task
        ),
        running_remaining_time=100.0,
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            minimum_improvement=0.05,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R1"
    )

    assert (
        result.changed
        is False
    )

    assert (
        result.best_alternative_cost
        <
        result.current_cost
    )

    assert (
        result.improvement
        >
        0.05
    )

    assert (
        result.reason
        ==
        "emergency_start_guard"
    )


def test_emergency_current_infeasible_still_reassigns():

    task = make_waiting_task(
        priority=3,
    )

    r1 = RobotRuntimeState(
        robot=make_robot(
            "R1",
            battery=0.80,
            status="offline",
        ),
        waiting_tasks=[
            task,
        ],
    )

    running_task = Task(
        task_id="RUNNING",
        task_type="general_delivery",
        source="SOURCE",
        destination="DESTINATION",
        priority=1,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        status="running",
        assigned_robot="R2",
        created_at=0.0,
    )

    r2 = RobotRuntimeState(
        robot=make_robot(
            "R2",
            battery=0.80,
            status="busy",
        ),
        running_task=(
            running_task
        ),
        running_remaining_time=100.0,
    )

    result = (
        evaluate_dynamic_weighted_reassignment(
            task=task,
            runtimes=[
                r1,
                r2,
            ],
            places=make_places(),
            current_time=0.0,
            service_time_seconds=0.0,
        )
    )

    assert (
        result.selected_robot
        ==
        "R2"
    )

    assert (
        result.changed
        is True
    )

    assert (
        result.reason
        ==
        "current_infeasible"
    )