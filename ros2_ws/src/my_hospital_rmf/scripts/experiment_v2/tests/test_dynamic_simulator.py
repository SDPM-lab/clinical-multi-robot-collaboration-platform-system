#!/usr/bin/env python3

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
)

from experiment_v2.models import (
    SimulationScenario,
)

from experiment_v2.simulator import (
    DynamicWeightedSimulator,
    run_dynamic_weighted_simulation,
)


# ==========================================================
# Helpers
# ==========================================================

def make_places():

    return {
        "SOURCE": Place(
            place_id="SOURCE",
            x=0.0,
            y=0.0,
            map_name="L1",
        ),

        "DESTINATION": Place(
            place_id="DESTINATION",
            x=10.0,
            y=0.0,
            map_name="L1",
        ),
    }


def make_robot(
    robot_id: str,
    battery: float,
) -> RobotState:

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status="idle",
        battery=battery,
        x=0.0,
        y=0.0,
        map_name="L1",
        capabilities={
            "navigation",
            "general_delivery",
        },
        available=True,
    )


def make_task() -> Task:

    return Task(
        task_id="T1",
        task_type="general_delivery",
        source="SOURCE",
        destination="DESTINATION",
        priority=1,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=0.0,
    )


def make_scenario(
    r1_battery: float,
    r2_battery: float,
):

    return SimulationScenario(
        name="dynamic_test",
        tasks=[
            make_task(),
        ],
        robots=[
            make_robot(
                "R1",
                r1_battery,
            ),
            make_robot(
                "R2",
                r2_battery,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )


# ==========================================================
# Actual Queue Migration
# ==========================================================

def test_dynamic_pass_moves_waiting_task():

    simulator = (
        DynamicWeightedSimulator(
            scenario=make_scenario(
                r1_battery=0.50,
                r2_battery=1.00,
            )
        )
    )

    # Simulator deep copy 後，
    # 要使用 Simulator 內部的 Task。
    task = (
        simulator.scenario.tasks[0]
    )

    task.status = "assigned"

    task.assigned_robot = "R1"

    simulator.runtimes[
        "R1"
    ].waiting_tasks.append(
        task
    )

    record = (
        simulator.task_records[
            task.task_id
        ]
    )

    record.status = "assigned"

    record.assigned_robot = "R1"

    record.assigned_at = 0.0

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T2"
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R2"
    )

    assert (
        task
        not in
        simulator.runtimes[
            "R1"
        ].waiting_tasks
    )

    assert (
        task
        in
        simulator.runtimes[
            "R2"
        ].waiting_tasks
    )

    assert (
        record.assigned_robot
        ==
        "R2"
    )

    reassignment = (
        simulator
        .decision_records[-1]
    )

    assert (
        reassignment
        .decision_type
        ==
        "reassignment"
    )

    assert (
        reassignment
        .previous_robot
        ==
        "R1"
    )

    assert (
        reassignment
        .selected_robot
        ==
        "R2"
    )

    assert (
        reassignment.changed
        is True
    )

    assert (
        reassignment
        .cascade_depth
        ==
        1
    )


# ==========================================================
# Hysteresis Stay
# ==========================================================

def test_dynamic_pass_can_keep_current_robot():

    simulator = (
        DynamicWeightedSimulator(
            scenario=make_scenario(
                r1_battery=0.80,
                r2_battery=0.90,
            )
        )
    )

    task = (
        simulator.scenario.tasks[0]
    )

    task.status = "assigned"

    task.assigned_robot = "R1"

    simulator.runtimes[
        "R1"
    ].waiting_tasks.append(
        task
    )

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T2"
        )
    )

    assert changed is False

    assert (
        task.assigned_robot
        ==
        "R1"
    )

    assert (
        task
        in
        simulator.runtimes[
            "R1"
        ].waiting_tasks
    )

    decision = (
        simulator
        .decision_records[-1]
    )

    assert (
        decision.changed
        is False
    )

    assert (
        decision
        .decision_type
        ==
        "reassignment"
    )


# ==========================================================
# End-to-End
# ==========================================================

def test_dynamic_weighted_episode_runs():

    scenario = (
        make_scenario(
            r1_battery=0.80,
            r2_battery=0.80,
        )
    )

    result = (
        run_dynamic_weighted_simulation(
            scenario=scenario,
            seed=123,
        )
    )

    assert (
        result.method
        ==
        "dynamic_weighted_heuristic"
    )

    assert (
        result
        .task_records[
            "T1"
        ]
        .status
        ==
        "completed"
    )

    # 至少有 Initial Assignment。
    assert any(
        decision.decision_type
        ==
        "assignment"
        for decision
        in result.decision_records
    )


def test_immediate_reversal_guard_prevents_ping_pong():

    simulator = (
        DynamicWeightedSimulator(
            scenario=make_scenario(
                r1_battery=0.50,
                r2_battery=1.00,
            )
        )
    )

    task = (
        simulator.scenario.tasks[0]
    )

    task.status = "assigned"
    task.assigned_robot = "R1"

    simulator.runtimes[
        "R1"
    ].waiting_tasks.append(
        task
    )

    # ======================================================
    # 第一次：
    #
    # R1 -> R2
    # ======================================================

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T2"
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R2"
    )

    assert (
        simulator
        .last_departed_robot[
            task.task_id
        ]
        ==
        "R1"
    )

    # ======================================================
    # 現在反過來讓 R1 明顯更好。
    #
    # Weighted 會想：
    #
    # R2 -> R1
    #
    # 但這正是 Immediate Reversal，
    # 所以應阻止。
    # ======================================================

    simulator.runtimes[
        "R1"
    ].robot.battery = 1.00

    simulator.runtimes[
        "R2"
    ].robot.battery = 0.50

    simulator.current_time = 100.0

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T3"
        )
    )

    assert changed is False

    assert (
        task.assigned_robot
        ==
        "R2"
    )


def test_reversal_guard_allows_move_to_third_robot():

    scenario = SimulationScenario(
        name="three_robot_dynamic",
        tasks=[
            make_task(),
        ],
        robots=[
            make_robot(
                "R1",
                0.50,
            ),
            make_robot(
                "R2",
                1.00,
            ),
            make_robot(
                "R3",
                0.40,
            ),
        ],
        places=make_places(),
        robot_speed_mps=1.0,
        service_time_seconds=0.0,
    )

    simulator = (
        DynamicWeightedSimulator(
            scenario=scenario
        )
    )

    task = (
        simulator.scenario.tasks[0]
    )

    task.status = "assigned"
    task.assigned_robot = "R1"

    simulator.runtimes[
        "R1"
    ].waiting_tasks.append(
        task
    )

    # R1 -> R2
    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T2"
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R2"
    )

    assert (
        simulator
        .last_departed_robot[
            task.task_id
        ]
        ==
        "R1"
    )

    # ======================================================
    # 接著讓 R3 成為最好。
    #
    # R2 -> R3 是合法的，
    # 因為 R3 不是剛離開的 R1。
    # ======================================================

    simulator.runtimes[
        "R1"
    ].robot.battery = 0.40

    simulator.runtimes[
        "R2"
    ].robot.battery = 0.50

    simulator.runtimes[
        "R3"
    ].robot.battery = 1.00

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T3"
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R3"
    )

    # 現在剛離開的是 R2。
    assert (
        simulator
        .last_departed_robot[
            task.task_id
        ]
        ==
        "R2"
    )


def test_reversal_guard_does_not_block_safety_reassignment():

    simulator = (
        DynamicWeightedSimulator(
            scenario=make_scenario(
                r1_battery=0.50,
                r2_battery=1.00,
            )
        )
    )

    task = (
        simulator.scenario.tasks[0]
    )

    task.status = "assigned"
    task.assigned_robot = "R1"

    simulator.runtimes[
        "R1"
    ].waiting_tasks.append(
        task
    )

    # R1 -> R2
    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id="arrival:T2"
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R2"
    )

    assert (
        simulator
        .last_departed_robot[
            task.task_id
        ]
        ==
        "R1"
    )

    # ======================================================
    # R2 現在 offline。
    #
    # 正常 Reversal Guard 會阻止：
    # R2 -> R1
    #
    # 但因為 Current Robot infeasible，
    # Safety 必須優先。
    # ======================================================

    simulator.runtimes[
        "R2"
    ].robot.status = "offline"

    simulator.runtimes[
        "R1"
    ].robot.status = "idle"

    simulator.runtimes[
        "R1"
    ].robot.battery = 1.00

    changed = (
        simulator
        ._run_dynamic_reassignment_pass(
            root_event_id=(
                "robot_status:R2"
            )
        )
    )

    assert changed is True

    assert (
        task.assigned_robot
        ==
        "R1"
    )