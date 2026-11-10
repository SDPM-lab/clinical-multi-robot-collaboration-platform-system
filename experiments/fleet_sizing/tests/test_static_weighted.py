from __future__ import annotations

import copy

import pytest

from experiments.fleet_sizing.baseline.static_weighted import (
    StaticWeightedCandidate,
    StaticWeightedDecision,
    StaticWeightedScheduler,
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
    scheduler = StaticWeightedScheduler()

    assert (
        scheduler.NAME
        == "static_weighted"
    )


def test_default_alpha_is_0_5():
    scheduler = StaticWeightedScheduler()

    assert (
        scheduler.alpha
        == pytest.approx(0.5)
    )


def test_custom_alpha_is_stored():
    scheduler = StaticWeightedScheduler(
        alpha=0.7
    )

    assert (
        scheduler.alpha
        == pytest.approx(0.7)
    )


@pytest.mark.parametrize(
    "alpha",
    [
        -0.1,
        1.1,
        -10.0,
        5.0,
    ],
)
def test_invalid_alpha_raises(
    alpha: float,
):
    with pytest.raises(
        ValueError
    ):
        StaticWeightedScheduler(
            alpha=alpha
        )


@pytest.mark.parametrize(
    "alpha",
    [
        0.0,
        0.5,
        1.0,
    ],
)
def test_boundary_and_middle_alpha_are_valid(
    alpha: float,
):
    scheduler = StaticWeightedScheduler(
        alpha=alpha
    )

    assert (
        scheduler.alpha
        == pytest.approx(alpha)
    )


# ============================================================
# Observable Load
# ============================================================


def test_idle_robot_with_empty_queue_has_zero_load():
    robot = make_medical_robot()

    assert (
        StaticWeightedScheduler
        .get_observable_load(
            robot
        )
        == 0
    )


def test_busy_robot_with_empty_queue_has_load_one():
    robot = make_medical_robot(
        status="busy"
    )

    robot.current_task_id = "ACTIVE"

    assert (
        StaticWeightedScheduler
        .get_observable_load(
            robot
        )
        == 1
    )


def test_idle_robot_with_two_queued_tasks_has_load_two():
    robot = make_medical_robot()

    robot.queued_task_ids = [
        "T1",
        "T2",
    ]

    assert (
        StaticWeightedScheduler
        .get_observable_load(
            robot
        )
        == 2
    )


def test_busy_robot_with_two_queued_tasks_has_load_three():
    robot = make_medical_robot(
        status="busy"
    )

    robot.current_task_id = "ACTIVE"

    robot.queued_task_ids = [
        "T1",
        "T2",
    ]

    assert (
        StaticWeightedScheduler
        .get_observable_load(
            robot
        )
        == 3
    )


# ============================================================
# Normalization
# ============================================================


def test_normalize_by_max():
    value = (
        StaticWeightedScheduler
        .normalize_by_max(
            value=20.0,
            maximum=100.0,
        )
    )

    assert (
        value
        == pytest.approx(0.2)
    )


def test_normalize_zero_max_returns_zero():
    value = (
        StaticWeightedScheduler
        .normalize_by_max(
            value=0.0,
            maximum=0.0,
        )
    )

    assert (
        value
        == pytest.approx(0.0)
    )


def test_negative_normalization_value_raises():
    with pytest.raises(
        ValueError
    ):
        (
            StaticWeightedScheduler
            .normalize_by_max(
                value=-1.0,
                maximum=10.0,
            )
        )


def test_negative_normalization_maximum_raises():
    with pytest.raises(
        ValueError
    ):
        (
            StaticWeightedScheduler
            .normalize_by_max(
                value=1.0,
                maximum=-10.0,
            )
        )


# ============================================================
# Capability / Feasibility
# ============================================================


def test_medication_candidates_include_medical_and_ward_only():
    scheduler = StaticWeightedScheduler()

    task = make_task(
        task_type=TASK_MEDICATION,
    )

    robots = [
        make_clean_robot("C01"),
        make_medical_robot("M01"),
        make_ward_robot("W01"),
    ]

    candidates = scheduler.build_candidates(
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

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M01",
        "W01",
    ]


def test_specimen_only_medical_is_candidate():
    scheduler = StaticWeightedScheduler()

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

    candidates = scheduler.build_candidates(
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

    assert [
        candidate.robot_id
        for candidate
        in candidates
    ] == [
        "M01",
    ]


def test_busy_robot_can_be_candidate():
    scheduler = StaticWeightedScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        status="busy",
    )

    robot.current_task_id = "ACTIVE"
    robot.current_task_start_time_s = 0.0
    robot.current_task_completion_time_s = 9999.0
    robot.current_task_destination = "ward_b_2"

    task = make_task(
        task_id="NEW",
    )

    candidates = scheduler.build_candidates(
        robots=[
            robot,
        ],
        task=task,
        tasks_by_id={
            "NEW": task,
        },
        current_time_s=100.0,
        travel_time_fn=(
            constant_travel_time
        ),
    )

    assert len(
        candidates
    ) == 1

    assert (
        candidates[0].robot_id
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
def test_unavailable_robot_is_not_candidate(
    status: str,
):
    scheduler = StaticWeightedScheduler()

    robot = make_medical_robot(
        robot_id="M01",
        status=status,
    )

    task = make_task()

    candidates = scheduler.build_candidates(
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

    assert candidates == []


# ============================================================
# Cost Calculation
# ============================================================


def test_weighted_cost_is_calculated_correctly():
    """
    M01:
        approach = 20
        load = 4

    M02:
        approach = 50
        load = 1

    W01:
        approach = 100
        load = 0

    max approach = 100
    max load = 4

    alpha = 0.5

    M01:
        0.5 * 0.2
        + 0.5 * 1.0
        = 0.6
    """

    scheduler = StaticWeightedScheduler(
        alpha=0.8
    )

    task = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=100.0,
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_destination = "ward_b_2"

    m01.queued_task_ids = [
        "M01_Q1",
        "M01_Q2",
        "M01_Q3",
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    m02.queued_task_ids = [
        "M02_Q1",
    ]

    w01 = make_ward_robot(
        robot_id="W01",
        current_location="ward_a_2",
    )

    queued_tasks = {
        "M01_Q1": make_task(
            task_id="M01_Q1",
            destination="ward_b_2",
        ),
        "M01_Q2": make_task(
            task_id="M01_Q2",
            destination="ward_b_2",
        ),
        "M01_Q3": make_task(
            task_id="M01_Q3",
            destination="ward_b_2",
        ),
        "M02_Q1": make_task(
            task_id="M02_Q1",
            destination="ward_a_2",
        ),
        "NEW": task,
    }

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 50.0,
        },
        default=100.0,
    )

    # W01 must have 100 s approach.
    w01.current_location = "consult_1_2"

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 20.0,

            (
                "ward_a_2",
                "pharmacy",
            ): 50.0,

            (
                "consult_1_2",
                "pharmacy",
            ): 100.0,
        }
    )

    candidates = scheduler.build_candidates(
        robots=[
            m01,
            m02,
            w01,
        ],
        task=task,
        tasks_by_id=queued_tasks,
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    by_id = {
        candidate.robot_id: candidate
        for candidate
        in candidates
    }

    m01_candidate = by_id[
        "M01"
    ]

    assert (
        m01_candidate.observable_load
        == 4
    )

    assert (
        m01_candidate
        .normalized_approach
        == pytest.approx(0.2)
    )

    assert (
        m01_candidate
        .normalized_load
        == pytest.approx(1.0)
    )

    assert (
        m01_candidate.weighted_cost
        == pytest.approx(0.36)
    )


def test_static_weighted_can_choose_farther_less_busy_robot():
    """
    This is the main behavioral difference from
    Projected Nearest.

    M01:
        closer, but heavily loaded

    M02:
        slightly farther, but idle

    Weighted cost should choose M02.
    """

    scheduler = StaticWeightedScheduler()

    task = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=100.0,
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_b_2",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_destination = "ward_b_2"

    m01.queued_task_ids = [
        "Q1",
        "Q2",
        "Q3",
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_a_2",
    )

    queued_tasks = {
        "Q1": make_task(
            task_id="Q1",
            destination="ward_b_2",
        ),
        "Q2": make_task(
            task_id="Q2",
            destination="ward_b_2",
        ),
        "Q3": make_task(
            task_id="Q3",
            destination="ward_b_2",
        ),
        "NEW": task,
    }

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_b_2",
                "pharmacy",
            ): 20.0,

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
        task=task,
        tasks_by_id=queued_tasks,
        current_time_s=100.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M02"
    )


# ============================================================
# Alpha Extremes
# ============================================================


def test_alpha_one_behaves_as_travel_only():
    """
    alpha = 1 means workload contributes zero.
    """

    scheduler = StaticWeightedScheduler(
        alpha=1.0
    )

    task = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_destination = "ward_a_2"

    m01.queued_task_ids = [
        "Q1",
        "Q2",
        "Q3",
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    queued_tasks = {
        "Q1": make_task(
            task_id="Q1",
        ),
        "Q2": make_task(
            task_id="Q2",
        ),
        "Q3": make_task(
            task_id="Q3",
        ),
        "NEW": task,
    }

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 10.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 40.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id=queued_tasks,
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )


def test_alpha_zero_behaves_as_load_only():
    """
    alpha = 0 means travel contributes zero.
    """

    scheduler = StaticWeightedScheduler(
        alpha=0.0
    )

    task = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_destination = "ward_a_2"

    m01.queued_task_ids = [
        "Q1",
        "Q2",
    ]

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    queued_tasks = {
        "Q1": make_task(
            task_id="Q1",
        ),
        "Q2": make_task(
            task_id="Q2",
        ),
        "NEW": task,
    }

    travel_time_fn = make_travel_time_fn(
        {
            (
                "ward_a_2",
                "pharmacy",
            ): 5.0,

            (
                "ward_b_2",
                "pharmacy",
            ): 100.0,
        }
    )

    decision = scheduler.decide(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id=queued_tasks,
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M02"
    )


# ============================================================
# Tie Breakers
# ============================================================


def test_equal_cost_prefers_shorter_approach():
    scheduler = StaticWeightedScheduler(
        alpha=0.8
    )

    task = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    m01 = make_medical_robot(
        robot_id="M01",
        current_location="ward_a_2",
        status="busy",
    )

    m01.current_task_id = "ACTIVE"
    m01.current_task_destination = "ward_a_2"

    m02 = make_medical_robot(
        robot_id="M02",
        current_location="ward_b_2",
    )

    m02.queued_task_ids = [
        "Q1",
    ]

    queued_tasks = {
        "Q1": make_task(
            task_id="Q1",
            destination="ward_b_2",
        ),
        "NEW": task,
    }

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

    candidates = scheduler.build_candidates(
        robots=[
            m01,
            m02,
        ],
        task=task,
        tasks_by_id=queued_tasks,
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    # Manually ensure tie if needed by checking
    # selection-key behavior directly.
    candidate_a = copy.deepcopy(
        candidates[0]
    )

    candidate_b = copy.deepcopy(
        candidates[1]
    )

    custom_a = StaticWeightedCandidate(
        robot_id="M01",
        task_id="NEW",
        placement_evaluation=(
            candidate_a
            .placement_evaluation
        ),
        observable_load=2,
        normalized_approach=0.5,
        normalized_load=1.0,
        weighted_cost=0.5,
    )

    custom_b = StaticWeightedCandidate(
        robot_id="M02",
        task_id="NEW",
        placement_evaluation=(
            candidate_b
            .placement_evaluation
        ),
        observable_load=1,
        normalized_approach=1.0,
        normalized_load=0.0,
        weighted_cost=0.5,
    )

    selected = scheduler.select_candidate(
        [
            custom_b,
            custom_a,
        ]
    )

    assert selected is not None

    assert (
        selected.robot_id
        == "M01"
    )


def test_exact_tie_is_broken_by_robot_id():
    scheduler = StaticWeightedScheduler()

    task = make_task(
        task_id="NEW",
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
            "NEW": task,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision.selected_robot_id
        == "M01"
    )


# ============================================================
# Decision Metadata
# ============================================================


def test_decision_records_all_candidates():
    scheduler = StaticWeightedScheduler()

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

    assert (
        len(
            decision.all_candidates
        )
        == 3
    )

    assert (
        decision.alpha
        == pytest.approx(0.5)
    )


def test_no_feasible_robot_returns_clean_decision():
    scheduler = StaticWeightedScheduler()

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
        decision.selected_candidate
        is None
    )

    assert (
        decision.all_candidates
        == ()
    )

    assert (
        decision.decision_status
        == "no_feasible_robot"
    )


# ============================================================
# Queue Commit
# ============================================================


def test_commit_false_does_not_modify_robot_queues():
    scheduler = StaticWeightedScheduler()

    task = make_task(
        task_id="NEW",
    )

    m01 = make_medical_robot("M01")
    m02 = make_medical_robot("M02")

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
            "NEW": task,
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
    scheduler = StaticWeightedScheduler(
        alpha=1.0
    )

    task = make_task(
        task_id="NEW",
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
            "NEW": task,
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
            "NEW",
        ]
    )

    assert (
        m02.queued_task_ids
        == []
    )


def test_emergency_queue_order_is_preserved_when_committed():
    scheduler = StaticWeightedScheduler()

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
# Iterable / Determinism
# ============================================================


def test_input_robot_order_does_not_change_decision():
    task_a = make_task(
        task_id="NEW",
        source="pharmacy",
    )

    task_b = copy.deepcopy(
        task_a
    )

    scheduler_a = StaticWeightedScheduler()
    scheduler_b = StaticWeightedScheduler()

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
            ): 10.0,

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
            "NEW": task_a,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=robots_b,
        task=task_b,
        tasks_by_id={
            "NEW": task_b,
        },
        current_time_s=0.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )


def test_generator_input_works_with_commit_true():
    scheduler = StaticWeightedScheduler(
        alpha=1.0
    )

    task = make_task(
        task_id="NEW",
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
            "NEW": task,
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
            "NEW",
        ]
    )


# ============================================================
# Anti-Leakage
# ============================================================


def test_incoming_service_time_does_not_change_decision():
    scheduler_a = StaticWeightedScheduler()
    scheduler_b = StaticWeightedScheduler()

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
    )


def test_existing_queue_service_time_does_not_change_decision():
    scheduler_a = StaticWeightedScheduler()
    scheduler_b = StaticWeightedScheduler()

    old_fast = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
        service_time_s=5.0,
    )

    old_slow = make_task(
        task_id="OLD",
        source="lab",
        destination="ward_b_2",
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


def test_active_actual_completion_time_does_not_change_decision():
    scheduler_a = StaticWeightedScheduler()
    scheduler_b = StaticWeightedScheduler()

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

    decision_a = scheduler_a.decide(
        robots=robots_fast,
        task=task_a,
        tasks_by_id={
            "NEW": task_a,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    decision_b = scheduler_b.decide(
        robots=robots_slow,
        task=task_b,
        tasks_by_id={
            "NEW": task_b,
        },
        current_time_s=50.0,
        travel_time_fn=travel_time_fn,
    )

    assert (
        decision_a.selected_robot_id
        == decision_b.selected_robot_id
    )


def test_active_task_service_time_does_not_change_decision():
    scheduler_a = StaticWeightedScheduler()
    scheduler_b = StaticWeightedScheduler()

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