from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

from experiments.fleet_sizing.baseline.projected_nearest import (
    ProjectedNearestScheduler,
)


# ============================================================
# Import Compatibility
# ============================================================

FLEET_SIZING_DIR = (
    Path(__file__).resolve().parents[1]
)

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(FLEET_SIZING_DIR),
    )


from experiments.fleet_sizing.baseline.static_weighted import (
    StaticWeightedScheduler,
)

from experiments.fleet_sizing.config import (
    PRIORITY_EMERGENCY,
    PRIORITY_NORMAL,
    ROBOT_TYPE_MEDICAL,
    TASK_MEDICATION,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
    _AssignmentContext,
)


# ============================================================
# Helpers
# ============================================================


def make_task(
    task_id: str,
    source: str = "pharmacy",
    destination: str = "ward_a_2",
    priority: int = PRIORITY_NORMAL,
    arrival_time_s: float = 0.0,
    service_time_s: float = 30.0,
) -> TaskState:

    return TaskState(
        task_id=task_id,
        task_type=TASK_MEDICATION,
        source=source,
        destination=destination,
        priority=priority,
        arrival_time_s=arrival_time_s,
        service_time_s=service_time_s,
    )


def make_medical_robot(
    robot_id: str = "M01",
    current_location: str = "charging_station_2",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        robot_type=ROBOT_TYPE_MEDICAL,
        capabilities=[
            TASK_MEDICATION,
        ],
        current_location=current_location,
        status="idle",
        available_time_s=0.0,
        future_location=current_location,
    )


# ============================================================
# Basic Public Run
# ============================================================


def test_scheduling_simulator_runs():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result = simulator.run()

    assert len(
        result.tasks
    ) > 0

    assert len(
        result.assignments
    ) > 0

    assert (
        result.scheduler_name
        == "static_weighted"
    )

    assert (
        result.fleet_configuration
        == (2, 2, 3)
    )

    assert (
        result.workload_multiplier
        == pytest.approx(4.0)
    )


def test_all_generated_tasks_are_completed():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result = simulator.run()

    assert all(
        task.status
        == "completed"
        for task
        in result.tasks
    )

    assert (
        len(result.assignments)
        == len(result.tasks)
    )


# ============================================================
# Reproducibility
# ============================================================


def test_same_seed_same_assignment_sequence():

    simulator_a = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    simulator_b = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result_a = simulator_a.run()
    result_b = simulator_b.run()

    assignments_a = [
        (
            record.task_id,
            record.robot_id,
        )
        for record
        in result_a.assignments
    ]

    assignments_b = [
        (
            record.task_id,
            record.robot_id,
        )
        for record
        in result_b.assignments
    ]

    assert (
        assignments_a
        == assignments_b
    )


# ============================================================
# Active Task Non-Preemption
# ============================================================


def test_active_task_is_not_preempted_by_new_emergency():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            0,
            1,
            0,
        ),
        seed=1,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    robot = simulator.robots[0]

    active = make_task(
        task_id="ACTIVE",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
        service_time_s=500.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=10.0,
        service_time_s=10.0,
    )

    simulator.tasks = [
        active,
        emergency,
    ]

    simulator.tasks_by_id = {
        "ACTIVE": active,
        "EMERGENCY": emergency,
    }

    # Assign + start active task.
    robot.queued_task_ids = [
        "ACTIVE"
    ]

    active.assigned_robot = (
        robot.robot_id
    )

    active.assignment_time_s = 0.0

    simulator._assignment_context[
        "ACTIVE"
    ] = _AssignmentContext(
        assignment_time_s=0.0,
        robot_was_busy=False,
    )

    simulator._start_next_task(
        robot=robot,
        current_time_s=0.0,
    )

    assert (
        robot.current_task_id
        == "ACTIVE"
    )

    # Emergency arrives while ACTIVE is executing.
    simulator._handle_arrival(
        task_id="EMERGENCY",
        current_time_s=10.0,
    )

    # ACTIVE must still be active.
    assert (
        robot.current_task_id
        == "ACTIVE"
    )

    # Emergency should wait in future queue.
    assert (
        "EMERGENCY"
        in robot.queued_task_ids
    )


# ============================================================
# Priority + Aging Queue Execution
# ============================================================


def test_emergency_executes_before_waiting_normal_task():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            0,
            1,
            0,
        ),
        seed=1,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    robot = simulator.robots[0]

    active = make_task(
        task_id="ACTIVE",
        priority=PRIORITY_NORMAL,
        arrival_time_s=0.0,
        service_time_s=100.0,
    )

    normal = make_task(
        task_id="NORMAL",
        priority=PRIORITY_NORMAL,
        arrival_time_s=10.0,
        service_time_s=10.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        priority=PRIORITY_EMERGENCY,
        arrival_time_s=20.0,
        service_time_s=10.0,
    )

    simulator.tasks = [
        active,
        normal,
        emergency,
    ]

    simulator.tasks_by_id = {
        "ACTIVE": active,
        "NORMAL": normal,
        "EMERGENCY": emergency,
    }

    # Start ACTIVE.
    robot.queued_task_ids = [
        "ACTIVE"
    ]

    active.assigned_robot = (
        robot.robot_id
    )

    active.assignment_time_s = 0.0

    simulator._assignment_context[
        "ACTIVE"
    ] = _AssignmentContext(
        assignment_time_s=0.0,
        robot_was_busy=False,
    )

    simulator._start_next_task(
        robot=robot,
        current_time_s=0.0,
    )

    # NORMAL arrives.
    simulator._handle_arrival(
        task_id="NORMAL",
        current_time_s=10.0,
    )

    # EMERGENCY arrives later.
    simulator._handle_arrival(
        task_id="EMERGENCY",
        current_time_s=20.0,
    )

    assert (
        robot.current_task_id
        == "ACTIVE"
    )

    assert (
        robot.queued_task_ids[0]
        == "EMERGENCY"
    )

    assert (
        robot.queued_task_ids[1]
        == "NORMAL"
    )


# ============================================================
# Completion Starts Next Queued Task
# ============================================================


def test_completion_starts_next_queued_task():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            0,
            1,
            0,
        ),
        seed=1,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    robot = simulator.robots[0]

    first = make_task(
        task_id="FIRST",
        arrival_time_s=0.0,
        service_time_s=10.0,
    )

    second = make_task(
        task_id="SECOND",
        arrival_time_s=1.0,
        service_time_s=10.0,
    )

    simulator.tasks = [
        first,
        second,
    ]

    simulator.tasks_by_id = {
        "FIRST": first,
        "SECOND": second,
    }

    robot.queued_task_ids = [
        "FIRST"
    ]

    first.assigned_robot = (
        robot.robot_id
    )

    first.assignment_time_s = 0.0

    simulator._assignment_context[
        "FIRST"
    ] = _AssignmentContext(
        assignment_time_s=0.0,
        robot_was_busy=False,
    )

    simulator._start_next_task(
        robot=robot,
        current_time_s=0.0,
    )

    first_completion = (
        first.completion_time_s
    )

    assert (
        first_completion
        is not None
    )

    simulator._handle_arrival(
        task_id="SECOND",
        current_time_s=1.0,
    )

    assert (
        "SECOND"
        in robot.queued_task_ids
    )

    simulator._handle_completion(
        robot_id=robot.robot_id,
        task_id="FIRST",
        current_time_s=(
            first_completion
        ),
    )

    assert (
        first.status
        == "completed"
    )

    assert (
        robot.current_task_id
        == "SECOND"
    )

    assert (
        second.start_time_s
        == pytest.approx(
            first_completion
        )
    )


# ============================================================
# No Task Overlap Per Robot
# ============================================================


def test_robot_assignments_do_not_overlap():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result = simulator.run()

    by_robot = {}

    for record in result.assignments:

        by_robot.setdefault(
            record.robot_id,
            [],
        ).append(
            record
        )

    for records in by_robot.values():

        ordered = sorted(
            records,
            key=lambda record:
                record.dispatch_start_time_s,
        )

        for previous, current in zip(
            ordered,
            ordered[1:],
        ):

            assert (
                current.dispatch_start_time_s
                >=
                previous.completion_time_s
            )


# ============================================================
# Queue Delay Semantics
# ============================================================


def test_busy_assignment_has_positive_or_zero_queue_delay():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result = simulator.run()

    busy_records = [
        record
        for record
        in result.assignments
        if record.robot_was_busy
    ]

    assert busy_records

    assert all(
        record.queue_delay_s
        >= 0.0
        for record
        in busy_records
    )


# ============================================================
# Assignment Timing Consistency
# ============================================================


def test_assignment_timing_is_consistent():

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        workload_multiplier=4.0,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    result = simulator.run()

    for record in result.assignments:

        assert (
            record.source_arrival_time_s
            ==
            pytest.approx(
                record.dispatch_start_time_s
                + record.approach_time_s
            )
        )

        assert (
            record.completion_time_s
            ==
            pytest.approx(
                record.source_arrival_time_s
                + record.task_travel_time_s
                + record.service_time_s
            )
        )


# ============================================================
# Scheduler Anti-Leakage Through Simulator
# ============================================================


def test_active_completion_ground_truth_not_used_by_scheduler():

    simulator_a = SchedulingSimulator(
        fleet_configuration=(
            0,
            2,
            0,
        ),
        seed=1,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    simulator_b = SchedulingSimulator(
        fleet_configuration=(
            0,
            2,
            0,
        ),
        seed=1,
        scheduler=(
            StaticWeightedScheduler(
                alpha=0.8
            )
        ),
    )

    task_a = make_task(
        task_id="NEW",
        source="pharmacy",
        arrival_time_s=50.0,
    )

    task_b = copy.deepcopy(
        task_a
    )

    simulator_a.tasks = [
        task_a
    ]

    simulator_b.tasks = [
        task_b
    ]

    simulator_a.tasks_by_id = {
        "NEW": task_a,
    }

    simulator_b.tasks_by_id = {
        "NEW": task_b,
    }

    m01_a = simulator_a.robots[0]
    m02_a = simulator_a.robots[1]

    m01_b = simulator_b.robots[0]
    m02_b = simulator_b.robots[1]

    for robot in [
        m01_a,
        m01_b,
    ]:

        robot.status = "busy"
        robot.current_task_id = "ACTIVE"
        robot.current_task_destination = (
            "ward_b_2"
        )

    # Only change hidden ground-truth completion.
    m01_a.current_task_completion_time_s = (
        100.0
    )

    m01_b.current_task_completion_time_s = (
        10000.0
    )

    decision_a = (
        simulator_a.scheduler.decide(
            robots=[
                m01_a,
                m02_a,
            ],
            task=task_a,
            tasks_by_id={
                "NEW": task_a,
            },
            current_time_s=50.0,
            travel_time_fn=(
                simulator_a._travel_time
            ),
            commit_queue=False,
        )
    )

    decision_b = (
        simulator_b.scheduler.decide(
            robots=[
                m01_b,
                m02_b,
            ],
            task=task_b,
            tasks_by_id={
                "NEW": task_b,
            },
            current_time_s=50.0,
            travel_time_fn=(
                simulator_b._travel_time
            ),
            commit_queue=False,
        )
    )

    assert (
        decision_a.selected_robot_id
        ==
        decision_b.selected_robot_id
    )


def test_battery_no_feasible_robot_becomes_waiting_instead_of_unserved():

    scheduler = ProjectedNearestScheduler()

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    task = TaskState(
        task_id="T_WAIT",
        task_type="specimen_delivery",
        source="ward_a_2",
        destination="lab",
        priority=3,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    simulator.tasks = [
        task,
    ]

    simulator.tasks_by_id = {
        task.task_id:
        task,
    }

    # Make all medical robots unavailable.
    for robot in simulator.robots:

        if robot.robot_type == "medical":

            robot.status = "charging"
            robot.battery_soc = 0.50

    simulator._handle_arrival(
        task_id=task.task_id,
        current_time_s=100.0,
    )

    assert (
        task.status
        == "waiting"
    )

    assert (
        task.assigned_robot
        is None
    )

    assert (
        task.task_id
        in simulator.reassignment_task_ids
    )

    assert (
        task.arrival_time_s
        == 100.0
    )


def test_waiting_task_is_reassigned_after_charging_complete():

    scheduler = (
        ProjectedNearestScheduler()
    )

    simulator = SchedulingSimulator(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    task = TaskState(
        task_id="T_WAIT",
        task_type="specimen_delivery",
        source="ward_a_2",
        destination="lab",
        priority=3,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    simulator.tasks = [
        task,
    ]

    simulator.tasks_by_id = {
        task.task_id:
        task,
    }

    medical_robots = [
        robot
        for robot
        in simulator.robots
        if robot.robot_type
        == "medical"
    ]

    for robot in medical_robots:
        robot.status = "charging"
        robot.battery_soc = 0.50

    simulator._handle_arrival(
        task_id=(
            task.task_id
        ),
        current_time_s=100.0,
    )

    assert (
        task.status
        == "waiting"
    )

    robot = medical_robots[0]

    robot.status = "idle"
    robot.battery_soc = 0.80

    activated = (
        simulator
        ._activate_next_reassignment(
            current_time_s=200.0
        )
    )

    assert activated is True

    assert (
        task.task_id
        not in simulator
        .reassignment_task_ids
    )

    assert (
        task.assigned_robot
        is not None
    )

    assert (
        task.status
        == "active"
    )

    assert (
        task.assignment_time_s
        == 200.0
    )

    assert (
        task.arrival_time_s
        == 100.0
    )


def test_released_downstream_task_enters_same_time_reassignment():

    scheduler = (
        ProjectedNearestScheduler()
    )

    simulator = SchedulingSimulator(
        fleet_configuration=(
            1,
            1,
            1,
        ),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    def fake_travel_time(
        source: str,
        destination: str,
    ) -> float:

        if source == destination:
            return 0.0

        if (
            source == "pharmacy"
            and destination == "ward_a_2"
        ):
            return 1200.0

        return 600.0


    simulator._travel_time = (
        fake_travel_time
    )

    robot = next(
        robot
        for robot
        in simulator.robots
        if robot.robot_type
        == "medical"
    )

    robot.battery_soc = 0.40
    robot.status = "idle"

    old_task = TaskState(
        task_id="T_OLD",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    incoming = TaskState(
        task_id="T_NEW",
        task_type="specimen_delivery",
        source="ward_b_2",
        destination="lab",
        priority=3,
        arrival_time_s=200.0,
        service_time_s=0.0,
    )

    old_task.assigned_robot = (
        robot.robot_id
    )
    old_task.assignment_time_s = 100.0
    old_task.status = "queued"

    robot.queued_task_ids = [
        old_task.task_id,
    ]

    robot.assigned_task_ids = [
        old_task.task_id,
    ]

    simulator.tasks = [
        old_task,
        incoming,
    ]

    simulator.tasks_by_id = {
        old_task.task_id:
        old_task,
        incoming.task_id:
        incoming,
    }

    simulator._handle_arrival(
        task_id=(
            incoming.task_id
        ),
        current_time_s=200.0,
    )

    assert (
        incoming.assigned_robot
        == robot.robot_id
    )

    assert (
        old_task.arrival_time_s
        == 100.0
    )

    assert (
        old_task.status
        in {
            "waiting",
            "queued",
            "active",
        }
    )


def test_minimum_battery_soc_tracks_navigation_drain():

    scheduler = (
        ProjectedNearestScheduler()
    )

    simulator = SchedulingSimulator(
        fleet_configuration=(
            1,
            1,
            1,
        ),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    robot = next(
        robot
        for robot
        in simulator.robots
        if robot.robot_type
        == "medical"
    )

    robot.battery_soc = 1.0
    robot.minimum_battery_soc = 1.0

    task = TaskState(
        task_id="T_BATTERY",
        task_type="specimen_delivery",
        source="ward_a_2",
        destination="lab",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    simulator.tasks = [
        task,
    ]

    simulator.tasks_by_id = {
        task.task_id:
        task,
    }

    simulator._handle_arrival(
        task_id=task.task_id,
        current_time_s=100.0,
    )

    assert (
        robot.battery_soc
        < 1.0
    )

    assert (
        robot.minimum_battery_soc
        == pytest.approx(
            robot.battery_soc
        )
    )


def test_battery_reserve_can_reach_charger_from_all_task_waypoints():

    from experiments.fleet_sizing.config import (
        BATTERY_MIN_RESERVE_SOC,
        BATTERY_TRAVEL_DRAIN_PER_SECOND,
        CHARGING_WAYPOINT,
    )

    from experiments.fleet_sizing.travel_time import (
        TravelTimeModel,
    )

    task_waypoints = [
        "pharmacy",
        "lab",
        "ward_a_2",
        "ward_b_2",
        "nurse_station",
    ]

    travel_model = (
        TravelTimeModel()
    )

    return_energy_soc = []

    for waypoint in task_waypoints:

        travel_time_s = (
            travel_model
            .get_travel_time_mean(
                waypoint,
                CHARGING_WAYPOINT,
            )
        )

        energy_soc = (
            travel_time_s
            * BATTERY_TRAVEL_DRAIN_PER_SECOND
        )

        return_energy_soc.append(
            energy_soc
        )

    assert (
        max(return_energy_soc)
        <= BATTERY_MIN_RESERVE_SOC
    )


def test_return_to_charge_count_increments():

    scheduler = (
        ProjectedNearestScheduler()
    )

    simulator = SchedulingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    robot = next(
        robot
        for robot in simulator.robots
        if robot.robot_type == "medical"
    )

    robot.battery_soc = 0.20
    robot.current_location = "lab"

    assert robot.return_to_charge_count == 0

    simulator._start_return_to_charge(
        robot=robot,
        current_time_s=100.0,
    )

    assert (
        robot.return_to_charge_count
        == 1
    )


def test_charging_count_increments_on_arrival():

    scheduler = (
        ProjectedNearestScheduler()
    )

    simulator = SchedulingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    robot = next(
        robot
        for robot in simulator.robots
        if robot.robot_type == "medical"
    )

    robot.status = "returning_to_charge"
    robot.current_location = "lab"
    robot.battery_soc = 0.20

    assert robot.charging_count == 0

    simulator._handle_return_to_charge_complete(
        robot_id=robot.robot_id,
        current_time_s=200.0,
    )

    assert (
        robot.charging_count
        == 1
    )


def test_charging_complete_resumes_existing_queued_task():

    scheduler = ProjectedNearestScheduler()

    simulator = SchedulingSimulator(
        fleet_configuration=(0, 1, 0),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    robot = simulator.robots[0]

    task = make_task(
        task_id="QUEUED_AFTER_CHARGE",
        source="pharmacy",
        destination="ward_a_2",
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    simulator.tasks = [task]

    simulator.tasks_by_id = {
        task.task_id: task,
    }

    task.assigned_robot = robot.robot_id
    task.assignment_time_s = 100.0
    task.status = "queued"

    robot.queued_task_ids = [
        task.task_id,
    ]

    robot.assigned_task_ids = [
        task.task_id,
    ]

    simulator._assignment_context[
        task.task_id
    ] = _AssignmentContext(
        assignment_time_s=100.0,
        robot_was_busy=True,
    )

    robot.status = "charging"
    robot.current_location = "charging_station_2"
    robot.battery_soc = 0.20
    robot.charging_start_time_s = 100.0
    robot.charging_end_time_s = 4420.0
    robot.charging_start_soc = 0.20

    simulator._handle_charging_complete(
        robot_id=robot.robot_id,
        current_time_s=4420.0,
    )

    assert (
        robot.current_task_id
        == task.task_id
    )

    assert (
        task.status
        == "active"
    )


def test_task_completion_retries_waiting_reassignment():

    scheduler = ProjectedNearestScheduler()

    simulator = SchedulingSimulator(
        fleet_configuration=(0, 1, 0),
        seed=1001,
        scheduler=scheduler,
        workload_multiplier=1.0,
        enable_battery_model=True,
    )

    robot = simulator.robots[0]

    active_task = make_task(
        task_id="ACTIVE_TASK",
        source="pharmacy",
        destination="ward_a_2",
        arrival_time_s=0.0,
        service_time_s=0.0,
    )

    waiting_task = make_task(
        task_id="WAITING_TASK",
        source="pharmacy",
        destination="ward_b_2",
        arrival_time_s=10.0,
        service_time_s=0.0,
    )

    simulator.tasks = [
        active_task,
        waiting_task,
    ]

    simulator.tasks_by_id = {
        active_task.task_id: active_task,
        waiting_task.task_id: waiting_task,
    }

    active_task.assigned_robot = robot.robot_id
    active_task.assignment_time_s = 0.0
    active_task.status = "active"

    robot.current_task_id = active_task.task_id
    robot.current_task_destination = (
        active_task.destination
    )
    robot.status = "busy"

    waiting_task.status = "waiting"

    simulator.reassignment_task_ids = [
        waiting_task.task_id,
    ]

    simulator._handle_completion(
        robot_id=robot.robot_id,
        task_id=active_task.task_id,
        current_time_s=100.0,
    )

    while simulator._activate_next_reassignment(
        current_time_s=100.0
    ):
        pass

    assert (
        waiting_task.status
        in {
            "queued",
            "active",
        }
    )

    assert (
        waiting_task.assigned_robot
        == robot.robot_id
    )

    assert (
        waiting_task.task_id
        not in simulator.reassignment_task_ids
    )


def test_released_task_during_reassignment_is_not_lost():

    scheduler = ProjectedNearestScheduler()

    simulator = SchedulingSimulator(
        fleet_configuration=(2, 2, 3),
        seed=8002,
        scheduler=scheduler,
        workload_multiplier=4.0,
        enable_battery_model=True,
    )

    result = simulator.run()

    incomplete = [
        task
        for task in result.tasks
        if task.status != "completed"
    ]

    assert incomplete == []