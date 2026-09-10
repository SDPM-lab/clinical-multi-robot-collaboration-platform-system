#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)


# ==========================================================
# Task Model
# ==========================================================

def test_task_model():

    task = Task(
        task_id="T001",
        task_type="medicine_delivery",
        source="pharmacy",
        destination="ward_a",
        priority=2,
        required_capabilities=[
            "navigation",
            "medicine_delivery",
        ],
        created_at=10.0,
    )

    assert task.task_id == "T001"

    assert (
        task.priority
        ==
        2
    )

    assert (
        task.status
        ==
        "pending"
    )

    assert (
        task.required_capabilities
        ==
        {
            "navigation",
            "medicine_delivery",
        }
    )

    assert (
        task.created_at
        ==
        10.0
    )


# ==========================================================
# Invalid Priority
# ==========================================================

def test_invalid_task_priority():

    with pytest.raises(
        ValueError
    ):

        Task(
            task_id="T001",
            task_type="general_delivery",
            source="storage",
            destination="ward_a",
            priority=4,
        )


# ==========================================================
# Robot Model
# ==========================================================

def test_robot_model():

    robot = RobotState(
        robot_id="hospital_robot_1",
        fleet_name="hospital_fleet",
        status="idle",
        battery=0.80,
        x=10.0,
        y=20.0,
        map_name="L1",
        capabilities=[
            "navigation",
            "medicine_delivery",
        ],
    )

    assert (
        robot.robot_id
        ==
        "hospital_robot_1"
    )

    assert (
        robot.status
        ==
        "idle"
    )

    assert (
        robot.battery
        ==
        0.80
    )

    assert (
        robot.capabilities
        ==
        {
            "navigation",
            "medicine_delivery",
        }
    )


# ==========================================================
# Busy Robot Can Still Be Available
# ==========================================================

def test_busy_robot_can_still_be_available():

    robot = RobotState(
        robot_id="hospital_robot_1",
        fleet_name="hospital_fleet",
        status="busy",
        battery=0.75,
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities={
            "navigation",
        },
        current_task="T001",
        available=True,
    )

    assert (
        robot.status
        ==
        "busy"
    )

    assert (
        robot.available
        is True
    )

    assert (
        robot.current_task
        ==
        "T001"
    )


# ==========================================================
# Invalid Battery
# ==========================================================

def test_invalid_robot_battery():

    with pytest.raises(
        ValueError
    ):

        RobotState(
            robot_id="hospital_robot_1",
            fleet_name="hospital_fleet",
            status="idle",
            battery=1.20,
            x=0.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
            },
        )