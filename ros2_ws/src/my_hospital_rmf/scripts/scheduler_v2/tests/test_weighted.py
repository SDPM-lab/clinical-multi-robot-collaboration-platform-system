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

from scheduler_v2.robot_selection.weighted import (
    normalize_cost,
    validate_weights,
    calculate_weighted_candidate_score,
    score_weighted_candidates,
    select_weighted_feasible_robot,
)


# ==========================================================
# Helpers
# ==========================================================

def make_task(
    task_id: str = "NEW",
    priority: int = 1,
    source: str = "SOURCE",
    destination: str = "DESTINATION",
    created_at: float = 10.0,
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


def make_robot(
    robot_id: str,
    x: float,
    battery: float = 0.80,
    status: str = "idle",
    available: bool = True,
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
        x=x,
        y=0.0,
        map_name="L1",
        capabilities=capabilities,
        available=available,
    )


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
            30.0,
            0.0,
            "L1",
        ),

        "WAIT_SOURCE": Place(
            "WAIT_SOURCE",
            10.0,
            0.0,
            "L1",
        ),

        "WAIT_END": Place(
            "WAIT_END",
            1.0,
            0.0,
            "L1",
        ),
    }


# ==========================================================
# Normalization
# ==========================================================

def test_normalize_cost():

    assert (
        normalize_cost(
            value=25.0,
            reference=50.0,
        )
        ==
        0.5
    )


def test_normalize_cost_is_capped_at_one():

    assert (
        normalize_cost(
            value=100.0,
            reference=50.0,
        )
        ==
        1.0
    )


def test_invalid_normalization_reference():

    with pytest.raises(
        ValueError
    ):

        normalize_cost(
            value=10.0,
            reference=0.0,
        )


# ==========================================================
# Weights
# ==========================================================

def test_valid_weights():

    validate_weights(
        distance_weight=0.50,
        battery_weight=0.30,
        workload_weight=0.20,
    )


def test_invalid_weights_sum():

    with pytest.raises(
        ValueError
    ):

        validate_weights(
            distance_weight=0.50,
            battery_weight=0.30,
            workload_weight=0.30,
        )


# ==========================================================
# Candidate Score
# ==========================================================

def test_weighted_candidate_score():

    task = make_task()

    runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=10.0,
            battery=0.80,
        )
    )

    score = (
        calculate_weighted_candidate_score(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            distance_reference=50.0,
            workload_reference=300.0,
            service_time_seconds=0.0,
        )
    )

    # Distance:
    # 10 / 50 = 0.2
    #
    # Battery:
    # 1 - 0.8 = 0.2
    #
    # Workload:
    # 0
    #
    # Total:
    # 0.5*0.2 + 0.3*0.2 + 0.2*0
    # = 0.16

    assert (
        score.distance_cost
        ==
        pytest.approx(
            0.20
        )
    )

    assert (
        score.battery_cost
        ==
        pytest.approx(
            0.20
        )
    )

    assert (
        score.workload_cost
        ==
        0.0
    )

    assert (
        score.total_cost
        ==
        pytest.approx(
            0.16
        )
    )


# ==========================================================
# Weighted Can Differ From Nearest
# ==========================================================

def test_weighted_can_reject_nearest_due_to_battery_and_workload():

    task = make_task(
        priority=1,
        created_at=10.0,
    )

    # ------------------------------------------------------
    # R1：
    #
    # 最終 projected distance 很近，
    # 但：
    # - battery 很低
    # - 前面 workload 很大
    # ------------------------------------------------------

    waiting_high = make_task(
        task_id="WAIT_HIGH",
        priority=2,
        source="WAIT_SOURCE",
        destination="WAIT_END",
        created_at=0.0,
    )

    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=10.0,
            battery=0.35,
        ),
        waiting_tasks=[
            waiting_high,
        ],
    )

    # ------------------------------------------------------
    # R2：
    #
    # 距離比較遠，
    # 但：
    # - battery 高
    # - 無 workload
    # ------------------------------------------------------

    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=10.0,
            battery=1.0,
        )
    )

    selected = (
        select_weighted_feasible_robot(
            task=task,
            runtimes=[
                runtime_r1,
                runtime_r2,
            ],
            places=make_places(),
            current_time=10.0,

            # R1 Waiting Task 的 service time
            # 故意設大，形成高 workload。
            service_time_seconds=300.0,

            distance_reference=50.0,
            workload_reference=300.0,
        )
    )

    assert selected.robot_id == "R2"


# ==========================================================
# Projected State Is Used
# ==========================================================

def test_weighted_uses_projected_position():

    task = make_task(
        priority=1,
        created_at=10.0,
    )

    waiting_high = make_task(
        task_id="WAIT_HIGH",
        priority=2,
        source="WAIT_SOURCE",
        destination="WAIT_END",
        created_at=0.0,
    )

    runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=20.0,
            battery=0.80,
        ),
        waiting_tasks=[
            waiting_high,
        ],
    )

    score = (
        calculate_weighted_candidate_score(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            service_time_seconds=0.0,
            distance_reference=50.0,
            workload_reference=300.0,
        )
    )

    # Waiting Task 最後到 WAIT_END=(1,0)。
    #
    # 所以 NEW 的 projected position
    # 應該是 (1,0)，而不是目前的 (20,0)。
    assert (
        score.projection.projected_x
        ==
        1.0
    )

    assert (
        score.projection.distance_to_source
        ==
        1.0
    )


# ==========================================================
# Candidate Filter
# ==========================================================

def test_weighted_excludes_infeasible_robot():

    task = make_task()

    invalid_near = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
            battery=0.10,
        )
    )

    valid_far = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=10.0,
            battery=0.80,
        )
    )

    scores = (
        score_weighted_candidates(
            task=task,
            runtimes=[
                invalid_near,
                valid_far,
            ],
            places=make_places(),
            current_time=10.0,
            battery_threshold=0.20,
        )
    )

    assert [
        score.robot.robot_id
        for score in scores
    ] == [
        "R2",
    ]


# ==========================================================
# Tie Break
# ==========================================================

def test_equal_weighted_cost_uses_robot_id():

    task = make_task()

    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=5.0,
            battery=0.80,
        )
    )

    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=-5.0,
            battery=0.80,
        )
    )

    selected = (
        select_weighted_feasible_robot(
            task=task,
            runtimes=[
                runtime_r2,
                runtime_r1,
            ],
            places=make_places(),
            current_time=10.0,
        )
    )

    assert selected.robot_id == "R1"


# ==========================================================
# No Candidate
# ==========================================================

def test_no_feasible_robot_returns_none():

    task = make_task()

    runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
            status="offline",
        )
    )

    selected = (
        select_weighted_feasible_robot(
            task=task,
            runtimes=[
                runtime,
            ],
            places=make_places(),
            current_time=10.0,
        )
    )

    assert selected is None