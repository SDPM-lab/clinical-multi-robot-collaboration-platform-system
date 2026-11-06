from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(FLEET_SIZING_DIR),
    )

from models import (
    RobotState,
    TaskState,
)


def make_robot():
    return RobotState(
        robot_id="M01",
        robot_type="medical",
        capabilities=[
            "medication_delivery",
            "specimen_delivery",
        ],
        current_location="charging_station_2",
        future_location="charging_station_2",
    )


def test_new_robot_is_idle():
    robot = make_robot()

    assert robot.is_idle()
    assert not robot.is_busy()

    assert robot.current_task_id is None
    assert robot.queue_length() == 0
    assert robot.scheduled_task_count() == 0


def test_robot_with_active_task_is_busy():
    robot = make_robot()

    robot.current_task_id = "T001"

    assert robot.is_busy()
    assert not robot.is_idle()
    assert robot.has_active_task()

    assert robot.scheduled_task_count() == 1


def test_robot_with_queue_is_busy():
    robot = make_robot()

    robot.queued_task_ids.append(
        "T002"
    )

    assert robot.is_busy()
    assert not robot.is_idle()

    assert robot.queue_length() == 1
    assert robot.scheduled_task_count() == 1


def test_active_task_is_not_in_future_queue():
    robot = make_robot()

    robot.current_task_id = "T001"

    robot.queued_task_ids = [
        "T002",
        "T003",
    ]

    assert robot.current_task_id == "T001"

    assert robot.queued_task_ids == [
        "T002",
        "T003",
    ]

    assert (
        robot.current_task_id
        not in robot.queued_task_ids
    )

    assert robot.scheduled_task_count() == 3


def test_remaining_busy_time():
    robot = make_robot()

    robot.available_time_s = 500.0

    assert (
        robot.remaining_busy_time(
            200.0
        )
        == 300.0
    )

    assert (
        robot.remaining_busy_time(
            600.0
        )
        == 0.0
    )


def test_available_robot_uses_current_location():
    robot = make_robot()

    robot.current_location = "lab"
    robot.future_location = "ward_a_2"

    robot.available_time_s = 100.0

    origin = robot.get_assignment_origin(
        current_time_s=200.0
    )

    assert origin == "lab"


def test_busy_robot_uses_future_location():
    robot = make_robot()

    robot.current_location = "lab"
    robot.future_location = "ward_a_2"

    robot.available_time_s = 500.0

    origin = robot.get_assignment_origin(
        current_time_s=200.0
    )

    assert origin == "ward_a_2"


def test_task_waiting_time():
    task = TaskState(
        task_id="T001",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=2,
        arrival_time_s=100.0,
        service_time_s=50.0,
    )

    task.start_time_s = 180.0

    assert task.waiting_time_s == 80.0


def test_task_source_response_time():
    task = TaskState(
        task_id="T001",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=2,
        arrival_time_s=100.0,
        service_time_s=50.0,
    )

    task.source_arrival_time_s = 250.0

    assert (
        task.source_response_time_s
        == 150.0
    )


def test_task_total_time():
    task = TaskState(
        task_id="T001",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=2,
        arrival_time_s=100.0,
        service_time_s=50.0,
    )

    task.completion_time_s = 500.0

    assert task.total_time_s == 400.0