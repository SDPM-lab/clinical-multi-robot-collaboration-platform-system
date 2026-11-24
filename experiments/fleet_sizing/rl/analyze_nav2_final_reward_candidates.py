from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "pareto_reward_confirmation_nav2_validation"
    / "confirmation_episode_runs.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "nav2_final_reward_candidates"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CANDIDATE_A = "sweep25"
CANDIDATE_B = "sweep12"

MODEL_SEEDS = (
    7001,
    7101,
    7102,
    7103,
    7104,
)

METRICS = {
    "average_waiting_time_s": "lower",
    "p95_waiting_time_s": "lower",
    "high_waiting_time_s": "lower",
    "emergency_waiting_time_s": "lower",
    "total_travel_time_s": "lower",
    "jain_task_fairness": "higher",
}

BOOTSTRAPS = 10000
RNG_SEED = 20261116


def load_rows():

    with INPUT_PATH.open(
        newline="",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def main():

    rows = load_rows()

    # --------------------------------------------------------
    # Index:
    # (config, model_seed, eval_seed) -> row
    # --------------------------------------------------------

    index = {}

    for row in rows:

        config = row["config"]

        if config not in (
            CANDIDATE_A,
            CANDIDATE_B,
        ):
            continue

        model_seed = int(
            row["model_seed"]
        )

        # evaluate_battery_v2 stores the evaluation seed
        # under "seed".
        eval_seed = int(
            row["seed"]
        )

        index[
            (
                config,
                model_seed,
                eval_seed,
            )
        ] = row

    # --------------------------------------------------------
    # Find common validation seeds for every model pair
    # --------------------------------------------------------

    common_eval_seeds = None

    for model_seed in MODEL_SEEDS:

        seeds_a = {
            key[2]
            for key in index
            if (
                key[0] == CANDIDATE_A
                and key[1] == model_seed
            )
        }

        seeds_b = {
            key[2]
            for key in index
            if (
                key[0] == CANDIDATE_B
                and key[1] == model_seed
            )
        }

        common = (
            seeds_a
            & seeds_b
        )

        if common_eval_seeds is None:
            common_eval_seeds = common
        else:
            common_eval_seeds &= common

    common_eval_seeds = sorted(
        common_eval_seeds
    )

    if len(common_eval_seeds) != 30:
        raise RuntimeError(
            "Expected 30 common validation seeds, "
            f"found {len(common_eval_seeds)}"
        )

    print(
        "Common validation seeds:",
        len(common_eval_seeds),
        common_eval_seeds[0],
        common_eval_seeds[-1],
    )

    rng = np.random.default_rng(
        RNG_SEED
    )

    result_rows = []

    # --------------------------------------------------------
    # Hierarchical paired bootstrap
    #
    # Difference orientation:
    # positive = sweep25 better
    # --------------------------------------------------------

    for metric, direction in METRICS.items():

        per_seed_differences = []

        for model_seed in MODEL_SEEDS:

            differences = []

            for eval_seed in common_eval_seeds:

                a = float(
                    index[
                        (
                            CANDIDATE_A,
                            model_seed,
                            eval_seed,
                        )
                    ][metric]
                )

                b = float(
                    index[
                        (
                            CANDIDATE_B,
                            model_seed,
                            eval_seed,
                        )
                    ][metric]
                )

                if direction == "lower":
                    difference = b - a
                else:
                    difference = a - b

                differences.append(
                    difference
                )

            per_seed_differences.append(
                float(
                    np.mean(
                        differences
                    )
                )
            )

        observed = float(
            np.mean(
                per_seed_differences
            )
        )

        boot = np.empty(
            BOOTSTRAPS,
            dtype=float,
        )

        for b in range(
            BOOTSTRAPS
        ):

            sampled_model_indices = (
                rng.integers(
                    0,
                    len(MODEL_SEEDS),
                    size=len(
                        MODEL_SEEDS
                    ),
                )
            )

            model_means = []

            for model_index in (
                sampled_model_indices
            ):

                model_seed = (
                    MODEL_SEEDS[
                        model_index
                    ]
                )

                sampled_eval_indices = (
                    rng.integers(
                        0,
                        len(
                            common_eval_seeds
                        ),
                        size=len(
                            common_eval_seeds
                        ),
                    )
                )

                differences = []

                for eval_index in (
                    sampled_eval_indices
                ):

                    eval_seed = (
                        common_eval_seeds[
                            eval_index
                        ]
                    )

                    a = float(
                        index[
                            (
                                CANDIDATE_A,
                                model_seed,
                                eval_seed,
                            )
                        ][metric]
                    )

                    b_value = float(
                        index[
                            (
                                CANDIDATE_B,
                                model_seed,
                                eval_seed,
                            )
                        ][metric]
                    )

                    if direction == "lower":
                        diff = (
                            b_value - a
                        )
                    else:
                        diff = (
                            a - b_value
                        )

                    differences.append(
                        diff
                    )

                model_means.append(
                    np.mean(
                        differences
                    )
                )

            boot[b] = np.mean(
                model_means
            )

        ci_low = float(
            np.percentile(
                boot,
                2.5,
            )
        )

        ci_high = float(
            np.percentile(
                boot,
                97.5,
            )
        )

        seed_wins_a = sum(
            value > 0
            for value
            in per_seed_differences
        )

        seed_wins_b = sum(
            value < 0
            for value
            in per_seed_differences
        )

        if ci_low > 0:
            conclusion = (
                "sweep25_better"
            )
        elif ci_high < 0:
            conclusion = (
                "sweep12_better"
            )
        else:
            conclusion = (
                "ci_crosses_zero"
            )

        result_rows.append(
            {
                "metric":
                metric,

                "direction":
                direction,

                "difference_positive_means":
                "sweep25_better",

                "observed_difference":
                observed,

                "ci95_low":
                ci_low,

                "ci95_high":
                ci_high,

                "sweep25_model_seed_wins":
                seed_wins_a,

                "sweep12_model_seed_wins":
                seed_wins_b,

                "ties":
                (
                    len(
                        MODEL_SEEDS
                    )
                    - seed_wins_a
                    - seed_wins_b
                ),

                "conclusion":
                conclusion,
            }
        )

    output_path = (
        OUTPUT_DIR
        / "hierarchical_paired_bootstrap.csv"
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                result_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            result_rows
        )

    print()
    print("=" * 120)
    print(
        "NAV2 FINAL REWARD CANDIDATE COMPARISON"
    )
    print("=" * 120)

    for row in result_rows:

        print(
            f"{row['metric']:<28} "
            f"diff={row['observed_difference']:>10.4f} "
            f"CI=[{row['ci95_low']:>10.4f}, "
            f"{row['ci95_high']:>10.4f}] "
            f"seed wins "
            f"25={row['sweep25_model_seed_wins']} "
            f"12={row['sweep12_model_seed_wins']} "
            f"=> {row['conclusion']}"
        )

    print()
    print(
        "Output:",
        output_path,
    )


if __name__ == "__main__":
    main()
