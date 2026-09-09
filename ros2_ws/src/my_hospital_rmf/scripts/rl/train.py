#!/usr/bin/env python3

import os

from sb3_contrib import (
    MaskablePPO,
)

from stable_baselines3.common.monitor import (
    Monitor,
)

from rl.training_env import (
    RandomizedHospitalGymEnv,
)

from rl.rl_config import (
    TOTAL_TIMESTEPS,
    PPO_SEED,
    TRAINING_SEEDS,
    TRAIN_TASK_COUNTS,
    TRAIN_LOADS,
)


# ==========================================================
# Path
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_DIR = os.path.join(
    SCRIPT_DIR,
    "models",
)

LOG_DIR = os.path.join(
    SCRIPT_DIR,
    "logs",
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_dynamic_v2_33d_reward_v3",
)


# ==========================================================
# Main
# ==========================================================

def main():

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )

    os.makedirs(
        LOG_DIR,
        exist_ok=True,
    )

    print("=" * 100)
    print("MASKABLE PPO TRAINING")
    print("=" * 100)

    print(
        "Total Timesteps:",
        TOTAL_TIMESTEPS,
    )

    print(
        "PPO Seed:",
        PPO_SEED,
    )

    print(
        "Training Seeds:",
        f"{TRAINING_SEEDS[0]}"
        f" ~ "
        f"{TRAINING_SEEDS[-1]}",
    )

    print(
        "Training Task Counts:",
        TRAIN_TASK_COUNTS,
    )

    print(
        "Training Loads:",
        TRAIN_LOADS,
    )

    print(
        "Model Output:",
        MODEL_PATH,
    )

    print()

    # ======================================================
    # Environment
    # ======================================================

    env = (
        RandomizedHospitalGymEnv(
            enable_dynamic_reassignment=True,
        )
    )

    env = Monitor(
        env
    )

    # ======================================================
    # Maskable PPO
    # ======================================================

    model = MaskablePPO(

        policy=(
            "MlpPolicy"
        ),

        env=env,

        learning_rate=(
            3e-4
        ),

        n_steps=(
            1024
        ),

        batch_size=(
            64
        ),

        n_epochs=(
            10
        ),

        gamma=(
            0.99
        ),

        gae_lambda=(
            0.95
        ),

        clip_range=(
            0.2
        ),

        ent_coef=(
            0.01
        ),

        verbose=(
            1
        ),

        seed=(
            PPO_SEED
        ),

        device=(
            "cpu"
        ),

        tensorboard_log=(
            LOG_DIR
        ),
    )

    # ======================================================
    # Train
    # ======================================================

    model.learn(
        total_timesteps=(
            TOTAL_TIMESTEPS
        ),

        progress_bar=True,
    )

    # ======================================================
    # Save
    # ======================================================

    model.save(
        MODEL_PATH
    )

    env.close()

    print()
    print("=" * 100)
    print("TRAINING COMPLETED")
    print("=" * 100)

    print(
        "Model saved:",
        MODEL_PATH + ".zip",
    )


if __name__ == "__main__":
    main()