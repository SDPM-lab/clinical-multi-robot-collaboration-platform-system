#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.candidate_filter import (
    is_robot_operational,
    has_required_capabilities,
    has_safe_battery,
    is_feasible_robot,
    filter_feasible_robots,
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
    robot_id: str = "R1",
    status: str = "idle",
    battery: float = 0.80,
    capabilities: set[str] | None = None,
    available: bool = True,
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
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities=capabilities,
        available=available,
    )


# ==========================================================
# Operational Status
# ==========================================================

def test_idle_robot_is_operational():

    robot = make_robot(
        status="idle"
    )

    assert (
        is_robot_operational(robot)
        is True
    )


def test_busy_robot_is_operational():

    robot = make_robot(
        status="busy"
    )

    assert (
        is_robot_operational(robot)
        is True
    )


@pytest.mark.parametrize(
    "status",
    [
        "charging",
        "error",
        "offline",
    ],
)
def test_non_operational_status_is_rejected(
    status,
):

    robot = make_robot(
        status=status
    )

    assert (
        is_robot_operational(robot)
        is False
    )


# ==========================================================
# Capability
# ==========================================================

def test_robot_with_all_capabilities_matches():

    task = make_task()

    robot = make_robot(
        capabilities={
            "navigation",
            "medicine_delivery",
            "manipulation",
        }
    )

    assert (
        has_required_capabilities(
            task=task,
            robot=robot,
        )
        is True
    )


def test_robot_missing_capability_is_rejected():

    task = make_task()

    robot = make_robot(
        capabilities={
            "navigation",
        }
    )

    assert (
        has_required_capabilities(
            task=task,
            robot=robot,
        )
        is False
    )


# ==========================================================
# Battery
# ==========================================================

def test_robot_above_battery_threshold_is_safe():

    robot = make_robot(
        battery=0.50
    )

    assert (
        has_safe_battery(
            robot=robot,
            battery_threshold=0.20,
        )
        is True
    )


def test_robot_exactly_at_battery_threshold_is_safe():

    robot = make_robot(
        battery=0.20
    )

    assert (
        has_safe_battery(
            robot=robot,
            battery_threshold=0.20,
        )
        is True
    )


def test_robot_below_battery_threshold_is_rejected():

    robot = make_robot(
        battery=0.19
    )

    assert (
        has_safe_battery(
            robot=robot,
            battery_threshold=0.20,
        )
        is False
    )


def test_invalid_battery_threshold():

    robot = make_robot()

    with pytest.raises(
        ValueError
    ):

        has_safe_battery(
            robot=robot,
            battery_threshold=1.20,
        )


# ==========================================================
# Available
# ==========================================================

def test_unavailable_robot_is_not_feasible():

    task = make_task()

    robot = make_robot(
        available=False
    )

    assert (
        is_feasible_robot(
            task=task,
            robot=robot,
        )
        is False
    )


# ==========================================================
# Busy Robot
# ==========================================================

def test_busy_available_robot_can_be_candidate():

    task = make_task()

    robot = make_robot(
        status="busy",
        battery=0.80,
        available=True,
    )

    assert (
        is_feasible_robot(
            task=task,
            robot=robot,
        )
        is True
    )


# ==========================================================
# Full Filter
# ==========================================================

def test_filter_feasible_robots():

    task = make_task()

    valid_idle = make_robot(
        robot_id="R1",
        status="idle",
        battery=0.80,
    )

    valid_busy = make_robot(
        robot_id="R2",
        status="busy",
        battery=0.70,
    )

    low_battery = make_robot(
        robot_id="R3",
        battery=0.10,
    )

    wrong_capability = make_robot(
        robot_id="R4",
        capabilities={
            "navigation",
        },
    )

    charging = make_robot(
        robot_id="R5",
        status="charging",
    )

    unavailable = make_robot(
        robot_id="R6",
        available=False,
    )

    candidates = (
        filter_feasible_robots(
            task=task,
            robots=[
                valid_idle,
                valid_busy,
                low_battery,
                wrong_capability,
                charging,
                unavailable,
            ],
            battery_threshold=0.20,
        )
    )

    assert [
        robot.robot_id
        for robot in candidates
    ] == [
        "R1",
        "R2",
    ]


def test_no_feasible_robot_returns_empty_list():

    task = make_task()

    robot = make_robot(
        battery=0.10
    )

    candidates = (
        filter_feasible_robots(
            task=task,
            robots=[
                robot,
            ],
            battery_threshold=0.20,
        )
    )

    assert candidates == []