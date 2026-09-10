#!/usr/bin/env python3

import pytest

from experiment_v2.models import (
    RobotEpisodeRecord,
    SchedulerDecisionRecord,
    SimulationResult,
    TaskExecutionRecord,
)

from experiment_v2.metrics import (
    calculate_average_waiting_time,
    calculate_waiting_time_by_priority,
    calculate_average_completion_time,
    calculate_makespan,
    calculate_total_travel_distance,
    calculate_task_success_rate,
    calculate_robot_utilization,
    calculate_jain_fairness_index,
    calculate_average_decision_time,
    calculate_max_decision_time,
    calculate_metrics,
    calculate_reassignment_decision_count,
    calculate_reassignment_count,
    calculate_reassignment_rate,
    calculate_average_reassignments_per_task,
    calculate_max_reassignments_per_task,
    calculate_max_cascade_depth,
)


# ==========================================================
# Helper
# ==========================================================

def make_result() -> SimulationResult:

    return SimulationResult(
        scenario_name="metrics_test",
        method="weighted_heuristic",
        episode_start_time=0.0,
        episode_end_time=100.0,

        task_records={
            # ----------------------------------------------
            # T1
            #
            # waiting:
            # 10 - 0 = 10
            #
            # completion:
            # 40 - 0 = 40
            # ----------------------------------------------

            "T1": TaskExecutionRecord(
                task_id="T1",
                priority=0,
                arrival_time=0.0,
                assigned_robot="R1",
                assigned_at=0.0,
                start_time=10.0,
                completion_time=40.0,
                status="completed",
                travel_distance=20.0,
            ),

            # ----------------------------------------------
            # T2
            #
            # waiting:
            # 30 - 10 = 20
            #
            # completion:
            # 70 - 10 = 60
            # ----------------------------------------------

            "T2": TaskExecutionRecord(
                task_id="T2",
                priority=2,
                arrival_time=10.0,
                assigned_robot="R2",
                assigned_at=10.0,
                start_time=30.0,
                completion_time=70.0,
                status="completed",
                travel_distance=30.0,
            ),

            # ----------------------------------------------
            # T3
            #
            # Emergency
            #
            # waiting:
            # 25 - 20 = 5
            #
            # completion:
            # 100 - 20 = 80
            # ----------------------------------------------

            "T3": TaskExecutionRecord(
                task_id="T3",
                priority=3,
                arrival_time=20.0,
                assigned_robot="R1",
                assigned_at=20.0,
                start_time=25.0,
                completion_time=100.0,
                status="completed",
                travel_distance=10.0,
            ),

            # ----------------------------------------------
            # T4
            #
            # Failed，從未開始。
            # 不可把 Waiting Time 當成 0。
            # ----------------------------------------------

            "T4": TaskExecutionRecord(
                task_id="T4",
                priority=1,
                arrival_time=30.0,
                status="failed",
                failure_reason=(
                    "no_feasible_robot"
                ),
            ),
        },

        decision_records=[
            SchedulerDecisionRecord(
                task_id="T1",
                simulation_time=0.0,
                method="weighted_heuristic",
                selected_robot="R1",
                decision_duration_seconds=0.01,
            ),

            SchedulerDecisionRecord(
                task_id="T2",
                simulation_time=10.0,
                method="weighted_heuristic",
                selected_robot="R2",
                decision_duration_seconds=0.02,
            ),

            SchedulerDecisionRecord(
                task_id="T3",
                simulation_time=20.0,
                method="weighted_heuristic",
                selected_robot="R1",
                decision_duration_seconds=0.03,
            ),

            SchedulerDecisionRecord(
                task_id="T4",
                simulation_time=30.0,
                method="weighted_heuristic",
                selected_robot=None,
                decision_duration_seconds=0.04,
            ),
        ],

        robot_records={
            "R1": RobotEpisodeRecord(
                robot_id="R1",
                total_travel_distance=30.0,
                busy_time=60.0,
                completed_tasks=2,
            ),

            "R2": RobotEpisodeRecord(
                robot_id="R2",
                total_travel_distance=30.0,
                busy_time=40.0,
                completed_tasks=1,
            ),
        },
    )


# ==========================================================
# Waiting Time
# ==========================================================

def test_average_waiting_time():

    result = make_result()

    # (10 + 20 + 5) / 3
    assert (
        calculate_average_waiting_time(
            result
        )
        ==
        pytest.approx(
            35.0 / 3.0
        )
    )


def test_waiting_time_by_priority():

    result = make_result()

    values = (
        calculate_waiting_time_by_priority(
            result
        )
    )

    assert values[0] == 10.0

    # Priority 1 只有 failed T4，
    # 沒有真正 start。
    assert values[1] is None

    assert values[2] == 20.0

    assert values[3] == 5.0


# ==========================================================
# Completion Time
# ==========================================================

def test_average_completion_time():

    result = make_result()

    # (40 + 60 + 80) / 3
    assert (
        calculate_average_completion_time(
            result
        )
        ==
        60.0
    )


# ==========================================================
# Makespan
# ==========================================================

def test_makespan():

    result = make_result()

    assert (
        calculate_makespan(
            result
        )
        ==
        100.0
    )


# ==========================================================
# Distance
# ==========================================================

def test_total_travel_distance():

    result = make_result()

    assert (
        calculate_total_travel_distance(
            result
        )
        ==
        60.0
    )


# ==========================================================
# Success Rate
# ==========================================================

def test_task_success_rate():

    result = make_result()

    # 3 completed / 4 total
    assert (
        calculate_task_success_rate(
            result
        )
        ==
        0.75
    )


# ==========================================================
# Utilization
# ==========================================================

def test_robot_utilization():

    result = make_result()

    utilization = (
        calculate_robot_utilization(
            result
        )
    )

    assert (
        utilization["R1"]
        ==
        0.60
    )

    assert (
        utilization["R2"]
        ==
        0.40
    )


# ==========================================================
# Jain's Fairness Index
# ==========================================================

def test_jain_fairness_equal_workload():

    fairness = (
        calculate_jain_fairness_index(
            [
                0.5,
                0.5,
            ]
        )
    )

    assert fairness == 1.0


def test_jain_fairness_unequal_workload():

    fairness = (
        calculate_jain_fairness_index(
            [
                1.0,
                0.0,
            ]
        )
    )

    # (1 + 0)^2
    # -----------
    # 2(1^2+0^2)
    #
    # = 0.5
    assert fairness == 0.5


def test_jain_fairness_all_zero():

    fairness = (
        calculate_jain_fairness_index(
            [
                0.0,
                0.0,
            ]
        )
    )

    assert fairness == 1.0


def test_negative_jain_value_rejected():

    with pytest.raises(
        ValueError
    ):

        calculate_jain_fairness_index(
            [
                0.5,
                -0.1,
            ]
        )


# ==========================================================
# Decision Time
# ==========================================================

def test_decision_time():

    result = make_result()

    assert (
        calculate_average_decision_time(
            result
        )
        ==
        pytest.approx(
            0.025
        )
    )

    assert (
        calculate_max_decision_time(
            result
        )
        ==
        0.04
    )


# ==========================================================
# Failed Tasks
# ==========================================================

def test_failed_task_does_not_fake_zero_waiting_time():

    result = make_result()

    failed = (
        result.task_records[
            "T4"
        ]
    )

    assert (
        failed.waiting_time
        is None
    )

    assert (
        failed.completion_duration
        is None
    )


# ==========================================================
# No Completed Task
# ==========================================================

def test_no_completed_task_has_undefined_time_metrics():

    result = SimulationResult(
        scenario_name="all_failed",
        method="weighted_heuristic",
        episode_start_time=0.0,
        episode_end_time=10.0,

        task_records={
            "T1": TaskExecutionRecord(
                task_id="T1",
                priority=1,
                arrival_time=0.0,
                status="failed",
            ),
        },
    )

    assert (
        calculate_average_waiting_time(
            result
        )
        is None
    )

    assert (
        calculate_average_completion_time(
            result
        )
        is None
    )

    assert (
        calculate_makespan(
            result
        )
        is None
    )

    assert (
        calculate_task_success_rate(
            result
        )
        ==
        0.0
    )


# ==========================================================
# Full Metrics
# ==========================================================

def test_calculate_full_metrics():

    metrics = (
        calculate_metrics(
            make_result()
        )
    )

    assert (
        metrics.total_tasks
        ==
        4
    )

    assert (
        metrics.completed_tasks
        ==
        3
    )

    assert (
        metrics.failed_tasks
        ==
        1
    )

    assert (
        metrics.total_decisions
        ==
        4
    )

    assert (
        metrics.task_success_rate
        ==
        0.75
    )

    assert (
        metrics.total_travel_distance
        ==
        60.0
    )

    assert (
        metrics.average_task_completion_time
        ==
        60.0
    )

    # R1 = 0.6
    # R2 = 0.4
    #
    # Jain:
    #
    # (0.6 + 0.4)^2
    # ----------------
    # 2(0.6² + 0.4²)
    #
    # = 1 / 1.04
    assert (
        metrics.jain_fairness_index
        ==
        pytest.approx(
            1.0 / 1.04
        )
    )


# ==========================================================
# Dynamic Metrics Fixture
# ==========================================================

def make_dynamic_metrics_result():

    task_records = {
        task_id: TaskExecutionRecord(
            task_id=task_id,
            priority=1,
            arrival_time=0.0,
        )
        for task_id
        in [
            "T1",
            "T2",
            "T3",
            "T4",
        ]
    }

    decisions = [
        # Initial Assignment
        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=0.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R1",
            decision_duration_seconds=0.001,
        ),

        # T1: R1 -> R2
        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=10.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R2",
            previous_robot="R1",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="arrival:T2",
            cascade_depth=1,
        ),

        # T1: reevaluated but stays R2
        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=10.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R2",
            previous_robot="R2",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="arrival:T2",
            cascade_depth=2,
        ),

        # T1: R2 -> R3
        SchedulerDecisionRecord(
            task_id="T1",
            simulation_time=20.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R3",
            previous_robot="R2",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="completion:T5",
            cascade_depth=1,
        ),

        # T2: R2 -> R1
        SchedulerDecisionRecord(
            task_id="T2",
            simulation_time=30.0,
            method=(
                "dynamic_weighted_heuristic"
            ),
            selected_robot="R1",
            previous_robot="R2",
            decision_duration_seconds=0.001,
            decision_type="reassignment",
            root_event_id="arrival:T6",
            cascade_depth=1,
        ),
    ]

    return SimulationResult(
        scenario_name="dynamic_metrics",
        method=(
            "dynamic_weighted_heuristic"
        ),
        episode_start_time=0.0,
        episode_end_time=100.0,
        task_records=task_records,
        decision_records=decisions,
        robot_records={},
    )


def test_reassignment_decision_count():

    result = (
        make_dynamic_metrics_result()
    )

    assert (
        calculate_reassignment_decision_count(
            result
        )
        ==
        4
    )


def test_reassignment_count():

    result = (
        make_dynamic_metrics_result()
    )

    # T1:
    # R1 -> R2
    # R2 -> R2  (Stay)
    # R2 -> R3
    #
    # T2:
    # R2 -> R1
    #
    # Actual Changes = 3
    assert (
        calculate_reassignment_count(
            result
        )
        ==
        3
    )


def test_reassignment_rate():

    result = (
        make_dynamic_metrics_result()
    )

    assert (
        calculate_reassignment_rate(
            result
        )
        ==
        pytest.approx(
            3.0 / 4.0
        )
    )


def test_average_and_max_reassignments_per_task():

    result = (
        make_dynamic_metrics_result()
    )

    # 3 actual changes / 4 total tasks
    assert (
        calculate_average_reassignments_per_task(
            result
        )
        ==
        pytest.approx(
            0.75
        )
    )

    # T1 真正換 Robot 2 次。
    assert (
        calculate_max_reassignments_per_task(
            result
        )
        ==
        2
    )


def test_max_cascade_depth():

    result = (
        make_dynamic_metrics_result()
    )

    assert (
        calculate_max_cascade_depth(
            result
        )
        ==
        2
    )


def test_static_result_has_zero_dynamic_metrics():

    result = SimulationResult(
        scenario_name="static",
        method="weighted_heuristic",
        episode_start_time=0.0,
        episode_end_time=10.0,
        task_records={
            "T1": TaskExecutionRecord(
                task_id="T1",
                priority=1,
                arrival_time=0.0,
            ),
        },
        decision_records=[
            SchedulerDecisionRecord(
                task_id="T1",
                simulation_time=0.0,
                method="weighted_heuristic",
                selected_robot="R1",
                decision_duration_seconds=0.001,
            ),
        ],
        robot_records={},
    )

    metrics = (
        calculate_metrics(
            result
        )
    )

    assert (
        metrics
        .reassignment_decision_count
        ==
        0
    )

    assert (
        metrics.reassignment_count
        ==
        0
    )

    assert (
        metrics.reassignment_rate
        ==
        0.0
    )

    assert (
        metrics
        .average_reassignments_per_task
        ==
        0.0
    )

    assert (
        metrics
        .max_reassignments_per_task
        ==
        0
    )

    assert (
        metrics.max_cascade_depth
        ==
        0
    )