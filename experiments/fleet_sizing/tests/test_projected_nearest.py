from __future__ import annotations

import copy

import pytest

from experiments.fleet_sizing.baseline.projected_nearest import (
    ProjectedNearestDecision,
    ProjectedNearestScheduler,
)

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    ROBOT_TYPE_CLEAN,
    ROBOT_TYPE_MEDICAL,
    ROBOT_TYPE_WARD,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
    TASK_WASTE,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Test Helpers
# ============================================================


def make_task(
    task_id: str = "T1",
    task_type: str = TASK_MEDICATION,
    source: str = "pharmacy",
    destination: str = "ward_a_2",
    priority: int = PRIORITY_NORMAL,
    arrival_time_s: float = 0.0,
    service_time_s: float = 30.0,
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


def make_clean_robot(
    robot_id: str = "C01",
    current_location: str = "charging_station_2",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=ROBOT_TYPE_CLEAN,
        capabilities=[
            TASK_WASTE,
            TASK_CLOTHES,
        ],
        current_location=current_location,
        status=status,
    )


def make_medical_robot(
    robot_id: str = "M01",
    current_location: str = "charging_station_2",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=ROBOT_TYPE_MEDICAL,
        capabilities=[
            TASK_SPECIMEN,
            TASK_MEDICATION,
        ],
        current_location=current_location,
        status=status,
    )


def make_ward_robot(
    robot_id: str = "W01",
    current_location: str = "charging_station_2",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=ROBOT_TYPE_WARD,
        capabilities=[
            TASK_MEDICATION,
            TASK_WARD,
        ],
        current_location=current_location,
        status=status,
    )


def constant_travel_time(
    source: str,
    destination: str,
) -> float:

    if source == destination:
        return 0.0

    return 10.0


def make_travel_time_fn(
    values: dict[
        tuple[str, str],
        float,
    ],
    default: float = 100.0,
):
    def travel_time_fn(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        return values.get(
            (
                source,
                destination,
            ),
            default,
        )

    return travel_time_fn


# ============================================================
# Basic Metadata
# ============================================================


def test_scheduler_name():
    scheduler = ProjectedNearestScheduler()

    assert (
        scheduler.NAME
        == "projected_nearest"
    )


def test_decision_dataclass_can_be_created():
    decision = ProjectedNearestDecision(
        task_id="T1",
        selected_robot_id="M01",
        candidate_count=1,
        candidate_robot_ids=(
            "M01",
        ),
        selected_evaluation=None,
        released_task_ids=(),
        decision_status="assigned",
    )

    assert decision.task_id == "T1"

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        decision.candidate_count
        == 1
    )

    assert (
        decision.candidate_robot_ids
        == ("M01",)
    )

    assert (
        decision.decision_status
        == "assigned"
    )


# ============================================================
# Capability Filtering
# ============================================================


def test_medication_evaluates_medical_and_ward_only():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    evaluations = (
        scheduler.evaluate_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                constant_travel_time
            ),
        )
    )

    assert [
        evaluation.robot_id
        for evaluation
        in evaluations
    ] == [
        "M01",
        "W01",
    ]


def test_specimen_only_evaluates_medical_robot():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_type=TASK_SPECIMEN,
        source="lab",
        destination="ward_a_2",
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    evaluations = (
        scheduler.evaluate_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                constant_travel_time
            ),
        )
    )

    assert [
        evaluation.robot_id
        for evaluation
        in evaluations
    ] == [
        "M01",
    ]


def test_ward_service_only_evaluates_ward_robot():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_type=TASK_WARD,
        source="nurse_station",
        destination="ward_a_2",
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    evaluations = (
        scheduler.evaluate_candidates(
            robots=robots,
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                constant_travel_time
            ),
        )
    )

    assert [
        evaluation.robot_id
        for evaluation
        in evaluations
    ] == [
        "W01",
    ]


# ============================================================
# Robot Status
# ============================================================


def test_busy_robot_is_still_evaluated():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 9999.0
    robot.current_task_destination = "ward_b_2"

    task = make_task(
        task_id="NEXT",
    )

    evaluations = (
        scheduler.evaluate_candidates(
            robots=[
                robot,
            ],
            task=task,
            tasks_by_id={
                "NEXT": task,
            },
            current_time_s=100.0,
            travel_time_fn=(
                constant_travel_time
            ),
        )
    )

    assert len(
        evaluations
    ) == 1

    assert (
        evaluations[0].robot_id
        == "M01"
    )


@pytest.mark.parametrize(
    "status",
    [
        "offline",
        "error",
        "charging",
    ],
)
def test_unavailable_robot_is_not_evaluated(
    status: str,
):
    scheduler = ProjectedNearestScheduler()

    task = make_task()

    robot = make_medical_robot(
        robot_id="M01",
        status=status,
    )

    evaluations = (
        scheduler.evaluate_candidates(
            robots=[
                robot,
            ],
            task=task,
            tasks_by_id={
                task.task_id: task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                constant_travel_time
            ),
        )
    )

    assert evaluations == []


# ============================================================
# Core Projected Nearest Selection
# ============================================================


def test_selects_robot_with_shortest_projected_approach_time():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 50.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        decision.selected_evaluation
        is not None
    )

    assert (
        decision
        .selected_evaluation
        .projected_approach_time_s
        == pytest.approx(20.0)
    )


def test_projected_nearest_can_differ_from_current_nearest():
    """
    M01 current location is very close to the new task source,
    but it has an active task ending far away.

    M02 current location is farther now, but its projected
    origin is closer.

    Projected Nearest must choose M02.
    """

    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_start_time_s = 0.0
    m01.current_task_completion_time_s = 9999.0
    m01.current_task_destination = "ward_a_2"

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 80.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 20.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id={
            "NEW": task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M02"
    )


# ============================================================
# Projected Origin
# ============================================================


def test_active_task_destination_is_used_as_projected_origin():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 5000.0
    robot.current_task_destination = "ward_b_2"

    task = make_task(
        task_id="NEW",
        source="lab",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "lab",
            ): 35.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "NEW": task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    evaluation = (
        decision.selected_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation.assignment_origin
        == "ward_b_2"
    )

    assert (
        evaluation
        .projected_approach_time_s
        == pytest.approx(35.0)
    )


def test_previous_queued_task_destination_becomes_new_task_origin():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    existing = make_task(
        task_id="OLD",
        source="pharmacy",
        destination="ward_b_2",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    incoming = make_task(
        task_id="NEW",
        source="lab",
        destination="ward_a_2",
        priority=PRIORITY_NORMAL,
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "OLD"
    ]

    travel_time_fn = make_travel_time_fn(
        {
            (
                "charging_station_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_b_2",
                "lab",
            ): 40.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=incoming,
        tasks_by_id={
            "OLD": existing,
            "NEW": incoming,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    evaluation = (
        decision.selected_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation
        .projected_queue_position
        == 2
    )

    assert (
        evaluation.tasks_ahead_count
        == 1
    )

    assert (
        evaluation.assignment_origin
        == "ward_b_2"
    )

    assert (
        evaluation
        .projected_approach_time_s
        == pytest.approx(40.0)
    )


# ============================================================
# Priority + Aging
# ============================================================


def test_emergency_task_can_move_before_existing_normal_queue():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
    )

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "NORMAL"
    ]

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=emergency,
        tasks_by_id={
            "NORMAL": normal,
            "EMERGENCY": emergency,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    evaluation = (
        decision.selected_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation
        .projected_queue_position
        == 1
    )

    assert (
        evaluation.tasks_ahead_count
        == 0
    )

    projected_ids = [
        item.task_id
        for item
        in evaluation
        .queue_projection
        .projected_tasks
    ]

    assert projected_ids == [
        "EMERGENCY",
        "NORMAL",
    ]


def test_active_task_is_never_preempted_by_emergency():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 5000.0
    robot.current_task_destination = "ward_b_2"

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "NORMAL"
    ]

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=emergency,
        tasks_by_id={
            "NORMAL": normal,
            "EMERGENCY": emergency,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=True,
    )

    assert (
        robot.current_task_id
        == "ACTIVE"
    )

    assert (
        "ACTIVE"
        not in robot.queued_task_ids
    )

    assert (
        robot.queued_task_ids
        == [
            "EMERGENCY",
            "NORMAL",
        ]
    )


# ============================================================
# No Feasible Robot
# ============================================================


def test_no_feasible_robot_returns_clean_decision():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_type=TASK_SPECIMEN,
    )

    robots = [
        make_clean_robot("C01"),
        make_ward_robot("W01"),
    ]

    decision = scheduler.decide(
        robots=robots,
        task=task,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
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
        decision.candidate_robot_ids
        == ()
    )

    assert (
        decision.selected_evaluation
        is None
    )

    assert (
        decision.decision_status
        == "no_feasible_robot"
    )


# ============================================================
# Decision Metadata
# ============================================================


def test_decision_records_all_candidate_robot_ids():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_ward_robot("W01"),
        make_medical_robot("M02"),
        make_clean_robot("C01"),
        make_medical_robot("M01"),
    ]

    decision = scheduler.decide(
        robots=robots,
        task=task,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    assert (
        decision.candidate_count
        == 3
    )

    assert (
        decision.candidate_robot_ids
        == (
            "M01",
            "M02",
            "W01",
        )
    )


# ============================================================
# Tie Breakers
# ============================================================


def test_equal_approach_prefers_fewer_tasks_ahead():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=100.0,
    )

    queued = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
        arrival_time_s=0.0,
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m01.queued_task_ids = [
        "OLD"
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 20.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id={
            "OLD": queued,
            "NEW": task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M02"
    )


def test_exact_tie_is_broken_by_robot_id():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 20.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m02,
            m01,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )


def test_shorter_approach_wins_even_with_more_tasks_ahead():
    """
    Queue load is only a tie breaker.

    Projected Nearest must remain a nearest-first baseline.
    """

    scheduler = ProjectedNearestScheduler()

    incoming = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=100.0,
    )

    queued = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
        arrival_time_s=0.0,
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m01.queued_task_ids = [
        "OLD"
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 30.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=incoming,
        tasks_by_id={
            "OLD": queued,
            "NEW": incoming,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )


# ============================================================
# Determinism / Iterable Handling
# ============================================================


def test_input_robot_order_does_not_change_decision():
    scheduler_a = ProjectedNearestScheduler()
    scheduler_b = ProjectedNearestScheduler()

    task_a = make_task(
        task_id="T1",
        source="pharmacy",
    )

    task_b = copy.deepcopy(
        task_a
    )

    robots_a = [
        make_medical_robot(
            "M01",
            current_location="ward_a_2",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b_2",
        ),
    ]

    robots_b = [
        make_medical_robot(
            "M02",
            current_location="ward_b_2",
        ),
        make_medical_robot(
            "M01",
            current_location="ward_a_2",
        ),
    ]

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 50.0,
        }
    )

    decision_a = scheduler_a.decide(
        robots=robots_a,
        task=task_a,
        tasks_by_id={
            "T1": task_a,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
        task=task_b,
        tasks_by_id={
            "T1": task_b,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
        == "M01"
    )


def test_generator_input_works_with_commit_true():
    """
    Protect against Iterable / generator exhaustion.
    """

    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 50.0,
        }
    )

    robots_generator = (
        robot
        for robot in [
            m01,
            m02,
        ]
    )

    decision = scheduler.decide(
        robots=robots_generator,
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
        commit_queue=True,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        m01.queued_task_ids
        == [
            "T1",
        ]
    )

    assert (
        m02.queued_task_ids
        == []
    )


# ============================================================
# Queue Commit
# ============================================================


def test_commit_false_does_not_modify_any_robot():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    before_m01 = list(
        m01.queued_task_ids
    )

    before_m02 = list(
        m02.queued_task_ids
    )

    scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=False,
    )

    assert (
        m01.queued_task_ids
        == before_m01
    )

    assert (
        m02.queued_task_ids
        == before_m02
    )


def test_commit_true_only_updates_selected_robot():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 50.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
        commit_queue=True,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        m01.queued_task_ids
        == [
            "T1",
        ]
    )

    assert (
        m02.queued_task_ids
        == []
    )


def test_commit_true_preserves_priority_queue_order():
    scheduler = ProjectedNearestScheduler()

    robot = make_medical_robot(
        robot_id="M01",
    )

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "NORMAL"
    ]

    scheduler.decide(
        robots=[
            robot,
        ],
        task=emergency,
        tasks_by_id={
            "NORMAL": normal,
            "EMERGENCY": emergency,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=True,
    )

    assert (
        robot.queued_task_ids
        == [
            "EMERGENCY",
            "NORMAL",
        ]
    )


# ============================================================
# Duration-Free Evaluation
# ============================================================


def test_selected_evaluation_contains_expected_placement():
    scheduler = ProjectedNearestScheduler()

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    robot = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 25.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    evaluation = (
        decision.selected_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation.assignment_origin
        == "ward_a_2"
    )

    assert (
        evaluation.current_queue_length
        == 0
    )

    assert (
        evaluation.projected_queue_length
        == 1
    )

    assert (
        evaluation.projected_queue_position
        == 1
    )

    assert (
        evaluation.tasks_ahead_count
        == 0
    )

    assert (
        evaluation
        .projected_approach_time_s
        == pytest.approx(25.0)
    )


# ============================================================
# Anti-Leakage Tests
# ============================================================


def test_incoming_service_time_does_not_change_decision():
    """
    The incoming task's realized service duration must not
    affect Projected Nearest.
    """

    scheduler_a = ProjectedNearestScheduler()
    scheduler_b = ProjectedNearestScheduler()

    task_fast = make_task(
        task_id="NEW",
        source="pharmacy",
        service_time_s=5.0,
    )

    task_slow = make_task(
        task_id="NEW",
        source="pharmacy",
        service_time_s=5000.0,
    )

    robots_a = [
        make_medical_robot(
            "M01",
            current_location="ward_a_2",
        ),
        make_medical_robot(
            "M02",
            current_location="ward_b_2",
        ),
    ]

    robots_b = copy.deepcopy(
        robots_a
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 40.0,
        }
    )

    decision_a = scheduler_a.decide(
        robots=robots_a,
        task=task_fast,
        tasks_by_id={
            "NEW": task_fast,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
        task=task_slow,
        tasks_by_id={
            "NEW": task_slow,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
        == "M01"
    )

    assert (
        decision_a.selected_evaluation
        is not None
    )

    assert (
        decision_b.selected_evaluation
        is not None
    )

    assert (
        decision_a
        .selected_evaluation
        .projected_approach_time_s
        == pytest.approx(
            decision_b
            .selected_evaluation
            .projected_approach_time_s
        )
    )


def test_existing_queued_service_time_does_not_change_decision():
    """
    Existing queued tasks may have completely different
    realized service durations, but Projected Nearest should
    only use their queue position and destination.
    """

    scheduler_a = ProjectedNearestScheduler()
    scheduler_b = ProjectedNearestScheduler()

    old_fast = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
        arrival_time_s=0.0,
        service_time_s=5.0,
    )

    old_slow = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
        arrival_time_s=0.0,
        service_time_s=5000.0,
    )

    incoming_a = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=100.0,
    )

    incoming_b = copy.deepcopy(
        incoming_a
    )

    m01_a = make_medical_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    m01_a.queued_task_ids = [
        "OLD"
    ]

    m02_a = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    robots_a = [
        m01_a,
        m02_a,
    ]

    robots_b = copy.deepcopy(
        robots_a
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 30.0,
        }
    )

    decision_a = scheduler_a.decide(
        robots=robots_a,
        task=incoming_a,
        tasks_by_id={
            "OLD": old_fast,
            "NEW": incoming_a,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
        task=incoming_b,
        tasks_by_id={
            "OLD": old_slow,
            "NEW": incoming_b,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )

    assert (
        decision_a.selected_robot_id
        == "M01"
    )


def test_active_actual_completion_time_does_not_change_decision():
    """
    Environment ground-truth active completion time must not
    affect Projected Nearest.
    """

    scheduler_a = ProjectedNearestScheduler()
    scheduler_b = ProjectedNearestScheduler()

    m01_fast = make_medical_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    m01_fast.current_task_id = "ACTIVE"
    m01_fast.current_task_start_time_s = 0.0
    m01_fast.current_task_completion_time_s = 100.0
    m01_fast.current_task_destination = "ward_b_2"

    m02_fast = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    robots_fast = [
        m01_fast,
        m02_fast,
    ]

    robots_slow = copy.deepcopy(
        robots_fast
    )

    robots_slow[
        0
    ].current_task_completion_time_s = (
        10000.0
    )

    task_a = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    task_b = copy.deepcopy(
        task_a
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 30.0,
        }
    )

    decision_fast = scheduler_a.decide(
        robots=robots_fast,
        task=task_a,
        tasks_by_id={
            "NEW": task_a,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    decision_slow = scheduler_b.decide(
        robots=robots_slow,
        task=task_b,
        tasks_by_id={
            "NEW": task_b,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_fast.selected_robot_id
        == decision_slow.selected_robot_id
        == "M01"
    )

    assert (
        decision_fast.selected_evaluation
        is not None
    )

    assert (
        decision_slow.selected_evaluation
        is not None
    )

    assert (
        decision_fast
        .selected_evaluation
        .assignment_origin
        ==
        decision_slow
        .selected_evaluation
        .assignment_origin
        ==
        "ward_b_2"
    )


def test_active_task_service_time_is_irrelevant_to_decision():
    """
    Even if an active TaskState exists in tasks_by_id and its
    realized service time changes, duration-free projection
    must not depend on it.
    """

    scheduler_a = ProjectedNearestScheduler()
    scheduler_b = ProjectedNearestScheduler()

    active_fast = make_task(
        task_id="ACTIVE",
        source="pharmacy",
        destination="ward_b_2",
        service_time_s=5.0,
    )

    active_slow = make_task(
        task_id="ACTIVE",
        source="pharmacy",
        destination="ward_b_2",
        service_time_s=5000.0,
    )

    incoming_a = make_task(
        task_id="NEW",
        source="lab",
    )

    incoming_b = copy.deepcopy(
        incoming_a
    )

    robot_a = make_medical_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    robot_a.current_task_id = "ACTIVE"
    robot_a.current_task_start_time_s = 0.0
    robot_a.current_task_completion_time_s = 100.0
    robot_a.current_task_destination = "ward_b_2"

    robot_b = copy.deepcopy(
        robot_a
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "lab",
            ): 15.0,
        }
    )

    decision_a = scheduler_a.decide(
        robots=[
            robot_a,
        ],
        task=incoming_a,
        tasks_by_id={
            "ACTIVE": active_fast,
            "NEW": incoming_a,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=[
            robot_b,
        ],
        task=incoming_b,
        tasks_by_id={
            "ACTIVE": active_slow,
            "NEW": incoming_b,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
        == "M01"
    )

    assert (
        decision_a.selected_evaluation
        is not None
    )

    assert (
        decision_b.selected_evaluation
        is not None
    )

    assert (
        decision_a
        .selected_evaluation
        .projected_approach_time_s
        == pytest.approx(
            decision_b
            .selected_evaluation
            .projected_approach_time_s
        )
    )


def test_projected_nearest_excludes_battery_infeasible_robot():

    def fake_travel_time(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        return 600.0

    scheduler = (
        ProjectedNearestScheduler()
    )

    task = TaskState(
        task_id="T_NEW",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=3,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    robot_ok = RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="charging_station_2",
        status="idle",
        battery_soc=0.40,
    )

    robot_low = RobotState(
        robot_id="M02",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="pharmacy",
        status="idle",
        battery_soc=0.20,
    )

    decision = (
        scheduler.decide(
            robots=[
                robot_ok,
                robot_low,
            ],
            task=task,
            tasks_by_id={
                task.task_id:
                task,
            },
            current_time_s=100.0,
            travel_time_fn=(
                fake_travel_time
            ),
            enable_battery_model=True,
        )
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        decision.candidate_robot_ids
        == (
            "M01",
        )
    )


def test_projected_nearest_allows_candidate_when_downstream_task_can_be_released():

    def fake_travel_time(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        if (
            source == "pharmacy"
            and
            destination == "ward_a_2"
        ):
            return 1200.0

        return 600.0

    scheduler = (
        ProjectedNearestScheduler()
    )

    robot = RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="charging_station_2",
        status="idle",
        battery_soc=0.40,
    )

    old_task = TaskState(
        task_id="T2",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    incoming = TaskState(
        task_id="T3",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_b_2",
        priority=3,
        arrival_time_s=200.0,
        service_time_s=0.0,
    )

    robot.queued_task_ids = [
        old_task.task_id,
    ]

    tasks_by_id = {
        old_task.task_id:
        old_task,
        incoming.task_id:
        incoming,
    }

    decision = (
        scheduler.decide(
            robots=[
                robot,
            ],
            task=incoming,
            tasks_by_id=(
                tasks_by_id
            ),
            current_time_s=200.0,
            travel_time_fn=(
                fake_travel_time
            ),
            enable_battery_model=True,
        )
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        decision.candidate_robot_ids
        == (
            "M01",
        )
    )


def test_projected_nearest_battery_commit_releases_downstream_task():

    def fake_travel_time(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        if (
            source == "pharmacy"
            and
            destination == "ward_a_2"
        ):
            return 1200.0

        return 600.0

    scheduler = (
        ProjectedNearestScheduler()
    )

    robot = RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="charging_station_2",
        status="idle",
        battery_soc=0.40,
    )

    old_task = TaskState(
        task_id="T2",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    incoming = TaskState(
        task_id="T3",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_b_2",
        priority=3,
        arrival_time_s=200.0,
        service_time_s=0.0,
    )

    old_task.assigned_robot = (
        robot.robot_id
    )
    old_task.assignment_time_s = 100.0
    old_task.queue_position = 1
    old_task.status = "queued"

    robot.queued_task_ids = [
        old_task.task_id,
    ]

    robot.assigned_task_ids = [
        old_task.task_id,
    ]

    tasks_by_id = {
        old_task.task_id:
        old_task,
        incoming.task_id:
        incoming,
    }

    decision = (
        scheduler.decide(
            robots=[
                robot,
            ],
            task=incoming,
            tasks_by_id=(
                tasks_by_id
            ),
            current_time_s=200.0,
            travel_time_fn=(
                fake_travel_time
            ),
            commit_queue=True,
            enable_battery_model=True,
        )
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        decision.released_task_ids
        == (
            "T2",
        )
    )

    assert (
        robot.queued_task_ids
        == [
            "T3",
        ]
    )

    assert (
        old_task.status
        == "waiting"
    )

    assert (
        old_task.assigned_robot
        is None
    )

    assert (
        old_task.assignment_time_s
        is None
    )

    assert (
        old_task.queue_position
        is None
    )

    # Original arrival time must survive reassignment.
    assert (
        old_task.arrival_time_s
        == 100.0
    )