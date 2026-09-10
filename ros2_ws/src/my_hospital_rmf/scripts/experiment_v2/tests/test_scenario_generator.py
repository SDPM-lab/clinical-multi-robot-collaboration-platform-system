#!/usr/bin/env python3

import pytest

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)


# ==========================================================
# Reproducibility
# ==========================================================

def test_same_seed_generates_same_scenario():

    scenario_a = (
        generate_hospital_scenario(
            seed=8000,
            task_count=20,
        )
    )

    scenario_b = (
        generate_hospital_scenario(
            seed=8000,
            task_count=20,
        )
    )

    assert (
        scenario_a.tasks
        ==
        scenario_b.tasks
    )

    assert (
        scenario_a.robots
        ==
        scenario_b.robots
    )

    assert (
        scenario_a.places
        ==
        scenario_b.places
    )


def test_different_seed_changes_scenario():

    scenario_a = (
        generate_hospital_scenario(
            seed=8000,
            task_count=20,
        )
    )

    scenario_b = (
        generate_hospital_scenario(
            seed=8001,
            task_count=20,
        )
    )

    assert (
        scenario_a.tasks
        !=
        scenario_b.tasks
        or
        scenario_a.robots
        !=
        scenario_b.robots
    )


# ==========================================================
# Task Count
# ==========================================================

def test_task_count():

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=50,
        )
    )

    assert len(
        scenario.tasks
    ) == 50


# ==========================================================
# Arrival Time
# ==========================================================

def test_task_arrival_times_are_monotonic():

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=50,
        )
    )

    arrival_times = [
        task.created_at
        for task
        in scenario.tasks
    ]

    assert arrival_times == sorted(
        arrival_times
    )

    assert (
        arrival_times[0]
        ==
        0.0
    )


# ==========================================================
# Priority
# ==========================================================

def test_priorities_are_valid():

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=100,
        )
    )

    assert all(
        task.priority
        in {
            0,
            1,
            2,
            3,
        }
        for task
        in scenario.tasks
    )


# ==========================================================
# Places
# ==========================================================

def test_all_task_places_exist():

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=100,
        )
    )

    for task in scenario.tasks:

        assert (
            task.source
            in scenario.places
        )

        assert (
            task.destination
            in scenario.places
        )


# ==========================================================
# Heterogeneous Fleet
# ==========================================================

def test_robot_capabilities_are_heterogeneous():

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=10,
        )
    )

    capability_sets = {
        frozenset(
            robot.capabilities
        )
        for robot
        in scenario.robots
    }

    assert len(
        capability_sets
    ) > 1


# ==========================================================
# Invalid Configuration
# ==========================================================

def test_invalid_task_count():

    with pytest.raises(
        ValueError
    ):

        generate_hospital_scenario(
            seed=8000,
            task_count=-1,
        )


def test_invalid_interarrival_time():

    with pytest.raises(
        ValueError
    ):

        generate_hospital_scenario(
            seed=8000,
            mean_interarrival_seconds=0.0,
        )