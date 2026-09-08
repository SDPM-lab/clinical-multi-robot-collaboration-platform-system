#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler.models import (
    Task,
    RobotState,
)

from scheduler.task_selection.fcfs_scheduler import (
    FCFSScheduler,
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
# Scenario
# ==========================================================

def create_scenario():

    waypoints = {

        "start": (
            0.0,
            0.0,
        ),

        "source": (
            0.0,
            0.0,
        ),

        "ward_a": (
            10.0,
            0.0,
        ),

        "ward_b": (
            20.0,
            0.0,
        ),
    }

    # ------------------------------------------------------
    # 只放一台 Robot
    #
    # 這樣 T1、T2 必定都排到 robot_1。
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # 兩筆 Task 都在 time=0 到達。
    #
    # T1:
    # source 0 → ward_a 10
    #
    # distance = 10
    # service = 10 + fixed 5 = 15 sec
    #
    # T2 被預約時 robot_1 已經 Busy 到 15 sec。
    #
    # Robot Queue 尾端位置已經是 ward_a = 10。
    #
    # T2:
    # robot ward_a 10 → source 0 = 10
    # source 0 → ward_b 20 = 20
    #
    # distance = 30
    # service = 30 + 5 = 35 sec
    #
    # 所以：
    #
    # T1 start = 0
    # T1 completion = 15
    #
    # T2 start = 15
    # T2 completion = 50
    # ------------------------------------------------------

    tasks = [

        Task(
            task_id="T1",
            task_type="general_delivery",
            source="source",
            destination="ward_a",
            priority=1,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),

        Task(
            task_id="T2",
            task_type="general_delivery",
            source="source",
            destination="ward_b",
            priority=1,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),
    ]

    task_arrival_times = {
        "T1": 0.0,
        "T2": 0.0,
    }

    return TestScenario(
        name="busy_reservation_test",
        waypoints=waypoints,
        robots=robots,
        tasks=tasks,
        task_arrival_times=task_arrival_times,
    )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 90)
    print("BASELINE SIMULATOR BUSY RESERVATION TEST")
    print("=" * 90)

    scenario = (
        create_scenario()
    )

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            FCFSScheduler()
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

    records = (
        result[
            "records"
        ]
    )

    for record in records:

        print(
            f"{record.task_id}"
            f" | robot={record.robot_id}"
            f" | arrival={record.arrival_time:.2f}"
            f" | start={record.start_time:.2f}"
            f" | completion={record.completion_time:.2f}"
            f" | wait={record.waiting_time:.2f}"
            f" | service={record.service_time:.2f}"
            f" | distance={record.travel_distance:.2f}"
        )

    print()
    print(
        "Simulation End Time:",
        result[
            "simulation_end_time"
        ],
    )

    # ======================================================
    # Assertions
    # ======================================================

    assert (
        len(records)
        ==
        2
    )

    t1 = records[0]
    t2 = records[1]

    assert (
        t1.robot_id
        ==
        "robot_1"
    )

    assert (
        t2.robot_id
        ==
        "robot_1"
    )

    # ------------------------------------------------------
    # T1
    # ------------------------------------------------------

    assert abs(
        t1.start_time
        -
        0.0
    ) < 1e-6

    assert abs(
        t1.completion_time
        -
        15.0
    ) < 1e-6

    # ------------------------------------------------------
    # T2 必須排在 T1 後面
    # ------------------------------------------------------

    assert abs(
        t2.start_time
        -
        t1.completion_time
    ) < 1e-6

    assert abs(
        t2.start_time
        -
        15.0
    ) < 1e-6

    assert abs(
        t2.waiting_time
        -
        15.0
    ) < 1e-6

    assert abs(
        t2.completion_time
        -
        50.0
    ) < 1e-6

    assert abs(
        result[
            "simulation_end_time"
        ]
        -
        50.0
    ) < 1e-6

    print()
    print(
        "Busy robot selected: PASS"
    )

    print(
        "Queued start time: PASS"
    )

    print(
        "Waiting time: PASS"
    )

    print(
        "Simulation end time: PASS"
    )

    print()
    print(
        "BUSY RESERVATION SIMULATOR TEST: PASS"
    )


if __name__ == "__main__":
    main()