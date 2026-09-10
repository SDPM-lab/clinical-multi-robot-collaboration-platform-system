#!/usr/bin/env python3

import random

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.robot_selection.random_feasible import (
    select_random_robot,
    select_random_feasible_robot,
)

from scheduler_v2.robot_selection.random_feasible import (
    select_random_projected_feasible_robot,
)


# ==========================================================
# Helpers
# ==========================================================

def make_task() -> Task:

    return Task(
        task_id="T001",
        task_type="medicine_delivery",
        source="pharmacy",
        destination="ward_a",
        priority=2,
        required_capabilities={
            "navigation",
            "medicine_delivery",
        },
        created_at=0.0,
    )


def make_robot(
    robot_id: str,
    status: str = "idle",
    battery: float = 0.80,
    capabilities: set[str] | None = None,
    available: bool = True,
    x: float = 0.0,
    y: float = 0.0,
) -> RobotState:

    if capabilities is None:

        capabilities = {
            "navigation",
            "medicine_delivery",
        }

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status=status,
        battery=battery,
        x=x,
        y=y,
        map_name="L1",
        capabilities=capabilities,
        available=available,
    )


# ==========================================================
# Empty Candidates
# ==========================================================

def test_no_candidates_returns_none():

    rng = random.Random(123)

    selected = (
        select_random_robot(
            candidates=[],
            rng=rng,
        )
    )

    assert selected is None


# ==========================================================
# Single Candidate
# ==========================================================

def test_single_candidate_is_selected():

    robot = make_robot(
        "R1"
    )

    rng = random.Random(123)

    selected = (
        select_random_robot(
            candidates=[
                robot,
            ],
            rng=rng,
        )
    )

    assert selected is robot


# ==========================================================
# Reproducibility
# ==========================================================

def test_same_seed_produces_same_sequence():

    robots = [
        make_robot("R1"),
        make_robot("R2"),
        make_robot("R3"),
    ]

    rng_a = random.Random(
        12345
    )

    rng_b = random.Random(
        12345
    )

    sequence_a = [
        select_random_robot(
            candidates=robots,
            rng=rng_a,
        ).robot_id
        for _ in range(20)
    ]

    sequence_b = [
        select_random_robot(
            candidates=robots,
            rng=rng_b,
        ).robot_id
        for _ in range(20)
    ]

    assert (
        sequence_a
        ==
        sequence_b
    )


# ==========================================================
# Candidate Filter Integration
# ==========================================================

def test_random_feasible_only_selects_valid_robot():

    task = make_task()

    valid_robot = make_robot(
        robot_id="R1",
        battery=0.80,
    )

    low_battery_robot = make_robot(
        robot_id="R2",
        battery=0.10,
    )

    wrong_capability_robot = (
        make_robot(
            robot_id="R3",
            capabilities={
                "navigation",
            },
        )
    )

    offline_robot = make_robot(
        robot_id="R4",
        status="offline",
    )

    rng = random.Random(
        123
    )

    for _ in range(20):

        selected = (
            select_random_feasible_robot(
                task=task,
                robots=[
                    valid_robot,
                    low_battery_robot,
                    wrong_capability_robot,
                    offline_robot,
                ],
                rng=rng,
                battery_threshold=0.20,
            )
        )

        assert (
            selected
            is valid_robot
        )


# ==========================================================
# Busy Robot Is Still Eligible
# ==========================================================

def test_busy_robot_can_be_random_candidate():

    task = make_task()

    busy_robot = make_robot(
        robot_id="R1",
        status="busy",
        battery=0.80,
        available=True,
    )

    rng = random.Random(
        123
    )

    selected = (
        select_random_feasible_robot(
            task=task,
            robots=[
                busy_robot,
            ],
            rng=rng,
        )
    )

    assert selected is busy_robot


# ==========================================================
# No Feasible Robot
# ==========================================================

def test_no_feasible_robot_returns_none():

    task = make_task()

    low_battery_robot = make_robot(
        robot_id="R1",
        battery=0.10,
    )

    offline_robot = make_robot(
        robot_id="R2",
        status="offline",
    )

    rng = random.Random(
        123
    )

    selected = (
        select_random_feasible_robot(
            task=task,
            robots=[
                low_battery_robot,
                offline_robot,
            ],
            rng=rng,
            battery_threshold=0.20,
        )
    )

    assert selected is None


# ==========================================================
# Random Does Not Use Distance
# ==========================================================

def test_random_baseline_accepts_near_and_far_robots():

    task = make_task()

    near_robot = make_robot(
        robot_id="NEAR",
        x=1.0,
        y=1.0,
    )

    far_robot = make_robot(
        robot_id="FAR",
        x=1000.0,
        y=1000.0,
    )

    rng = random.Random(
        54321
    )

    selected_ids = {
        select_random_feasible_robot(
            task=task,
            robots=[
                near_robot,
                far_robot,
            ],
            rng=rng,
        ).robot_id
        for _ in range(100)
    }

    # Random Feasible 不會因距離而永久排除 FAR。
    #
    # 固定 seed 下，100 次應可看到兩台 Robot
    # 都曾被選到。
    assert selected_ids == {
        "NEAR",
        "FAR",
    }


def test_random_projected_feasible_respects_battery_projection():

    task = Task(
        task_id="T_PROJECTED_BATTERY",
        task_type="general_delivery",
        source="SOURCE",
        destination="DESTINATION",
        priority=1,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=0.0,
    )

    places = {
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
    }

    unsafe_runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            battery=0.21,
            capabilities={
                "navigation",
                "general_delivery",
            },
        )
    )

    safe_runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            battery=0.80,
            capabilities={
                "navigation",
                "general_delivery",
            },
        )
    )

    selected = (
        select_random_projected_feasible_robot(
            task=task,
            runtimes=[
                unsafe_runtime,
                safe_runtime,
            ],
            places=places,
            current_time=0.0,
            rng=random.Random(0),
            battery_threshold=0.20,
            battery_drain_per_meter=0.001,
        )
    )

    assert selected is not None

    assert (
        selected.robot_id
        ==
        "R2"
    )