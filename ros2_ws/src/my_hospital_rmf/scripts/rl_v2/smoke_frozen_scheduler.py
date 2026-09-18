#!/usr/bin/env python3

from copy import deepcopy

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from scheduler_v2.runtime import (
    RobotRuntimeState,
)

from rl_v2.frozen_scheduler import (
    FrozenInitialAssignmentScheduler,
)


MODEL_PATH = (
    "rl_v2/models/"
    "long_horizon_ppo_102k_seed42.zip"
)


def main():

    # ======================================================
    # 使用已知 Debug Seed
    # ======================================================

    scenario = (
        generate_hospital_scenario(
            seed=8000,
            task_count=1,
        )
    )

    task = deepcopy(
        scenario.tasks[0]
    )

    # ======================================================
    # 將 Scenario Robot 轉成 Runtime State
    # ======================================================

    runtimes = {}

    for robot in scenario.robots:

        robot_copy = deepcopy(
            robot
        )

        runtimes[
            robot_copy.robot_id
        ] = (
            RobotRuntimeState(
                robot=robot_copy,
                robot_speed_mps=(
                    scenario
                    .robot_speed_mps
                ),
            )
        )

    # ======================================================
    # Load Frozen PPO
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

    # ======================================================
    # Predict
    # ======================================================

    decision = (
        scheduler.assign_task(
            task=task,
            runtimes=runtimes,
            places=scenario.places,
            current_time=(
                task.created_at
            ),
        )
    )

    # ======================================================
    # Output
    # ======================================================

    print(
        "=" * 80
    )

    print(
        "FROZEN INITIAL ASSIGNMENT "
        "SCHEDULER SMOKE TEST"
    )

    print(
        "=" * 80
    )

    print(
        "Task ID       :",
        task.task_id,
    )

    print(
        "Task Type     :",
        task.task_type,
    )

    print(
        "Priority      :",
        task.priority,
    )

    print(
        "Source        :",
        task.source,
    )

    print(
        "Destination   :",
        task.destination,
    )

    print(
        "Required Caps :",
        sorted(
            task.required_capabilities
        ),
    )

    print()

    print(
        "Feasible      :",
        list(
            decision
            .feasible_robot_ids
        ),
    )

    print(
        "Selected      :",
        decision.selected_robot,
    )

    print(
        "Action Index  :",
        decision.action_index,
    )

    print(
        "Decision Time :",
        f"{decision.decision_time_ms:.3f} ms",
    )

    print(
        "=" * 80
    )

    if (
        decision.selected_robot
        is None
    ):

        print(
            "RESULT: NO FEASIBLE ROBOT"
        )

    else:

        assert (
            decision.selected_robot
            in
            decision.feasible_robot_ids
        )

        print(
            "RESULT: PASS"
        )


if __name__ == "__main__":

    main()
