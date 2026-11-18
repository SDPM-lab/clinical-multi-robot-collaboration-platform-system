from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from experiments.fleet_sizing.rl.evaluate_battery_v2 import (
    evaluate_model,
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

OUTPUT_DIR = (
    RL_RESULTS_DIR
    / "pareto_reward_confirmation_nav2_validation"
)


# ============================================================
# Formal Nav2 Validation Seeds
# ============================================================

VALIDATION_SEEDS = tuple(
    range(
        9501,
        9531,
    )
)


# ============================================================
# Helpers
# ============================================================

def safe_mean(values):

    if not values:
        return 0.0

    return float(
        statistics.mean(
            values
        )
    )


def safe_std(values):

    if len(values) < 2:
        return 0.0

    return float(
        statistics.stdev(
            values
        )
    )


def write_csv(
    path: Path,
    rows: list[dict],
):

    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


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


def parse_config_name(
    run_name: str,
) -> str:

    # reward_confirm_nav2_sweep06_...
    parts = (
        run_name.split("_")
    )

    if (
        len(parts) < 4
        or parts[0] != "reward"
        or parts[1] != "confirm"
        or parts[2] != "nav2"
    ):
        raise ValueError(
            f"Unexpected Nav2 run name: {run_name}"
        )

    return parts[3]


# ============================================================
# Main
# ============================================================

def main():

    pareto_new_sweeps = {
        "sweep03",
        "sweep04",
        "sweep06",
        "sweep12",
        "sweep21",
        "sweep25",
        "sweep27",
    }

    run_dirs = sorted(
        path
        for path in MODEL_DIR.glob(
            "reward_confirm_nav2_*_200k"
        )
        if parse_config_name(path.name)
        in pareto_new_sweeps
    )

    if len(run_dirs) != 35:
        raise RuntimeError(
            f"Expected 35 Nav2 model directories, "
            f"found {len(run_dirs)}"
        )

    if not run_dirs:

        raise FileNotFoundError(
            "No confirmation models found."
        )

    print(
        "=" * 100
    )

    print(
        "NAV2 REWARD WEIGHT CONFIRMATION VALIDATION"
    )

    print(
        "=" * 100
    )

    print(
        "Models found:",
        len(
            run_dirs
        ),
    )

    print(
        "Validation seeds:",
        f"{VALIDATION_SEEDS[0]}-{VALIDATION_SEEDS[-1]}",
    )

    print(
        "=" * 100
    )

    all_episode_rows = []

    per_model_summary = []

    grouped_model_summaries = defaultdict(
        list
    )

    for run_dir in run_dirs:

        model_path = (
            run_dir
            / "final_model.zip"
        )

        metadata_path = (
            METADATA_DIR
            / f"{run_dir.name}.json"
        )

        if not model_path.exists():
            continue

        if not metadata_path.exists():

            raise FileNotFoundError(
                f"Missing metadata: "
                f"{metadata_path}"
            )

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

        config_name = (
            parse_config_name(
                run_dir.name
            )
        )

        model_seed = int(
            metadata[
                "model_seed"
            ]
        )

        model_name = (
            f"{config_name}_"
            f"seed{model_seed}"
        )

        print()
        print(
            "#" * 100
        )

        print(
            "Config:",
            config_name,
        )

        print(
            "Model seed:",
            model_seed,
        )

        print(
            (
                "Weights: "
                f"W={reward_config['waiting_weight']:.2f}, "
                f"A={reward_config['approach_weight']:.2f}, "
                f"Q={reward_config['queue_weight']:.2f}, "
                f"I={reward_config['imbalance_weight']:.2f}"
            )
        )

        rows = (
            evaluate_model(
                model_path=(
                    model_path
                ),
                model_name=(
                    model_name
                ),

                validation_seeds=(
                    VALIDATION_SEEDS
                ),
            )
        )

        for row in rows:

            all_episode_rows.append(
                {
                    "config":
                    config_name,

                    "model_seed":
                    model_seed,

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

                    **row,
                }
            )

        metrics = {
            "average_waiting_time_s":
            safe_mean(
                [
                    float(
                        row[
                            "average_waiting_time_s"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "p95_waiting_time_s":
            safe_mean(
                [
                    float(
                        row[
                            "p95_waiting_time_s"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "high_waiting_time_s":
            safe_mean(
                [
                    float(
                        row[
                            "high_waiting_time_s"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "emergency_waiting_time_s":
            safe_mean(
                [
                    float(
                        row[
                            "emergency_waiting_time_s"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "total_travel_time_s":
            safe_mean(
                [
                    float(
                        row[
                            "total_travel_time_s"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "jain_task_fairness":
            safe_mean(
                [
                    float(
                        row[
                            "jain_task_fairness"
                        ]
                    )
                    for row
                    in rows
                ]
            ),

            "completion_rate":
            safe_mean(
                [
                    float(
                        row[
                            "completion_rate"
                        ]
                    )
                    for row
                    in rows
                ]
            ),
        }

        model_summary = {
            "config":
            config_name,

            "model_seed":
            model_seed,

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

            **metrics,
        }

        per_model_summary.append(
            model_summary
        )

        grouped_model_summaries[
            config_name
        ].append(
            model_summary
        )

    # ========================================================
    # Aggregate across PPO model seeds
    # ========================================================

    config_summary_rows = []

    metric_names = [
        "average_waiting_time_s",
        "p95_waiting_time_s",
        "high_waiting_time_s",
        "emergency_waiting_time_s",
        "total_travel_time_s",
        "jain_task_fairness",
        "completion_rate",
    ]

    for (
        config_name,
        rows,
    ) in sorted(
        grouped_model_summaries.items()
    ):

        first = rows[0]

        summary = {
            "config":
            config_name,

            "model_seed_count":
            len(
                rows
            ),

            "waiting_weight":
            first[
                "waiting_weight"
            ],

            "approach_weight":
            first[
                "approach_weight"
            ],

            "queue_weight":
            first[
                "queue_weight"
            ],

            "imbalance_weight":
            first[
                "imbalance_weight"
            ],
        }

        for metric in metric_names:

            values = [
                float(
                    row[
                        metric
                    ]
                )
                for row
                in rows
            ]

            summary[
                f"{metric}_mean"
            ] = safe_mean(
                values
            )

            summary[
                f"{metric}_std"
            ] = safe_std(
                values
            )

        config_summary_rows.append(
            summary
        )

    # ========================================================
    # Output
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    episode_path = (
        OUTPUT_DIR
        / "confirmation_episode_runs.csv"
    )

    model_path = (
        OUTPUT_DIR
        / "confirmation_model_summary.csv"
    )

    config_path = (
        OUTPUT_DIR
        / "confirmation_config_summary.csv"
    )

    write_csv(
        episode_path,
        all_episode_rows,
    )

    write_csv(
        model_path,
        per_model_summary,
    )

    write_csv(
        config_path,
        config_summary_rows,
    )

    print()
    print(
        "=" * 150
    )

    print(
        "CONFIRMATION CONFIG SUMMARY"
    )

    print(
        "=" * 150
    )

    print(
        f"{'Config':<10}"
        f"{'W':>6}"
        f"{'A':>6}"
        f"{'Q':>6}"
        f"{'I':>6}"
        f"{'Wait':>11}"
        f"{'±SD':>9}"
        f"{'P95':>11}"
        f"{'High':>11}"
        f"{'Emer':>11}"
        f"{'Travel':>14}"
        f"{'Jain':>9}"
        f"{'Comp':>9}"
    )

    print(
        "-" * 150
    )

    for row in (
        config_summary_rows
    ):

        print(
            f"{row['config']:<10}"

            f"{row['waiting_weight']:>6.2f}"
            f"{row['approach_weight']:>6.2f}"
            f"{row['queue_weight']:>6.2f}"
            f"{row['imbalance_weight']:>6.2f}"

            f"{row['average_waiting_time_s_mean']:>11.2f}"

            f"{row['average_waiting_time_s_std']:>9.2f}"

            f"{row['p95_waiting_time_s_mean']:>11.2f}"

            f"{row['high_waiting_time_s_mean']:>11.2f}"

            f"{row['emergency_waiting_time_s_mean']:>11.2f}"

            f"{row['total_travel_time_s_mean']:>14.2f}"

            f"{row['jain_task_fairness_mean']:>9.3f}"

            f"{row['completion_rate_mean']:>9.4f}"
        )

    print(
        "=" * 150
    )

    print(
        "Episode-level:",
        episode_path,
    )

    print(
        "Per-model:",
        model_path,
    )

    print(
        "Per-config:",
        config_path,
    )


if __name__ == "__main__":
    main()
