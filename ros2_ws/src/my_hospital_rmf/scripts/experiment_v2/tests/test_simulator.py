#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
)

from experiment_v2.models import (
    BaselineMethod,
    SimulationScenario,
)

from experiment_v2.simulator import (
    run_static_simulation,
)


# ==========================================================
# Helpers
# ==========================================================

def make_robot(
    robot_id: str,
    x: float = 0.0,
    battery: float = 0.80,
    status: str = "idle",
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status=status,
        battery=battery,
        x=x,
        y=0.0,
        map_name="L1",
        capabilities={
            "navigation",
            "general_delivery",
        },
        available=True,
    )


def make_task(
    task_id: str,
    source: str,
    destination: str,
    priority: int = 1,
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
            10.0,
            0.0,
            "L1",
        ),

        "C": Place(
            "C",
            20.0,
            0.0,
            "L1",
        ),

        "D": Place(
            "D",
            30.0,
            0.0,
            "L1",
        ),

        "E": Place(
            "E",
            90.0,
            0.0,
            "L1",
        ),
    }


# ==========================================================
# Single Task
# ==========================================================

def test_single_task_full_execution():

    scenario = SimulationScenario(
        name="single_task",
        tasks=[
            make_task(
                task_id="T1",
                source="A",
                destination="B",
                created_at=0.0,
            ),
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=0.0,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=5.0,
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    record = (
        result.task_records[
            "T1"
        ]
    )

    assert (
        record.assigned_robot
        ==
        "R1"
    )

    assert (
        record.assigned_at
        ==
        0.0
    )

    assert (
        record.start_time
        ==
        0.0
    )

    # A -> B = 10 sec
    # service = 5 sec
    assert (
        record.completion_time
        ==
        15.0
    )

    assert (
        record.travel_distance
        ==
        10.0
    )

    assert (
        record.waiting_time
        ==
        0.0
    )

    assert (
        record.completion_duration
        ==
        15.0
    )

    robot_record = (
        result.robot_records[
            "R1"
        ]
    )

    assert (
        robot_record.total_travel_distance
        ==
        10.0
    )

    assert (
        robot_record.busy_time
        ==
        15.0
    )

    assert (
        robot_record.completed_tasks
        ==
        1
    )

    assert (
        result.episode_end_time
        ==
        15.0
    )


# ==========================================================
# Running Non-Preemptive + Waiting Priority
# ==========================================================

def test_running_task_is_non_preemptive_but_waiting_queue_uses_priority():

    # ------------------------------------------------------
    # T1:
    # t=0
    # A -> B
    # 10 sec
    #
    # T2:
    # t=1
    # Low
    #
    # T3:
    # t=2
    # Emergency
    #
    # T1 不被 T3 搶占。
    #
    # 但 T1 完成後：
    #
    # T3 必須先於 T2。
    # ------------------------------------------------------

    t1 = make_task(
        task_id="T1",
        source="A",
        destination="B",
        priority=0,
        created_at=0.0,
    )

    t2 = make_task(
        task_id="T2",
        source="B",
        destination="A",
        priority=0,
        created_at=1.0,
    )

    t3 = make_task(
        task_id="T3",
        source="B",
        destination="C",
        priority=3,
        created_at=2.0,
    )

    scenario = SimulationScenario(
        name="priority_queue",
        tasks=[
            t1,
            t2,
            t3,
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=0.0,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    r1 = result.task_records["T1"]
    r2 = result.task_records["T2"]
    r3 = result.task_records["T3"]

    # T1 Running 不被 Emergency 搶占。
    assert (
        r1.completion_time
        ==
        10.0
    )

    # T3 在 t=2 到達，
    # 但必須等 T1 跑完。
    assert (
        r3.start_time
        ==
        10.0
    )

    # T3:
    # B -> C = 10 sec
    #
    # 所以 t=20 完成。
    assert (
        r3.completion_time
        ==
        20.0
    )

    # T2 被 Emergency 插隊。
    assert (
        r2.start_time
        ==
        20.0
    )


# ==========================================================
# Same-Time Priority
# ==========================================================

def test_same_time_arrivals_use_priority_before_start():

    low = make_task(
        task_id="LOW",
        source="A",
        destination="B",
        priority=0,
        created_at=0.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        source="A",
        destination="C",
        priority=3,
        created_at=0.0,
    )

    # 故意把 Low 放在 list 前面。
    scenario = SimulationScenario(
        name="same_time",
        tasks=[
            low,
            emergency,
        ],
        robots=[
            make_robot(
                robot_id="R1",
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    emergency_record = (
        result.task_records[
            "EMERGENCY"
        ]
    )

    low_record = (
        result.task_records[
            "LOW"
        ]
    )

    assert (
        emergency_record.start_time
        ==
        0.0
    )

    assert (
        low_record.start_time
        >
        emergency_record.start_time
    )


# ==========================================================
# Nearest vs Weighted
# ==========================================================

def test_nearest_and_weighted_can_choose_different_robots():

    task = make_task(
        task_id="T1",
        source="A",
        destination="B",
        created_at=0.0,
    )

    # R1:
    # 很近，但 battery 只有 21%
    #
    # R2:
    # 比較遠，但 battery 100%
    scenario = SimulationScenario(
        name="nearest_vs_weighted",
        tasks=[
            task,
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=1.0,
                battery=0.30,
            ),
            make_robot(
                robot_id="R2",
                x=10.0,
                battery=1.00,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    nearest_result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    weighted_result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .WEIGHTED_HEURISTIC
            ),
        )
    )

    assert (
        nearest_result
        .task_records["T1"]
        .assigned_robot
        ==
        "R1"
    )

    assert (
        weighted_result
        .task_records["T1"]
        .assigned_robot
        ==
        "R2"
    )


# ==========================================================
# Scenario Must Not Be Mutated
# ==========================================================

def test_simulation_does_not_mutate_original_scenario():

    task = make_task(
        task_id="T1",
        source="A",
        destination="B",
        created_at=0.0,
    )

    robot = make_robot(
        robot_id="R1",
        x=0.0,
    )

    scenario = SimulationScenario(
        name="immutable_input",
        tasks=[
            task,
        ],
        robots=[
            robot,
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    run_static_simulation(
        scenario=scenario,
        method=(
            BaselineMethod
            .PROJECTED_NEAREST
        ),
    )

    # 原 Scenario 不可被 Simulator 改掉。
    assert task.status == "pending"

    assert (
        task.assigned_robot
        is None
    )

    assert (
        robot.status
        ==
        "idle"
    )

    assert robot.x == 0.0


# ==========================================================
# No Feasible Robot
# ==========================================================

def test_task_fails_when_no_feasible_robot_exists():

    task = make_task(
        task_id="T1",
        source="A",
        destination="B",
        created_at=0.0,
    )

    scenario = SimulationScenario(
        name="no_candidate",
        tasks=[
            task,
        ],
        robots=[
            make_robot(
                robot_id="R1",
                battery=0.10,
            ),
        ],
        places=make_places(),
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    record = (
        result.task_records[
            "T1"
        ]
    )

    assert (
        record.status
        ==
        "failed"
    )

    assert (
        record.failure_reason
        ==
        "no_feasible_robot"
    )

    assert (
        record.assigned_robot
        is None
    )

    assert (
        record.start_time
        is None
    )

    assert (
        record.completion_time
        is None
    )


# ==========================================================
# Static Assignment
# ==========================================================

def test_static_nearest_does_not_reassign_old_waiting_task():

    # ------------------------------------------------------
    # R1 = x0
    # R2 = x20
    #
    # RUN:
    # t0
    # A(0) -> B(10)
    # → R1
    #
    # OLD:
    # t1
    # source around B
    # → 當時 projected nearest 是 R1
    #
    # EMERGENCY:
    # t2
    # 插到 OLD 前面
    # 並把 R1 帶到 E(90)
    #
    # 之後 OLD 對 R2 已經比較近，
    # 但 Static Nearest 不會重新派工。
    # ------------------------------------------------------

    places = {
        "A": Place(
            "A",
            0.0,
            0.0,
            "L1",
        ),

        "B": Place(
            "B",
            10.0,
            0.0,
            "L1",
        ),

        "OLD_SOURCE": Place(
            "OLD_SOURCE",
            11.0,
            0.0,
            "L1",
        ),

        "OLD_DEST": Place(
            "OLD_DEST",
            12.0,
            0.0,
            "L1",
        ),

        "E": Place(
            "E",
            90.0,
            0.0,
            "L1",
        ),
    }

    running = make_task(
        task_id="RUN",
        source="A",
        destination="B",
        priority=1,
        created_at=0.0,
    )

    old = make_task(
        task_id="OLD",
        source="OLD_SOURCE",
        destination="OLD_DEST",
        priority=1,
        created_at=1.0,
    )

    emergency = make_task(
        task_id="EMERGENCY",
        source="B",
        destination="E",
        priority=3,
        created_at=2.0,
    )

    scenario = SimulationScenario(
        name="static_no_reassignment",
        tasks=[
            running,
            old,
            emergency,
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=0.0,
            ),
            make_robot(
                robot_id="R2",
                x=20.0,
            ),
        ],
        places=places,
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    old_record = (
        result.task_records[
            "OLD"
        ]
    )

    emergency_record = (
        result.task_records[
            "EMERGENCY"
        ]
    )

    # OLD 在 t=1 時確實被派給 R1。
    assert (
        old_record.assigned_robot
        ==
        "R1"
    )

    # Emergency 也選 R1，
    # 並插到 OLD 前面。
    assert (
        emergency_record
        .assigned_robot
        ==
        "R1"
    )

    assert (
        emergency_record.start_time
        <
        old_record.start_time
    )

    # 即使 Emergency 執行後，
    # R1 被帶到很遠的 E，
    # OLD 仍然保持原始 Assignment。
    assert (
        old_record.assigned_robot
        ==
        "R1"
    )


# ==========================================================
# Decision Record
# ==========================================================

def test_assignment_decision_is_recorded():

    scenario = SimulationScenario(
        name="decision",
        tasks=[
            make_task(
                task_id="T1",
                source="A",
                destination="B",
            ),
        ],
        robots=[
            make_robot(
                robot_id="R1",
            ),
        ],
        places=make_places(),
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    assert (
        len(
            result.decision_records
        )
        ==
        1
    )

    decision = (
        result.decision_records[
            0
        ]
    )

    assert (
        decision.task_id
        ==
        "T1"
    )

    assert (
        decision.selected_robot
        ==
        "R1"
    )

    assert (
        decision.decision_type
        ==
        "assignment"
    )

    assert (
        decision
        .decision_duration_seconds
        >=
        0.0
    )


# ==========================================================
# Battery Dynamics
# ==========================================================

def test_task_start_reserves_battery():

    scenario = SimulationScenario(
        name="battery_reservation",
        tasks=[
            make_task(
                task_id="T1",
                source="A",
                destination="B",
                created_at=0.0,
            ),
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=0.0,
                battery=0.80,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    from experiment_v2.simulator import (
        StaticSimulator,
    )

    simulator = StaticSimulator(
        scenario=scenario,
        method=(
            BaselineMethod
            .PROJECTED_NEAREST
        ),
    )

    simulator.run()

    final_battery = (
        simulator
        .runtimes["R1"]
        .robot
        .battery
    )

    # A -> B = 10m
    #
    # default drain:
    # 10 * 0.0005 = 0.005
    #
    # 0.80 - 0.005 = 0.795
    assert (
        final_battery
        ==
        pytest.approx(
            0.795
        )
    )


def test_projected_battery_prevents_unsafe_assignment():

    scenario = SimulationScenario(
        name="battery_safety",
        tasks=[
            make_task(
                task_id="T1",
                source="A",
                destination="D",
                created_at=0.0,
            ),
        ],
        robots=[
            make_robot(
                robot_id="R1",
                x=0.0,
                battery=0.21,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    result = (
        run_static_simulation(
            scenario=scenario,
            method=(
                BaselineMethod
                .PROJECTED_NEAREST
            ),
        )
    )

    record = (
        result.task_records[
            "T1"
        ]
    )

    # A -> D = 30m
    #
    # consumption:
    # 30 * 0.0005 = 0.015
    #
    # projected after:
    # 0.21 - 0.015 = 0.195
    #
    # < 0.20
    #
    # 所以即使 current battery
    # 本身大於 threshold，
    # 仍不能 Assignment。
    assert (
        record.status
        ==
        "failed"
    )

    assert (
        record.failure_reason
        ==
        "no_feasible_robot"
    )