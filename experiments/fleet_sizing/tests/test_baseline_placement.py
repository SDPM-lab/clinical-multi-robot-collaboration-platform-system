from __future__ import annotations

import copy

import pytest

from experiments.fleet_sizing.baseline.common import (
    apply_placement_queue_order,
    evaluate_feasible_placement_candidates,
    evaluate_placement_candidate_robot,
    project_robot_queue_placement,
)

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    ROBOT_TYPE_MEDICAL,
    TASK_MEDICATION,
    TASK_SPECIMEN,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Test Helpers
# ============================================================


def make_task(
    task_id: str,
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


def make_robot(
    robot_id: str = "M01",
    current_location: str = "charging_station_2",
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=ROBOT_TYPE_MEDICAL,
        capabilities=[
            TASK_MEDICATION,
            TASK_SPECIMEN,
        ],
        current_location=current_location,
        status=status,
    )


def make_travel_time_fn(
    values: dict[tuple[str, str], float],
    default: float = 100.0,
):
    def travel_time_fn(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        return values.get(
            (source, destination),
            default,
        )

    return travel_time_fn


def constant_travel_time(
    source: str,
    destination: str,
) -> float:

    if source == destination:
        return 0.0

    return 10.0


# ============================================================
# Basic Placement Projection
# ============================================================


def test_idle_robot_uses_current_location_as_origin():
    robot = make_robot(
        current_location="charging_station_2",
    )

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    projection = project_robot_queue_placement(
        robot=robot,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=constant_travel_time,
        extra_task=task,
    )

    projected = projection.get_task("T1")

    assert projected is not None

    assert (
        projected.origin
        == "charging_station_2"
    )

    assert (
        projected.queue_position
        == 1
    )

    assert (
        projected.tasks_ahead_count
        == 0
    )

    assert (
        projected.approach_time_s
        == pytest.approx(10.0)
    )


def test_busy_robot_uses_active_task_destination_as_origin():
    robot = make_robot(
        current_location="pharmacy",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 9999.0
    robot.current_task_destination = "ward_b_2"

    task = make_task(
        task_id="NEXT",
        source="pharmacy",
    )

    travel_time_fn = make_travel_time_fn(
        {
            ("ward_b_2", "pharmacy"): 40.0,
        }
    )

    projection = project_robot_queue_placement(
        robot=robot,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
        extra_task=task,
    )

    projected = projection.get_task("NEXT")

    assert projected is not None

    assert (
        projected.origin
        == "ward_b_2"
    )

    assert (
        projected.approach_time_s
        == pytest.approx(40.0)
    )


# ============================================================
# Future Queue Location Chain
# ============================================================


def test_previous_task_destination_becomes_next_origin():
    robot = make_robot(
        current_location="charging_station_2",
    )

    first = make_task(
        task_id="FIRST",
        source="pharmacy",
        destination="ward_b_2",
        arrival_time_s=0.0,
    )

    second = make_task(
        task_id="SECOND",
        source="lab",
        destination="ward_a_2",
        arrival_time_s=10.0,
    )

    robot.queued_task_ids = [
        "FIRST"
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
            ): 35.0,
        }
    )

    projection = project_robot_queue_placement(
        robot=robot,
        tasks_by_id={
            "FIRST": first,
            "SECOND": second,
        },
        current_time_s=10.0,
        travel_time_fn=travel_time_fn,
        extra_task=second,
    )

    projected_second = (
        projection.get_task(
            "SECOND"
        )
    )

    assert projected_second is not None

    assert (
        projected_second.origin
        == "ward_b_2"
    )

    assert (
        projected_second
        .approach_time_s
        == pytest.approx(35.0)
    )


# ============================================================
# Priority + Aging
# ============================================================


def test_emergency_moves_before_normal_in_placement_projection():
    robot = make_robot()

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

    projection = project_robot_queue_placement(
        robot=robot,
        tasks_by_id={
            "NORMAL": normal,
            "EMERGENCY": emergency,
        },
        current_time_s=100.0,
        travel_time_fn=constant_travel_time,
        extra_task=emergency,
    )

    projected_ids = [
        item.task_id
        for item
        in projection.projected_tasks
    ]

    assert projected_ids == [
        "EMERGENCY",
        "NORMAL",
    ]


def test_tasks_ahead_count_matches_queue_position():
    robot = make_robot()

    first = make_task(
        task_id="T1",
        arrival_time_s=0.0,
    )

    second = make_task(
        task_id="T2",
        arrival_time_s=1.0,
    )

    robot.queued_task_ids = [
        "T1"
    ]

    projection = project_robot_queue_placement(
        robot=robot,
        tasks_by_id={
            "T1": first,
            "T2": second,
        },
        current_time_s=1.0,
        travel_time_fn=constant_travel_time,
        extra_task=second,
    )

    projected_first = (
        projection.get_task("T1")
    )

    projected_second = (
        projection.get_task("T2")
    )

    assert projected_first is not None
    assert projected_second is not None

    assert (
        projected_first.queue_position
        == 1
    )

    assert (
        projected_first.tasks_ahead_count
        == 0
    )

    assert (
        projected_second.queue_position
        == 2
    )

    assert (
        projected_second.tasks_ahead_count
        == 1
    )


# ============================================================
# Critical Anti-Leakage Tests
# ============================================================


def test_service_time_does_not_change_placement_projection():
    """
    Scheduler 不得因為 realized service_time_s 不同
    而得到不同 placement projection。
    """

    task_fast = make_task(
        task_id="T1",
        service_time_s=20.0,
    )

    task_slow = make_task(
        task_id="T1",
        service_time_s=2000.0,
    )

    robot_a = make_robot(
        robot_id="M01",
    )

    robot_b = copy.deepcopy(
        robot_a
    )

    projection_a = (
        project_robot_queue_placement(
            robot=robot_a,
            tasks_by_id={
                "T1": task_fast,
            },
            current_time_s=0.0,
            travel_time_fn=constant_travel_time,
            extra_task=task_fast,
        )
    )

    projection_b = (
        project_robot_queue_placement(
            robot=robot_b,
            tasks_by_id={
                "T1": task_slow,
            },
            current_time_s=0.0,
            travel_time_fn=constant_travel_time,
            extra_task=task_slow,
        )
    )

    projected_a = (
        projection_a.get_task("T1")
    )

    projected_b = (
        projection_b.get_task("T1")
    )

    assert projected_a is not None
    assert projected_b is not None

    assert (
        projected_a.queue_position
        == projected_b.queue_position
    )

    assert (
        projected_a.origin
        == projected_b.origin
    )

    assert (
        projected_a.tasks_ahead_count
        == projected_b.tasks_ahead_count
    )

    assert (
        projected_a.approach_time_s
        == pytest.approx(
            projected_b.approach_time_s
        )
    )


def test_active_actual_completion_time_does_not_change_projection():
    """
    Scheduler 不得因為 environment ground-truth
    current_task_completion_time_s 不同而改變 placement。
    """

    robot_fast = make_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    robot_fast.current_task_id = "ACTIVE"
    robot_fast.current_task_start_time_s = 0.0
    robot_fast.current_task_completion_time_s = 100.0
    robot_fast.current_task_destination = "ward_b_2"

    robot_slow = copy.deepcopy(
        robot_fast
    )

    robot_slow.current_task_completion_time_s = (
        10000.0
    )

    task_a = make_task(
        task_id="NEXT",
        source="pharmacy",
    )

    task_b = copy.deepcopy(
        task_a
    )

    travel_time_fn = make_travel_time_fn(
        {
            ("ward_b_2", "pharmacy"): 40.0,
        }
    )

    projection_fast = (
        project_robot_queue_placement(
            robot=robot_fast,
            tasks_by_id={
                "NEXT": task_a,
            },
            current_time_s=50.0,
            travel_time_fn=travel_time_fn,
            extra_task=task_a,
        )
    )

    projection_slow = (
        project_robot_queue_placement(
            robot=robot_slow,
            tasks_by_id={
                "NEXT": task_b,
            },
            current_time_s=50.0,
            travel_time_fn=travel_time_fn,
            extra_task=task_b,
        )
    )

    projected_fast = (
        projection_fast.get_task(
            "NEXT"
        )
    )

    projected_slow = (
        projection_slow.get_task(
            "NEXT"
        )
    )

    assert projected_fast is not None
    assert projected_slow is not None

    assert (
        projected_fast.origin
        == projected_slow.origin
        == "ward_b_2"
    )

    assert (
        projected_fast
        .approach_time_s
        == pytest.approx(
            projected_slow
            .approach_time_s
        )
    )

    assert (
        projected_fast
        .queue_position
        == projected_slow
        .queue_position
    )


# ============================================================
# Candidate Evaluation
# ============================================================


def test_placement_candidate_evaluation_contains_expected_fields():
    robot = make_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    evaluation = (
        evaluate_placement_candidate_robot(
            robot=robot,
            task=task,
            tasks_by_id={
                "T1": task,
            },
            current_time_s=0.0,
            travel_time_fn=constant_travel_time,
        )
    )

    assert evaluation.robot_id == "M01"
    assert evaluation.task_id == "T1"

    assert (
        evaluation.assignment_origin
        == "charging_station_2"
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
        == pytest.approx(10.0)
    )


def test_feasible_placement_candidates_are_sorted_by_robot_id():
    m02 = make_robot(
        robot_id="M02",
    )

    m01 = make_robot(
        robot_id="M01",
    )

    task = make_task(
        task_id="T1",
    )

    evaluations = (
        evaluate_feasible_placement_candidates(
            robots=[
                m02,
                m01,
            ],
            task=task,
            tasks_by_id={
                "T1": task,
            },
            current_time_s=0.0,
            travel_time_fn=constant_travel_time,
        )
    )

    assert [
        evaluation.robot_id
        for evaluation
        in evaluations
    ] == [
        "M01",
        "M02",
    ]


# ============================================================
# Commit
# ============================================================


def test_apply_placement_queue_order_updates_only_future_queue():
    robot = make_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 1000.0
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

    projection = (
        project_robot_queue_placement(
            robot=robot,
            tasks_by_id={
                "NORMAL": normal,
                "EMERGENCY": emergency,
            },
            current_time_s=100.0,
            travel_time_fn=constant_travel_time,
            extra_task=emergency,
        )
    )

    apply_placement_queue_order(
        robot=robot,
        projection=projection,
    )

    assert (
        robot.current_task_id
        == "ACTIVE"
    )

    assert (
        robot.queued_task_ids
        == [
            "EMERGENCY",
            "NORMAL",
        ]
    )


def test_apply_placement_projection_to_wrong_robot_raises():
    m01 = make_robot(
        robot_id="M01",
    )

    m02 = make_robot(
        robot_id="M02",
    )

    task = make_task(
        task_id="T1",
    )

    projection = (
        project_robot_queue_placement(
            robot=m01,
            tasks_by_id={
                "T1": task,
            },
            current_time_s=0.0,
            travel_time_fn=constant_travel_time,
            extra_task=task,
        )
    )

    with pytest.raises(
        ValueError
    ):
        apply_placement_queue_order(
            robot=m02,
            projection=projection,
        )


# ============================================================
# Validation
# ============================================================


def test_negative_approach_time_raises():
    robot = make_robot()

    task = make_task(
        task_id="T1",
    )

    def negative_travel_time(
        source: str,
        destination: str,
    ) -> float:
        return -1.0

    with pytest.raises(
        ValueError
    ):
        project_robot_queue_placement(
            robot=robot,
            tasks_by_id={
                "T1": task,
            },
            current_time_s=0.0,
            travel_time_fn=(
                negative_travel_time
            ),
            extra_task=task,
        )