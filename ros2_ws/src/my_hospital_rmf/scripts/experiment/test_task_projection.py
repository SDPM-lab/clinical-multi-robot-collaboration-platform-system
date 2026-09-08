#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler.models import (
    Task,
    RobotState,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)

from experiment.simulator import (
    BaselineSimulator,
    RunningTaskState,
)


@dataclass
class TestScenario:

    name: str
    waypoints: dict
    robots: list
    tasks: list
    task_arrival_times: dict


def create_scenario():

    waypoints = {

        "source": (
            0.0,
            0.0,
        ),

        "running_dest": (
            10.0,
            0.0,
        ),

        "low_dest": (
            20.0,
            0.0,
        ),

        "high_dest": (
            30.0,
            0.0,
        ),
    }

    robots = [

        RobotState(
            robot_id="robot_1",
            fleet_name="hospital_fleet",
            status="busy",
            battery=0.90,
            x=0.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
                "general_delivery",
            },
            current_task=None,
            available=False,
        ),
    ]

    tasks = []

    task_arrival_times = {}

    return TestScenario(
        name="task_projection_test",
        waypoints=waypoints,
        robots=robots,
        tasks=tasks,
        task_arrival_times=task_arrival_times,
    )


def main():

    print("=" * 90)
    print("TASK-SPECIFIC QUEUE PROJECTION TEST")
    print("=" * 90)

    scenario = (
        create_scenario()
    )

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            PriorityScheduler()
        ),

        robot_scheduler=(
            NearestScheduler(
                scenario.waypoints
            )
        ),

        robot_speed=1.0,

        service_time=5.0,
    )

    simulator.current_time = (
        20.0
    )

    sim_state = (
        simulator.robot_states[
            "robot_1"
        ]
    )

    # ======================================================
    # Running Task
    #
    # 現在時間 = 20
    # completion = 50
    #
    # 所以 remaining running time = 30 sec
    # ======================================================

    running_task = Task(
        task_id="RUNNING",
        task_type="general_delivery",
        source="source",
        destination="running_dest",
        priority=1,
        required_capabilities=[
            "navigation",
            "general_delivery",
        ],
    )

    sim_state.running_task = (
        RunningTaskState(

            task=running_task,

            arrival_time=0.0,

            start_time=0.0,

            completion_time=50.0,

            service_time=50.0,

            travel_distance=45.0,

            destination_x=10.0,

            destination_y=0.0,
        )
    )

    # ======================================================
    # Queue 裡先有一筆 Low
    # ======================================================

    low_task = Task(
        task_id="LOW",
        task_type="general_delivery",
        source="source",
        destination="low_dest",
        priority=0,
        required_capabilities=[
            "navigation",
            "general_delivery",
        ],
    )

    sim_state.waiting_tasks.append(
        low_task
    )

    # ======================================================
    # 新來一筆 High
    #
    # Priority 排序後應該是：
    #
    # RUNNING
    # ↓
    # HIGH
    # ↓
    # LOW
    #
    # 所以 HIGH 前面的 workload
    # 只能有 RUNNING 剩餘的 30 秒。
    #
    # HIGH 真正開始時 Robot 應位於
    # running_dest = (10, 0)
    # ======================================================

    high_task = Task(
        task_id="HIGH",
        task_type="general_delivery",
        source="source",
        destination="high_dest",
        priority=2,
        required_capabilities=[
            "navigation",
            "general_delivery",
        ],
    )

    projection = (
        simulator.project_task_on_robot(
            sim_state,
            high_task,
        )
    )

    print(
        "Projected X:",
        projection[
            "projected_x"
        ],
    )

    print(
        "Projected Y:",
        projection[
            "projected_y"
        ],
    )

    print(
        "Workload Before Task:",
        projection[
            "workload_before_task"
        ],
    )

    print(
        "Queue Length Before Task:",
        projection[
            "queue_length_before_task"
        ],
    )

    print(
        "Distance To Source:",
        projection[
            "distance_to_source"
        ],
    )

    # ======================================================
    # Assertions
    # ======================================================

    assert abs(
        projection[
            "projected_x"
        ]
        -
        10.0
    ) < 1e-6

    assert abs(
        projection[
            "projected_y"
        ]
        -
        0.0
    ) < 1e-6

    assert abs(
        projection[
            "workload_before_task"
        ]
        -
        30.0
    ) < 1e-6

    assert (
        projection[
            "queue_length_before_task"
        ]
        ==
        0
    )

    assert abs(
        projection[
            "distance_to_source"
        ]
        -
        10.0
    ) < 1e-6

    print()
    print(
        "Priority insertion position: PASS"
    )

    print(
        "Workload before task: PASS"
    )

    print(
        "Projected robot position: PASS"
    )

    print()
    print(
        "TASK-SPECIFIC PROJECTION TEST: PASS"
    )


if __name__ == "__main__":
    main()