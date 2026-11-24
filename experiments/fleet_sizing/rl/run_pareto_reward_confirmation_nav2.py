from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# ============================================================
# Confirmation Configurations
# ============================================================

REWARD_CONFIGS = [
    {
        "name": "sweep03",
        "waiting": 0.35,
        "approach": 0.30,
        "queue": 0.25,
        "imbalance": 0.10,
    },
    {
        "name": "sweep04",
        "waiting": 0.35,
        "approach": 0.35,
        "queue": 0.15,
        "imbalance": 0.15,
    },
    {
        "name": "sweep06",
        "waiting": 0.35,
        "approach": 0.35,
        "queue": 0.25,
        "imbalance": 0.05,
    },
    {
        "name": "sweep12",
        "waiting": 0.40,
        "approach": 0.35,
        "queue": 0.15,
        "imbalance": 0.10,
    },
    {
        "name": "sweep21",
        "waiting": 0.45,
        "approach": 0.35,
        "queue": 0.15,
        "imbalance": 0.05,
    },
    {
        "name": "sweep25",
        "waiting": 0.50,
        "approach": 0.25,
        "queue": 0.20,
        "imbalance": 0.05,
    },
    {
        "name": "sweep27",
        "waiting": 0.50,
        "approach": 0.30,
        "queue": 0.15,
        "imbalance": 0.05,
    },
]


MODEL_SEEDS = [
    7001,
    7101,
    7102,
    7103,
    7104,
]


DEFAULT_TIMESTEPS = 200_000


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

MODEL_DIR = (
    RESULTS_DIR
    / "models"
)


# ============================================================
# Helpers
# ============================================================

def weight_tag(
    value: float,
) -> str:

    return (
        f"{int(round(value * 100)):02d}"
    )


def build_run_name(
    config: dict,
    model_seed: int,
    timesteps: int,
) -> str:

    return (
        "reward_confirm_nav2_"
        f"{config['name']}_"
        f"w{weight_tag(config['waiting'])}_"
        f"a{weight_tag(config['approach'])}_"
        f"q{weight_tag(config['queue'])}_"
        f"i{weight_tag(config['imbalance'])}_"
        f"seed{model_seed}_"
        f"{timesteps // 1000}k"
    )


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Train selected Reward Weight "
            "configurations across multiple "
            "PPO model seeds."
        )
    )

    parser.add_argument(
        "--timesteps",
        type=int,
        default=DEFAULT_TIMESTEPS,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional maximum number "
            "of model runs."
        ),
    )

    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main():

    args = parse_args()

    jobs = []

    for config in REWARD_CONFIGS:

        for model_seed in MODEL_SEEDS:

            jobs.append(
                (
                    config,
                    model_seed,
                )
            )

    if args.limit is not None:
        jobs = jobs[
            :args.limit
        ]

    print(
        "=" * 90
    )

    print(
        "REWARD WEIGHT CONFIRMATION"
    )

    print(
        "=" * 90
    )

    print(
        "Reward configs:",
        len(
            REWARD_CONFIGS
        ),
    )

    print(
        "Model seeds:",
        MODEL_SEEDS,
    )

    print(
        "Total planned runs:",
        len(
            jobs
        ),
    )

    print(
        "Timesteps per run:",
        args.timesteps,
    )

    print(
        "=" * 90
    )

    for index, (
        config,
        model_seed,
    ) in enumerate(
        jobs,
        start=1,
    ):

        run_name = (
            build_run_name(
                config=config,
                model_seed=model_seed,
                timesteps=args.timesteps,
            )
        )

        final_model = (
            MODEL_DIR
            / run_name
            / "final_model.zip"
        )

        print()
        print(
            "-" * 90
        )

        print(
            f"[{index:02d}/"
            f"{len(jobs):02d}]"
        )

        print(
            "Run:",
            run_name,
        )

        print(
            (
                "Weights: "
                f"W={config['waiting']:.2f}, "
                f"A={config['approach']:.2f}, "
                f"Q={config['queue']:.2f}, "
                f"I={config['imbalance']:.2f}"
            )
        )

        print(
            "Model seed:",
            model_seed,
        )

        if (
            final_model.exists()
            and not args.force
        ):

            print(
                "SKIP: final model already exists."
            )

            continue

        command = [
            sys.executable,
            "-m",
            (
                "experiments.fleet_sizing.rl."
                "train_battery_v2"
            ),

            "--model-seed",
            str(
                model_seed
            ),

            "--timesteps",
            str(
                args.timesteps
            ),

            "--run-name",
            run_name,

            "--approach-weight",
            str(
                config[
                    "approach"
                ]
            ),

            "--queue-weight",
            str(
                config[
                    "queue"
                ]
            ),

            "--imbalance-weight",
            str(
                config[
                    "imbalance"
                ]
            ),

            "--waiting-weight",
            str(
                config[
                    "waiting"
                ]
            ),

            "--checkpoint-frequency",
            "25000",
        ]

        print(
            "Command:"
        )

        print(
            " ".join(
                command
            )
        )

        if args.dry_run:
            continue

        subprocess.run(
            command,
            check=True,
            cwd=str(
                PROJECT_ROOT
            ),
        )

    print()
    print(
        "=" * 90
    )

    if args.dry_run:
        print(
            "DRY RUN COMPLETE"
        )
    else:
        print(
            "CONFIRMATION TRAINING COMPLETE"
        )

    print(
        "=" * 90
    )


if __name__ == "__main__":
    main()
