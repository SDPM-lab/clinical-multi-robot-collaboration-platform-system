from __future__ import annotations

import copy

import numpy as np
import pytest

from experiments.fleet_sizing.config import (
    CHARGING_WAYPOINT,
    ROBOT_CAPABILITIES,
    ROBOT_TYPE_CLEAN,
    ROBOT_TYPE_MEDICAL,
    ROBOT_TYPE_WARD,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)

from experiments.fleet_sizing.rl.observation import (
    BATTERY_LAYOUT,
    DEFAULT_LAYOUT,
    LOCATIONS,
    ObservationEncoder,
    calculate_load_imbalance,
    observable_load,
    robot_battery_unavailable,
)


# ============================================================
# Helpers
# ============================================================


ROBOT_IDS = (
    "C01",
    "C02",
    "M01",
    "M02",
    "W01",
    "W02",
    "W03",
)


def make_robot(
    robot_id: str,
    robot_type: str,
    *,
    current_location: str = CHARGING_WAYPOINT,
    status: str = "idle",
    current_task_id: str | None = None,
    current_task_destination: str | None = None,
    queued_task_ids: list[str] | None = None,
    current_task_completion_time_s: float | None = None,
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=robot_type,
        capabilities=sorted(
            ROBOT_CAPABILITIES[
                robot_type
            ]
        ),
        current_location=current_location,
        status=status,
        current_task_id=current_task_id,
        current_task_destination=(
            current_task_destination
        ),
        current_task_completion_time_s=(
            current_task_completion_time_s
        ),
        queued_task_ids=list(
            queued_task_ids or []
        ),
        available_time_s=0.0,
        future_location=current_location,
    )


def make_fleet() -> list[
    RobotState
]:

    return [
        make_robot(
            "C01",
            ROBOT_TYPE_CLEAN,
        ),
        make_robot(
            "C02",
            ROBOT_TYPE_CLEAN,
        ),
        make_robot(
            "M01",
            ROBOT_TYPE_MEDICAL,
        ),
        make_robot(
            "M02",
            ROBOT_TYPE_MEDICAL,
        ),
        make_robot(
            "W01",
            ROBOT_TYPE_WARD,
        ),
        make_robot(
            "W02",
            ROBOT_TYPE_WARD,
        ),
        make_robot(
            "W03",
            ROBOT_TYPE_WARD,
        ),
    ]


def make_task(
    task_id: str = "T001",
    task_type: str = "medication_delivery",
    priority: int = 2,
    source: str = "pharmacy",
    destination: str = "ward_a_2",
    arrival_time_s: float = 100.0,
    service_time_s: float = 999.0,
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


def fake_travel_time(
    source: str,
    destination: str,
) -> float:

    if source == destination:
        return 0.0

    table = {
        (
            CHARGING_WAYPOINT,
            "pharmacy",
        ): 100.0,

        (
            "ward_a_2",
            "pharmacy",
        ): 50.0,

        (
            "ward_b_2",
            "pharmacy",
        ): 200.0,

        (
            "pharmacy",
            "ward_a_2",
        ): 120.0,

        (
            "pharmacy",
            "ward_b_2",
        ): 180.0,
    }

    return table.get(
        (
            source,
            destination,
        ),
        150.0,
    )


def make_encoder() -> ObservationEncoder:

    return ObservationEncoder(
        robot_ids=ROBOT_IDS
    )


# ============================================================
# Layout
# ============================================================


def test_default_observation_size_is_84():

    assert (
        DEFAULT_LAYOUT.total_size
        == 84
    )


def test_encoder_reports_expected_size():

    encoder = make_encoder()

    assert (
        encoder.observation_size
        == 84
    )


def test_encoder_rejects_wrong_robot_count():

    with pytest.raises(
        ValueError
    ):

        ObservationEncoder(
            robot_ids=(
                "C01",
                "C02",
            )
        )


def test_encoder_rejects_duplicate_robot_ids():

    with pytest.raises(
        ValueError
    ):

        ObservationEncoder(
            robot_ids=(
                "C01",
                "C01",
                "M01",
                "M02",
                "W01",
                "W02",
                "W03",
            )
        )


# ============================================================
# Basic Observation
# ============================================================


def test_observation_has_expected_shape():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task()

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert (
        observation.shape
        == (
            84,
        )
    )


def test_observation_dtype_is_float32():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task()

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert (
        observation.dtype
        == np.float32
    )


def test_observation_is_finite():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task()

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert np.all(
        np.isfinite(
            observation
        )
    )


# ============================================================
# Task Encoding
# ============================================================


def test_task_type_one_hot_is_correct():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task(
        task_type=(
            "medication_delivery"
        )
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    task_type_vector = (
        observation[
            0:5
        ]
    )

    assert np.array_equal(
        task_type_vector,
        np.asarray(
            [
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
            ],
            dtype=np.float32,
        )
    )


def test_priority_one_hot_is_correct():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task(
        priority=3
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    priority_vector = (
        observation[
            5:9
        ]
    )

    assert np.array_equal(
        priority_vector,
        np.asarray(
            [
                0.0,
                0.0,
                0.0,
                1.0,
            ],
            dtype=np.float32,
        )
    )


# ============================================================
def test_source_one_hot_is_correct():

    encoder = make_encoder()
    robots = make_fleet()

    task = make_task(
        source="pharmacy",
        destination="ward_a_2",
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id: task
        },
        current_time_s=100.0,
        travel_time_fn=fake_travel_time,
    )

    source_vector = observation[9:25]

    expected = np.zeros(
        16,
        dtype=np.float32,
    )

    expected[
        LOCATIONS.index(
            "pharmacy"
        )
    ] = 1.0

    assert np.array_equal(
        source_vector,
        expected,
    )


def test_destination_one_hot_is_correct():

    encoder = make_encoder()
    robots = make_fleet()

    task = make_task(
        source="pharmacy",
        destination="ward_a_2",
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id: task
        },
        current_time_s=100.0,
        travel_time_fn=fake_travel_time,
    )

    destination_vector = (
        observation[25:41]
    )

    expected = np.zeros(
        16,
        dtype=np.float32,
    )

    expected[
        LOCATIONS.index(
            "ward_a_2"
        )
    ] = 1.0

    assert np.array_equal(
        destination_vector,
        expected,
    )


def test_different_destination_changes_observation():

    encoder = make_encoder()

    robots = make_fleet()

    first_task = make_task(
        source="pharmacy",
        destination="ward_a_2",
    )

    second_task = make_task(
        source="pharmacy",
        destination="ward_b_2",
    )

    first = encoder.encode(
        task=first_task,
        robots=robots,
        tasks_by_id={
            first_task.task_id:
            first_task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    second = encoder.encode(
        task=second_task,
        robots=robots,
        tasks_by_id={
            second_task.task_id:
            second_task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert not np.array_equal(
        first,
        second,
    )


def test_unknown_source_is_rejected():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task(
        source="unknown_room",
        destination="ward_a_2",
    )

    with pytest.raises(
        ValueError
    ):
        encoder.encode(
            task=task,
            robots=robots,
            tasks_by_id={
                task.task_id:
                task
            },
            current_time_s=100.0,
            travel_time_fn=(
                fake_travel_time
            ),
        )


# ============================================================
# Robot Feature Helpers
# ============================================================


def test_observable_load_idle_empty_is_zero():

    robot = make_robot(
        "M01",
        ROBOT_TYPE_MEDICAL,
    )

    assert (
        observable_load(
            robot
        )
        == 0
    )


def test_observable_load_busy_plus_queue():

    robot = make_robot(
        "M01",
        ROBOT_TYPE_MEDICAL,
        status="busy",
        current_task_id="ACTIVE",
        current_task_destination=(
            "ward_a_2"
        ),
        queued_task_ids=[
            "Q1",
            "Q2",
        ],
    )

    assert (
        observable_load(
            robot
        )
        == 3
    )


def test_load_imbalance_zero_when_all_idle():

    robots = make_fleet()

    assert (
        calculate_load_imbalance(
            robots
        )
        == pytest.approx(
            0.0
        )
    )


def test_load_imbalance_one_for_maximal_spread():

    robots = make_fleet()

    robots[2].status = "busy"
    robots[2].current_task_id = (
        "ACTIVE"
    )

    assert (
        calculate_load_imbalance(
            robots
        )
        == pytest.approx(
            1.0
        )
    )


# ============================================================
# Capability / Feasibility Representation
# ============================================================


def test_medication_capability_features():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task(
        task_type=(
            "medication_delivery"
        )
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    robot_start = 41
    feature_size = 6

    capability_values = []

    for index in range(
        7
    ):

        offset = (
            robot_start
            + (
                index
                * feature_size
            )
        )

        capability_values.append(
            observation[
                offset
            ]
        )

    assert capability_values == [
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    ]


def test_specimen_only_medical_has_capability():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task(
        task_type=(
            "specimen_delivery"
        ),
        source="ward_a_2",
        destination="lab",
    )

    observation = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    robot_start = 41
    feature_size = 6

    capability_values = [
        observation[
            robot_start
            + index
            * feature_size
        ]
        for index
        in range(7)
    ]

    assert capability_values == [
        0.0,
        0.0,
        1.0,
        1.0,
        0.0,
        0.0,
        0.0,
    ]


# ============================================================
# Determinism
# ============================================================


def test_same_state_produces_same_observation():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task()

    kwargs = dict(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    first = encoder.encode(
        **kwargs
    )

    second = encoder.encode(
        **kwargs
    )

    assert np.array_equal(
        first,
        second,
    )


def test_robot_input_order_does_not_change_observation():

    encoder = make_encoder()

    robots = make_fleet()

    task = make_task()

    first = encoder.encode(
        task=task,
        robots=robots,
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    second = encoder.encode(
        task=task,
        robots=list(
            reversed(
                robots
            )
        ),
        tasks_by_id={
            task.task_id:
            task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert np.array_equal(
        first,
        second,
    )


# ============================================================
# Anti-Leakage
# ============================================================


def test_incoming_service_time_does_not_change_observation():

    encoder = make_encoder()

    robots = make_fleet()

    first_task = make_task(
        service_time_s=10.0
    )

    second_task = make_task(
        service_time_s=99999.0
    )

    first = encoder.encode(
        task=first_task,
        robots=robots,
        tasks_by_id={
            first_task.task_id:
            first_task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    second = encoder.encode(
        task=second_task,
        robots=robots,
        tasks_by_id={
            second_task.task_id:
            second_task
        },
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert np.array_equal(
        first,
        second,
    )


def test_active_actual_completion_time_does_not_change_observation():

    encoder = make_encoder()

    task = make_task()

    robots_a = make_fleet()

    robots_a[2].status = "busy"
    robots_a[2].current_task_id = (
        "ACTIVE"
    )
    robots_a[2].current_task_destination = (
        "ward_a_2"
    )
    robots_a[2].current_task_completion_time_s = (
        200.0
    )

    robots_b = copy.deepcopy(
        robots_a
    )

    robots_b[2].current_task_completion_time_s = (
        999999.0
    )

    active_task = TaskState(
        task_id="ACTIVE",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=0.0,
        service_time_s=50000.0,
        status="active",
    )

    tasks_by_id = {
        task.task_id:
        task,

        active_task.task_id:
        active_task,
    }

    first = encoder.encode(
        task=task,
        robots=robots_a,
        tasks_by_id=tasks_by_id,
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    second = encoder.encode(
        task=task,
        robots=robots_b,
        tasks_by_id=tasks_by_id,
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert np.array_equal(
        first,
        second,
    )


def test_existing_queued_service_time_does_not_change_observation():

    encoder = make_encoder()

    incoming = make_task()

    robots = make_fleet()

    robots[2].status = "busy"
    robots[2].current_task_id = (
        "ACTIVE"
    )
    robots[2].current_task_destination = (
        "ward_a_2"
    )
    robots[2].queued_task_ids = [
        "Q1"
    ]

    active_task = TaskState(
        task_id="ACTIVE",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=0.0,
        service_time_s=123.0,
        status="active",
    )

    queued_a = TaskState(
        task_id="Q1",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_b_2",
        priority=1,
        arrival_time_s=50.0,
        service_time_s=10.0,
        status="assigned",
    )

    queued_b = copy.deepcopy(
        queued_a
    )

    queued_b.service_time_s = (
        999999.0
    )

    tasks_a = {
        incoming.task_id:
        incoming,

        active_task.task_id:
        active_task,

        queued_a.task_id:
        queued_a,
    }

    tasks_b = {
        incoming.task_id:
        incoming,

        active_task.task_id:
        active_task,

        queued_b.task_id:
        queued_b,
    }

    first = encoder.encode(
        task=incoming,
        robots=robots,
        tasks_by_id=tasks_a,
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    second = encoder.encode(
        task=incoming,
        robots=robots,
        tasks_by_id=tasks_b,
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert np.array_equal(
        first,
        second,
    )

def test_battery_observation_layout_size():

    assert (
        BATTERY_LAYOUT.total_size
        == 98
    )


def test_default_observation_layout_size():

    assert (
        DEFAULT_LAYOUT.total_size
        == 84
    )


def test_battery_unavailable_status():

    robot = make_robot(
        robot_id="M01",
        robot_type="medical",
        status="charging",
    )

    assert (
        robot_battery_unavailable(
            robot
        )
        == 1.0
    )

    robot.status = "idle"

    assert (
        robot_battery_unavailable(
            robot
        )
        == 0.0
    )