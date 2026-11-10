from __future__ import annotations

import csv
import statistics
from pathlib import Path

import experiments.fleet_sizing.rl.evaluate_battery_v2 as evaluator


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RESULTS_ROOT = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

OUTPUT_DIR = (
    RESULTS_ROOT
    / "reward_tuned_multiseed"
)

# Fresh evaluation scenarios
FRESH_SEEDS = list(
    range(
        9101,
        9131,
    )
)

# Force evaluator to use fresh seeds
evaluator.VALIDATION_SEEDS = (
    FRESH_SEEDS
)

MODELS = {
    7001:
    RESULTS_ROOT
    / "checkpoints"
    / "ppo_battery_v2_reward_tuned_200k"
    / "maskable_ppo_140000_steps.zip",

    7101:
    RESULTS_ROOT
    / "checkpoints"
    / "ppo_battery_v2_reward_tuned_seed7101_200k"
    / "maskable_ppo_140000_steps.zip",

    7102:
    RESULTS_ROOT
    / "checkpoints"
    / "ppo_battery_v2_reward_tuned_seed7102_200k"
    / "maskable_ppo_140000_steps.zip",

    7103:
    RESULTS_ROOT
    / "checkpoints"
    / "ppo_battery_v2_reward_tuned_seed7103_200k"
    / "maskable_ppo_140000_steps.zip",

    7104:
    RESULTS_ROOT
    / "checkpoints"
    / "ppo_battery_v2_reward_tuned_seed7104_200k"
    / "maskable_ppo_140000_steps.zip",
}


METRICS = [
    "completion_rate",
    "average_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
]


def mean(values):
    return float(
        statistics.mean(
            values
        )
    )


def stdev(values):
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


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    episode_rows = []
    model_rows = []

    print(
        "=" * 110
    )

    print(
        "REWARD-TUNED PPO MULTI-SEED ROBUSTNESS"
    )

    print(
        "=" * 110
    )

    print(
        "Checkpoint: 140k"
    )

    print(
        "Model seeds:",
        list(
            MODELS.keys()
        ),
    )

    print(
        "Fresh evaluation seeds:",
        "9101-9130",
    )

    print(
        "=" * 110
    )

    for (
        model_seed,
        model_path,
    ) in MODELS.items():

        if not model_path.exists():

            raise FileNotFoundError(
                model_path
            )

        model_name = (
            f"reward_tuned_140k_"
            f"seed{model_seed}"
        )

        print()
        print(
            "#" * 110
        )

        print(
            "Evaluating model seed:",
            model_seed,
        )

        print(
            "Model:",
            model_path,
        )

        rows = evaluator.evaluate_model(
            model_path=model_path,
            model_name=model_name,
        )

        for row in rows:

            episode_rows.append(
                {
                    "model_seed":
                    model_seed,

                    **row,
                }
            )

        summary = {
            "model_seed":
            model_seed,
        }

        for metric in METRICS:

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
            ] = mean(
                values
            )

            summary[
                f"{metric}_std"
            ] = stdev(
                values
            )

        model_rows.append(
            summary
        )

    # ========================================================
    # Aggregate across five PPO model seeds
    # Each model contributes one mean value.
    # ========================================================

    aggregate_row = {
        "model_seed_count":
        len(
            model_rows
        ),
    }

    for metric in METRICS:

        values = [
            float(
                row[
                    f"{metric}_mean"
                ]
            )
            for row
            in model_rows
        ]

        aggregate_row[
            f"{metric}_mean"
        ] = mean(
            values
        )

        aggregate_row[
            f"{metric}_between_model_seed_std"
        ] = stdev(
            values
        )

    episode_path = (
        OUTPUT_DIR
        / "multiseed_episode_runs.csv"
    )

    model_path = (
        OUTPUT_DIR
        / "multiseed_model_summary.csv"
    )

    aggregate_path = (
        OUTPUT_DIR
        / "multiseed_aggregate_summary.csv"
    )

    write_csv(
        episode_path,
        episode_rows,
    )

    write_csv(
        model_path,
        model_rows,
    )

    write_csv(
        aggregate_path,
        [
            aggregate_row
        ],
    )

    print()
    print(
        "=" * 130
    )

    print(
        "PER-MODEL SUMMARY"
    )

    print(
        "=" * 130
    )

    print(
        f"{'Seed':<8}"
        f"{'Wait':>11}"
        f"{'P95':>11}"
        f"{'High':>11}"
        f"{'Emer':>11}"
        f"{'Travel':>14}"
        f"{'Jain':>10}"
        f"{'Comp':>10}"
    )

    print(
        "-" * 130
    )

    for row in model_rows:

        print(
            f"{row['model_seed']:<8}"
            f"{row['average_waiting_time_s_mean']:>11.2f}"
            f"{row['p95_waiting_time_s_mean']:>11.2f}"
            f"{row['high_waiting_time_s_mean']:>11.2f}"
            f"{row['emergency_waiting_time_s_mean']:>11.2f}"
            f"{row['total_travel_time_s_mean']:>14.2f}"
            f"{row['jain_task_fairness_mean']:>10.3f}"
            f"{row['completion_rate_mean']:>10.4f}"
        )

    print(
        "=" * 130
    )

    print()
    print(
        "AGGREGATE ACROSS MODEL SEEDS"
    )

    print(
        "-" * 90
    )

    print(
        "Avg Wait:",
        f"{aggregate_row['average_waiting_time_s_mean']:.2f}",
        "±",
        f"{aggregate_row['average_waiting_time_s_between_model_seed_std']:.2f}",
    )

    print(
        "P95 Wait:",
        f"{aggregate_row['p95_waiting_time_s_mean']:.2f}",
        "±",
        f"{aggregate_row['p95_waiting_time_s_between_model_seed_std']:.2f}",
    )

    print(
        "High Wait:",
        f"{aggregate_row['high_waiting_time_s_mean']:.2f}",
        "±",
        f"{aggregate_row['high_waiting_time_s_between_model_seed_std']:.2f}",
    )

    print(
        "Emergency Wait:",
        f"{aggregate_row['emergency_waiting_time_s_mean']:.2f}",
        "±",
        f"{aggregate_row['emergency_waiting_time_s_between_model_seed_std']:.2f}",
    )

    print(
        "Travel:",
        f"{aggregate_row['total_travel_time_s_mean']:.2f}",
        "±",
        f"{aggregate_row['total_travel_time_s_between_model_seed_std']:.2f}",
    )

    print(
        "Jain:",
        f"{aggregate_row['jain_task_fairness_mean']:.4f}",
        "±",
        f"{aggregate_row['jain_task_fairness_between_model_seed_std']:.4f}",
    )

    print(
        "Completion:",
        f"{aggregate_row['completion_rate_mean']:.4f}",
        "±",
        f"{aggregate_row['completion_rate_between_model_seed_std']:.4f}",
    )

    print()
    print(
        "Episode-level:",
        episode_path,
    )

    print(
        "Per-model:",
        model_path,
    )

    print(
        "Aggregate:",
        aggregate_path,
    )


if __name__ == "__main__":
    main()
