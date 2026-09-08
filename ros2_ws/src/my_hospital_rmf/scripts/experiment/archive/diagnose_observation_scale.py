#!/usr/bin/env python3

import statistics

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
# Diagnostic Conditions
# ==========================================================

TASK_COUNTS = [
    20,
    50,
    100,
]

LOADS = [
    "low",
    "medium",
    "high",
]

SEEDS = [
    5000,
    5001,
    5002,
]


# ==========================================================
# Observation Labels
#
# 33D:
#
# Task = 6
#
# Robot 1 = 9
# Robot 2 = 9
# Robot 3 = 9
# ==========================================================

OBS_LABELS = [

    # ======================================================
    # Task
    # ======================================================

    "task_0",
    "task_1",
    "task_2",
    "task_3",
    "task_4",
    "task_5",

    # ======================================================
    # Robot 1
    # ======================================================

    "r1_projected_x",
    "r1_projected_y",
    "r1_battery",
    "r1_workload_before_task",
    "r1_distance_to_source",
    "r1_capability_match",
    "r1_queue_length_before_task",
    "r1_total_queue_length",
    "r1_completed_tasks_ratio",

    # ======================================================
    # Robot 2
    # ======================================================

    "r2_projected_x",
    "r2_projected_y",
    "r2_battery",
    "r2_workload_before_task",
    "r2_distance_to_source",
    "r2_capability_match",
    "r2_queue_length_before_task",
    "r2_total_queue_length",
    "r2_completed_tasks_ratio",

    # ======================================================
    # Robot 3
    # ======================================================

    "r3_projected_x",
    "r3_projected_y",
    "r3_battery",
    "r3_workload_before_task",
    "r3_distance_to_source",
    "r3_capability_match",
    "r3_queue_length_before_task",
    "r3_total_queue_length",
    "r3_completed_tasks_ratio",
]


# ==========================================================
# Observation Collector
# ==========================================================

def collect_observations(
    task_count,
    load,
    seed,
):

    scenario = (
        generate_random_scenario(

            task_count=(
                task_count
            ),

            seed=(
                seed
            ),

            load=(
                load
            ),

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    env = HospitalGymEnv(

        scenario=(
            scenario
        ),

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    observation, info = (
        env.reset()
    )

    observations = []

    while True:

        observations.append(
            observation.copy()
        )

        # ==================================================
        # Diagnostic Action
        #
        # 這裡不使用 PPO，
        # 只選第一個合法 action。
        #
        # 目的：
        # 收集 observation scale，
        # 不是評估 policy performance。
        # ==================================================

        mask = (
            env.action_masks()
        )

        valid_actions = [
            index
            for index, valid
            in enumerate(mask)
            if valid
        ]

        if not valid_actions:

            raise RuntimeError(
                "No valid actions."
            )

        action = (
            valid_actions[
                0
            ]
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = (
            env.step(
                action
            )
        )

        if (
            terminated
            or truncated
        ):

            break

    env.close()

    return observations


# ==========================================================
# Flatten Statistics
# ==========================================================

def calculate_stats(
    all_observations,
):

    if not all_observations:

        raise RuntimeError(
            "No observations collected."
        )

    dimension = len(
        all_observations[
            0
        ]
    )

    values_by_dimension = [
        []
        for _ in range(
            dimension
        )
    ]

    for observation in (
        all_observations
    ):

        if len(
            observation
        ) != dimension:

            raise RuntimeError(
                "Observation dimension changed."
            )

        for index, value in enumerate(
            observation
        ):

            values_by_dimension[
                index
            ].append(
                float(
                    value
                )
            )

    stats = []

    for index, values in enumerate(
        values_by_dimension
    ):

        mean_value = (
            statistics.mean(
                values
            )
        )

        if len(
            values
        ) >= 2:

            std_value = (
                statistics.stdev(
                    values
                )
            )

        else:

            std_value = 0.0

        stats.append(
            {
                "index":
                    index,

                "label":
                    (
                        OBS_LABELS[
                            index
                        ]
                        if index < len(
                            OBS_LABELS
                        )
                        else f"obs_{index}"
                    ),

                "min":
                    min(
                        values
                    ),

                "max":
                    max(
                        values
                    ),

                "mean":
                    mean_value,

                "std":
                    std_value,
            }
        )

    return stats


# ==========================================================
# Print Stats
# ==========================================================

def print_stats(
    stats,
):

    print()

    print("=" * 120)

    print(
        "OBSERVATION SCALE SUMMARY"
    )

    print("=" * 120)

    print(
        f"{'Idx':>3}"
        f" | "
        f"{'Feature':<30}"
        f" | "
        f"{'Min':>12}"
        f" | "
        f"{'Max':>12}"
        f" | "
        f"{'Mean':>12}"
        f" | "
        f"{'Std':>12}"
    )

    print("-" * 120)

    for row in stats:

        print(
            f"{row['index']:>3}"
            f" | "
            f"{row['label']:<30}"
            f" | "
            f"{row['min']:>12.3f}"
            f" | "
            f"{row['max']:>12.3f}"
            f" | "
            f"{row['mean']:>12.3f}"
            f" | "
            f"{row['std']:>12.3f}"
        )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 120)

    print(
        "RL OBSERVATION SCALE DIAGNOSTIC"
    )

    print("=" * 120)

    print(
        "Task Counts:",
        TASK_COUNTS,
    )

    print(
        "Loads:",
        LOADS,
    )

    print(
        "Seeds:",
        SEEDS,
    )

    all_observations = []

    for task_count in (
        TASK_COUNTS
    ):

        for load in (
            LOADS
        ):

            for seed in (
                SEEDS
            ):

                observations = (
                    collect_observations(

                        task_count=(
                            task_count
                        ),

                        load=(
                            load
                        ),

                        seed=(
                            seed
                        ),
                    )
                )

                all_observations.extend(
                    observations
                )

                print(
                    f"Collected"
                    f" | tasks={task_count}"
                    f" | load={load:<6}"
                    f" | seed={seed}"
                    f" | observations="
                    f"{len(observations)}"
                )

    print()

    print(
        "Total Observations:",
        len(
            all_observations
        ),
    )

    stats = (
        calculate_stats(
            all_observations
        )
    )

    print_stats(
        stats
    )


if __name__ == "__main__":
    main()