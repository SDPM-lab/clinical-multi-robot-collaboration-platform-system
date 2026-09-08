#!/usr/bin/env python3

import os
import statistics

import numpy as np

from sb3_contrib import (
    MaskablePPO,
)

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from rl.hospital_gym_env import (
    HospitalGymEnv,
)


# ==========================================================
# Config
# ==========================================================

EVALUATION_SEEDS = list(
    range(10)
)

TASK_COUNT = 20

LOAD = (
    "medium"
)


# ==========================================================
# Path
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    SCRIPT_DIR,
    "models",
    "maskable_ppo_hospital.zip",
)


# ==========================================================
# Run One Episode
# ==========================================================

def run_episode(
    model,
    seed,
):

    scenario = (
        generate_random_scenario(

            task_count=TASK_COUNT,

            seed=seed,

            load=LOAD,

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    env = HospitalGymEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    (
        observation,
        info,
    ) = env.reset()

    action_choice_counts = {
        1: 0,
        2: 0,
        3: 0,
    }

    capability_choice_counts = {
        1: 0,
        2: 0,
        3: 0,
    }

    robot_task_counts = {
        robot_id: 0
        for robot_id
        in env.core_env.robot_ids
    }

    total_reward = 0.0

    while True:

        task = (
            env.core_env.current_task
        )

        required_capabilities = set(
            task.required_capabilities
        )

        capability_count = 0

        for sim_state in (
            env.core_env.robot_states.values()
        ):

            robot_capabilities = set(
                sim_state.robot.capabilities
            )

            if required_capabilities.issubset(
                robot_capabilities
            ):

                capability_count += 1

        capability_choice_counts[
            capability_count
        ] = (
            capability_choice_counts.get(
                capability_count,
                0,
            )
            +
            1
        )

        mask = (
            env.action_masks()
        )

        valid_count = int(
            np.sum(
                mask
            )
        )

        action_choice_counts[
            valid_count
        ] = (
            action_choice_counts.get(
                valid_count,
                0,
            )
            +
            1
        )

        (
            action,
            _
        ) = model.predict(

            observation,

            action_masks=mask,

            deterministic=True,
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        total_reward += (
            reward
        )

        robot_id = (
            info[
                "robot_id"
            ]
        )

        robot_task_counts[
            robot_id
        ] += 1

        if (
            terminated
            or truncated
        ):
            break

    # ======================================================
    # Final execution metrics
    #
    # 新版 step() 只做 Assignment。
    # 真正的 start / completion / waiting / distance
    # 必須在 Episode 結束後由 execution_records 取得。
    # ======================================================

    execution_records = list(
        env.core_env.execution_records
    )

    waiting_times = [
        record.waiting_time
        for record
        in execution_records
    ]

    completion_times = [
        (
            record.completion_time
            -
            record.arrival_time
        )
        for record
        in execution_records
    ]

    travel_distances = [
        record.travel_distance
        for record
        in execution_records
    ]

    emergency_waiting_times = [
        record.waiting_time
        for record
        in execution_records
        if record.priority == 3
    ]

    high_waiting_times = [
        record.waiting_time
        for record
        in execution_records
        if record.priority == 2
    ]

    # 使用 final execution records 重新統計每台 Robot 任務數。
    robot_task_counts = {
        robot_id: 0
        for robot_id
        in env.core_env.robot_ids
    }

    for record in execution_records:
        robot_task_counts[
            record.robot_id
        ] += 1

    if len(execution_records) != TASK_COUNT:
        raise RuntimeError(
            "Execution record count mismatch: "
            f"expected {TASK_COUNT}, "
            f"got {len(execution_records)}"
        )

    simulation_end_time = (
        env.core_env
        .get_simulation_end_time()
    )

    robot_utilizations = []

    for sim_state in (
        env.core_env
        .robot_states
        .values()
    ):

        utilization = (
            sim_state.total_busy_time
            /
            simulation_end_time
        )

        robot_utilizations.append(
            utilization
        )

    env.close()

    return {

        "seed":
            seed,

        "average_waiting_time":
            statistics.mean(
                waiting_times
            ),

        "average_completion_time":
            statistics.mean(
                completion_times
            ),

        "emergency_waiting_time":
            (
                statistics.mean(
                    emergency_waiting_times
                )
                if emergency_waiting_times
                else None
            ),

        "high_waiting_time":
            (
                statistics.mean(
                    high_waiting_times
                )
                if high_waiting_times
                else None
            ),

        "total_travel_distance":
            sum(
                travel_distances
            ),

        "makespan":
            simulation_end_time,

        "average_utilization":
            statistics.mean(
                robot_utilizations
            ),

        "task_load_std":
            statistics.pstdev(
                robot_task_counts.values()
            ),

        "success_rate":
            (
                len(execution_records)
                /
                TASK_COUNT
            ),

        "total_reward":
            total_reward,

        "one_choice":
            action_choice_counts[
                1
            ],

        "two_choices":
            action_choice_counts[
                2
            ],

        "three_choices":
            action_choice_counts[
                3
            ],

        "capability_one_choice":
            capability_choice_counts[
                1
            ],

        "capability_two_choices":
            capability_choice_counts[
                2
            ],

        "capability_three_choices":
            capability_choice_counts[
                3
            ],
    }


# ==========================================================
# Mean / Std Helper
# ==========================================================

def mean_std(
    values,
):

    values = [
        value
        for value
        in values
        if value is not None
    ]

    if not values:
        return None, None

    mean_value = (
        statistics.mean(
            values
        )
    )

    std_value = (
        statistics.stdev(
            values
        )
        if len(values) >= 2
        else 0.0
    )

    return (
        mean_value,
        std_value,
    )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 110)
    print("MASKABLE PPO EVALUATION")
    print("=" * 110)

    print(
        "Model:",
        MODEL_PATH,
    )

    print(
        "Task Count:",
        TASK_COUNT,
    )

    print(
        "Load:",
        LOAD,
    )

    print(
        "Evaluation Seeds:",
        EVALUATION_SEEDS,
    )

    print()

    model = MaskablePPO.load(
        MODEL_PATH,
        device="cpu",
    )

    results = []

    for seed in (
        EVALUATION_SEEDS
    ):

        result = run_episode(
            model,
            seed,
        )

        results.append(
            result
        )

        print(
            f"Seed {seed:02d}"
            f" | wait="
            f"{result['average_waiting_time']:.2f}"
            f" | P3="
            f"{result['emergency_waiting_time'] if result['emergency_waiting_time'] is not None else 'N/A'}"
            f" | dist="
            f"{result['total_travel_distance']:.2f}"
            f" | makespan="
            f"{result['makespan']:.2f}"
            f" | reward="
            f"{result['total_reward']:.3f}"
            f" | choices="
            f"{result['one_choice']}/"
            f"{result['two_choices']}/"
            f"{result['three_choices']}"
        )

    print()
    print("=" * 110)
    print("SUMMARY")
    print("=" * 110)

    metrics = [
        "average_waiting_time",
        "average_completion_time",
        "emergency_waiting_time",
        "high_waiting_time",
        "total_travel_distance",
        "makespan",
        "average_utilization",
        "task_load_std",
        "success_rate",
        "total_reward",
    ]

    for metric in metrics:

        mean_value, std_value = (
            mean_std(
                [
                    result[
                        metric
                    ]
                    for result
                    in results
                ]
            )
        )

        print(
            f"{metric:<28}"
            f"{mean_value:.3f}"
            f" ± "
            f"{std_value:.3f}"
        )

    one_choice = sum(
        result[
            "one_choice"
        ]
        for result
        in results
    )

    two_choices = sum(
        result[
            "two_choices"
        ]
        for result
        in results
    )

    three_choices = sum(
        result[
            "three_choices"
        ]
        for result
        in results
    )

    total_decisions = (
        one_choice
        +
        two_choices
        +
        three_choices
    )

    capability_one_choice = sum(

        result[
            "capability_one_choice"
        ]

        for result
        in results
    )

    capability_two_choices = sum(

        result[
            "capability_two_choices"
        ]

        for result
        in results
    )

    capability_three_choices = sum(

        result[
            "capability_three_choices"
        ]

        for result
        in results
    )

    print()
    print("=" * 110)
    print("ACTION CHOICE ANALYSIS")
    print("=" * 110)

    print(
        "1 valid robot:",
        one_choice,
        f"({one_choice / total_decisions:.1%})",
    )

    print(
        "2 valid robots:",
        two_choices,
        f"({two_choices / total_decisions:.1%})",
    )

    print(
        "3 valid robots:",
        three_choices,
        f"({three_choices / total_decisions:.1%})",
    )

    print()

    print(
        "Real RL decisions:",
        two_choices + three_choices,
        "/",
        total_decisions,
    )

    print()
    print("=" * 110)
    print("CAPABILITY CHOICE ANALYSIS")
    print("=" * 110)

    print(
        "1 capability-compatible robot:",
        capability_one_choice,
    )

    print(
        "2 capability-compatible robots:",
        capability_two_choices,
    )

    print(
        "3 capability-compatible robots:",
        capability_three_choices,
    )

    capability_multi_choice = (
        capability_two_choices
        +
        capability_three_choices
    )

    print()

    print(
        "Capability allows competition:",
        capability_multi_choice,
        "/",
        total_decisions,
        f"({capability_multi_choice / total_decisions:.1%})",
    )

    print()
    print(
        "EVALUATION COMPLETED"
    )


if __name__ == "__main__":
    main()