#!/usr/bin/env python3

from copy import deepcopy

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)

from rl_v2.frozen_scheduler import (
    FrozenInitialAssignmentScheduler,
)

from rl_v2.runtime_state_manager import (
    RuntimeStateManager,
)


MODEL_PATH = (
    "rl_v2/models/"
    "long_horizon_ppo_102k_seed42.zip"
)


def main():

    # ======================================================
    # Scenario
    # ======================================================

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=2,
        )
    )

    task1 = deepcopy(
        scenario.tasks[0]
    )

    task2 = deepcopy(
        scenario.tasks[1]
    )

    robots = [
        deepcopy(robot)
        for robot
        in scenario.robots
    ]

    # ======================================================
    # Runtime Manager
    # ======================================================

    manager = (
        RuntimeStateManager(
            robots=robots,
            robot_speed_mps=(
                scenario
                .robot_speed_mps
            ),
        )
    )

    # ======================================================
    # Frozen PPO
    # ======================================================

    scheduler = (
        FrozenInitialAssignmentScheduler(
            model_path=(
                MODEL_PATH
            ),
            service_time_seconds=(
                scenario
                .service_time_seconds
            ),
        )
    )

    print()
    print(
        "STEP 0 - INITIAL STATE"
    )

    manager.print_state()

    # ======================================================
    # T001 Initial Assignment
    # ======================================================

    print()
    print(
        "STEP 1 - ASSIGN T001"
    )

    decision1 = (
        scheduler.assign_task(
            task=task1,
            runtimes=(
                manager.get_runtimes()
            ),
            places=scenario.places,
            current_time=(
                task1.created_at
            ),
        )
    )

    if (
        decision1.selected_robot
        is None
    ):

        raise RuntimeError(
            "T001 has no feasible robot"
        )

    print(
        "T001 selected:",
        decision1.selected_robot,
    )

    manager.enqueue_task(
        task=task1,
        robot_id=(
            decision1
            .selected_robot
        ),
        current_time=(
            task1.created_at
        ),
    )

    manager.print_state()

    # ======================================================
    # T001 Start
    #
    # 先用 60 秒作 Smoke。
    #
    # 真正接 RMF 時，
    # remaining_time 會由執行狀態 / ETA 更新。
    # ======================================================

    print()
    print(
        "STEP 2 - START T001"
    )

    manager.start_task(
        robot_id=(
            decision1
            .selected_robot
        ),
        task_id=(
            task1.task_id
        ),
        remaining_time=60.0,
    )

    manager.print_state()

    # ======================================================
    # Before T002 Assignment
    #
    # 印出每台 Robot 對 T002 的 Projection。
    # ======================================================

    print()
    print(
        "STEP 3 - T002 PROJECTION"
    )

    print(
        "=" * 100
    )

    for robot_id in sorted(
        manager.get_runtimes()
    ):

        runtime = (
            manager
            .get_runtimes()[
                robot_id
            ]
        )

        projection = (
            project_task_on_robot(
                task=task2,
                runtime=runtime,
                places=scenario.places,
                current_time=(
                    task2.created_at
                ),
                service_time_seconds=(
                    scenario
                    .service_time_seconds
                ),
            )
        )

        print(
            f"{robot_id:<20} "
            f"running="
            f"{str(
                None
                if runtime.running_task
                is None
                else
                runtime.running_task.task_id
            ):<8} "
            f"remaining="
            f"{runtime.running_remaining_time:>7.2f}s "
            f"workload_before="
            f"{projection.workload_before_task:>8.2f}s "
            f"queue_before="
            f"{projection.queue_length_before_task:>2}"
        )

    print(
        "=" * 100
    )

    # ======================================================
    # T002 Assignment
    # ======================================================

    print()
    print(
        "STEP 4 - ASSIGN T002"
    )

    decision2 = (
        scheduler.assign_task(
            task=task2,
            runtimes=(
                manager.get_runtimes()
            ),
            places=scenario.places,
            current_time=(
                task2.created_at
            ),
        )
    )

    print(
        "T002 feasible:",
        list(
            decision2
            .feasible_robot_ids
        ),
    )

    print(
        "T002 selected:",
        decision2.selected_robot,
    )

    print(
        "T002 decision time:",
        f"{decision2.decision_time_ms:.3f} ms",
    )

    if (
        decision2.selected_robot
        is None
    ):

        raise RuntimeError(
            "T002 has no feasible robot"
        )

    manager.enqueue_task(
        task=task2,
        robot_id=(
            decision2
            .selected_robot
        ),
        current_time=(
            task2.created_at
        ),
    )

    manager.print_state()

    # ======================================================
    # Assertions
    # ======================================================

    runtime1 = (
        manager.get_runtime(
            decision1.selected_robot
        )
    )

    assert (
        runtime1.running_task
        is not None
    )

    assert (
        runtime1.running_task.task_id
        ==
        task1.task_id
    )

    assert (
        runtime1.running_remaining_time
        ==
        60.0
    )

    assert (
        task2.assigned_robot
        ==
        decision2.selected_robot
    )

    print()

    print(
        "=" * 90
    )

    print(
        "RUNTIME + FROZEN PPO "
        "INTEGRATION: PASS"
    )

    print(
        "=" * 90
    )


if __name__ == "__main__":

    main()
