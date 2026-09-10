#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projection import (
    calculate_distance,
    calculate_task_travel_distance,
    calculate_task_duration,
    project_task_on_robot,
)


# ==========================================================
# Helpers
# ==========================================================

def make_task(
    task_id: str,
    priority: int,
    source: str,
    destination: str,
    created_at: float = 0.0,
) -> Task:

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source=source,
        destination=destination,
        priority=priority,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=created_at,
    )


def make_robot(
    x: float = 0.0,
    y: float = 0.0,
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id="R1",
        fleet_name="hospital_fleet",
        status=status,
        battery=0.80,
        x=x,
        y=y,
        map_name="L1",
        capabilities={
            "navigation",
            "general_delivery",
        },
        available=True,
    )


def make_places():

    return {
        "A": Place(
            "A",
            0.0,
            0.0,
            "L1",
        ),
        "B": Place(
            "B",
            3.0,
            4.0,
            "L1",
        ),
        "C": Place(
            "C",
            6.0,
            8.0,
            "L1",
        ),
        "D": Place(
            "D",
            9.0,
            12.0,
            "L1",
        ),
        "E": Place(
            "E",
            10.0,
            0.0,
            "L1",
        ),
        "F": Place(
            "F",
            13.0,
            4.0,
            "L1",
        ),
    }


# ==========================================================
# Distance
# ==========================================================

def test_euclidean_distance():

    start = Place(
        "START",
        0.0,
        0.0,
        "L1",
    )

    end = Place(
        "END",
        3.0,
        4.0,
        "L1",
    )

    assert (
        calculate_distance(
            start,
            end,
        )
        ==
        5.0
    )


def test_distance_between_different_maps_rejected():

    start = Place(
        "START",
        0.0,
        0.0,
        "L1",
    )

    end = Place(
        "END",
        0.0,
        0.0,
        "L2",
    )

    with pytest.raises(
        ValueError
    ):

        calculate_distance(
            start,
            end,
        )


# ==========================================================
# Task Duration
# ==========================================================

def test_task_duration():

    places = make_places()

    task = make_task(
        "T1",
        priority=1,
        source="B",
        destination="C",
    )

    # A -> B = 5
    # B -> C = 5
    #
    # speed = 1 m/s
    # travel = 10 sec
    #
    # service = 10 sec
    #
    # total = 20 sec

    duration = (
        calculate_task_duration(
            task=task,
            start_place=places["A"],
            places=places,
            robot_speed_mps=1.0,
            service_time_seconds=10.0,
        )
    )

    assert duration == 20.0


# ==========================================================
# Idle Robot Projection
# ==========================================================

def test_idle_robot_projection():

    robot = make_robot(
        x=0.0,
        y=0.0,
    )

    runtime = RobotRuntimeState(
        robot=robot,
    )

    task = make_task(
        "T1",
        priority=1,
        source="B",
        destination="C",
    )

    projection = (
        project_task_on_robot(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
            service_time_seconds=10.0,
        )
    )

    assert (
        projection.workload_before_task
        ==
        0.0
    )

    assert (
        projection.queue_length_before_task
        ==
        0
    )

    assert (
        projection.distance_to_source
        ==
        5.0
    )

    assert (
        projection.projected_x,
        projection.projected_y,
    ) == (
        0.0,
        0.0,
    )


# ==========================================================
# Running Task Projection
# ==========================================================

def test_running_task_is_non_preemptive():

    running_task = make_task(
        "RUNNING",
        priority=0,
        source="A",
        destination="E",
    )

    new_task = make_task(
        "NEW",
        priority=3,
        source="F",
        destination="D",
    )

    robot = make_robot(
        status="busy",
    )

    runtime = RobotRuntimeState(
        robot=robot,
        running_task=running_task,
        running_remaining_time=20.0,
    )

    projection = (
        project_task_on_robot(
            task=new_task,
            runtime=runtime,
            places=make_places(),
            current_time=100.0,
            service_time_seconds=10.0,
        )
    )

    # Running Task 不會因為 NEW 是 Emergency 被搶占。
    assert (
        projection.workload_before_task
        ==
        20.0
    )

    # Running 完成後 Robot 在 E=(10,0)
    # NEW source F=(13,4)
    # Distance = 5
    assert (
        projection.distance_to_source
        ==
        5.0
    )

    assert (
        projection.projected_x,
        projection.projected_y,
    ) == (
        10.0,
        0.0,
    )


# ==========================================================
# Priority Queue Projection
# ==========================================================

def test_high_priority_new_task_can_jump_ahead():

    old_low = make_task(
        "OLD_LOW",
        priority=0,
        source="B",
        destination="C",
        created_at=100.0,
    )

    new_high = make_task(
        "NEW_HIGH",
        priority=2,
        source="B",
        destination="C",
        created_at=110.0,
    )

    robot = make_robot()

    runtime = RobotRuntimeState(
        robot=robot,
        waiting_tasks=[
            old_low,
        ],
    )

    projection = (
        project_task_on_robot(
            task=new_high,
            runtime=runtime,
            places=make_places(),
            current_time=110.0,
            aging_interval_seconds=120.0,
            service_time_seconds=10.0,
        )
    )

    assert (
        projection.queue_length_before_task
        ==
        0
    )

    assert (
        projection.task_ids_before
        ==
        ()
    )

    assert (
        projection.workload_before_task
        ==
        0.0
    )


def test_lower_priority_task_accounts_for_tasks_ahead():

    high = make_task(
        "HIGH",
        priority=2,
        source="B",
        destination="C",
        created_at=0.0,
    )

    low = make_task(
        "LOW",
        priority=0,
        source="D",
        destination="A",
        created_at=10.0,
    )

    robot = make_robot()

    runtime = RobotRuntimeState(
        robot=robot,
        waiting_tasks=[
            high,
        ],
        robot_speed_mps=1.0,
    )

    projection = (
        project_task_on_robot(
            task=low,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            aging_interval_seconds=120.0,
            service_time_seconds=10.0,
        )
    )

    # HIGH:
    #
    # current A -> B = 5
    # B -> C = 5
    # service = 10
    #
    # workload = 20 sec
    assert (
        projection.workload_before_task
        ==
        20.0
    )

    # HIGH 最後到 C=(6,8)
    #
    # LOW source D=(9,12)
    #
    # distance = 5
    assert (
        projection.distance_to_source
        ==
        5.0
    )

    assert (
        projection.queue_length_before_task
        ==
        1
    )

    assert (
        projection.task_ids_before
        ==
        (
            "HIGH",
        )
    )


# ==========================================================
# Duplicate Task
# ==========================================================

def test_duplicate_task_id_rejected():

    task = make_task(
        "T1",
        priority=1,
        source="B",
        destination="C",
    )

    runtime = RobotRuntimeState(
        robot=make_robot(),
        waiting_tasks=[
            task,
        ],
    )

    with pytest.raises(
        ValueError
    ):

        project_task_on_robot(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,
        )


# ==========================================================
# Task Travel Distance
# ==========================================================

def test_task_travel_distance():

    places = make_places()

    task = make_task(
        "T_DISTANCE",
        priority=1,
        source="B",
        destination="C",
    )

    # A -> B = 5
    # B -> C = 5
    #
    # total = 10
    distance = (
        calculate_task_travel_distance(
            task=task,
            start_place=places["A"],
            places=places,
        )
    )

    assert distance == 10.0


# ==========================================================
# Battery Projection
# ==========================================================

def test_idle_robot_battery_projection():

    robot = make_robot(
        x=0.0,
        y=0.0,
    )

    robot.battery = 0.80

    runtime = RobotRuntimeState(
        robot=robot,
    )

    task = make_task(
        "T_BATTERY",
        priority=1,
        source="B",
        destination="C",
    )

    projection = (
        project_task_on_robot(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=0.0,

            # A -> B -> C
            # = 5 + 5 = 10 m
            #
            # 10 * 0.01 = 0.10
            battery_drain_per_meter=0.01,
            service_time_seconds=0.0,
        )
    )

    assert (
        projection
        .projected_battery_before_task
        ==
        pytest.approx(
            0.80
        )
    )

    assert (
        projection
        .expected_task_battery_consumption
        ==
        pytest.approx(
            0.10
        )
    )

    assert (
        projection
        .projected_battery_after_task
        ==
        pytest.approx(
            0.70
        )
    )


def test_waiting_task_reduces_projected_battery():

    high = make_task(
        "HIGH",
        priority=2,
        source="B",
        destination="C",
        created_at=0.0,
    )

    low = make_task(
        "LOW",
        priority=0,
        source="D",
        destination="A",
        created_at=10.0,
    )

    robot = make_robot(
        x=0.0,
        y=0.0,
    )

    robot.battery = 0.80

    runtime = RobotRuntimeState(
        robot=robot,
        waiting_tasks=[
            high,
        ],
    )

    projection = (
        project_task_on_robot(
            task=low,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            battery_drain_per_meter=0.01,
            service_time_seconds=0.0,
        )
    )

    # HIGH：
    #
    # A -> B = 5
    # B -> C = 5
    #
    # total = 10 m
    #
    # battery consumption = 0.10
    #
    # 所以 LOW 開始前：
    #
    # 0.80 - 0.10 = 0.70
    assert (
        projection
        .projected_battery_before_task
        ==
        pytest.approx(
            0.70
        )
    )

    # LOW：
    #
    # HIGH 完成在 C=(6,8)
    #
    # C -> D = 5
    # D -> A = 15
    #
    # total = 20 m
    #
    # consumption = 0.20
    assert (
        projection
        .expected_task_battery_consumption
        ==
        pytest.approx(
            0.20
        )
    )

    assert (
        projection
        .projected_battery_after_task
        ==
        pytest.approx(
            0.50
        )
    )


def test_emergency_jump_does_not_count_lower_priority_waiting_battery():

    old_low = make_task(
        "OLD_LOW",
        priority=0,
        source="B",
        destination="D",
        created_at=0.0,
    )

    emergency = make_task(
        "EMERGENCY",
        priority=3,
        source="B",
        destination="C",
        created_at=10.0,
    )

    robot = make_robot(
        x=0.0,
        y=0.0,
    )

    robot.battery = 0.80

    runtime = RobotRuntimeState(
        robot=robot,
        waiting_tasks=[
            old_low,
        ],
    )

    projection = (
        project_task_on_robot(
            task=emergency,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
            battery_drain_per_meter=0.01,
            service_time_seconds=0.0,
        )
    )

    # Emergency 會插到 OLD_LOW 前面，
    # 因此開始 Emergency 前，
    # OLD_LOW 尚未執行也尚未耗電。
    assert (
        projection.task_ids_before
        ==
        ()
    )

    assert (
        projection
        .projected_battery_before_task
        ==
        pytest.approx(
            0.80
        )
    )