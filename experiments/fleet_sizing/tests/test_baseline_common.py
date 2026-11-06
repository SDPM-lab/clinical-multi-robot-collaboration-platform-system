from __future__ import annotations

import copy

import pytest

from experiments.fleet_sizing.baseline.common import (
    AGING_INTERVAL_SECONDS,
    apply_projected_queue_order,
    build_pending_queue,
    evaluate_candidate_robot,
    evaluate_feasible_candidates,
    evaluate_battery_feasible_placement_candidates,
    get_effective_priority,
    get_feasible_robots,
    get_queue_sort_key,
    get_robot_queued_tasks,
    get_waiting_time_s,
    order_waiting_tasks,
    project_robot_queue,
    robot_can_perform_task,
    robot_is_feasible,
    robot_status_is_assignable,
    validate_priority,
    validate_robot,
    validate_scheduler_state,
    validate_task,
)

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
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
    robot_id: str,
    robot_type: str = ROBOT_TYPE_MEDICAL,
    capabilities: list[str] | None = None,
    current_location: str = "charging_station_2",
    status: str = "idle",
) -> RobotState:

    if capabilities is None:

        if (
            robot_type
            == ROBOT_TYPE_CLEAN
        ):

            capabilities = [
                TASK_WASTE,
                TASK_CLOTHES,
            ]

        elif (
            robot_type
            == ROBOT_TYPE_MEDICAL
        ):

            capabilities = [
                TASK_MEDICATION,
                TASK_SPECIMEN,
            ]

        elif (
            robot_type
            == ROBOT_TYPE_WARD
        ):

            capabilities = [
                TASK_MEDICATION,
                TASK_WARD,
            ]

        else:

            capabilities = []

    return RobotState(
        robot_id=robot_id,
        robot_type=robot_type,
        capabilities=list(
            capabilities
        ),
        current_location=current_location,
        status=status,
    )


def fixed_travel_time(
    source: str,
    destination: str,
) -> float:
    """
    Deterministic artificial travel-time model.

    This deliberately does NOT use the real hospital travel
    model because these are unit tests for queue logic.

    Same location:
        0 seconds

    Any different location:
        10 seconds
    """

    if (
        source
        == destination
    ):
        return 0.0

    return 10.0


# ============================================================
# Waiting / Aging
# ============================================================


def test_waiting_time_is_zero_before_arrival():
    task = make_task(
        task_id="T1",
        arrival_time_s=100.0,
    )

    waiting = get_waiting_time_s(
        task=task,
        current_time_s=50.0,
    )

    assert waiting == 0.0


def test_waiting_time_is_current_minus_arrival():
    task = make_task(
        task_id="T1",
        arrival_time_s=100.0,
    )

    waiting = get_waiting_time_s(
        task=task,
        current_time_s=250.0,
    )

    assert waiting == pytest.approx(
        150.0
    )


def test_effective_priority_increases_with_aging():
    task = make_task(
        task_id="T1",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    current_time_s = (
        AGING_INTERVAL_SECONDS
        * 2
    )

    effective_priority = (
        get_effective_priority(
            task=task,
            current_time_s=current_time_s,
        )
    )

    assert effective_priority == (
        PRIORITY_NORMAL + 2.0
    )


def test_emergency_effective_priority_is_not_aged():
    task = make_task(
        task_id="E1",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=0.0,
    )

    effective_priority = (
        get_effective_priority(
            task=task,
            current_time_s=10000.0,
        )
    )

    assert effective_priority == float(
        PRIORITY_EMERGENCY
    )


# ============================================================
# Priority Queue Ordering
# ============================================================


def test_emergency_always_before_non_emergency():
    """
    Even an extremely old Low-priority task must not
    overtake an Emergency task.
    """

    old_low = make_task(
        task_id="LOW",
        priority=PRIORITY_LOW,
        arrival_time_s=0.0,
    )

    new_emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=10000.0,
    )

    ordered = order_waiting_tasks(
        tasks=[
            old_low,
            new_emergency,
        ],
        current_time_s=10000.0,
    )

    assert ordered[0].task_id == (
        "EMERGENCY"
    )

    assert ordered[1].task_id == (
        "LOW"
    )


def test_older_emergency_task_comes_first():
    emergency_old = make_task(
        task_id="E1",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=100.0,
    )

    emergency_new = make_task(
        task_id="E2",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=200.0,
    )

    ordered = order_waiting_tasks(
        tasks=[
            emergency_new,
            emergency_old,
        ],
        current_time_s=300.0,
    )

    assert [
        task.task_id
        for task in ordered
    ] == [
        "E1",
        "E2",
    ]


def test_aging_can_move_old_normal_ahead_of_new_high():
    """
    Normal task:
        priority = 1
        waiting  = 480 seconds
        aging bonus = 4

        effective priority = 5

    New High:
        priority = 2
        waiting = 0

        effective priority = 2

    Therefore the old Normal task should come first.
    """

    old_normal = make_task(
        task_id="NORMAL_OLD",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
    )

    new_high = make_task(
        task_id="HIGH_NEW",
        priority=PRIORITY_HIGH,
        arrival_time_s=480.0,
    )

    ordered = order_waiting_tasks(
        tasks=[
            new_high,
            old_normal,
        ],
        current_time_s=480.0,
    )

    assert ordered[0].task_id == (
        "NORMAL_OLD"
    )

    assert ordered[1].task_id == (
        "HIGH_NEW"
    )


def test_queue_order_is_deterministic():
    task_b = make_task(
        task_id="B",
        priority=PRIORITY_NORMAL,
        arrival_time_s=100.0,
    )

    task_a = make_task(
        task_id="A",
        priority=PRIORITY_NORMAL,
        arrival_time_s=100.0,
    )

    ordered = order_waiting_tasks(
        tasks=[
            task_b,
            task_a,
        ],
        current_time_s=100.0,
    )

    assert [
        task.task_id
        for task in ordered
    ] == [
        "A",
        "B",
    ]


# ============================================================
# Capability Matching
# ============================================================


def test_clean_robot_capability_matching():
    clean = make_robot(
        robot_id="C01",
        robot_type=ROBOT_TYPE_CLEAN,
    )

    waste = make_task(
        task_id="WASTE",
        task_type=TASK_WASTE,
    )

    specimen = make_task(
        task_id="SPEC",
        task_type=TASK_SPECIMEN,
    )

    assert robot_can_perform_task(
        clean,
        waste,
    )

    assert not robot_can_perform_task(
        clean,
        specimen,
    )


def test_medical_robot_capability_matching():
    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
    )

    medication = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    specimen = make_task(
        task_id="SPEC",
        task_type=TASK_SPECIMEN,
    )

    ward = make_task(
        task_id="WARD",
        task_type=TASK_WARD,
    )

    assert robot_can_perform_task(
        medical,
        medication,
    )

    assert robot_can_perform_task(
        medical,
        specimen,
    )

    assert not robot_can_perform_task(
        medical,
        ward,
    )


def test_ward_robot_capability_matching():
    ward_robot = make_robot(
        robot_id="W01",
        robot_type=ROBOT_TYPE_WARD,
    )

    medication = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    ward_task = make_task(
        task_id="WARD",
        task_type=TASK_WARD,
    )

    specimen = make_task(
        task_id="SPEC",
        task_type=TASK_SPECIMEN,
    )

    assert robot_can_perform_task(
        ward_robot,
        medication,
    )

    assert robot_can_perform_task(
        ward_robot,
        ward_task,
    )

    assert not robot_can_perform_task(
        ward_robot,
        specimen,
    )


# ============================================================
# Robot Availability
# ============================================================


def test_idle_robot_is_assignable():
    robot = make_robot(
        robot_id="M01",
        status="idle",
    )

    assert robot_status_is_assignable(
        robot
    )


def test_busy_robot_is_still_assignable():
    """
    Busy robots may accept future tasks.
    """

    robot = make_robot(
        robot_id="M01",
        status="busy",
    )

    assert robot_status_is_assignable(
        robot
    )


@pytest.mark.parametrize(
    "status",
    [
        "offline",
        "error",
        "charging",
    ],
)
def test_unavailable_robot_statuses_are_not_assignable(
    status: str,
):
    robot = make_robot(
        robot_id="M01",
        status=status,
    )

    assert not (
        robot_status_is_assignable(
            robot
        )
    )


def test_robot_feasibility_requires_capability_and_status():
    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
        status="idle",
    )

    medication = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    assert robot_is_feasible(
        medical,
        medication,
    )

    medical.status = "offline"

    assert not robot_is_feasible(
        medical,
        medication,
    )


# ============================================================
# Feasible Robot Filtering
# ============================================================


def test_get_feasible_robots_for_medication():
    clean = make_robot(
        robot_id="C01",
        robot_type=ROBOT_TYPE_CLEAN,
    )

    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
    )

    ward = make_robot(
        robot_id="W01",
        robot_type=ROBOT_TYPE_WARD,
    )

    task = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    feasible = get_feasible_robots(
        robots=[
            clean,
            medical,
            ward,
        ],
        task=task,
    )

    ids = {
        robot.robot_id
        for robot in feasible
    }

    assert ids == {
        "M01",
        "W01",
    }


def test_busy_feasible_robot_is_not_filtered_out():
    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
        status="busy",
    )

    task = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    feasible = get_feasible_robots(
        robots=[
            medical
        ],
        task=task,
    )

    assert len(feasible) == 1

    assert feasible[0].robot_id == "M01"


# ============================================================
# Active Task / Queue Invariant
# ============================================================


def test_active_task_is_not_in_future_queue():
    robot = make_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"

    robot.queued_task_ids = [
        "ACTIVE"
    ]

    tasks = {
        "ACTIVE": make_task(
            task_id="ACTIVE"
        )
    }

    with pytest.raises(
        ValueError
    ):
        get_robot_queued_tasks(
            robot=robot,
            tasks_by_id=tasks,
        )


def test_unknown_queued_task_raises_keyerror():
    robot = make_robot(
        robot_id="M01",
    )

    robot.queued_task_ids = [
        "DOES_NOT_EXIST"
    ]

    with pytest.raises(
        KeyError
    ):
        get_robot_queued_tasks(
            robot=robot,
            tasks_by_id={},
        )


# ============================================================
# Pending Queue
# ============================================================


def test_new_emergency_task_is_inserted_before_waiting_tasks():
    robot = make_robot(
        robot_id="M01",
        status="busy",
    )

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "NORMAL"
    ]

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=200.0,
    )

    tasks = {
        "NORMAL": normal,
        "EMERGENCY": emergency,
    }

    queue = build_pending_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=200.0,
        extra_task=emergency,
    )

    assert [
        task.task_id
        for task in queue
    ] == [
        "EMERGENCY",
        "NORMAL",
    ]


def test_extra_task_is_not_duplicated():
    robot = make_robot(
        robot_id="M01",
    )

    task = make_task(
        task_id="T1"
    )

    robot.queued_task_ids = [
        "T1"
    ]

    tasks = {
        "T1": task
    }

    queue = build_pending_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=0.0,
        extra_task=task,
    )

    assert len(queue) == 1

    assert queue[0].task_id == "T1"


# ============================================================
# Queue Projection - Idle Robot
# ============================================================


def test_idle_robot_projection_uses_current_location():
    robot = make_robot(
        robot_id="M01",
        current_location="charging_station_2",
        status="idle",
    )

    task = make_task(
        task_id="T1",
        source="pharmacy",
        destination="ward_a_2",
        arrival_time_s=100.0,
        service_time_s=30.0,
    )

    tasks = {
        "T1": task
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=100.0,
        travel_time_fn=fixed_travel_time,
        extra_task=task,
    )

    projected = projection.get_task(
        "T1"
    )

    assert projected is not None

    assert projected.origin == (
        "charging_station_2"
    )

    assert projected.start_time_s == (
        pytest.approx(100.0)
    )

    assert projected.approach_time_s == (
        pytest.approx(10.0)
    )

    assert (
        projected.source_arrival_time_s
        == pytest.approx(110.0)
    )

    assert (
        projected.task_travel_time_s
        == pytest.approx(10.0)
    )

    assert (
        projected.completion_time_s
        == pytest.approx(150.0)
    )


# ============================================================
# Queue Projection - Busy Robot
# ============================================================


def test_busy_robot_projection_starts_after_active_task():
    robot = make_robot(
        robot_id="M01",
        current_location="pharmacy",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"

    robot.current_task_start_time_s = (
        100.0
    )

    robot.current_task_completion_time_s = (
        300.0
    )

    robot.current_task_destination = (
        "ward_b_2"
    )

    future_task = make_task(
        task_id="NEXT",
        source="pharmacy",
        destination="ward_a_2",
        arrival_time_s=200.0,
        service_time_s=30.0,
    )

    tasks = {
        "NEXT": future_task
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=200.0,
        travel_time_fn=fixed_travel_time,
        extra_task=future_task,
    )

    projected = projection.get_task(
        "NEXT"
    )

    assert projected is not None

    assert projected.origin == (
        "ward_b_2"
    )

    assert projected.start_time_s == (
        pytest.approx(300.0)
    )


def test_active_task_is_never_projected_as_future_task():
    robot = make_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"

    robot.current_task_completion_time_s = (
        300.0
    )

    robot.current_task_destination = (
        "ward_a_2"
    )

    future = make_task(
        task_id="FUTURE"
    )

    robot.queued_task_ids = [
        "FUTURE"
    ]

    tasks = {
        "FUTURE": future
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=100.0,
        travel_time_fn=fixed_travel_time,
    )

    projected_ids = [
        item.task_id
        for item
        in projection.projected_tasks
    ]

    assert "ACTIVE" not in (
        projected_ids
    )

    assert projected_ids == [
        "FUTURE"
    ]


# ============================================================
# Projected Timing Consistency
# ============================================================


def test_projected_tasks_do_not_overlap():
    robot = make_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    task_1 = make_task(
        task_id="T1",
        source="pharmacy",
        destination="ward_a_2",
        priority=PRIORITY_HIGH,
        arrival_time_s=0.0,
        service_time_s=30.0,
    )

    task_2 = make_task(
        task_id="T2",
        source="pharmacy",
        destination="ward_b_2",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
        service_time_s=30.0,
    )

    robot.queued_task_ids = [
        "T1",
        "T2",
    ]

    tasks = {
        "T1": task_1,
        "T2": task_2,
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=0.0,
        travel_time_fn=fixed_travel_time,
    )

    first = (
        projection.projected_tasks[0]
    )

    second = (
        projection.projected_tasks[1]
    )

    assert (
        second.start_time_s
        >= first.completion_time_s
    )


def test_previous_destination_becomes_next_origin():
    robot = make_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    task_1 = make_task(
        task_id="T1",
        source="pharmacy",
        destination="ward_a_2",
        priority=PRIORITY_HIGH,
    )

    task_2 = make_task(
        task_id="T2",
        source="lab",
        destination="ward_b_2",
        priority=PRIORITY_NORMAL,
    )

    robot.queued_task_ids = [
        "T1",
        "T2",
    ]

    tasks = {
        "T1": task_1,
        "T2": task_2,
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=0.0,
        travel_time_fn=fixed_travel_time,
    )

    first = (
        projection.projected_tasks[0]
    )

    second = (
        projection.projected_tasks[1]
    )

    assert first.task_id == "T1"

    assert second.task_id == "T2"

    assert second.origin == (
        task_1.destination
    )


# ============================================================
# Projection Must Not Mutate Real State
# ============================================================


def test_projection_does_not_modify_robot_state():
    robot = make_robot(
        robot_id="M01",
    )

    existing = make_task(
        task_id="OLD",
        priority=PRIORITY_NORMAL,
    )

    incoming = make_task(
        task_id="NEW",
        priority=PRIORITY_EMERGENCY,
    )

    robot.queued_task_ids = [
        "OLD"
    ]

    tasks = {
        "OLD": existing,
        "NEW": incoming,
    }

    before = copy.deepcopy(
        robot
    )

    project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=100.0,
        travel_time_fn=fixed_travel_time,
        extra_task=incoming,
    )

    assert (
        robot.queued_task_ids
        == before.queued_task_ids
    )

    assert (
        robot.current_location
        == before.current_location
    )

    assert (
        robot.current_task_id
        == before.current_task_id
    )


def test_projection_does_not_modify_task_state():
    robot = make_robot(
        robot_id="M01",
    )

    task = make_task(
        task_id="T1"
    )

    tasks = {
        "T1": task
    }

    before = copy.deepcopy(
        task
    )

    project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=100.0,
        travel_time_fn=fixed_travel_time,
        extra_task=task,
    )

    assert (
        task.assigned_robot
        == before.assigned_robot
    )

    assert (
        task.start_time_s
        == before.start_time_s
    )

    assert (
        task.source_arrival_time_s
        == before.source_arrival_time_s
    )

    assert (
        task.completion_time_s
        == before.completion_time_s
    )


# ============================================================
# Candidate Evaluation
# ============================================================


def test_evaluate_candidate_robot():
    robot = make_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    task = make_task(
        task_id="T1",
        source="pharmacy",
        destination="ward_a_2",
        arrival_time_s=100.0,
        service_time_s=30.0,
    )

    tasks = {
        "T1": task
    }

    candidate = (
        evaluate_candidate_robot(
            robot=robot,
            task=task,
            tasks_by_id=tasks,
            current_time_s=100.0,
            travel_time_fn=(
                fixed_travel_time
            ),
        )
    )

    assert candidate.robot_id == (
        "M01"
    )

    assert candidate.task_id == (
        "T1"
    )

    assert (
        candidate.projected_queue_position
        == 1
    )

    assert (
        candidate.projected_approach_time_s
        == pytest.approx(10.0)
    )

    assert (
        candidate.projected_waiting_time_s
        == pytest.approx(0.0)
    )

    assert (
        candidate.projected_response_time_s
        == pytest.approx(10.0)
    )


def test_evaluate_infeasible_candidate_raises_error():
    clean = make_robot(
        robot_id="C01",
        robot_type=ROBOT_TYPE_CLEAN,
    )

    specimen = make_task(
        task_id="SPEC",
        task_type=TASK_SPECIMEN,
    )

    with pytest.raises(
        ValueError
    ):
        evaluate_candidate_robot(
            robot=clean,
            task=specimen,
            tasks_by_id={
                "SPEC": specimen
            },
            current_time_s=0.0,
            travel_time_fn=(
                fixed_travel_time
            ),
        )


def test_evaluate_feasible_candidates_for_medication():
    clean = make_robot(
        robot_id="C01",
        robot_type=ROBOT_TYPE_CLEAN,
    )

    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
    )

    ward = make_robot(
        robot_id="W01",
        robot_type=ROBOT_TYPE_WARD,
    )

    task = make_task(
        task_id="MED",
        task_type=TASK_MEDICATION,
    )

    tasks = {
        "MED": task
    }

    candidates = (
        evaluate_feasible_candidates(
            robots=[
                ward,
                clean,
                medical,
            ],
            task=task,
            tasks_by_id=tasks,
            current_time_s=0.0,
            travel_time_fn=(
                fixed_travel_time
            ),
        )
    )

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M01",
        "W01",
    ]


# ============================================================
# Queue Commit
# ============================================================


def test_apply_projected_queue_order():
    robot = make_robot(
        robot_id="M01",
    )

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
    )

    robot.queued_task_ids = [
        "NORMAL"
    ]

    tasks = {
        "NORMAL": normal,
        "EMERGENCY": emergency,
    }

    projection = project_robot_queue(
        robot=robot,
        tasks_by_id=tasks,
        current_time_s=0.0,
        travel_time_fn=fixed_travel_time,
        extra_task=emergency,
    )

    # Projection itself must not change real state.
    assert robot.queued_task_ids == [
        "NORMAL"
    ]

    apply_projected_queue_order(
        robot=robot,
        projection=projection,
    )

    assert robot.queued_task_ids == [
        "EMERGENCY",
        "NORMAL",
    ]


def test_apply_projection_to_wrong_robot_raises_error():
    robot_1 = make_robot(
        robot_id="M01",
    )

    robot_2 = make_robot(
        robot_id="M02",
    )

    task = make_task(
        task_id="T1"
    )

    projection = project_robot_queue(
        robot=robot_1,
        tasks_by_id={
            "T1": task
        },
        current_time_s=0.0,
        travel_time_fn=fixed_travel_time,
        extra_task=task,
    )

    with pytest.raises(
        ValueError
    ):
        apply_projected_queue_order(
            robot=robot_2,
            projection=projection,
        )


# ============================================================
# Travel-Time Validation
# ============================================================


def test_negative_approach_time_raises_error():
    robot = make_robot(
        robot_id="M01",
    )

    task = make_task(
        task_id="T1"
    )

    def invalid_travel_time(
        source: str,
        destination: str,
    ) -> float:
        return -1.0

    with pytest.raises(
        ValueError
    ):
        project_robot_queue(
            robot=robot,
            tasks_by_id={
                "T1": task
            },
            current_time_s=0.0,
            travel_time_fn=(
                invalid_travel_time
            ),
            extra_task=task,
        )


# ============================================================
# Validation
# ============================================================


def test_validate_supported_priorities():
    validate_priority(
        PRIORITY_LOW
    )

    validate_priority(
        PRIORITY_NORMAL
    )

    validate_priority(
        PRIORITY_HIGH
    )

    validate_priority(
        PRIORITY_EMERGENCY
    )


def test_validate_invalid_priority_raises_error():
    with pytest.raises(
        ValueError
    ):
        validate_priority(
            999
        )


def test_validate_task_rejects_same_source_destination():
    task = make_task(
        task_id="T1",
        source="pharmacy",
        destination="pharmacy",
    )

    with pytest.raises(
        ValueError
    ):
        validate_task(
            task
        )


def test_validate_task_rejects_negative_service_time():
    task = make_task(
        task_id="T1",
        service_time_s=-1.0,
    )

    with pytest.raises(
        ValueError
    ):
        validate_task(
            task
        )


def test_validate_robot_rejects_active_task_in_queue():
    robot = make_robot(
        robot_id="M01"
    )

    robot.current_task_id = "ACTIVE"

    robot.queued_task_ids = [
        "ACTIVE"
    ]

    with pytest.raises(
        ValueError
    ):
        validate_robot(
            robot
        )


def test_validate_scheduler_state_rejects_duplicate_robot_ids():
    robot_1 = make_robot(
        robot_id="M01"
    )

    robot_2 = make_robot(
        robot_id="M01"
    )

    task = make_task(
        task_id="T1"
    )

    with pytest.raises(
        ValueError
    ):
        validate_scheduler_state(
            robots=[
                robot_1,
                robot_2,
            ],
            tasks_by_id={
                "T1": task
            },
        )


def test_validate_scheduler_state_accepts_valid_state():
    clean = make_robot(
        robot_id="C01",
        robot_type=ROBOT_TYPE_CLEAN,
    )

    medical = make_robot(
        robot_id="M01",
        robot_type=ROBOT_TYPE_MEDICAL,
    )

    ward = make_robot(
        robot_id="W01",
        robot_type=ROBOT_TYPE_WARD,
    )

    tasks = {
        "T1": make_task(
            task_id="T1",
            task_type=TASK_MEDICATION,
        ),
        "T2": make_task(
            task_id="T2",
            task_type=TASK_WASTE,
            source="ward_a_2",
            destination="waste_return_2",
        ),
    }

    # Should not raise.
    validate_scheduler_state(
        robots=[
            clean,
            medical,
            ward,
        ],
        tasks_by_id=tasks,
    )


def test_battery_candidate_filter_rejects_incoming_task_when_infeasible():

    def fake_travel_time(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        return 600.0

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
        current_location="charging_station_2",
        status="idle",
        battery_soc=0.30,
    )

    evaluations = (
        evaluate_battery_feasible_placement_candidates(
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

    assert [
        evaluation.robot_id
        for evaluation
        in evaluations
    ] == [
        "M01",
    ]


def test_battery_candidate_filter_allows_incoming_when_downstream_is_released():

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

    evaluations = (
        evaluate_battery_feasible_placement_candidates(
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

    assert len(
        evaluations
    ) == 1

    assert (
        evaluations[0]
        .robot_id
        == "M01"
    )