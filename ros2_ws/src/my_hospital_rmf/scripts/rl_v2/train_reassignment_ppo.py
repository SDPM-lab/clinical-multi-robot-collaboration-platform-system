#!/usr/bin/env python3

import argparse

from pathlib import Path

from stable_baselines3.common.monitor import (
    Monitor,
)

from sb3_contrib import (
    MaskablePPO,
)

from sb3_contrib.common.maskable.utils import (
    is_masking_supported,
)

from rl_v2.reassignment_training_env import (
    SeededReassignmentHospitalRLEnv,
)

from rl_v2.system_reward import (
    SystemRewardConfig,
)

from rl_v2.reassignment_shaping import (
    ReassignmentShapingConfig,
)

TRAIN_SEEDS = tuple(
    range(
        6000,
        7800,
    )
)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Train Dedicated "
            "Reassignment Maskable PPO."
        )
    )

    parser.add_argument(
        "--assignment-model",
        type=str,
        default=(
            "rl_v2/models/"
            "long_horizon_ppo_102k_seed42.zip"
        ),
    )

    parser.add_argument(
        "--total-timesteps",
        type=int,
        default=10240,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    parser.add_argument(
        "--output",
        type=str,
        default=(
            "rl_v2/models/"
            "reassignment_ppo_smoke"
        ),
    )

    parser.add_argument(
        "--gae-lambda",
        type=float,
        default=0.95,
    )

    parser.add_argument(
        "--shaping-weight",
        type=float,
        default=0.0,
    )

    args = parser.parse_args()

    shaping_config = (
        None
        if args.shaping_weight <= 0.0
        else ReassignmentShapingConfig(
            shaping_weight=args.shaping_weight,
        )
    )

    # ======================================================
    # Frozen Assignment Policy
    # ======================================================

    assignment_policy = (
        MaskablePPO.load(
            args.assignment_model,
            device="cpu",
        )
    )

    # ======================================================
    # Dedicated Reassignment Env
    # ======================================================

    env = (
        SeededReassignmentHospitalRLEnv(
            assignment_policy=(
                assignment_policy
            ),
            scenario_seeds=(
                TRAIN_SEEDS
            ),
            sampling_seed=(
                args.seed
            ),
            task_count=50,

            # 原始 System Reward。
            # 目前不加入 explicit migration penalty。
            reward_config=(
                SystemRewardConfig(
                    reassignment_penalty=0.0,
                )
            ),

            shaping_config=shaping_config,
        )
    )

    env = Monitor(
        env
    )

    if not is_masking_supported(
        env
    ):

        raise RuntimeError(
            "Environment does not "
            "support action masking"
        )

    # ======================================================
    # Reassignment PPO
    # ======================================================

    model = MaskablePPO(
        policy="MlpPolicy",

        env=env,

        learning_rate=3e-4,

        n_steps=1024,

        batch_size=64,

        n_epochs=10,

        gamma=1.0,

        gae_lambda=args.gae_lambda,

        clip_range=0.2,

        ent_coef=0.0,

        vf_coef=0.5,

        max_grad_norm=0.5,

        verbose=1,

        seed=args.seed,

        device="cpu",
    )

    print()
    print(
        "========================================"
    )

    print(
        "DEDICATED REASSIGNMENT MASKABLE PPO"
    )

    print(
        "========================================"
    )

    print(
        f"Assignment model : "
        f"{args.assignment_model}"
    )

    print(
        f"Training seeds   : "
        f"{TRAIN_SEEDS[0]} "
        f"~ {TRAIN_SEEDS[-1]}"
    )

    print(
        f"Timesteps        : "
        f"{args.total_timesteps}"
    )

    print(
        f"PPO seed         : "
        f"{args.seed}"
    )

    print(
        f"Shaping weight   : "
        f"{args.shaping_weight}"
    )

    print(
        "Observation      : 54"
    )

    print(
        "Initial assign   : frozen Static PPO"
    )

    print(
        "RL decisions     : reassignment only"
    )

    print(
        "Reward           : "
        "actual system cost"
        + (
            " + projected-improvement shaping"
            if args.shaping_weight > 0.0
            else ""
        )
    )

    print(
        "Reassign penalty : 0.0"
    )

    print(
        "Gamma            : 1.0"
    )

    print(
        "Action masking   : enabled"
    )

    print(
        "========================================"
    )

    model.learn(
        total_timesteps=(
            args.total_timesteps
        )
    )

    output = Path(
        args.output
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    model.save(
        str(output)
    )

    print()
    print(
        "Training completed"
    )

    print(
        f"Model saved to: "
        f"{output}.zip"
    )

    print(
        f"GAE lambda       : "
        f"{args.gae_lambda}"
    )


if __name__ == "__main__":

    main()
