from __future__ import annotations

from copy import deepcopy

import pytest

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Helpers
# ============================================================


def make_task(
    task_id: str,
    task_type: str = "medication_delivery",
    source: str = "pharmacy",
    destination: str = "ward_a",
    priority: int = 1,
    arrival_time_s: float = 0.0,
    service_time_s: float = 60.0,
) -> TaskState:

    return TaskState(
        task_id=task_id,
        task_type=task_type,
        source=source,
        destination=destination,
        priority=priority,
        arrival_time_s=arrival_time_s,
        service_time_s=service_time_s,
    )


def make_medical_robot(
    robot_id: str,
    current_location: str = "pharmacy",
    status: str = "idle",
    current_task_id: str | None = None,
    current_task_destination: str | None = None,
    current_task_completion_time_s: float | None = None,
    queued_task_ids: list[str] | None = None,
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type="medical",
        capabilities={
            "medication_delivery",
            "specimen_delivery",
        },
        current_location=current_location,
        status=status,
        current_task_id=current_task_id,
        current_task_completion_time_s=(
            current_task_completion_time_s
        ),
        current_task_destination=(
            current_task_destination
        ),
        queued_task_ids=list(
            queued_task_ids or []
        ),
    )


def make_ward_robot(
    robot_id: str,
    current_location: str = "ward_a",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type="ward",
        capabilities={
            "medication_delivery",
            "ward_service",
        },
        current_location=current_location,
        status=status,
    )


def make_clean_robot(
    robot_id: str,
    current_location: str = "utility_room",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type="clean",
        capabilities={
            "waste_transport",
            "clothes_collection",
        },
        current_location=current_location,
        status=status,
    )


def simple_travel_time(
    origin: str,
    destination: str,
) -> float:

    if origin == destination:
        return 0.0

    distances = {
        ("pharmacy", "ward_a"): 10.0,
        ("ward_a", "pharmacy"): 10.0,

        ("lab", "pharmacy"): 20.0,
        ("pharmacy", "lab"): 20.0,

        ("ward_b", "pharmacy"): 40.0,
        ("pharmacy", "ward_b"): 40.0,

        ("charging_station", "pharmacy"): 60.0,
        ("pharmacy", "charging_station"): 60.0,

        ("ward_a", "ward_b"): 15.0,
        ("ward_b", "ward_a"): 15.0,

        ("lab", "ward_a"): 25.0,
        ("ward_a", "lab"): 25.0,

        ("lab", "ward_b"): 30.0,
        ("ward_b", "lab"): 30.0,
    }

    return distances.get(
        (origin, destination),
        20.0,
    )


# ============================================================
# Basic Configuration
# ============================================================


def test_scheduler_name():

    scheduler = (
        DynamicWeightedScheduler()
    )

    assert (
        scheduler.NAME
        == "dynamic_weighted"
    )


def test_default_alpha_range():

    scheduler = DynamicWeightedScheduler()

    assert (
        scheduler.alpha_min
        == pytest.approx(0.4)
    )

    assert (
        scheduler.alpha_max
        == pytest.approx(0.8)
    )


def test_custom_alpha_range_is_stored():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.9,
        )
    )

    assert (
        scheduler.alpha_min
        == pytest.approx(0.4)
    )

    assert (
        scheduler.alpha_max
        == pytest.approx(0.9)
    )


@pytest.mark.parametrize(
    "alpha_min,alpha_max",
    [
        (-0.1, 0.7),
        (0.2, 1.1),
        (0.8, 0.5),
        (-1.0, 2.0),
    ],
)
def test_invalid_alpha_range_raises(
    alpha_min,
    alpha_max,
):

    with pytest.raises(
        ValueError
    ):

        DynamicWeightedScheduler(
            alpha_min=alpha_min,
            alpha_max=alpha_max,
        )


# ============================================================
# Observable Load
# ============================================================


def test_idle_robot_with_empty_queue_has_zero_load():

    robot = make_medical_robot(
        "M01"
    )

    assert (
        DynamicWeightedScheduler
        .get_observable_load(robot)
        == 0
    )


def test_busy_robot_with_empty_queue_has_load_one():

    robot = make_medical_robot(
        "M01",
        status="busy",
        current_task_id="ACTIVE",
        current_task_destination="ward_a",
        current_task_completion_time_s=100.0,
    )

    assert (
        DynamicWeightedScheduler
        .get_observable_load(robot)
        == 1
    )


def test_busy_robot_with_two_queued_tasks_has_load_three():

    robot = make_medical_robot(
        "M01",
        status="busy",
        current_task_id="ACTIVE",
        current_task_destination="ward_a",
        current_task_completion_time_s=100.0,
        queued_task_ids=[
            "Q1",
            "Q2",
        ],
    )

    assert (
        DynamicWeightedScheduler
        .get_observable_load(robot)
        == 3
    )


# ============================================================
# Normalization
# ============================================================


def test_normalize_by_max():

    result = (
        DynamicWeightedScheduler
        .normalize_by_max(
            2.0,
            4.0,
        )
    )

    assert (
        result
        == pytest.approx(0.5)
    )


def test_normalize_zero_max_returns_zero():

    result = (
        DynamicWeightedScheduler
        .normalize_by_max(
            0.0,
            0.0,
        )
    )

    assert (
        result
        == pytest.approx(0.0)
    )


def test_negative_normalization_raises():

    with pytest.raises(
        ValueError
    ):

        (
            DynamicWeightedScheduler
            .normalize_by_max(
                -1.0,
                5.0,
            )
        )


# ============================================================
# Load Imbalance
# ============================================================


def test_balanced_load_has_zero_imbalance():

    imbalance = (
        DynamicWeightedScheduler
        .calculate_load_imbalance(
            [
                1.0,
                1.0,
                1.0,
            ]
        )
    )

    assert (
        imbalance
        == pytest.approx(0.0)
    )


def test_maximally_imbalanced_load_has_one():

    imbalance = (
        DynamicWeightedScheduler
        .calculate_load_imbalance(
            [
                1.0,
                0.0,
                0.0,
            ]
        )
    )

    assert (
        imbalance
        == pytest.approx(1.0)
    )


def test_partial_load_imbalance():

    imbalance = (
        DynamicWeightedScheduler
        .calculate_load_imbalance(
            [
                1.0,
                0.5,
                0.25,
            ]
        )
    )

    assert (
        imbalance
        == pytest.approx(0.75)
    )


def test_empty_load_list_has_zero_imbalance():

    imbalance = (
        DynamicWeightedScheduler
        .calculate_load_imbalance(
            []
        )
    )

    assert (
        imbalance
        == pytest.approx(0.0)
    )


def test_invalid_normalized_load_raises():

    with pytest.raises(
        ValueError
    ):

        (
            DynamicWeightedScheduler
            .calculate_load_imbalance(
                [
                    0.0,
                    1.2,
                ]
            )
        )


# ============================================================
# Dynamic Alpha
# ============================================================


def test_zero_imbalance_uses_alpha_max():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    alpha = (
        scheduler
        .calculate_dynamic_alpha(
            0.0
        )
    )

    assert (
        alpha
        == pytest.approx(0.8)
    )


def test_full_imbalance_uses_alpha_min():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    alpha = (
        scheduler
        .calculate_dynamic_alpha(
            1.0
        )
    )

    assert (
        alpha
        == pytest.approx(0.4)
    )


def test_half_imbalance_uses_midpoint_alpha():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    alpha = (
        scheduler
        .calculate_dynamic_alpha(
            0.5
        )
    )

    assert (
        alpha
        == pytest.approx(0.6)
    )


def test_alpha_decreases_when_imbalance_increases():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    low_imbalance_alpha = (
        scheduler
        .calculate_dynamic_alpha(
            0.2
        )
    )

    high_imbalance_alpha = (
        scheduler
        .calculate_dynamic_alpha(
            0.8
        )
    )

    assert (
        high_imbalance_alpha
        <
        low_imbalance_alpha
    )


# ============================================================
# Capability / Availability
# ============================================================


def test_medication_candidates_include_medical_and_ward():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1",
        task_type="medication_delivery",
    )

    robots = [
        make_medical_robot(
            "M01"
        ),
        make_ward_robot(
            "W01"
        ),
        make_clean_robot(
            "C01"
        ),
    ]

    candidates, _, _ = (
        scheduler.build_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    robot_ids = {
        candidate.robot_id
        for candidate
        in candidates
    }

    assert robot_ids == {
        "M01",
        "W01",
    }


def test_specimen_only_medical_is_candidate():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1",
        task_type="specimen_delivery",
        source="lab",
        destination="ward_a",
    )

    robots = [
        make_medical_robot(
            "M01"
        ),
        make_ward_robot(
            "W01"
        ),
        make_clean_robot(
            "C01"
        ),
    ]

    candidates, _, _ = (
        scheduler.build_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M01"
    ]


@pytest.mark.parametrize(
    "status",
    [
        "offline",
        "error",
        "charging",
    ],
)
def test_unavailable_robot_is_not_candidate(
    status,
):

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01",
            status=status,
        ),
        make_medical_robot(
            "M02",
        ),
    ]

    candidates, _, _ = (
        scheduler.build_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M02"
    ]


# ============================================================
# Adaptive Behaviour
# ============================================================


def test_balanced_idle_fleet_uses_alpha_max():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    (
        _,
        imbalance,
        alpha,
    ) = scheduler.build_candidates(
        robots=robots,
        task=task,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            simple_travel_time
        ),
    )

    assert (
        imbalance
        == pytest.approx(0.0)
    )

    assert (
        alpha
        == pytest.approx(0.8)
    )


def test_imbalanced_fleet_uses_alpha_min():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    q1 = make_task(
        "Q1",
        source="lab",
        destination="ward_a",
        arrival_time_s=-100.0,
    )

    q2 = make_task(
        "Q2",
        source="lab",
        destination="ward_b",
        arrival_time_s=-50.0,
    )

    incoming = make_task(
        "T1",
        priority=3,
    )

    robots = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
            queued_task_ids=[
                "Q1",
                "Q2",
            ],
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    tasks_by_id = {
        "Q1": q1,
        "Q2": q2,
        "T1": incoming,
    }

    (
        _,
        imbalance,
        alpha,
    ) = scheduler.build_candidates(
        robots=robots,
        task=incoming,
        tasks_by_id=tasks_by_id,
        current_time_s=0.0,
        travel_time_fn=(
            simple_travel_time
        ),
    )

    assert (
        imbalance
        == pytest.approx(1.0)
    )

    assert (
        alpha
        == pytest.approx(0.4)
    )


def test_balanced_idle_fleet_prefers_nearer_robot():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    decision = (
        scheduler.decide(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision.dynamic_alpha
        == pytest.approx(0.8)
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )


# ============================================================
# Decision Metadata
# ============================================================


def test_decision_records_dynamic_information():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01"
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    decision = (
        scheduler.decide(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision.decision_status
        == "assigned"
    )

    assert (
        decision.candidate_count
        == 2
    )

    assert (
        decision.alpha_min
        == pytest.approx(0.4)
    )

    assert (
        decision.alpha_max
        == pytest.approx(0.8)
    )

    assert (
        0.4
        <= decision.dynamic_alpha
        <= 0.8
    )

    assert (
        0.0
        <= decision.load_imbalance
        <= 1.0
    )


def test_no_feasible_robot_returns_clean_decision():

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=0.4,
            alpha_max=0.8,
        )
    )

    task = make_task(
        "T1",
        task_type="specimen_delivery",
    )

    robots = [
        make_clean_robot(
            "C01"
        ),
        make_ward_robot(
            "W01"
        ),
    ]

    decision = (
        scheduler.decide(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision.selected_robot_id
        is None
    )

    assert (
        decision.candidate_count
        == 0
    )

    assert (
        decision.decision_status
        == "no_feasible_robot"
    )

    assert (
        decision.load_imbalance
        == pytest.approx(0.0)
    )

    assert (
        decision.dynamic_alpha
        == pytest.approx(0.8)
    )


# ============================================================
# Queue Commit
# ============================================================


def test_commit_false_does_not_modify_robot_queues():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01"
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    before = [
        list(
            robot.queued_task_ids
        )
        for robot
        in robots
    ]

    scheduler.decide(
        robots=robots,
        task=task,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            simple_travel_time
        ),
        commit_queue=False,
    )

    after = [
        list(
            robot.queued_task_ids
        )
        for robot
        in robots
    ]

    assert after == before


def test_commit_true_updates_selected_robot_queue():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    decision = (
        scheduler.decide(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
            commit_queue=True,
        )
    )

    selected = next(
        robot
        for robot
        in robots
        if (
            robot.robot_id
            == decision.selected_robot_id
        )
    )

    assert (
        task.task_id
        in selected.queued_task_ids
    )


# ============================================================
# Determinism
# ============================================================


def test_input_robot_order_does_not_change_decision():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task_a = make_task(
        "T1"
    )

    task_b = deepcopy(
        task_a
    )

    robots_a = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    robots_b = list(
        reversed(
            deepcopy(
                robots_a
            )
        )
    )

    decision_a = (
        scheduler.decide(
            robots=robots_a,
            task=task_a,
            tasks_by_id={
                task_a.task_id:
                task_a,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    decision_b = (
        scheduler.decide(
            robots=robots_b,
            task=task_b,
            tasks_by_id={
                task_b.task_id:
                task_b,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision_a.selected_robot_id
        ==
        decision_b.selected_robot_id
    )

    assert (
        decision_a.dynamic_alpha
        ==
        pytest.approx(
            decision_b.dynamic_alpha
        )
    )


def test_generator_input_works_with_commit_true():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task = make_task(
        "T1"
    )

    robots = [
        make_medical_robot(
            "M01"
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    decision = (
        scheduler.decide(
            robots=(
                robot
                for robot
                in robots
            ),
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
            commit_queue=True,
        )
    )

    assert (
        decision.selected_robot_id
        is not None
    )


# ============================================================
# Anti-Leakage
# ============================================================


def test_incoming_service_time_does_not_change_decision():

    scheduler = (
        DynamicWeightedScheduler()
    )

    robots_a = [
        make_medical_robot(
            "M01",
            current_location="pharmacy",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    robots_b = deepcopy(
        robots_a
    )

    task_short = make_task(
        "T1",
        service_time_s=1.0,
    )

    task_long = make_task(
        "T1",
        service_time_s=100000.0,
    )

    decision_short = (
        scheduler.decide(
            robots=robots_a,
            task=task_short,
            tasks_by_id={
                "T1": task_short,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    decision_long = (
        scheduler.decide(
            robots=robots_b,
            task=task_long,
            tasks_by_id={
                "T1": task_long,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision_short.selected_robot_id
        ==
        decision_long.selected_robot_id
    )

    assert (
        decision_short.dynamic_alpha
        ==
        pytest.approx(
            decision_long.dynamic_alpha
        )
    )


def test_existing_queue_service_time_does_not_change_decision():

    scheduler = (
        DynamicWeightedScheduler()
    )

    incoming_a = make_task(
        "T1",
        priority=3,
    )

    incoming_b = deepcopy(
        incoming_a
    )

    queued_short = make_task(
        "Q1",
        source="lab",
        destination="ward_a",
        priority=1,
        arrival_time_s=-100.0,
        service_time_s=1.0,
    )

    queued_long = make_task(
        "Q1",
        source="lab",
        destination="ward_a",
        priority=1,
        arrival_time_s=-100.0,
        service_time_s=100000.0,
    )

    robots_a = [
        make_medical_robot(
            "M01",
            queued_task_ids=[
                "Q1"
            ],
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    robots_b = deepcopy(
        robots_a
    )

    decision_short = (
        scheduler.decide(
            robots=robots_a,
            task=incoming_a,
            tasks_by_id={
                "Q1": queued_short,
                "T1": incoming_a,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    decision_long = (
        scheduler.decide(
            robots=robots_b,
            task=incoming_b,
            tasks_by_id={
                "Q1": queued_long,
                "T1": incoming_b,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision_short.selected_robot_id
        ==
        decision_long.selected_robot_id
    )

    assert (
        decision_short.dynamic_alpha
        ==
        pytest.approx(
            decision_long.dynamic_alpha
        )
    )


def test_active_actual_completion_time_does_not_change_decision():

    scheduler = (
        DynamicWeightedScheduler()
    )

    task_a = make_task(
        "T1"
    )

    task_b = deepcopy(
        task_a
    )

    robots_a = [
        make_medical_robot(
            "M01",
            current_location="lab",
            status="busy",
            current_task_id="ACTIVE",
            current_task_destination="ward_a",
            current_task_completion_time_s=10.0,
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b",
        ),
    ]

    robots_b = deepcopy(
        robots_a
    )

    robots_b[
        0
    ].current_task_completion_time_s = (
        100000.0
    )

    decision_a = (
        scheduler.decide(
            robots=robots_a,
            task=task_a,
            tasks_by_id={
                task_a.task_id:
                task_a,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    decision_b = (
        scheduler.decide(
            robots=robots_b,
            task=task_b,
            tasks_by_id={
                task_b.task_id:
                task_b,
            },
            current_time_s=0.0,
            travel_time_fn=(
                simple_travel_time
            ),
        )
    )

    assert (
        decision_a.selected_robot_id
        ==
        decision_b.selected_robot_id
    )

    assert (
        decision_a.dynamic_alpha
        ==
        pytest.approx(
            decision_b.dynamic_alpha
        )
    )