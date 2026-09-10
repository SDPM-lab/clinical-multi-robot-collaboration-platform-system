#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
)

from experiment_v2.models import (
    BaselineMethod,
    SimulationScenario,
    TaskExecutionRecord,
    SchedulerDecisionRecord,
    SimulationResult,
)


# ==========================================================
# Helpers
# ==========================================================

def make_task(
    task_id: str = "T001",
    created_at: float = 0.0,
) -> Task:

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source="A",
        destination="B",
        priority=1,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=created_at,
    )


def make_robot(
    robot_id: str = "R1",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status="idle",
        battery=0.80,
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities={
            "navigation",
            "general_delivery",
        },
        available=True,
    )


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
    }


# ==========================================================
# Baseline Method
# ==========================================================

def test_baseline_method_values():

    assert (
        BaselineMethod
        .RANDOM_FEASIBLE
        .value
        ==
        "random_feasible"
    )

    assert (
        BaselineMethod
        .PROJECTED_NEAREST
        .value
        ==
        "projected_nearest"
    )

    assert (
        BaselineMethod
        .WEIGHTED_HEURISTIC
        .value
        ==
        "weighted_heuristic"
    )

    assert (
        BaselineMethod
        .DYNAMIC_WEIGHTED_HEURISTIC
        .value
        ==
        "dynamic_weighted_heuristic"
    )


# ==========================================================
# Scenario
# ==========================================================

def test_valid_scenario():

    scenario = SimulationScenario(
        name="test",
        tasks=[
            make_task(),
        ],
        robots=[
            make_robot(),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=30.0,
    )

    assert scenario.name == "test"

    assert len(
        scenario.tasks
    ) == 1

    assert len(
        scenario.robots
    ) == 1


def test_duplicate_task_id_rejected():

    with pytest.raises(
        ValueError
    ):

        SimulationScenario(
            name="test",
            tasks=[
                make_task("T001"),
                make_task("T001"),
            ],
            robots=[
                make_robot(),
            ],
            places=make_places(),
        )


def test_duplicate_robot_id_rejected():

    with pytest.raises(
        ValueError
    ):

        SimulationScenario(
            name="test",
            tasks=[
                make_task(),
            ],
            robots=[
                make_robot("R1"),
                make_robot("R1"),
            ],
            places=make_places(),
        )


def test_unknown_task_source_rejected():

    task = make_task()

    task.source = "UNKNOWN"

    with pytest.raises(
        ValueError
    ):

        SimulationScenario(
            name="test",
            tasks=[
                task,
            ],
            robots=[
                make_robot(),
            ],
            places=make_places(),
        )


def test_negative_arrival_time_rejected():

    with pytest.raises(
        ValueError
    ):

        SimulationScenario(
            name="test",
            tasks=[
                make_task(
                    created_at=-1.0
                ),
            ],
            robots=[
                make_robot(),
            ],
            places=make_places(),
        )


# ==========================================================
# Task Execution Record
# ==========================================================

def test_task_execution_record_metrics():

    record = TaskExecutionRecord(
        task_id="T001",
        priority=2,
        arrival_time=10.0,
        assigned_robot="R1",
        assigned_at=10.0,
        start_time=20.0,
        completion_time=50.0,
        status="completed",
        travel_distance=15.0,
    )

    assert (
        record.waiting_time
        ==
        10.0
    )

    assert (
        record.completion_duration
        ==
        40.0
    )


def test_unstarted_task_has_no_waiting_time():

    record = TaskExecutionRecord(
        task_id="T001",
        priority=1,
        arrival_time=10.0,
    )

    assert (
        record.waiting_time
        is None
    )


# ==========================================================
# Decision Record
# ==========================================================

def test_negative_decision_time_rejected():

    with pytest.raises(
        ValueError
    ):

        SchedulerDecisionRecord(
            task_id="T001",
            simulation_time=10.0,
            method="random_feasible",
            selected_robot="R1",
            decision_duration_seconds=-0.1,
        )


# ==========================================================
# Simulation Result
# ==========================================================

def test_episode_duration():

    result = SimulationResult(
        scenario_name="test",
        method="random_feasible",
        episode_start_time=0.0,
        episode_end_time=125.0,
    )

    assert (
        result.episode_duration
        ==
        125.0
    )


# ==========================================================
# Dynamic Scheduler Decision
# ==========================================================

def test_assignment_decision_is_not_changed():

    decision = SchedulerDecisionRecord(
        task_id="T1",
        simulation_time=10.0,
        method="weighted_heuristic",
        selected_robot="R1",
        decision_duration_seconds=0.001,
    )

    assert (
        decision.decision_type
        ==
        "assignment"
    )

    assert (
        decision.cascade_depth
        ==
        0
    )

    assert (
        decision.changed
        is False
    )


def test_reassignment_decision_changed():

    decision = SchedulerDecisionRecord(
        task_id="T1",
        simulation_time=20.0,
        method=(
            "dynamic_weighted_heuristic"
        ),
        selected_robot="R2",
        previous_robot="R1",
        decision_duration_seconds=0.001,
        decision_type="reassignment",
        root_event_id="arrival:T2",
        cascade_depth=1,
    )

    assert (
        decision.changed
        is True
    )


def test_reassignment_stay_is_not_changed():

    decision = SchedulerDecisionRecord(
        task_id="T1",
        simulation_time=20.0,
        method=(
            "dynamic_weighted_heuristic"
        ),
        selected_robot="R1",
        previous_robot="R1",
        decision_duration_seconds=0.001,
        decision_type="reassignment",
        root_event_id="arrival:T2",
        cascade_depth=1,
    )

    assert (
        decision.changed
        is False
    )


def test_reassignment_requires_previous_robot():

    with pytest.raises(
        ValueError
    ):

        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=20.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R2",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="arrival:T2",
            cascade_depth=1,
        )


def test_reassignment_requires_root_event():

    with pytest.raises(
        ValueError
    ):

        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=20.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R2",
            previous_robot="R1",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            cascade_depth=1,
        )


def test_reassignment_requires_positive_cascade_depth():

    with pytest.raises(
        ValueError
    ):

        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=20.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R2",
            previous_robot="R1",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="arrival:T2",
            cascade_depth=0,
        )