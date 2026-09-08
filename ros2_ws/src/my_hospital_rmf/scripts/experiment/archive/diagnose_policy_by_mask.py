#!/usr/bin/env python3

import os
from collections import defaultdict

import numpy as np
import torch

from sb3_contrib import MaskablePPO

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from rl.hospital_gym_env import HospitalGymEnv


TASK_COUNT = 100
LOAD = "medium"
SEED = 5000


SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RL_DIR = os.path.join(
    os.path.dirname(SCRIPT_DIR),
    "rl",
)

MODEL_DIR = os.path.join(
    RL_DIR,
    "models",
)


MODEL_PATHS = {
    "OLD PPO 50K":
        os.path.join(
            MODEL_DIR,
            "maskable_ppo_hospital_33d_reward_v3_50k.zip",
        ),

    "MULTIDIST PPO 100K":
        os.path.join(
            MODEL_DIR,
            "maskable_ppo_hospital_33d_reward_v3_multidist_100k.zip",
        ),

    "BALANCED MULTIDIST PPO 100K":
        os.path.join(
            MODEL_DIR,
            "maskable_ppo_hospital_33d_reward_v3_balanced_multidist_100k.zip",
        ),
}


ACTION_LABELS = {
    0: "robot_1",
    1: "robot_2",
    2: "robot_3",
}


def create_env():

    scenario = generate_random_scenario(
        task_count=TASK_COUNT,
        seed=SEED,
        load=LOAD,
        battery_profile=BATTERY_PROFILE,
        capability_profile=CAPABILITY_PROFILE,
    )

    return HospitalGymEnv(
        scenario=scenario,
        robot_speed=ROBOT_SPEED,
        service_time=SERVICE_TIME,
    )


def get_action_probabilities(
    model,
    observation,
    mask,
):

    obs_tensor = torch.as_tensor(
        observation,
        dtype=torch.float32,
        device=model.device,
    ).reshape(1, -1)

    mask_array = np.asarray(
        mask,
        dtype=bool,
    ).reshape(1, -1)

    with torch.no_grad():

        distribution = (
            model.policy.get_distribution(
                obs_tensor,
                action_masks=mask_array,
            )
        )

        probabilities = (
            distribution
            .distribution
            .probs
            .detach()
            .cpu()
            .numpy()[0]
        )

    return probabilities


def mask_name(
    mask,
):

    key = tuple(
        int(value)
        for value in mask
    )

    names = {
        (1, 1, 0):
            "robot_1 vs robot_2",

        (0, 1, 1):
            "robot_2 vs robot_3",

        (1, 1, 1):
            "all three",

        (0, 1, 0):
            "robot_2 only",

        (1, 0, 0):
            "robot_1 only",

        (0, 0, 1):
            "robot_3 only",
    }

    return names.get(
        key,
        str(key),
    )


def main():

    models = {}

    for label, path in MODEL_PATHS.items():

        if not os.path.exists(path):

            raise FileNotFoundError(
                f"{label}: {path}"
            )

        models[label] = (
            MaskablePPO.load(
                path,
                device="cpu",
            )
        )

    stats = {
        label: defaultdict(list)
        for label in models
    }

    mask_counts = defaultdict(int)

    env = create_env()

    observation, info = env.reset()

    reference_model = (
        models[
            "OLD PPO 50K"
        ]
    )

    while True:

        mask = env.action_masks()

        mask_key = tuple(
            int(value)
            for value in mask
        )

        mask_counts[
            mask_key
        ] += 1

        for label, model in models.items():

            probabilities = (
                get_action_probabilities(
                    model,
                    observation,
                    mask,
                )
            )

            stats[
                label
            ][
                mask_key
            ].append(
                probabilities
            )

        action, _ = (
            reference_model.predict(
                observation,
                action_masks=mask,
                deterministic=True,
            )
        )

        observation, reward, terminated, truncated, info = (
            env.step(
                int(action)
            )
        )

        if terminated or truncated:
            break

    env.close()

    print("=" * 110)
    print("COMMON-STATE POLICY BY MASK DIAGNOSTIC")
    print("=" * 110)

    print(
        "Scenario:",
        f"{TASK_COUNT} tasks"
        f" / {LOAD}"
        f" / seed {SEED}",
    )

    print()

    print("MASK COUNTS")
    print("-" * 110)

    for mask_key, count in sorted(
        mask_counts.items()
    ):

        print(
            f"{mask_key}"
            f" | {mask_name(mask_key):<25}"
            f" | states={count}"
        )

    for label in models:

        print()
        print("=" * 110)
        print(label)
        print("=" * 110)

        for mask_key, probability_rows in (
            stats[label].items()
        ):

            matrix = np.asarray(
                probability_rows,
                dtype=float,
            )

            mean_probs = (
                matrix.mean(
                    axis=0
                )
            )

            argmax_actions = (
                np.argmax(
                    matrix,
                    axis=1,
                )
            )

            print()
            print(
                f"MASK {mask_key}"
                f" | {mask_name(mask_key)}"
                f" | n={len(matrix)}"
            )

            print("-" * 110)

            for action in range(3):

                argmax_count = int(
                    np.sum(
                        argmax_actions
                        ==
                        action
                    )
                )

                print(
                    f"{ACTION_LABELS[action]:<10}"
                    f" | mean_prob="
                    f"{mean_probs[action]:.4f}"
                    f" | argmax="
                    f"{argmax_count:>3}"
                    f" | "
                    f"{argmax_count / len(matrix) * 100.0:6.2f}%"
                )


if __name__ == "__main__":
    main()