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

from rl_v2.long_horizon_training_env import (
    SeededLongHorizonHospitalRLEnv,
)


TRAIN_SEEDS = tuple(
    range(
        6000,
        7800,
    )
)


def main():

    parser = argparse.ArgumentParser()

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
            "long_horizon_ppo_smoke"
        ),
    )

    args = parser.parse_args()

    env = (
        SeededLongHorizonHospitalRLEnv(
            scenario_seeds=(
                TRAIN_SEEDS
            ),
            sampling_seed=(
                args.seed
            ),
            task_count=50,
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

    model = MaskablePPO(
        policy="MlpPolicy",
        env=env,

        learning_rate=3e-4,

        n_steps=1024,

        batch_size=64,

        n_epochs=10,

        # ----------------------------------------------
        # Long-horizon episodic objective:
        #
        # 不折扣未來實際 waiting cost。
        # ----------------------------------------------
        gamma=1.0,

        gae_lambda=0.95,

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
        "LONG-HORIZON MASKABLE PPO"
    )

    print(
        "========================================"
    )

    print(
        f"Training seeds : "
        f"{TRAIN_SEEDS[0]} "
        f"~ {TRAIN_SEEDS[-1]}"
    )

    print(
        f"Timesteps      : "
        f"{args.total_timesteps}"
    )

    print(
        f"PPO seed       : "
        f"{args.seed}"
    )

    print(
        "Reward         : "
        "actual system cost"
    )

    print(
        "Gamma          : 1.0"
    )

    print(
        "Action masking : enabled"
    )

    print(
        "========================================"
    )

    model.learn(
        total_timesteps=(
            args.total_timesteps
        ),
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


if __name__ == "__main__":

    main()
