from __future__ import annotations

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

from experiments.fleet_sizing.rl.action_mask import (
    ActionMaskBuilder,
)


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
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=robot_type,
        capabilities=sorted(
            ROBOT_CAPABILITIES[
                robot_type
            ]
        ),
        current_location=(
            CHARGING_WAYPOINT
        ),
        status=status,
        available_time_s=0.0,
        future_location=(
            CHARGING_WAYPOINT
        ),
    )


def make_fleet():

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
    task_type: str,
) -> TaskState:

    return TaskState(
        task_id="T001",
        task_type=task_type,
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=999.0,
    )


def make_builder():

    return ActionMaskBuilder(
        robot_ids=ROBOT_IDS
    )


def test_action_count_is_seven():

    builder = make_builder()

    assert (
        builder.action_count
        == 7
    )


def test_duplicate_robot_ids_rejected():

    with pytest.raises(
        ValueError
    ):

        ActionMaskBuilder(
            robot_ids=(
                "C01",
                "C01",
            )
        )


def test_empty_robot_ids_rejected():

    with pytest.raises(
        ValueError
    ):

        ActionMaskBuilder(
            robot_ids=()
        )


def test_medication_mask():

    builder = make_builder()

    mask = builder.build(
        task=make_task(
            "medication_delivery"
        ),
        robots=make_fleet(),
    )

    expected = np.asarray(
        [
            False,
            False,
            True,
            True,
            True,
            True,
            True,
        ],
        dtype=np.bool_,
    )

    assert np.array_equal(
        mask,
        expected,
    )


def test_specimen_mask():

    builder = make_builder()

    mask = builder.build(
        task=make_task(
            "specimen_delivery"
        ),
        robots=make_fleet(),
    )

    expected = np.asarray(
        [
            False,
            False,
            True,
            True,
            False,
            False,
            False,
        ],
        dtype=np.bool_,
    )

    assert np.array_equal(
        mask,
        expected,
    )


def test_waste_mask():

    builder = make_builder()

    mask = builder.build(
        task=make_task(
            "waste_transport"
        ),
        robots=make_fleet(),
    )

    expected = np.asarray(
        [
            True,
            True,
            False,
            False,
            False,
            False,
            False,
        ],
        dtype=np.bool_,
    )

    assert np.array_equal(
        mask,
        expected,
    )


def test_ward_service_mask():

    builder = make_builder()

    mask = builder.build(
        task=make_task(
            "ward_service"
        ),
        robots=make_fleet(),
    )

    expected = np.asarray(
        [
            False,
            False,
            False,
            False,
            True,
            True,
            True,
        ],
        dtype=np.bool_,
    )

    assert np.array_equal(
        mask,
        expected,
    )


def test_busy_feasible_robot_is_still_valid():

    builder = make_builder()

    robots = make_fleet()

    robots[2].status = "busy"

    mask = builder.build(
        task=make_task(
            "specimen_delivery"
        ),
        robots=robots,
    )

    assert bool(
        mask[2]
    )


@pytest.mark.parametrize(
    "status",
    [
        "offline",
        "error",
        "charging",
    ],
)
def test_unavailable_robot_is_masked(
    status,
):

    builder = make_builder()

    robots = make_fleet()

    robots[2].status = status

    mask = builder.build(
        task=make_task(
            "specimen_delivery"
        ),
        robots=robots,
    )

    assert not bool(
        mask[2]
    )

    assert bool(
        mask[3]
    )


def test_robot_input_order_does_not_change_mask():

    builder = make_builder()

    robots = make_fleet()

    task = make_task(
        "medication_delivery"
    )

    first = builder.build(
        task=task,
        robots=robots,
    )

    second = builder.build(
        task=task,
        robots=list(
            reversed(
                robots
            )
        ),
    )

    assert np.array_equal(
        first,
        second,
    )


def test_feasible_action_indices():

    builder = make_builder()

    indices = (
        builder
        .feasible_action_indices(
            task=make_task(
                "specimen_delivery"
            ),
            robots=make_fleet(),
        )
    )

    assert indices == (
        2,
        3,
    )


def test_action_to_robot_mapping():

    builder = make_builder()

    assert (
        builder
        .robot_id_from_action(
            0
        )
        == "C01"
    )

    assert (
        builder
        .robot_id_from_action(
            6
        )
        == "W03"
    )


def test_invalid_action_index_raises():

    builder = make_builder()

    with pytest.raises(
        IndexError
    ):
        builder.robot_id_from_action(
            7
        )


def test_robot_to_action_mapping():

    builder = make_builder()

    assert (
        builder
        .action_from_robot_id(
            "M02"
        )
        == 3
    )


def test_unknown_robot_id_raises():

    builder = make_builder()

    with pytest.raises(
        KeyError
    ):
        builder.action_from_robot_id(
            "UNKNOWN"
        )


def test_validate_feasible_action():

    builder = make_builder()

    assert builder.validate_action(
        action=2,
        task=make_task(
            "specimen_delivery"
        ),
        robots=make_fleet(),
    )


def test_validate_infeasible_action():

    builder = make_builder()

    assert not (
        builder.validate_action(
            action=0,
            task=make_task(
                "specimen_delivery"
            ),
            robots=make_fleet(),
        )
    )


def test_validate_out_of_range_action():

    builder = make_builder()

    assert not (
        builder.validate_action(
            action=99,
            task=make_task(
                "specimen_delivery"
            ),
            robots=make_fleet(),
        )
    )


def test_battery_mask_rejects_robot_when_incoming_task_itself_is_infeasible():

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
        service_time_s=999999.0,
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

    builder = ActionMaskBuilder(
        robot_ids=(
            "M01",
            "M02",
        )
    )

    tasks_by_id = {
        task.task_id:
        task,
    }

    mask = builder.build(
        task=task,
        robots=[
            robot_ok,
            robot_low,
        ],
        enable_battery_model=True,
        tasks_by_id=tasks_by_id,
        current_time_s=100.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert mask.tolist() == [
        True,
        False,
    ]


def test_battery_mask_allows_incoming_task_when_downstream_task_is_released():

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
        service_time_s=999999.0,
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
        "T2",
    ]

    tasks_by_id = {
        "T2": old_task,
        "T3": incoming,
    }

    builder = ActionMaskBuilder(
        robot_ids=(
            "M01",
        )
    )

    mask = builder.build(
        task=incoming,
        robots=[
            robot,
        ],
        enable_battery_model=True,
        tasks_by_id=tasks_by_id,
        current_time_s=200.0,
        travel_time_fn=(
            fake_travel_time
        ),
    )

    assert mask.tolist() == [
        True,
    ]


def test_charging_robot_is_masked():

    task = TaskState(
        task_id="T1",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=0.0,
        service_time_s=0.0,
    )

    robot = RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="charging_station_2",
        status="charging",
    )

    builder = ActionMaskBuilder(
        robot_ids=("M01",)
    )

    mask = builder.build(
        task=task,
        robots=[robot],
    )

    assert mask.tolist() == [
        False,
    ]


def test_returning_to_charge_robot_is_masked():

    task = TaskState(
        task_id="T1",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=0.0,
        service_time_s=0.0,
    )

    robot = RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="ward_a_2",
        status="returning_to_charge",
    )

    builder = ActionMaskBuilder(
        robot_ids=("M01",)
    )

    mask = builder.build(
        task=task,
        robots=[robot],
    )

    assert mask.tolist() == [
        False,
    ]