from __future__ import annotations

import argparse
import subprocess
import sys
from itertools import product
from pathlib import Path


# ============================================================
# Search Space
# ============================================================

WAITING_VALUES = [
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
]

APPROACH_VALUES = [
    0.20,
    0.25,
    0.30,
    0.35,
]

QUEUE_VALUES = [
    0.10,
    0.15,
    0.20,
    0.25,
]

IMBALANCE_VALUES = [
    0.05,
    0.10,
    0.15,
]


DEFAULT_TIMESTEPS = 50_000
DEFAULT_MODEL_SEED = 7001


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
# Weight Generation
# ============================================================

def generate_weight_combinations():

    combinations = []

    for (
        waiting,
        approach,
        queue,
        imbalance,
    ) in product(
        WAITING_VALUES,
        APPROACH_VALUES,
        QUEUE_VALUES,
        IMBALANCE_VALUES,
    ):

        total = (
            waiting
            + approach
            + queue
            + imbalance
        )

        if abs(
            total - 1.0
        ) > 1e-9:
            continue

        if not (
            waiting
            >= approach
            >= queue
            >= imbalance
        ):
            continue

        combinations.append(
            {
                "waiting": waiting,
                "approach": approach,
                "queue": queue,
                "imbalance": imbalance,
            }
        )

    return combinations


# ============================================================
# Naming
# ============================================================

def weight_tag(
    value: float,
) -> str:

    return (
        f"{int(round(value * 100)):02d}"
    )


def build_run_name(
    index: int,
    weights: dict,
    timesteps: int,
) -> str:

    return (
        f"reward_sweep_"
        f"{index:02d}_"
        f"w{weight_tag(weights['waiting'])}_"
        f"a{weight_tag(weights['approach'])}_"
        f"q{weight_tag(weights['queue'])}_"
        f"i{weight_tag(weights['imbalance'])}_"
        f"{timesteps // 1000}k"
    )


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Run Reward Weight Sweep "
            "for Battery V2 PPO."
        )
    )

    parser.add_argument(
        "--timesteps",
        type=int,
        default=DEFAULT_TIMESTEPS,
    )

    parser.add_argument(
        "--model-seed",
        type=int,
        default=DEFAULT_MODEL_SEED,
    )

    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help=(
            "1-based first combination "
            "to run."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional maximum number "
            "of combinations to run."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print commands without "
            "training."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Retrain even if final model "
            "already exists."
        ),
    )

    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main():

    args = parse_args()

    combinations = (
        generate_weight_combinations()
    )

    print(
        "=" * 78
    )
    print(
        "REWARD WEIGHT SWEEP"
    )
    print(
        "=" * 78
    )
    print(
        "Total valid combinations:",
        len(combinations),
    )
    print(
        "Timesteps per combination:",
        args.timesteps,
    )
    print(
        "Model seed:",
        args.model_seed,
    )
    print()

    selected = []

    for index, weights in enumerate(
        combinations,
        start=1,
    ):

        if index < args.start_index:
            continue

        selected.append(
            (
                index,
                weights,
            )
        )

    if args.limit is not None:
        selected = selected[
            :args.limit
        ]

    for (
        index,
        weights,
    ) in selected:

        run_name = (
            build_run_name(
                index=index,
                weights=weights,
                timesteps=args.timesteps,
            )
        )

        final_model = (
            MODEL_DIR
            / run_name
            / "final_model.zip"
        )

        print(
            "-" * 78
        )

        print(
            f"[{index:02d}/"
            f"{len(combinations):02d}]"
        )

        print(
            "Run:",
            run_name,
        )

        print(
            "Weights:",
            (
                f"Waiting={weights['waiting']:.2f}, "
                f"Approach={weights['approach']:.2f}, "
                f"Queue={weights['queue']:.2f}, "
                f"Imbalance={weights['imbalance']:.2f}"
            ),
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
                args.model_seed
            ),

            "--timesteps",
            str(
                args.timesteps
            ),

            "--run-name",
            run_name,

            "--approach-weight",
            str(
                weights[
                    "approach"
                ]
            ),

            "--queue-weight",
            str(
                weights[
                    "queue"
                ]
            ),

            "--imbalance-weight",
            str(
                weights[
                    "imbalance"
                ]
            ),

            "--waiting-weight",
            str(
                weights[
                    "waiting"
                ]
            ),

            "--checkpoint-frequency",
            str(
                args.timesteps
            ),
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
        "=" * 78
    )

    if args.dry_run:
        print(
            "DRY RUN COMPLETE"
        )
    else:
        print(
            "REWARD SWEEP TRAINING COMPLETE"
        )

    print(
        "=" * 78
    )


if __name__ == "__main__":
    main()
