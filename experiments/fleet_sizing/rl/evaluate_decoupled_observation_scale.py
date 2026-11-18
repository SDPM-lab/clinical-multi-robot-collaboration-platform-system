from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean, stdev

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.evaluate_scale_sensitivity import (
    evaluate_one,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

OUTPUT_DIR = (
    RESULTS_DIR
    / "decoupled_observation_scale_eval"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


REWARD_SCALE = 600

OBSERVATION_SCALES = (
    150,
    600,
)

MODEL_SEEDS = (
    7101,
    7102,
    7103,
    7104,
    7105,
)

VALIDATION_SEEDS = tuple(
    range(
        9501,
        9531,
    )
)

METRICS = (
    "completion_rate",
    "avg_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel",
    "jain_fairness",
)


def main() -> None:

    episode_rows = []

    for observation_scale in OBSERVATION_SCALES:

        for model_seed in MODEL_SEEDS:

            run_name = (
                f"decoupled_r{REWARD_SCALE}"
                f"_o{observation_scale}"
                f"_seed{model_seed}_50k"
            )

            model_path = (
                RESULTS_DIR
                / "models"
                / run_name
                / "final_model.zip"
            )

            if not model_path.exists():
                raise FileNotFoundError(
                    model_path
                )

            print()
            print("=" * 80)
            print(
                f"REWARD SCALE={REWARD_SCALE} "
                f"OBS SCALE={observation_scale} "
                f"MODEL SEED={model_seed}"
            )
            print("=" * 80)

            model = MaskablePPO.load(
                str(
                    model_path
                ),
                device="cpu",
            )

            for eval_seed in VALIDATION_SEEDS:

                # IMPORTANT:
                # scale controls reward config in evaluate_one().
                # observation scale is supplied separately below.
                result = evaluate_one(
                    model=model,
                    scale=REWARD_SCALE,
                    seed=eval_seed,
                    observation_scale=(
                        observation_scale
                    ),
                )

                row = {
                    "reward_scale":
                    REWARD_SCALE,

                    "observation_scale":
                    observation_scale,

                    "model_seed":
                    model_seed,

                    "eval_seed":
                    eval_seed,
                }

                for metric in METRICS:
                    row[
                        metric
                    ] = result[
                        metric
                    ]

                episode_rows.append(
                    row
                )

                print(
                    f"eval={eval_seed} "
                    f"avg="
                    f"{result['avg_waiting_time_s']:.2f} "
                    f"p95="
                    f"{result['p95_waiting_time_s']:.2f} "
                    f"high="
                    f"{result['high_waiting_time_s']:.2f} "
                    f"emg="
                    f"{result['emergency_waiting_time_s']:.2f} "
                    f"jain="
                    f"{result['jain_fairness']:.4f}"
                )

    episode_path = (
        OUTPUT_DIR
        / "episode_results.csv"
    )

    with episode_path.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                episode_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            episode_rows
        )

    model_rows = []

    for observation_scale in OBSERVATION_SCALES:

        for model_seed in MODEL_SEEDS:

            rows = [
                row
                for row in episode_rows
                if (
                    row["observation_scale"]
                    == observation_scale
                    and
                    row["model_seed"]
                    == model_seed
                )
            ]

            summary = {
                "reward_scale":
                REWARD_SCALE,

                "observation_scale":
                observation_scale,

                "model_seed":
                model_seed,
            }

            for metric in METRICS:

                summary[
                    metric
                ] = mean(
                    float(
                        row[metric]
                    )
                    for row in rows
                )

            model_rows.append(
                summary
            )

    model_path = (
        OUTPUT_DIR
        / "model_seed_summary.csv"
    )

    with model_path.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                model_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            model_rows
        )

    aggregate_rows = []

    for observation_scale in OBSERVATION_SCALES:

        rows = [
            row
            for row in model_rows
            if (
                row["observation_scale"]
                == observation_scale
            )
        ]

        aggregate = {
            "reward_scale":
            REWARD_SCALE,

            "observation_scale":
            observation_scale,
        }

        for metric in METRICS:

            values = [
                float(
                    row[metric]
                )
                for row in rows
            ]

            aggregate[
                f"{metric}_mean"
            ] = mean(
                values
            )

            aggregate[
                f"{metric}_model_seed_std"
            ] = (
                stdev(
                    values
                )
                if len(values) > 1
                else 0.0
            )

        aggregate_rows.append(
            aggregate
        )

    aggregate_path = (
        OUTPUT_DIR
        / "aggregate_summary.csv"
    )

    with aggregate_path.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                aggregate_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            aggregate_rows
        )

    print()
    print("=" * 80)
    print("OBSERVATION SCALE EVALUATION COMPLETE")
    print("=" * 80)

    for row in aggregate_rows:

        print()
        print(
            f"R={row['reward_scale']} "
            f"O={row['observation_scale']}"
        )

        print(
            "Avg Wait:",
            f"{row['avg_waiting_time_s_mean']:.2f}",
            "+/-",
            f"{row['avg_waiting_time_s_model_seed_std']:.2f}",
        )

        print(
            "P95:",
            f"{row['p95_waiting_time_s_mean']:.2f}",
            "+/-",
            f"{row['p95_waiting_time_s_model_seed_std']:.2f}",
        )

        print(
            "High:",
            f"{row['high_waiting_time_s_mean']:.2f}",
            "+/-",
            f"{row['high_waiting_time_s_model_seed_std']:.2f}",
        )

        print(
            "Emergency:",
            f"{row['emergency_waiting_time_s_mean']:.2f}",
            "+/-",
            f"{row['emergency_waiting_time_s_model_seed_std']:.2f}",
        )

        print(
            "Travel:",
            f"{row['total_travel_mean']:.2f}",
            "+/-",
            f"{row['total_travel_model_seed_std']:.2f}",
        )

        print(
            "Jain:",
            f"{row['jain_fairness_mean']:.4f}",
            "+/-",
            f"{row['jain_fairness_model_seed_std']:.4f}",
        )

    print()
    print("Episode:", episode_path)
    print("Per-model:", model_path)
    print("Aggregate:", aggregate_path)


if __name__ == "__main__":
    main()
