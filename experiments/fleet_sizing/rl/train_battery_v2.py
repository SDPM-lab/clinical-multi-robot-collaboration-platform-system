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

from experiments.fleet_sizing.rl.reward import (
    DEFAULT_REWARD_CONFIG,
    RewardConfig,
)


# ============================================================
# Frozen Experiment Configuration
# ============================================================

TRAINING_SEEDS = tuple(
    range(
        7001,
        7101,
    )
)

REFERENCE_FLEET = (
    2,  # Clean
    2,  # Medical
    3,  # Ward
)

WORKLOAD_MULTIPLIER = 4.0

DEFAULT_TOTAL_TIMESTEPS = 200_000

MODEL_SEED = 7001

ENABLE_BATTERY_MODEL = True

OBSERVATION_SIZE = 98


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
    *,
    reward_config: RewardConfig,
    observation_approach_scale_s: float,
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

            enable_battery_model=(
                ENABLE_BATTERY_MODEL
            ),

            reward_config=(
                reward_config
            ),

            observation_approach_scale_s=(
                observation_approach_scale_s
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
    model_seed: int,
    reward_config: RewardConfig,
    observation_approach_scale_s: float,
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
        OBSERVATION_SIZE,

        "battery_model_enabled":
        ENABLE_BATTERY_MODEL,

        "experiment_version":
        "battery_v2",

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
        model_seed,

        "total_timesteps":
        int(
            total_timesteps
        ),

        "ppo_config":
        PPO_CONFIG,

        "observation_approach_scale_s":
        observation_approach_scale_s,

        "reward_config": {
            "approach_weight":
            reward_config.approach_weight,

            "queue_weight":
            reward_config.queue_weight,

            "imbalance_weight":
            reward_config.imbalance_weight,

            "waiting_weight":
            reward_config.waiting_weight,

            "approach_scale_s":
            reward_config.approach_scale_s,

            "waiting_scale_s":
            reward_config.waiting_scale_s,

            "tasks_ahead_scale":
            reward_config.tasks_ahead_scale,

            "low_priority_weight":
            reward_config.low_priority_weight,

            "normal_priority_weight":
            reward_config.normal_priority_weight,

            "high_priority_weight":
            reward_config.high_priority_weight,

            "emergency_priority_weight":
            reward_config.emergency_priority_weight,
        },

        "model_path":
        str(
            model_path
        ),

        "notes": (
            "Battery v2 formal MaskablePPO training. "
            "Battery-aware action masking, queue repair, "
            "charging lifecycle, and 98-dimensional "
            "battery-aware observation are enabled. "
            "PPO hyperparameters are retained from v1 "
            "for controlled comparison."
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
    model_seed: int,
    reward_config: RewardConfig,
    observation_approach_scale_s: float,
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
        make_training_env(
            reward_config=(
                reward_config
            ),

            observation_approach_scale_s=(
                observation_approach_scale_s
            ),
        )
    )

    if (
        env.observation_space.shape
        != (
            OBSERVATION_SIZE,
        )
    ):

        raise RuntimeError(
            "Unexpected Battery v2 "
            "observation shape: "
            f"{env.observation_space.shape}"
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
                model_seed
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
        "Battery model:",
        ENABLE_BATTERY_MODEL,
    )

    print(
        "Observation:",
        OBSERVATION_SIZE,
    )

    print(
        "Actions:",
        7,
    )

    print(
        "Reward weights:",
        {
            "approach":
            reward_config.approach_weight,

            "queue":
            reward_config.queue_weight,

            "imbalance":
            reward_config.imbalance_weight,

            "waiting":
            reward_config.waiting_weight,
        },
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

            model_seed=(
                model_seed
            ),

            reward_config=(
                reward_config
            ),

            observation_approach_scale_s=(
                observation_approach_scale_s
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
        "--model-seed",
        type=int,
        default=MODEL_SEED,
        help=(
            "Random seed used by the PPO model."
        ),
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
            "ppo_battery_v2_200k"
        ),
        help=(
            "Name used for model, "
            "checkpoint, and metadata "
            "directories."
        ),
    )

    parser.add_argument(
        "--approach-weight",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .approach_weight
        ),
        help=(
            "Reward weight for projected "
            "approach time."
        ),
    )

    parser.add_argument(
        "--queue-weight",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .queue_weight
        ),
        help=(
            "Reward weight for tasks ahead."
        ),
    )

    parser.add_argument(
        "--imbalance-weight",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .imbalance_weight
        ),
        help=(
            "Reward weight for load imbalance."
        ),
    )

    parser.add_argument(
        "--waiting-weight",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .waiting_weight
        ),
        help=(
            "Reward weight for realized waiting."
        ),
    )

    parser.add_argument(
        "--approach-scale-s",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .approach_scale_s
        ),
        help=(
            "Normalization scale in seconds "
            "for projected approach time."
        ),
    )

    parser.add_argument(
        "--observation-approach-scale-s",
        type=float,
        default=600.0,
        help=(
            "Normalization scale in seconds "
            "for projected approach time "
            "in the observation only."
        ),
    )

    parser.add_argument(
        "--waiting-scale-s",
        type=float,
        default=(
            DEFAULT_REWARD_CONFIG
            .waiting_scale_s
        ),
        help=(
            "Normalization scale in seconds "
            "for realized waiting time."
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

    reward_weights = [
        args.approach_weight,
        args.queue_weight,
        args.imbalance_weight,
        args.waiting_weight,
    ]

    if any(
        weight < 0.0
        for weight
        in reward_weights
    ):
        raise ValueError(
            "Reward weights must be non-negative."
        )

    reward_weight_sum = sum(
        reward_weights
    )

    if abs(
        reward_weight_sum
        - 1.0
    ) > 1e-9:
        raise ValueError(
            "Reward weights must sum to 1.0; "
            f"got {reward_weight_sum:.6f}"
        )

    if args.approach_scale_s <= 0.0:
        raise ValueError(
            "approach-scale-s must be > 0"
        )

    if (
        args.observation_approach_scale_s
        <= 0.0
    ):
        raise ValueError(
            "observation-approach-scale-s "
            "must be > 0"
        )

    if args.waiting_scale_s <= 0.0:
        raise ValueError(
            "waiting-scale-s must be > 0"
        )

    reward_config = RewardConfig(
        approach_weight=(
            args.approach_weight
        ),

        queue_weight=(
            args.queue_weight
        ),

        imbalance_weight=(
            args.imbalance_weight
        ),

        waiting_weight=(
            args.waiting_weight
        ),

        approach_scale_s=(
            args.approach_scale_s
        ),

        waiting_scale_s=(
            args.waiting_scale_s
        ),
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

        model_seed=(
            args.model_seed
        ),

        reward_config=(
            reward_config
        ),

        observation_approach_scale_s=(
            args.observation_approach_scale_s
        ),
    )


if __name__ == "__main__":
    main()