#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler.models import (
    Task,
    RobotState,
)

from scheduler.task_selection.fcfs_scheduler import (
    FCFSScheduler,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)

from experiment.simulator import (
    BaselineSimulator,
)


# ==========================================================
# Minimal Scenario
# ==========================================================

@dataclass
class TestScenario:

    name: str
    waypoints: dict
    robots: list
    tasks: list
    task_arrival_times: dict


# ==========================================================
# Create Scenario
#
# 只有一台 Robot，因此所有 Task 都一定進 robot_1 queue。
#
# 時間設計：
#
# T0:
#   arrival = 0
#   priority = Normal
#   執行時間足夠長
#
# T1:
#   arrival = 5
#   priority = Low
#
# T2:
#   arrival = 10
#   priority = High
#
# 當 T0 還在執行時：
#
# waiting queue 會先有 T1，
# 接著 T2 到達。
#
# FCFS:
#   T0 → T1 → T2
#
# Priority:
#   T0 → T2 → T1
#
# T0 本身不可被搶占。
# ==========================================================

def create_scenario():

    waypoints = {

        "source": (
            0.0,
            0.0,
        ),

        "long_target": (
            100.0,
            0.0,
        ),

        "low_target": (
            110.0,
            0.0,
        ),

        "high_target": (
            120.0,
            0.0,
        ),
    }

    robots = [

        RobotState(
            robot_id="robot_1",
            fleet_name="hospital_fleet",
            status="idle",
            battery=0.90,
            x=0.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
                "general_delivery",
            },
            current_task=None,
            available=True,
        ),
    ]

    tasks = [

        # --------------------------------------------------
        # T0：
        #
        # distance = 100
        # fixed service = 5
        #
        # completion = 105
        #
        # 因此 T1 / T2 到達時，
        # robot_1 一定仍在執行 T0。
        # --------------------------------------------------

        Task(
            task_id="T0",
            task_type="general_delivery",
            source="source",
            destination="long_target",
            priority=1,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),

        # --------------------------------------------------
        # Low priority
        # --------------------------------------------------

        Task(
            task_id="T1",
            task_type="general_delivery",
            source="source",
            destination="low_target",
            priority=0,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),

        # --------------------------------------------------
        # High priority
        # --------------------------------------------------

        Task(
            task_id="T2",
            task_type="general_delivery",
            source="source",
            destination="high_target",
            priority=2,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),
    ]

    task_arrival_times = {

        "T0": 0.0,

        "T1": 5.0,

        "T2": 10.0,
    }

    return TestScenario(
        name="robot_priority_queue_test",
        waypoints=waypoints,
        robots=robots,
        tasks=tasks,
        task_arrival_times=task_arrival_times,
    )


# ==========================================================
# Run One Queue Policy
# ==========================================================

def run_test(
    name,
    task_scheduler,
):

    print()
    print("=" * 90)
    print(name)
    print("=" * 90)

    scenario = (
        create_scenario()
    )

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            task_scheduler
        ),

        robot_scheduler=(
            NearestScheduler(
                scenario.waypoints
            )
        ),

        robot_speed=1.0,

        service_time=5.0,
    )

    result = (
        simulator.run()
    )

    records = [
        record
        for record
        in result["records"]
        if record.success
    ]

    records = sorted(
        records,
        key=lambda record:
            record.start_time,
    )

    for record in records:

        print(
            f"{record.task_id}"
            f" | P={record.priority}"
            f" | arrival={record.arrival_time:.2f}"
            f" | start={record.start_time:.2f}"
            f" | complete={record.completion_time:.2f}"
            f" | wait={record.waiting_time:.2f}"
        )

    execution_order = [
        record.task_id
        for record
        in records
    ]

    print()
    print(
        "Execution Order:",
        " -> ".join(
            execution_order
        ),
    )

    return (
        execution_order,
        records,
    )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 90)
    print("PER-ROBOT QUEUE PRIORITY TEST")
    print("=" * 90)

    # ======================================================
    # FCFS
    # ======================================================

    (
        fcfs_order,
        fcfs_records,
    ) = run_test(

        "FCFS Robot Queue",

        FCFSScheduler(),
    )

    # ======================================================
    # Priority
    # ======================================================

    (
        priority_order,
        priority_records,
    ) = run_test(

        "Priority Robot Queue",

        PriorityScheduler(),
    )

    # ======================================================
    # Assertions
    # ======================================================

    assert (
        fcfs_order
        ==
        [
            "T0",
            "T1",
            "T2",
        ]
    )

    assert (
        priority_order
        ==
        [
            "T0",
            "T2",
            "T1",
        ]
    )

    # ------------------------------------------------------
    # T0 必須在兩種 Queue Policy 下都先執行，
    # 不能被後到的 High priority Task 搶占。
    # ------------------------------------------------------

    assert (
        fcfs_records[
            0
        ].task_id
        ==
        "T0"
    )

    assert (
        priority_records[
            0
        ].task_id
        ==
        "T0"
    )

    # ------------------------------------------------------
    # T0 起始時間也必須完全相同。
    # ------------------------------------------------------

    assert abs(
        fcfs_records[
            0
        ].start_time
        -
        0.0
    ) < 1e-6

    assert abs(
        priority_records[
            0
        ].start_time
        -
        0.0
    ) < 1e-6

    # ------------------------------------------------------
    # Priority 模式：
    #
    # T2 雖然比 T1 晚到，
    # 但 T0 完成後必須先執行 T2。
    # ------------------------------------------------------

    assert (
        priority_records[
            1
        ].task_id
        ==
        "T2"
    )

    print()
    print("=" * 90)

    print(
        "Running task non-preemption: PASS"
    )

    print(
        "FCFS local queue order: PASS"
    )

    print(
        "Priority local queue reorder: PASS"
    )

    print()

    print(
        "PER-ROBOT PRIORITY QUEUE TEST: PASS"
    )


if __name__ == "__main__":
    main()