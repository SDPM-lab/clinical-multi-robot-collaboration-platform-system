from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(0, str(FLEET_SIZING_DIR))

from config import (
    SIMULATION_DAYS,
    SECONDS_PER_DAY,
    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
)

from simulator import FleetSizingSimulator


def test_simulator_runs():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    assert len(result.tasks) > 0
    assert len(result.robots) == 3
    assert len(result.assignments) > 0


def test_all_tasks_have_valid_timing():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    for task in result.tasks:

        if task.status == "unserved":
            continue

        assert task.assignment_time_s is not None
        assert task.start_time_s is not None
        assert task.completion_time_s is not None

        assert (
            task.assignment_time_s
            >= task.arrival_time_s
        )

        assert (
            task.start_time_s
            >= task.arrival_time_s
        )

        assert (
            task.completion_time_s
            >= task.start_time_s
        )


def test_capability_assignment_is_valid():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    robots = {
        robot.robot_id: robot
        for robot in result.robots
    }

    for task in result.tasks:

        if task.assigned_robot is None:
            continue

        robot = robots[
            task.assigned_robot
        ]

        assert (
            task.task_type
            in robot.capabilities
        )


def test_clean_robot_only_handles_clean_tasks():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    for task in result.tasks:

        if task.assigned_robot != "C01":
            continue

        assert task.task_type in {
            TASK_WASTE,
            TASK_CLOTHES,
        }


def test_medical_robot_only_handles_medical_tasks():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    for task in result.tasks:

        if task.assigned_robot != "M01":
            continue

        assert task.task_type in {
            TASK_MEDICATION,
            TASK_SPECIMEN,
        }


def test_ward_robot_only_handles_ward_capabilities():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    for task in result.tasks:

        if task.assigned_robot != "W01":
            continue

        assert task.task_type in {
            TASK_MEDICATION,
            TASK_WARD,
        }


def test_busy_robot_preassignment_exists():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    busy_assignments = [
        record
        for record in result.assignments
        if record.robot_was_busy
    ]

    assert len(busy_assignments) > 0

    for record in busy_assignments:
        assert record.queue_delay_s > 0


def test_busy_task_starts_after_existing_queue():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    for record in result.assignments:

        if not record.robot_was_busy:
            continue

        assert (
            record.dispatch_start_time_s
            >= record.robot_previous_available_time_s
        )

        assert (
            record.dispatch_start_time_s
            > record.task_arrival_time_s
        )


def test_robot_assignments_do_not_overlap():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    by_robot = {}

    for record in result.assignments:
        by_robot.setdefault(
            record.robot_id,
            []
        ).append(record)

    for robot_id, records in by_robot.items():

        records.sort(
            key=lambda r:
            r.dispatch_start_time_s
        )

        for previous, current in zip(
            records,
            records[1:],
        ):

            assert (
                current.dispatch_start_time_s
                >= previous.completion_time_s
            ), (
                f"{robot_id} overlap: "
                f"{previous.task_id} ends at "
                f"{previous.completion_time_s}, "
                f"but {current.task_id} starts at "
                f"{current.dispatch_start_time_s}"
            )


def test_assignment_origin_matches_previous_destination_when_queued():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    by_robot = {}

    for record in result.assignments:
        by_robot.setdefault(
            record.robot_id,
            []
        ).append(record)

    for robot_id, records in by_robot.items():

        records.sort(
            key=lambda r:
            r.dispatch_start_time_s
        )

        for previous, current in zip(
            records,
            records[1:],
        ):

            # 如果 current 是直接接在 previous 後面，
            # 它應該從 previous destination 出發。
            if (
                current.dispatch_start_time_s
                == previous.completion_time_s
            ):
                assert (
                    current.assignment_origin
                    == previous.task_destination
                )


def test_horizon_classification():
    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    horizon_s = (
        SIMULATION_DAYS
        * SECONDS_PER_DAY
    )

    completed_within_horizon = [
        task
        for task in result.tasks
        if (
            task.completion_time_s
            is not None
            and task.completion_time_s
            <= horizon_s
        )
    ]

    completed_after_horizon = [
        task
        for task in result.tasks
        if (
            task.completion_time_s
            is not None
            and task.completion_time_s
            > horizon_s
        )
    ]

    assert (
        len(completed_within_horizon)
        + len(completed_after_horizon)
        <= len(result.tasks)
    )


def test_same_seed_same_assignment_result():
    simulator1 = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    simulator2 = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result1 = simulator1.run()
    result2 = simulator2.run()

    assignments1 = [
        (
            r.task_id,
            r.robot_id,
            r.dispatch_start_time_s,
            r.completion_time_s,
        )
        for r in result1.assignments
    ]

    assignments2 = [
        (
            r.task_id,
            r.robot_id,
            r.dispatch_start_time_s,
            r.completion_time_s,
        )
        for r in result2.assignments
    ]

    assert assignments1 == assignments2