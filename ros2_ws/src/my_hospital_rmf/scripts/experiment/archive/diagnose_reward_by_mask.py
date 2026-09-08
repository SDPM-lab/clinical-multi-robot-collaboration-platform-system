#!/usr/bin/env python3

import os
from collections import Counter, defaultdict

import numpy as np
import torch

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
# Diagnostic Scenario
# ==========================================================

TASK_COUNT = 100
LOAD = "medium"
SEED = 5000


# ==========================================================
# Paths
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RL_DIR = os.path.join(
    os.path.dirname(
        SCRIPT_DIR
    ),
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


# ==========================================================
# Create Fresh Environment
# ==========================================================

def create_env():

    scenario = (
        generate_random_scenario(

            task_count=(
                TASK_COUNT
            ),

            seed=(
                SEED
            ),

            load=(
                LOAD
            ),

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    return HospitalGymEnv(

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


# ==========================================================
# Replay Old-PPO Action History
# ==========================================================

def replay_to_state(
    action_history,
):

    env = (
        create_env()
    )

    observation, info = (
        env.reset()
    )

    for action in (
        action_history
    ):

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

        if terminated or truncated:

            raise RuntimeError(
                "Episode terminated during replay."
            )

    return (
        env,
        observation,
    )


# ==========================================================
# Immediate Reward Of Every Valid Action
# ==========================================================

def evaluate_valid_action_rewards(
    action_history,
):

    reference_env, observation = (
        replay_to_state(
            action_history
        )
    )

    mask = (
        reference_env.action_masks()
    )

    valid_actions = [
        index
        for index, valid
        in enumerate(mask)
        if valid
    ]

    reference_env.close()

    rewards = {}

    for action in (
        valid_actions
    ):

        candidate_env, _ = (
            replay_to_state(
                action_history
            )
        )

        (
            next_observation,
            reward,
            terminated,
            truncated,
            info,
        ) = (
            candidate_env.step(
                action
            )
        )

        rewards[
            action
        ] = float(
            reward
        )

        candidate_env.close()

    return (
        mask,
        rewards,
    )


# ==========================================================
# Policy Probabilities
# ==========================================================

def get_action_probabilities(
    model,
    observation,
    mask,
):

    obs_tensor = (
        torch.as_tensor(

            observation,

            dtype=torch.float32,

            device=(
                model.device
            ),
        )
        .reshape(
            1,
            -1,
        )
    )

    mask_array = (
        np.asarray(
            mask,
            dtype=bool,
        )
        .reshape(
            1,
            -1,
        )
    )

    with torch.no_grad():

        distribution = (
            model.policy.get_distribution(

                obs_tensor,

                action_masks=(
                    mask_array
                ),
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


# ==========================================================
# Mask Name
# ==========================================================

def mask_name(
    mask_key,
):

    names = {

        (1, 1, 0):
            "robot_1 vs robot_2",

        (0, 1, 1):
            "robot_2 vs robot_3",

        (1, 1, 1):
            "all three",
    }

    return names.get(
        mask_key,
        str(
            mask_key
        ),
    )


# ==========================================================
# Main
# ==========================================================

def main():

    # ======================================================
    # Load Models
    # ======================================================

    models = {}

    for (
        label,
        path,
    ) in MODEL_PATHS.items():

        if not os.path.exists(
            path
        ):

            raise FileNotFoundError(
                f"{label}: {path}"
            )

        models[
            label
        ] = (
            MaskablePPO.load(

                path,

                device="cpu",
            )
        )

    old_model = (
        models[
            "OLD PPO 50K"
        ]
    )

    # ======================================================
    # Statistics
    # ======================================================

    mask_counts = Counter()

    reward_best_counts = defaultdict(
        Counter
    )

    reward_sum_by_mask = defaultdict(
        Counter
    )

    model_argmax_counts = {

        label:
            defaultdict(
                Counter
            )

        for label
        in models
    }

    model_agreement_counts = {

        label:
            Counter()

        for label
        in models
    }

    model_regret_sums = {

        label:
            Counter()

        for label
        in models
    }

    # ======================================================
    # Reference Old-PPO Trajectory
    # ======================================================

    env = (
        create_env()
    )

    observation, info = (
        env.reset()
    )

    action_history = []

    while True:

        mask = (
            env.action_masks()
        )

        mask_key = tuple(
            int(value)
            for value in mask
        )

        mask_counts[
            mask_key
        ] += 1

        # ==================================================
        # Counterfactual Immediate Rewards
        # ==================================================

        (
            replay_mask,
            action_rewards,
        ) = (
            evaluate_valid_action_rewards(
                action_history
            )
        )

        replay_mask_key = tuple(
            int(value)
            for value
            in replay_mask
        )

        if (
            replay_mask_key
            !=
            mask_key
        ):

            raise RuntimeError(
                "Replay mask mismatch."
            )

        best_reward = max(
            action_rewards.values()
        )

        tolerance = 1e-9

        best_actions = [
            action

            for (
                action,
                reward,
            )
            in action_rewards.items()

            if abs(
                reward
                -
                best_reward
            )
            <= tolerance
        ]

        for (
            action,
            reward,
        ) in action_rewards.items():

            reward_sum_by_mask[
                mask_key
            ][
                action
            ] += (
                reward
            )

        for best_action in (
            best_actions
        ):

            reward_best_counts[
                mask_key
            ][
                best_action
            ] += (
                1.0
                /
                len(
                    best_actions
                )
            )

        # ==================================================
        # Evaluate All PPOs On Same State
        # ==================================================

        for (
            label,
            model,
        ) in models.items():

            probabilities = (
                get_action_probabilities(

                    model=(
                        model
                    ),

                    observation=(
                        observation
                    ),

                    mask=(
                        mask
                    ),
                )
            )

            chosen_action = int(
                np.argmax(
                    probabilities
                )
            )

            model_argmax_counts[
                label
            ][
                mask_key
            ][
                chosen_action
            ] += 1

            chosen_reward = (
                action_rewards[
                    chosen_action
                ]
            )

            regret = (
                best_reward
                -
                chosen_reward
            )

            model_regret_sums[
                label
            ][
                mask_key
            ] += (
                regret
            )

            if chosen_action in (
                best_actions
            ):

                model_agreement_counts[
                    label
                ][
                    mask_key
                ] += 1

        # ==================================================
        # Old PPO Advances Reference State
        # ==================================================

        (
            reference_action,
            _
        ) = (
            old_model.predict(

                observation,

                action_masks=(
                    mask
                ),

                deterministic=True,
            )
        )

        reference_action = int(
            reference_action
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = (
            env.step(
                reference_action
            )
        )

        action_history.append(
            reference_action
        )

        if terminated or truncated:

            break

    env.close()

    # ======================================================
    # Print Reward Results
    # ======================================================

    print("=" * 110)

    print(
        "COMMON-STATE REWARD-BY-MASK DIAGNOSTIC"
    )

    print("=" * 110)

    print(
        "Scenario:",
        f"{TASK_COUNT} tasks"
        f" / {LOAD}"
        f" / seed {SEED}",
    )

    print(
        "Reference trajectory:",
        "OLD PPO 50K",
    )

    for mask_key in sorted(
        mask_counts
    ):

        count = (
            mask_counts[
                mask_key
            ]
        )

        print()

        print("=" * 110)

        print(
            f"MASK {mask_key}"
            f" | "
            f"{mask_name(mask_key)}"
            f" | states={count}"
        )

        print("=" * 110)

        print()

        print(
            "IMMEDIATE REWARD-BEST DISTRIBUTION"
        )

        print("-" * 110)

        for action in range(
            3
        ):

            best_count = (
                reward_best_counts[
                    mask_key
                ][
                    action
                ]
            )

            if best_count == 0.0:

                continue

            print(
                f"{ACTION_LABELS[action]:<10}"
                f" | best="
                f"{best_count:>6.2f}"
                f" | "
                f"{best_count / count * 100.0:>6.2f}%"
            )

        print()

        print(
            "MEAN IMMEDIATE REWARD"
        )

        print("-" * 110)

        for action in range(
            3
        ):

            if (
                action
                not in
                reward_sum_by_mask[
                    mask_key
                ]
            ):

                continue

            mean_reward = (
                reward_sum_by_mask[
                    mask_key
                ][
                    action
                ]
                /
                count
            )

            print(
                f"{ACTION_LABELS[action]:<10}"
                f" | "
                f"{mean_reward:.6f}"
            )

        # ==================================================
        # Per-model Agreement
        # ==================================================

        print()

        print(
            "POLICY COMPARISON"
        )

        print("-" * 110)

        for label in models:

            agreement = (
                model_agreement_counts[
                    label
                ][
                    mask_key
                ]
            )

            average_regret = (
                model_regret_sums[
                    label
                ][
                    mask_key
                ]
                /
                count
            )

            print(
                f"{label:<32}"
                f" | agreement="
                f"{agreement:>3}/{count}"
                f" "
                f"({agreement / count * 100.0:6.2f}%)"
                f" | avg_regret="
                f"{average_regret:.6f}"
            )

            argmax_text = []

            for action in range(
                3
            ):

                argmax_count = (
                    model_argmax_counts[
                        label
                    ][
                        mask_key
                    ][
                        action
                    ]
                )

                if argmax_count > 0:

                    argmax_text.append(
                        f"{ACTION_LABELS[action]}"
                        f"="
                        f"{argmax_count}"
                    )

            print(
                " " * 35
                +
                "argmax: "
                +
                ", ".join(
                    argmax_text
                )
            )


if __name__ == "__main__":
    main()