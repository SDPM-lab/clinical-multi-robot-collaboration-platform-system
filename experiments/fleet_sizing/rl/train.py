from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import (
    CheckpointCallback,
)

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)


# ============================================================
# Frozen Experiment Configuration
# ============================================================

TRAINING_SEEDS = tuple(
    range(
        3001,
        3101,
    )
)

REFERENCE_FLEET = (
    2,  # Clean
    2,  # Medical
    3,  # Ward
)

WORKLOAD_MULTIPLIER = 4.0

DEFAULT_TOTAL_TIMESTEPS = 200_000

MODEL_SEED = 3001


# ============================================================
# PPO Initial Configuration
#
# These values are the initial formal-training configuration.
# They are NOT yet the final tuned hyperparameters.
# ============================================================

PPO_CONFIG = {
    "learning_rate": 3e-4,
    "n_steps": 512,
    "batch_size": 64,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "n_epochs": 10,
}


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RL_RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

MODEL_DIR = (
    RL_RESULTS_DIR
    / "models"
)

CHECKPOINT_DIR = (
    RL_RESULTS_DIR
    / "checkpoints"
)

METADATA_DIR = (
    RL_RESULTS_DIR
    / "metadata"
)


# ============================================================
# Environment
# ============================================================

def make_training_env(
) -> HospitalSchedulingEnv:

    return (
        HospitalSchedulingEnv(
            seed=(
                TRAINING_SEEDS[0]
            ),

            fleet_configuration=(
                REFERENCE_FLEET
            ),

            workload_multiplier=(
                WORKLOAD_MULTIPLIER
            ),

            episode_seeds=(
                TRAINING_SEEDS
            ),
        )
    )


# ============================================================
# Metadata
# ============================================================

def build_metadata(
    *,
    total_timesteps: int,
    model_path: Path,
) -> dict:

    return {
        "created_at":
        datetime.now()
        .astimezone()
        .isoformat(),

        "algorithm":
        "MaskablePPO",

        "policy":
        "MlpPolicy",

        "observation_size":
        84,

        "action_size":
        7,

        "training_seed_start":
        TRAINING_SEEDS[0],

        "training_seed_end":
        TRAINING_SEEDS[-1],

        "training_seed_count":
        len(
            TRAINING_SEEDS
        ),

        "fleet_configuration":
        list(
            REFERENCE_FLEET
        ),

        "workload_multiplier":
        WORKLOAD_MULTIPLIER,

        "model_seed":
        MODEL_SEED,

        "total_timesteps":
        int(
            total_timesteps
        ),

        "ppo_config":
        PPO_CONFIG,

        "model_path":
        str(
            model_path
        ),

        "notes": (
            "Initial formal MaskablePPO training configuration. "
            "Hyperparameters and reward configuration are not "
            "yet frozen as final tuned values."
        ),
    }


# ============================================================
# Training
# ============================================================

def train(
    *,
    total_timesteps: int,
    run_name: str,
    checkpoint_frequency: int,
) -> Path:

    if (
        total_timesteps
        <= 0
    ):
        raise ValueError(
            "total_timesteps must be > 0"
        )

    if (
        checkpoint_frequency
        <= 0
    ):
        raise ValueError(
            "checkpoint_frequency must be > 0"
        )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    METADATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_model_dir = (
        MODEL_DIR
        / run_name
    )

    run_checkpoint_dir = (
        CHECKPOINT_DIR
        / run_name
    )

    run_model_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_checkpoint_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    env = (
        make_training_env()
    )

    model = (
        MaskablePPO(
            policy="MlpPolicy",

            env=env,

            learning_rate=(
                PPO_CONFIG[
                    "learning_rate"
                ]
            ),

            n_steps=(
                PPO_CONFIG[
                    "n_steps"
                ]
            ),

            batch_size=(
                PPO_CONFIG[
                    "batch_size"
                ]
            ),

            gamma=(
                PPO_CONFIG[
                    "gamma"
                ]
            ),

            gae_lambda=(
                PPO_CONFIG[
                    "gae_lambda"
                ]
            ),

            clip_range=(
                PPO_CONFIG[
                    "clip_range"
                ]
            ),

            ent_coef=(
                PPO_CONFIG[
                    "ent_coef"
                ]
            ),

            vf_coef=(
                PPO_CONFIG[
                    "vf_coef"
                ]
            ),

            max_grad_norm=(
                PPO_CONFIG[
                    "max_grad_norm"
                ]
            ),

            n_epochs=(
                PPO_CONFIG[
                    "n_epochs"
                ]
            ),

            verbose=1,

            seed=(
                MODEL_SEED
            ),

            device="cpu",
        )
    )

    checkpoint_callback = (
        CheckpointCallback(
            save_freq=(
                checkpoint_frequency
            ),

            save_path=str(
                run_checkpoint_dir
            ),

            name_prefix=(
                "maskable_ppo"
            ),

            save_replay_buffer=False,

            save_vecnormalize=False,
        )
    )

    print(
        "=" * 70
    )

    print(
        "FORMAL MASKABLE PPO TRAINING"
    )

    print(
        "=" * 70
    )

    print(
        "Run name:",
        run_name,
    )

    print(
        "Training seeds:",
        f"{TRAINING_SEEDS[0]}"
        f"–{TRAINING_SEEDS[-1]}",
    )

    print(
        "Seed count:",
        len(
            TRAINING_SEEDS
        ),
    )

    print(
        "Fleet:",
        REFERENCE_FLEET,
    )

    print(
        "Workload multiplier:",
        WORKLOAD_MULTIPLIER,
    )

    print(
        "Observation:",
        84,
    )

    print(
        "Actions:",
        7,
    )

    print(
        "Total timesteps:",
        total_timesteps,
    )

    print(
        "Checkpoint every:",
        checkpoint_frequency,
    )

    print(
        "=" * 70
    )

    model.learn(
        total_timesteps=(
            total_timesteps
        ),

        callback=(
            checkpoint_callback
        ),

        reset_num_timesteps=True,
    )

    final_model_path = (
        run_model_dir
        / "final_model"
    )

    model.save(
        str(
            final_model_path
        )
    )

    metadata = (
        build_metadata(
            total_timesteps=(
                total_timesteps
            ),

            model_path=(
                final_model_path
            ),
        )
    )

    metadata_path = (
        METADATA_DIR
        / f"{run_name}.json"
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False,
        )

    env.close()

    print()
    print(
        "=" * 70
    )

    print(
        "TRAINING COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        "Model:",
        f"{final_model_path}.zip",
    )

    print(
        "Metadata:",
        metadata_path,
    )

    print(
        "Checkpoints:",
        run_checkpoint_dir,
    )

    return (
        final_model_path
    )


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = (
        argparse.ArgumentParser(
            description=(
                "Train the proposed "
                "MaskablePPO hospital "
                "robot scheduler."
            )
        )
    )

    parser.add_argument(
        "--timesteps",
        type=int,
        default=(
            DEFAULT_TOTAL_TIMESTEPS
        ),
        help=(
            "Total PPO training timesteps."
        ),
    )

    parser.add_argument(
        "--run-name",
        type=str,
        default=(
            "ppo_initial"
        ),
        help=(
            "Name used for model, "
            "checkpoint, and metadata "
            "directories."
        ),
    )

    parser.add_argument(
        "--checkpoint-frequency",
        type=int,
        default=(
            25_000
        ),
        help=(
            "Save a model checkpoint "
            "every N timesteps."
        ),
    )

    return (
        parser.parse_args()
    )


def main():

    args = (
        parse_args()
    )

    train(
        total_timesteps=(
            args.timesteps
        ),

        run_name=(
            args.run_name
        ),

        checkpoint_frequency=(
            args.checkpoint_frequency
        ),
    )


if __name__ == "__main__":
    main()