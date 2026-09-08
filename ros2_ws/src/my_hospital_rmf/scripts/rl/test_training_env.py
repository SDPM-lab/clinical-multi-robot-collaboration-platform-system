#!/usr/bin/env python3

import numpy as np

from rl.training_env import (
    RandomizedHospitalGymEnv,
)


def run_episode(
    env,
):

    (
        observation,
        info,
    ) = env.reset()

    scenario_seed = (
        info[
            "scenario_seed"
        ]
    )

    step_count = 0

    while True:

        mask = (
            env.action_masks()
        )

        valid_actions = (
            np.flatnonzero(
                mask
            )
        )

        if len(
            valid_actions
        ) == 0:

            raise RuntimeError(
                "No valid actions."
            )

        # ----------------------------------------------
        # 測試階段：
        # 隨便選第一個合法 Action
        # ----------------------------------------------

        action = int(
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
        ) = env.step(
            action
        )

        step_count += 1

        if (
            terminated
            or truncated
        ):
            break

    return {

        "scenario_seed":
            scenario_seed,

        "steps":
            step_count,

        "completed_tasks":
            info[
                "completed_tasks"
            ],

        "simulation_end_time":
            info[
                "simulation_end_time"
            ],

        "total_reward":
            info[
                "total_reward"
            ],
    }


def main():

    env = (
        RandomizedHospitalGymEnv()
    )

    print("=" * 100)
    print("RANDOMIZED TRAINING ENV TEST")
    print("=" * 100)

    seen_seeds = []

    # ======================================================
    # 跑 5 個 Episode
    #
    # 每次 reset() 應該可以換 Scenario。
    # ======================================================

    for episode in range(
        1,
        6,
    ):

        result = (
            run_episode(
                env
            )
        )

        seen_seeds.append(
            result[
                "scenario_seed"
            ]
        )

        print(
            f"Episode {episode}"
            f" | seed="
            f"{result['scenario_seed']}"
            f" | steps="
            f"{result['steps']}"
            f" | completed="
            f"{result['completed_tasks']}"
            f" | end="
            f"{result['simulation_end_time']:.2f}"
            f" | reward="
            f"{result['total_reward']:.3f}"
        )

    print()

    print(
        "Seeds:",
        seen_seeds,
    )

    # ----------------------------------------------
    # Training Seeds 不可碰 Evaluation 0~29
    # ----------------------------------------------

    assert all(
        seed >= 1000

        for seed
        in seen_seeds
    )

    # ----------------------------------------------
    # 至少要有不只一種 Scenario
    # ----------------------------------------------

    assert (
        len(
            set(
                seen_seeds
            )
        )
        > 1
    )

    print()
    print(
        "Training seed range: PASS"
    )

    print(
        "Scenario randomization: PASS"
    )

    print(
        "TRAINING ENV TEST: PASS"
    )


if __name__ == "__main__":
    main()