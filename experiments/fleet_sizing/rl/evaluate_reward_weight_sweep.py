from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.fleet_sizing.rl.evaluate_battery_v2 import (
    aggregate_model,
    evaluate_model,
    write_csv,
)


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

METADATA_DIR = (
    RL_RESULTS_DIR
    / "metadata"
)

OUTPUT_ROOT = (
    RL_RESULTS_DIR
    / "reward_weight_sweep_validation"
)


# ============================================================
# Helpers
# ============================================================

def timestep_tag(
    timesteps: int,
) -> str:

    if (
        timesteps
        % 1000
        == 0
    ):
        return (
            f"{timesteps // 1000}k"
        )

    return str(
        timesteps
    )


def get_sweep_index(
    run_name: str,
) -> int:

    # reward_sweep_01_...
    parts = (
        run_name
        .split("_")
    )

    try:
        return int(
            parts[2]
        )

    except (
        IndexError,
        ValueError,
    ):
        return 999999


def discover_models(
    *,
    timesteps: int,
) -> list[
    tuple[
        str,
        Path,
        Path,
    ]
]:

    tag = (
        timestep_tag(
            timesteps
        )
    )

    discovered = []

    pattern = (
        f"reward_sweep_*_{tag}"
    )

    for run_dir in (
        MODEL_DIR.glob(
            pattern
        )
    ):

        if not (
            run_dir.is_dir()
        ):
            continue

        model_path = (
            run_dir
            / "final_model.zip"
        )

        metadata_path = (
            METADATA_DIR
            / f"{run_dir.name}.json"
        )

        if not (
            model_path.exists()
        ):
            continue

        if not (
            metadata_path.exists()
        ):
            raise FileNotFoundError(
                "Metadata missing for "
                f"{run_dir.name}: "
                f"{metadata_path}"
            )

        discovered.append(
            (
                run_dir.name,
                model_path,
                metadata_path,
            )
        )

    discovered.sort(
        key=lambda item:
        get_sweep_index(
            item[0]
        )
    )

    return discovered


def load_metadata(
    path: Path,
) -> dict:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(
            file
        )


# ============================================================
# Main
# ============================================================

def main():

    parser = (
        argparse.ArgumentParser(
            description=(
                "Evaluate all Reward Weight "
                "Sweep PPO models on fixed "
                "Battery V2 validation seeds."
            )
        )
    )

    parser.add_argument(
        "--timesteps",
        type=int,
        default=50_000,
        help=(
            "Training timesteps of sweep "
            "models to evaluate."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional number of models "
            "to evaluate."
        ),
    )

    args = (
        parser.parse_args()
    )

    models = (
        discover_models(
            timesteps=(
                args.timesteps
            )
        )
    )

    if not models:

        raise FileNotFoundError(
            "No Reward Sweep models found "
            f"for {args.timesteps} timesteps."
        )

    if (
        args.limit
        is not None
    ):

        models = models[
            :args.limit
        ]

    print(
        "=" * 90
    )

    print(
        "REWARD WEIGHT SWEEP VALIDATION"
    )

    print(
        "=" * 90
    )

    print(
        "Models found:",
        len(
            models
        ),
    )

    print(
        "Training timesteps:",
        args.timesteps,
    )

    print(
        "Validation seeds:",
        "8101-8120",
    )

    print(
        "=" * 90
    )

    all_runs = []

    summaries = []

    for (
        run_name,
        model_path,
        metadata_path,
    ) in models:

        metadata = (
            load_metadata(
                metadata_path
            )
        )

        reward_config = (
            metadata[
                "reward_config"
            ]
        )

        sweep_index = (
            get_sweep_index(
                run_name
            )
        )

        config_info = {
            "sweep_index":
            sweep_index,

            "run_name":
            run_name,

            "waiting_weight":
            reward_config[
                "waiting_weight"
            ],

            "approach_weight":
            reward_config[
                "approach_weight"
            ],

            "queue_weight":
            reward_config[
                "queue_weight"
            ],

            "imbalance_weight":
            reward_config[
                "imbalance_weight"
            ],

            "model_seed":
            metadata[
                "model_seed"
            ],

            "training_timesteps":
            metadata[
                "total_timesteps"
            ],
        }

        print()
        print(
            "#" * 90
        )

        print(
            f"SWEEP {sweep_index:02d}"
        )

        print(
            (
                "Weights: "
                f"W={config_info['waiting_weight']:.2f}, "
                f"A={config_info['approach_weight']:.2f}, "
                f"Q={config_info['queue_weight']:.2f}, "
                f"I={config_info['imbalance_weight']:.2f}"
            )
        )

        rows = (
            evaluate_model(
                model_path=(
                    model_path
                ),
                model_name=(
                    f"sweep_{sweep_index:02d}"
                ),
            )
        )

        for row in rows:

            all_runs.append(
                {
                    **config_info,
                    **row,
                }
            )

        summary = (
            aggregate_model(
                (
                    f"sweep_"
                    f"{sweep_index:02d}"
                ),
                rows,
            )
        )

        summaries.append(
            {
                **config_info,
                **summary,
            }
        )

    output_dir = (
        OUTPUT_ROOT
        / timestep_tag(
            args.timesteps
        )
    )

    runs_path = (
        output_dir
        / "reward_sweep_validation_runs.csv"
    )

    summary_path = (
        output_dir
        / "reward_sweep_validation_summary.csv"
    )

    write_csv(
        runs_path,
        all_runs,
    )

    write_csv(
        summary_path,
        summaries,
    )

    print()
    print(
        "=" * 140
    )

    print(
        "REWARD WEIGHT SWEEP SUMMARY"
    )

    print(
        "=" * 140
    )

    print(
        f"{'ID':<6}"
        f"{'W':>6}"
        f"{'A':>6}"
        f"{'Q':>6}"
        f"{'I':>6}"
        f"{'Wait':>12}"
        f"{'P95':>12}"
        f"{'High':>12}"
        f"{'Emer':>12}"
        f"{'Travel':>14}"
        f"{'Jain':>10}"
        f"{'Comp':>10}"
    )

    print(
        "-" * 140
    )

    for summary in summaries:

        print(
            f"{summary['sweep_index']:<6}"

            f"{summary['waiting_weight']:>6.2f}"
            f"{summary['approach_weight']:>6.2f}"
            f"{summary['queue_weight']:>6.2f}"
            f"{summary['imbalance_weight']:>6.2f}"

            f"{summary['average_waiting_time_s_mean']:>12.2f}"

            f"{summary['p95_waiting_time_s_mean']:>12.2f}"

            f"{summary['high_waiting_time_s_mean']:>12.2f}"

            f"{summary['emergency_waiting_time_s_mean']:>12.2f}"

            f"{summary['total_travel_time_s_mean']:>14.2f}"

            f"{summary['jain_task_fairness_mean']:>10.3f}"

            f"{summary['completion_rate_mean']:>10.4f}"
        )

    print(
        "=" * 140
    )

    print(
        "Seed-level CSV:",
        runs_path,
    )

    print(
        "Summary CSV:",
        summary_path,
    )


if __name__ == "__main__":
    main()
