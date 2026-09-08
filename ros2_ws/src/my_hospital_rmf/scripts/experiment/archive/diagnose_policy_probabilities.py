#!/usr/bin/env python3

import math
import os
from collections import Counter

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

OLD_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_50k.zip",
)

MULTIDIST_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_multidist_100k.zip",
)

BALANCED_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_balanced_multidist_100k.zip",
)


# ==========================================================
# Labels
# ==========================================================

ACTION_LABELS = {
    0: "robot_1",
    1: "robot_2",
    2: "robot_3",
}


def action_label(
    action,
):

    return ACTION_LABELS.get(
        action,
        f"action_{action}",
    )


# ==========================================================
# Create Environment
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
# Get Masked Policy Probabilities
#
# 直接從 MaskablePPO policy distribution
# 取得目前三個 action 的 probability。
#
# Invalid action 經 mask 後 probability 應為 0。
# ==========================================================

def get_action_probabilities(
    model,
    observation,
    action_mask,
):

    observation_tensor = (
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
            action_mask,
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

                observation_tensor,

                action_masks=(
                    mask_array
                ),
            )
        )

        categorical = (
            distribution.distribution
        )

        probabilities = (
            categorical.probs
            .detach()
            .cpu()
            .numpy()[0]
        )

    return probabilities


# ==========================================================
# Entropy
# ==========================================================

def calculate_entropy(
    probabilities,
):

    entropy = 0.0

    for probability in (
        probabilities
    ):

        probability = float(
            probability
        )

        if probability > 0.0:

            entropy -= (
                probability
                *
                math.log(
                    probability
                )
            )

    return entropy


# ==========================================================
# Initialize Model Stats
# ==========================================================

def create_model_stats():

    return {

        "probability_sums":
            np.zeros(
                3,
                dtype=float,
            ),

        "argmax_counts":
            Counter(),

        "entropy_sum":
            0.0,

        "decision_count":
            0,

        # ----------------------------------------------
        # All 3 robots valid
        # ----------------------------------------------

        "all_valid_probability_sums":
            np.zeros(
                3,
                dtype=float,
            ),

        "all_valid_argmax_counts":
            Counter(),

        "all_valid_entropy_sum":
            0.0,

        "all_valid_count":
            0,

        # ----------------------------------------------
        # Pairwise comparison
        # ----------------------------------------------

        "r1_r2_count":
            0,

        "r1_r2_r2_preferred":
            0,

        "r1_r2_margin_sum":
            0.0,

        "r2_r3_count":
            0,

        "r2_r3_r2_preferred":
            0,

        "r2_r3_margin_sum":
            0.0,
    }


# ==========================================================
# Update Stats
# ==========================================================

def update_stats(
    stats,
    probabilities,
    mask,
):

    stats[
        "decision_count"
    ] += 1

    stats[
        "probability_sums"
    ] += probabilities

    entropy = (
        calculate_entropy(
            probabilities
        )
    )

    stats[
        "entropy_sum"
    ] += entropy

    chosen_action = int(
        np.argmax(
            probabilities
        )
    )

    stats[
        "argmax_counts"
    ][
        chosen_action
    ] += 1

    valid_actions = [
        index
        for index, valid
        in enumerate(mask)
        if valid
    ]

    # ======================================================
    # All Three Valid
    # ======================================================

    if len(
        valid_actions
    ) == 3:

        stats[
            "all_valid_count"
        ] += 1

        stats[
            "all_valid_probability_sums"
        ] += probabilities

        stats[
            "all_valid_entropy_sum"
        ] += entropy

        stats[
            "all_valid_argmax_counts"
        ][
            chosen_action
        ] += 1

    # ======================================================
    # Robot 1 vs Robot 2
    # ======================================================

    if (
        bool(mask[0])
        and
        bool(mask[1])
    ):

        stats[
            "r1_r2_count"
        ] += 1

        margin = (
            float(
                probabilities[1]
            )
            -
            float(
                probabilities[0]
            )
        )

        stats[
            "r1_r2_margin_sum"
        ] += margin

        if (
            probabilities[1]
            >
            probabilities[0]
        ):

            stats[
                "r1_r2_r2_preferred"
            ] += 1

    # ======================================================
    # Robot 2 vs Robot 3
    # ======================================================

    if (
        bool(mask[1])
        and
        bool(mask[2])
    ):

        stats[
            "r2_r3_count"
        ] += 1

        margin = (
            float(
                probabilities[1]
            )
            -
            float(
                probabilities[2]
            )
        )

        stats[
            "r2_r3_margin_sum"
        ] += margin

        if (
            probabilities[1]
            >
            probabilities[2]
        ):

            stats[
                "r2_r3_r2_preferred"
            ] += 1


# ==========================================================
# Print Model Summary
# ==========================================================

def print_model_summary(
    label,
    stats,
):

    decision_count = (
        stats[
            "decision_count"
        ]
    )

    mean_probabilities = (
        stats[
            "probability_sums"
        ]
        /
        decision_count
    )

    mean_entropy = (
        stats[
            "entropy_sum"
        ]
        /
        decision_count
    )

    print()

    print("=" * 110)

    print(
        label
    )

    print("=" * 110)

    print(
        "Decision States:",
        decision_count,
    )

    print(
        "Mean Entropy:",
        f"{mean_entropy:.6f}",
    )

    print()

    print(
        "MEAN MASKED ACTION PROBABILITY"
    )

    print("-" * 110)

    for action in range(
        3
    ):

        probability = (
            mean_probabilities[
                action
            ]
        )

        print(
            f"{action_label(action):<10}"
            f" | "
            f"{probability:>8.4f}"
            f" | "
            f"{probability * 100.0:>7.2f}%"
        )

    print()

    print(
        "DETERMINISTIC ARGMAX DISTRIBUTION"
    )

    print("-" * 110)

    for action in range(
        3
    ):

        count = (
            stats[
                "argmax_counts"
            ][
                action
            ]
        )

        print(
            f"{action_label(action):<10}"
            f" | "
            f"{count:>3}"
            f" | "
            f"{count / decision_count * 100.0:>7.2f}%"
        )

    # ======================================================
    # All Three Valid
    # ======================================================

    all_valid_count = (
        stats[
            "all_valid_count"
        ]
    )

    print()

    print(
        "ALL THREE ROBOTS VALID"
    )

    print("-" * 110)

    print(
        "States:",
        all_valid_count,
    )

    if all_valid_count > 0:

        all_valid_probabilities = (
            stats[
                "all_valid_probability_sums"
            ]
            /
            all_valid_count
        )

        all_valid_entropy = (
            stats[
                "all_valid_entropy_sum"
            ]
            /
            all_valid_count
        )

        print(
            "Mean Entropy:",
            f"{all_valid_entropy:.6f}",
        )

        for action in range(
            3
        ):

            probability = (
                all_valid_probabilities[
                    action
                ]
            )

            argmax_count = (
                stats[
                    "all_valid_argmax_counts"
                ][
                    action
                ]
            )

            print(
                f"{action_label(action):<10}"
                f" | mean_prob="
                f"{probability:>7.4f}"
                f" | argmax="
                f"{argmax_count:>3}"
                f" | "
                f"{argmax_count / all_valid_count * 100.0:>6.2f}%"
            )

    # ======================================================
    # Pairwise Bias
    # ======================================================

    print()

    print(
        "PAIRWISE ROBOT_2 BIAS"
    )

    print("-" * 110)

    r1_r2_count = (
        stats[
            "r1_r2_count"
        ]
    )

    if r1_r2_count > 0:

        preferred = (
            stats[
                "r1_r2_r2_preferred"
            ]
        )

        margin = (
            stats[
                "r1_r2_margin_sum"
            ]
            /
            r1_r2_count
        )

        print(
            "robot_2 > robot_1"
            f" | "
            f"{preferred}/{r1_r2_count}"
            f" | "
            f"{preferred / r1_r2_count * 100.0:.2f}%"
            f" | mean(P2-P1)="
            f"{margin:.4f}"
        )

    r2_r3_count = (
        stats[
            "r2_r3_count"
        ]
    )

    if r2_r3_count > 0:

        preferred = (
            stats[
                "r2_r3_r2_preferred"
            ]
        )

        margin = (
            stats[
                "r2_r3_margin_sum"
            ]
            /
            r2_r3_count
        )

        print(
            "robot_2 > robot_3"
            f" | "
            f"{preferred}/{r2_r3_count}"
            f" | "
            f"{preferred / r2_r3_count * 100.0:.2f}%"
            f" | mean(P2-P3)="
            f"{margin:.4f}"
        )


# ==========================================================
# Main
# ==========================================================

def main():

    model_paths = {

        "OLD PPO 50K":
            OLD_MODEL_PATH,

        "MULTIDIST PPO 100K":
            MULTIDIST_MODEL_PATH,

        "BALANCED MULTIDIST PPO 100K":
            BALANCED_MODEL_PATH,
    }

    for (
        label,
        model_path,
    ) in model_paths.items():

        if not os.path.exists(
            model_path
        ):

            raise FileNotFoundError(
                f"{label}: {model_path}"
            )

    # ======================================================
    # Load Models
    # ======================================================

    models = {

        label:
            MaskablePPO.load(

                model_path,

                device="cpu",
            )

        for (
            label,
            model_path,
        )
        in model_paths.items()
    }

    stats = {

        label:
            create_model_stats()

        for label
        in models
    }

    # ======================================================
    # Common Reference Environment
    #
    # 使用 OLD PPO trajectory。
    #
    # 三個 model 都只「觀察」同一批 state。
    # 真正控制 reference env 的只有 OLD PPO。
    # ======================================================

    reference_env = (
        create_env()
    )

    observation, info = (
        reference_env.reset()
    )

    old_model = (
        models[
            "OLD PPO 50K"
        ]
    )

    step_index = 0

    print("=" * 110)

    print(
        "COMMON-STATE PPO ACTION PROBABILITY DIAGNOSTIC"
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

    print()

    while True:

        mask = (
            reference_env.action_masks()
        )

        # ==================================================
        # Evaluate ALL Models On Same State
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

                    action_mask=(
                        mask
                    ),
                )
            )

            update_stats(

                stats=(
                    stats[
                        label
                    ]
                ),

                probabilities=(
                    probabilities
                ),

                mask=(
                    mask
                ),
            )

        # ==================================================
        # Old PPO Controls Reference Trajectory
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
            reference_env.step(
                reference_action
            )
        )

        step_index += 1

        if (
            terminated
            or truncated
        ):

            break

    reference_env.close()

    # ======================================================
    # Results
    # ======================================================

    print(
        "Common states collected:",
        step_index,
    )

    for label in models:

        print_model_summary(

            label=(
                label
            ),

            stats=(
                stats[
                    label
                ]
            ),
        )


if __name__ == "__main__":
    main()