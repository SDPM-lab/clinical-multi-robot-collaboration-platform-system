#!/usr/bin/env python3

import os

from sb3_contrib import (
    MaskablePPO,
)

from rl.training_env import (
    RandomizedHospitalGymEnv,
)


# ==========================================================
# Paths
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

os.makedirs(
    MODEL_DIR,
    exist_ok=True,
)

os.makedirs(
    LOG_DIR,
    exist_ok=True,
)


# ==========================================================
# Warm-start Source
#
# 使用目前效果最好的 Old PPO 50K。
# ==========================================================

SOURCE_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_50k.zip",
)


# ==========================================================
# Output
# ==========================================================

OUTPUT_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_warmstart_balanced_ft50k",
)


# ==========================================================
# Fine-tuning
#
# Old PPO:
#   50K fixed-distribution training
#
# +
#
# Balanced MultiDist:
#   50K fine-tuning
#
# =
#
# 約 100K total learning experience
#
# 這樣也方便和 scratch MultiDist 100K 比較。
# ==========================================================

FINETUNE_TIMESTEPS = 50_000


def main():

    print("=" * 100)
    print("WARM-START BALANCED MULTIDIST TRAINING")
    print("=" * 100)

    print(
        "Source model :",
        SOURCE_MODEL_PATH,
    )

    print(
        "Output model :",
        OUTPUT_MODEL_PATH + ".zip",
    )

    print(
        "Fine-tune steps:",
        FINETUNE_TIMESTEPS,
    )

    if not os.path.exists(
        SOURCE_MODEL_PATH
    ):

        raise FileNotFoundError(
            SOURCE_MODEL_PATH
        )

    # ======================================================
    # Balanced MultiDist Environment
    #
    # training_env.py 現在已經使用：
    #
    # 20 tasks  -> 62.5%
    # 50 tasks  -> 25.0%
    # 100 tasks -> 12.5%
    #
    # loads:
    # low / medium / high
    #
    # Reward / Observation 都保持不變。
    # ======================================================

    env = (
        RandomizedHospitalGymEnv()
    )

    # ======================================================
    # Load Existing PPO
    #
    # 注意：
    # 不是建立新的 MaskablePPO。
    #
    # 這裡會保留 Old PPO 已經學好的：
    #
    # policy network
    # value network
    # optimizer state
    #
    # 然後換成 Balanced MultiDist environment。
    # ======================================================

    model = (
        MaskablePPO.load(

            SOURCE_MODEL_PATH,

            env=(
                env
            ),

            device="cpu",
        )
    )

    print()

    print(
        "Loaded model timesteps:",
        model.num_timesteps,
    )

    print()

    print("=" * 100)
    print("START FINE-TUNING")
    print("=" * 100)

    # ======================================================
    # reset_num_timesteps=False
    #
    # 非常重要。
    #
    # 不把 Old PPO 的 50K 歸零，
    # 而是在原模型基礎上繼續訓練。
    # ======================================================

    model.learn(

        total_timesteps=(
            FINETUNE_TIMESTEPS
        ),

        reset_num_timesteps=False,

        progress_bar=True,
    )

    model.save(
        OUTPUT_MODEL_PATH
    )

    env.close()

    print()

    print("=" * 100)
    print("FINE-TUNING COMPLETED")
    print("=" * 100)

    print(
        "Model saved:",
        OUTPUT_MODEL_PATH + ".zip",
    )

    print(
        "Final model timesteps:",
        model.num_timesteps,
    )


if __name__ == "__main__":
    main()