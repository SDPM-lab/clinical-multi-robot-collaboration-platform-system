from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "reward_weight_confirmation_validation"
    / "confirmation_episode_runs.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "reward_weight_confirmation_validation"
    / "confirmation_statistics.csv"
)


TARGET_CONFIG = "sweep27"

COMPARISON_CONFIGS = [
    "sweep06",
    "sweep10",
    "sweep13",
    "sweep30",
]


METRICS = [
    (
        "average_waiting_time_s",
        "Avg Wait",
        "lower",
    ),
    (
        "p95_waiting_time_s",
        "P95 Wait",
        "lower",
    ),
    (
        "high_waiting_time_s",
        "High Wait",
        "lower",
    ),
    (
        "emergency_waiting_time_s",
        "Emergency Wait",
        "lower",
    ),
    (
        "total_travel_time_s",
        "Travel",
        "lower",
    ),
    (
        "jain_task_fairness",
        "Jain",
        "higher",
    ),
]


def mean(values):
    return float(
        np.mean(
            np.asarray(
                values,
                dtype=np.float64,
            )
        )
    )


def scenario_level_values(
    rows,
    config,
    metric,
):
    grouped = {}

    for row in rows:

        if (
            row["config"]
            != config
        ):
            continue

        seed = int(
            row["seed"]
        )

        grouped.setdefault(
            seed,
            [],
        ).append(
            float(
                row[
                    metric
                ]
            )
        )

    return {
        seed: mean(values)
        for seed, values
        in grouped.items()
    }


def main():

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        rows = list(
            csv.DictReader(
                file
            )
        )

    output_rows = []

    print(
        "=" * 130
    )

    print(
        "REWARD WEIGHT CONFIRMATION STATISTICS"
    )

    print(
        "=" * 130
    )

    for comparison in (
        COMPARISON_CONFIGS
    ):

        print()
        print(
            f"{TARGET_CONFIG} vs {comparison}"
        )

        print(
            "-" * 130
        )

        for (
            metric,
            label,
            direction,
        ) in METRICS:

            target = (
                scenario_level_values(
                    rows,
                    TARGET_CONFIG,
                    metric,
                )
            )

            other = (
                scenario_level_values(
                    rows,
                    comparison,
                    metric,
                )
            )

            common_seeds = sorted(
                set(
                    target
                )
                & set(
                    other
                )
            )

            x = np.asarray(
                [
                    target[
                        seed
                    ]
                    for seed
                    in common_seeds
                ],
                dtype=np.float64,
            )

            y = np.asarray(
                [
                    other[
                        seed
                    ]
                    for seed
                    in common_seeds
                ],
                dtype=np.float64,
            )

            diff = (
                x - y
            )

            mean_x = float(
                np.mean(
                    x
                )
            )

            mean_y = float(
                np.mean(
                    y
                )
            )

            mean_diff = float(
                np.mean(
                    diff
                )
            )

            if (
                abs(
                    mean_y
                )
                > 1e-12
            ):

                pct_change = (
                    (
                        mean_x
                        - mean_y
                    )
                    / mean_y
                    * 100.0
                )

            else:

                pct_change = 0.0

            if (
                len(
                    diff
                )
                >= 2
            ):

                sem = (
                    stats.sem(
                        diff
                    )
                )

                ci = (
                    stats.t.interval(
                        0.95,
                        df=(
                            len(
                                diff
                            )
                            - 1
                        ),
                        loc=(
                            mean_diff
                        ),
                        scale=(
                            sem
                        ),
                    )
                )

                t_result = (
                    stats.ttest_rel(
                        x,
                        y,
                    )
                )

                try:

                    wilcoxon_result = (
                        stats.wilcoxon(
                            x,
                            y,
                        )
                    )

                    wilcoxon_p = float(
                        wilcoxon_result.pvalue
                    )

                except ValueError:

                    wilcoxon_p = 1.0

                diff_std = float(
                    np.std(
                        diff,
                        ddof=1,
                    )
                )

                dz = (
                    mean_diff
                    / diff_std
                    if (
                        diff_std
                        > 1e-12
                    )
                    else 0.0
                )

            else:

                ci = (
                    mean_diff,
                    mean_diff,
                )

                t_result = None

                wilcoxon_p = 1.0

                dz = 0.0

            t_p = (
                float(
                    t_result.pvalue
                )
                if (
                    t_result
                    is not None
                )
                else 1.0
            )

            print(
                f"{label:<18}"
                f"{TARGET_CONFIG}={mean_x:>10.3f}  "
                f"{comparison}={mean_y:>10.3f}  "
                f"Δ={mean_diff:>10.3f}  "
                f"Δ%={pct_change:>8.2f}%  "
                f"95%CI=[{ci[0]:.3f}, {ci[1]:.3f}]  "
                f"p={t_p:.4g}"
            )

            output_rows.append(
                {
                    "target":
                    TARGET_CONFIG,

                    "comparison":
                    comparison,

                    "metric":
                    metric,

                    "direction":
                    direction,

                    "scenario_seed_count":
                    len(
                        common_seeds
                    ),

                    "target_mean":
                    mean_x,

                    "comparison_mean":
                    mean_y,

                    "difference":
                    mean_diff,

                    "percent_change":
                    pct_change,

                    "ci95_lower":
                    float(
                        ci[
                            0
                        ]
                    ),

                    "ci95_upper":
                    float(
                        ci[
                            1
                        ]
                    ),

                    "paired_t_p":
                    t_p,

                    "wilcoxon_p":
                    wilcoxon_p,

                    "cohens_dz":
                    dz,
                }
            )

    with OUTPUT_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = (
            csv.DictWriter(
                file,
                fieldnames=list(
                    output_rows[
                        0
                    ].keys()
                ),
            )
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    print()
    print(
        "=" * 130
    )

    print(
        "Saved:",
        OUTPUT_PATH,
    )

    print(
        "=" * 130
    )


if __name__ == "__main__":
    main()
