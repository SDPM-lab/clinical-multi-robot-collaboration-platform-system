from __future__ import annotations

import copy

import pytest

from experiments.fleet_sizing.baseline.random_feasible import (
    RandomFeasibleDecision,
    RandomFeasibleScheduler,
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
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    assert (
        scheduler.NAME
        == "random_feasible"
    )


def test_decision_dataclass_can_be_created():
    decision = RandomFeasibleDecision(
        task_id="T1",
        selected_robot_id="M01",
        candidate_count=1,
        candidate_robot_ids=(
            "M01",
        ),
        candidate_evaluation=None,
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


def test_medication_candidates_include_medical_and_ward_only():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    candidates = (
        scheduler.get_candidates(
            robots=robots,
            task=task,
        )
    )

    assert [
        robot.robot_id
        for robot
        in candidates
    ] == [
        "M01",
        "W01",
    ]


def test_specimen_candidates_only_include_medical():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

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

    candidates = (
        scheduler.get_candidates(
            robots=robots,
            task=task,
        )
    )

    assert [
        robot.robot_id
        for robot
        in candidates
    ] == [
        "M01",
    ]


def test_ward_service_candidates_only_include_ward():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

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

    candidates = (
        scheduler.get_candidates(
            robots=robots,
            task=task,
        )
    )

    assert [
        robot.robot_id
        for robot
        in candidates
    ] == [
        "W01",
    ]


def test_clean_task_candidates_only_include_clean():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_WASTE,
        source="ward_a_2",
        destination="waste_return_2",
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    candidates = (
        scheduler.get_candidates(
            robots=robots,
            task=task,
        )
    )

    assert [
        robot.robot_id
        for robot
        in candidates
    ] == [
        "C01",
    ]


# ============================================================
# Robot Status
# ============================================================


def test_busy_feasible_robot_can_be_candidate():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robot = make_medical_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 500.0
    robot.current_task_destination = "ward_b_2"

    candidates = (
        scheduler.get_candidates(
            robots=[
                robot,
            ],
            task=task,
        )
    )

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M01",
    ]


@pytest.mark.parametrize(
    "status",
    [
        "offline",
        "error",
        "charging",
    ],
)
def test_unavailable_robot_status_is_not_candidate(
    status: str,
):
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robot = make_medical_robot(
        robot_id="M01",
        status=status,
    )

    candidates = (
        scheduler.get_candidates(
            robots=[
                robot,
            ],
            task=task,
        )
    )

    assert candidates == []


# ============================================================
# Candidate Ordering
# ============================================================


def test_candidates_are_sorted_by_robot_id():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_ward_robot("W02"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
        make_medical_robot("M01"),
    ]

    candidates = (
        scheduler.get_candidates(
            robots=robots,
            task=task,
        )
    )

    assert [
        robot.robot_id
        for robot
        in candidates
    ] == [
        "M01",
        "M02",
        "W01",
        "W02",
    ]


# ============================================================
# Robot Selection
# ============================================================


def test_select_robot_returns_none_when_no_feasible_robot():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_SPECIMEN,
    )

    robots = [
        make_clean_robot("C01"),
        make_ward_robot("W01"),
    ]

    selected = (
        scheduler.select_robot(
            robots=robots,
            task=task,
        )
    )

    assert selected is None


def test_select_robot_always_selects_feasible_robot():
    scheduler = (
        RandomFeasibleScheduler(
            seed=123
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    for _ in range(100):

        selected = (
            scheduler.select_robot(
                robots=robots,
                task=task,
            )
        )

        assert selected is not None

        assert (
            selected.robot_id
            in {
                "M01",
                "W01",
            }
        )


# ============================================================
# Reproducibility
# ============================================================


def test_same_seed_produces_same_random_sequence():
    scheduler_a = (
        RandomFeasibleScheduler(
            seed=12345
        )
    )

    scheduler_b = (
        RandomFeasibleScheduler(
            seed=12345
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    sequence_a = [
        scheduler_a
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(30)
    ]

    sequence_b = [
        scheduler_b
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(30)
    ]

    assert (
        sequence_a
        == sequence_b
    )


def test_reset_reproduces_same_sequence():
    scheduler = (
        RandomFeasibleScheduler(
            seed=42
        )
    )

    task = make_task()

    robots = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    first_sequence = [
        scheduler
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(20)
    ]

    scheduler.reset()

    second_sequence = [
        scheduler
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(20)
    ]

    assert (
        first_sequence
        == second_sequence
    )


def test_reset_with_new_seed_changes_rng_state():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task()

    robots = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    first_sequence = [
        scheduler
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(30)
    ]

    scheduler.reset(
        seed=999
    )

    second_sequence = [
        scheduler
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(30)
    ]

    assert (
        first_sequence
        != second_sequence
    )


# ============================================================
# Decision
# ============================================================


def test_decide_returns_no_feasible_robot():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

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
        decision.candidate_evaluation
        is None
    )

    assert (
        decision.decision_status
        == "no_feasible_robot"
    )


def test_decide_returns_assigned_decision():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task()

    robots = [
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
        decision.task_id
        == task.task_id
    )

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
        decision.candidate_evaluation
        is not None
    )

    assert (
        decision.decision_status
        == "assigned"
    )


# ============================================================
# Duration-Free Placement Evaluation
# ============================================================


def test_decision_contains_duration_free_placement():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    task = make_task(
        task_id="T1",
        source="pharmacy",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "charging_station_2",
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
        decision.candidate_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation.assignment_origin
        == "charging_station_2"
    )

    assert (
        evaluation
        .projected_approach_time_s
        == pytest.approx(25.0)
    )

    assert (
        evaluation
        .projected_queue_position
        == 1
    )

    assert (
        evaluation.tasks_ahead_count
        == 0
    )


def test_busy_robot_placement_uses_active_destination():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

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
        source="pharmacy",
    )

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 45.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "NEXT": task,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    evaluation = (
        decision.candidate_evaluation
    )

    assert evaluation is not None

    assert (
        evaluation.assignment_origin
        == "ward_b_2"
    )

    assert (
        evaluation
        .projected_approach_time_s
        == pytest.approx(45.0)
    )


# ============================================================
# Queue Commit
# ============================================================


def test_commit_false_does_not_modify_robot_queue():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        "M01"
    )

    existing = make_task(
        task_id="OLD",
        arrival_time_s=0.0,
    )

    incoming = make_task(
        task_id="NEW",
        arrival_time_s=100.0,
    )

    robot.queued_task_ids = [
        "OLD"
    ]

    original_queue = list(
        robot.queued_task_ids
    )

    scheduler.decide(
        robots=[
            robot,
        ],
        task=incoming,
        tasks_by_id={
            "OLD": existing,
            "NEW": incoming,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=False,
    )

    assert (
        robot.queued_task_ids
        == original_queue
    )


def test_commit_true_updates_robot_queue():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        "M01"
    )

    task = make_task(
        task_id="T1"
    )

    scheduler.decide(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "T1": task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=True,
    )

    assert (
        robot.queued_task_ids
        == [
            "T1",
        ]
    )


def test_emergency_task_moves_to_front_when_committed():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        "M01"
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


def test_active_task_is_not_reordered_or_replaced():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 500.0
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


def test_busy_robot_can_receive_future_task():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    robot = make_medical_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 500.0
    robot.current_task_destination = "ward_b_2"

    task = make_task(
        task_id="FUTURE",
    )

    decision = scheduler.decide(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "FUTURE": task,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
        commit_queue=True,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )

    assert (
        robot.queued_task_ids
        == [
            "FUTURE",
        ]
    )

    assert (
        robot.current_task_id
        == "ACTIVE"
    )


# ============================================================
# Decision Metadata
# ============================================================


def test_decision_records_all_feasible_candidates():
    scheduler = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_medical_robot("M02"),
        make_clean_robot("C01"),
        make_ward_robot("W01"),
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


def test_robot_input_order_does_not_change_seeded_selection():
    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots_a = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    robots_b = [
        make_ward_robot("W01"),
        make_medical_robot("M02"),
        make_medical_robot("M01"),
    ]

    scheduler_a = (
        RandomFeasibleScheduler(
            seed=123
        )
    )

    scheduler_b = (
        RandomFeasibleScheduler(
            seed=123
        )
    )

    decision_a = scheduler_a.decide(
        robots=robots_a,
        task=task,
        tasks_by_id={
            task.task_id: task,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
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
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )


def test_random_scheduler_can_select_multiple_robots_over_many_draws():
    scheduler = (
        RandomFeasibleScheduler(
            seed=12345
        )
    )

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    selected_ids = {
        scheduler
        .select_robot(
            robots=robots,
            task=task,
        )
        .robot_id
        for _ in range(100)
    }

    assert len(
        selected_ids
    ) > 1


# ============================================================
# Anti-Leakage
# ============================================================


def test_service_time_does_not_change_seeded_random_decision():
    """
    同樣的 observable scheduler state 與 RNG seed 下，
    改變 realized TaskState.service_time_s
    不得改變 Random Feasible 的選擇。
    """

    task_fast = make_task(
        task_id="T1",
        service_time_s=10.0,
    )

    task_slow = make_task(
        task_id="T1",
        service_time_s=10000.0,
    )

    robots_a = [
        make_medical_robot("M01"),
        make_medical_robot("M02"),
        make_ward_robot("W01"),
    ]

    robots_b = copy.deepcopy(
        robots_a
    )

    scheduler_a = (
        RandomFeasibleScheduler(
            seed=777
        )
    )

    scheduler_b = (
        RandomFeasibleScheduler(
            seed=777
        )
    )

    decision_a = scheduler_a.decide(
        robots=robots_a,
        task=task_fast,
        tasks_by_id={
            "T1": task_fast,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
        task=task_slow,
        tasks_by_id={
            "T1": task_slow,
        },
        current_time_s=0.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )

    assert (
        decision_a.candidate_robot_ids
        == decision_b.candidate_robot_ids
    )

    assert (
        decision_a.candidate_evaluation
        is not None
    )

    assert (
        decision_b.candidate_evaluation
        is not None
    )

    assert (
        decision_a
        .candidate_evaluation
        .assignment_origin
        ==
        decision_b
        .candidate_evaluation
        .assignment_origin
    )

    assert (
        decision_a
        .candidate_evaluation
        .projected_approach_time_s
        == pytest.approx(
            decision_b
            .candidate_evaluation
            .projected_approach_time_s
        )
    )


def test_active_actual_completion_time_does_not_change_seeded_decision():
    """
    改變 environment ground-truth 的
    current_task_completion_time_s
    不得影響 Random Feasible 的派工結果。
    """

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
        task_id="T1",
    )

    task_b = copy.deepcopy(
        task_a
    )

    scheduler_a = (
        RandomFeasibleScheduler(
            seed=555
        )
    )

    scheduler_b = (
        RandomFeasibleScheduler(
            seed=555
        )
    )

    decision_a = scheduler_a.decide(
        robots=robots_fast,
        task=task_a,
        tasks_by_id={
            "T1": task_a,
        },
        current_time_s=50.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    decision_b = scheduler_b.decide(
        robots=robots_slow,
        task=task_b,
        tasks_by_id={
            "T1": task_b,
        },
        current_time_s=50.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )

    assert (
        decision_a.candidate_robot_ids
        == decision_b.candidate_robot_ids
    )

    if (
        decision_a.selected_robot_id
        == "M01"
    ):

        evaluation_a = (
            decision_a
            .candidate_evaluation
        )

        evaluation_b = (
            decision_b
            .candidate_evaluation
        )

        assert evaluation_a is not None
        assert evaluation_b is not None

        assert (
            evaluation_a
            .assignment_origin
            == "ward_b_2"
        )

        assert (
            evaluation_b
            .assignment_origin
            == "ward_b_2"
        )

        assert (
            evaluation_a
            .projected_approach_time_s
            == pytest.approx(
                evaluation_b
                .projected_approach_time_s
            )
        )


def test_existing_queued_task_service_time_does_not_change_placement():
    """
    Future queue 中既有任務的 realized service time
    即使不同，也不得影響 duration-free placement。
    """

    existing_fast = make_task(
        task_id="OLD",
        source="pharmacy",
        destination="ward_b_2",
        arrival_time_s=0.0,
        service_time_s=10.0,
    )

    existing_slow = make_task(
        task_id="OLD",
        source="pharmacy",
        destination="ward_b_2",
        arrival_time_s=0.0,
        service_time_s=5000.0,
    )

    incoming_a = make_task(
        task_id="NEW",
        source="lab",
        destination="ward_a_2",
        arrival_time_s=100.0,
    )

    incoming_b = copy.deepcopy(
        incoming_a
    )

    robot_a = make_medical_robot(
        robot_id="M01",
        current_location="charging_station_2",
    )

    robot_a.queued_task_ids = [
        "OLD"
    ]

    robot_b = copy.deepcopy(
        robot_a
    )

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

    scheduler_a = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    scheduler_b = (
        RandomFeasibleScheduler(
            seed=1
        )
    )

    decision_a = scheduler_a.decide(
        robots=[
            robot_a,
        ],
        task=incoming_a,
        tasks_by_id={
            "OLD": existing_fast,
            "NEW": incoming_a,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=[
            robot_b,
        ],
        task=incoming_b,
        tasks_by_id={
            "OLD": existing_slow,
            "NEW": incoming_b,
        },
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    evaluation_a = (
        decision_a
        .candidate_evaluation
    )

    evaluation_b = (
        decision_b
        .candidate_evaluation
    )

    assert evaluation_a is not None
    assert evaluation_b is not None

    assert (
        evaluation_a
        .projected_queue_position
        ==
        evaluation_b
        .projected_queue_position
    )

    assert (
        evaluation_a
        .assignment_origin
        ==
        evaluation_b
        .assignment_origin
    )

    assert (
        evaluation_a
        .projected_approach_time_s
        == pytest.approx(
            evaluation_b
            .projected_approach_time_s
        )
    )