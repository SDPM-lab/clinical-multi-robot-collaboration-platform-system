#!/usr/bin/env python3

import csv
import math
import os
import random
import statistics

from scipy.stats import (
    wilcoxon,
)


# ==========================================================
# Paths
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RESULTS_DIR = os.path.join(
    SCRIPT_DIR,
    "results",
)

RAW_CSV = os.path.join(
    RESULTS_DIR,
    "full_comparison_raw_results.csv",
)

OUTPUT_CSV = os.path.join(
    RESULTS_DIR,
    "full_comparison_statistical_analysis.csv",
)


# ==========================================================
# Methods
# ==========================================================

NEAREST_METHOD = (
    "Priority + Nearest"
)

RULE_METHOD = (
    "Priority + Rule-based"
)

PPO_METHOD = (
    "Priority + PPO 33D Reward v3 50K"
)


# ==========================================================
# Metrics
#
# lower_is_better:
#   數值越低越好
#
# higher_is_better:
#   數值越高越好
# ==========================================================

METRICS = {

    "average_waiting_time":
        "lower",

    "average_completion_time":
        "lower",

    "emergency_waiting_time":
        "lower",

    "high_waiting_time":
        "lower",

    "total_travel_distance":
        "lower",

    "makespan":
        "lower",

    "average_robot_utilization":
        "higher",

    "task_load_std":
        "lower",

    "utilization_std":
        "lower",

    "success_rate":
        "higher",
}


# ==========================================================
# Read CSV
# ==========================================================

def read_results():

    if not os.path.exists(
        RAW_CSV
    ):

        raise FileNotFoundError(
            f"Raw result file not found: {RAW_CSV}"
        )

    rows = []

    with open(
        RAW_CSV,
        "r",
        encoding="utf-8",
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            parsed = dict(
                row
            )

            parsed[
                "task_count"
            ] = int(
                row[
                    "task_count"
                ]
            )

            parsed[
                "seed"
            ] = int(
                row[
                    "seed"
                ]
            )

            for metric in METRICS:

                value = row.get(
                    metric
                )

                if (
                    value is None
                    or value == ""
                ):

                    parsed[
                        metric
                    ] = None

                else:

                    parsed[
                        metric
                    ] = float(
                        value
                    )

            rows.append(
                parsed
            )

    return rows


# ==========================================================
# Group By Condition
# ==========================================================

def build_index(
    rows,
):

    index = {}

    for row in rows:

        key = (
            row[
                "task_count"
            ],
            row[
                "load"
            ],
            row[
                "method"
            ],
            row[
                "seed"
            ],
        )

        index[
            key
        ] = row

    return index


# ==========================================================
# Paired Values
#
# 同一個：
#
# task_count
# load
# seed
#
# 進行成對比較。
# ==========================================================

def get_paired_values(
    index,
    task_count,
    load,
    method_a,
    method_b,
    metric,
):

    values_a = []
    values_b = []
    seeds = []

    for seed in range(30):

        key_a = (
            task_count,
            load,
            method_a,
            seed,
        )

        key_b = (
            task_count,
            load,
            method_b,
            seed,
        )

        if (
            key_a not in index
            or key_b not in index
        ):

            continue

        value_a = (
            index[
                key_a
            ].get(
                metric
            )
        )

        value_b = (
            index[
                key_b
            ].get(
                metric
            )
        )

        if (
            value_a is None
            or value_b is None
        ):

            continue

        values_a.append(
            value_a
        )

        values_b.append(
            value_b
        )

        seeds.append(
            seed
        )

    return (
        values_a,
        values_b,
        seeds,
    )


# ==========================================================
# Mean
# ==========================================================

def mean_or_none(
    values,
):

    if not values:

        return None

    return statistics.mean(
        values
    )


# ==========================================================
# Paired Cohen's dz
#
# dz =
# mean(pair differences)
# /
# std(pair differences)
#
# 注意：
# difference 定義為：
#
# PPO - Baseline
#
# lower-is-better metric：
# negative = PPO better
#
# higher-is-better metric：
# positive = PPO better
# ==========================================================

def paired_cohens_dz(
    differences,
):

    if len(
        differences
    ) < 2:

        return None

    std_diff = statistics.stdev(
        differences
    )

    if math.isclose(
        std_diff,
        0.0,
        abs_tol=1e-12,
    ):

        return 0.0

    return (
        statistics.mean(
            differences
        )
        /
        std_diff
    )


# ==========================================================
# Bootstrap 95% CI
#
# 對 paired differences 做 bootstrap。
# ==========================================================

def bootstrap_mean_ci(
    differences,
    iterations=10000,
    confidence=0.95,
    seed=2026,
):

    if not differences:

        return (
            None,
            None,
        )

    rng = random.Random(
        seed
    )

    n = len(
        differences
    )

    bootstrap_means = []

    for _ in range(
        iterations
    ):

        sample = [
            differences[
                rng.randrange(
                    n
                )
            ]
            for _ in range(
                n
            )
        ]

        bootstrap_means.append(
            statistics.mean(
                sample
            )
        )

    bootstrap_means.sort()

    alpha = (
        1.0
        -
        confidence
    )

    lower_index = int(
        (
            alpha
            /
            2.0
        )
        *
        iterations
    )

    upper_index = int(
        (
            1.0
            -
            alpha
            /
            2.0
        )
        *
        iterations
    )

    lower_index = max(
        0,
        min(
            lower_index,
            iterations - 1,
        ),
    )

    upper_index = max(
        0,
        min(
            upper_index,
            iterations - 1,
        ),
    )

    return (
        bootstrap_means[
            lower_index
        ],
        bootstrap_means[
            upper_index
        ],
    )


# ==========================================================
# Wilcoxon
# ==========================================================

def calculate_wilcoxon(
    values_a,
    values_b,
):

    if not values_a:

        return None

    differences = [
        a - b
        for a, b
        in zip(
            values_a,
            values_b,
        )
    ]

    if all(
        math.isclose(
            difference,
            0.0,
            abs_tol=1e-12,
        )
        for difference
        in differences
    ):

        return 1.0

    result = wilcoxon(
        values_a,
        values_b,
        alternative="two-sided",
        zero_method="wilcox",
    )

    return float(
        result.pvalue
    )


# ==========================================================
# Win Rate
# ==========================================================

def calculate_win_rate(
    values_a,
    values_b,
    direction,
):

    wins = 0
    losses = 0
    ties = 0

    for (
        value_a,
        value_b,
    ) in zip(
        values_a,
        values_b,
    ):

        if math.isclose(
            value_a,
            value_b,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):

            ties += 1
            continue

        if direction == "lower":

            if value_a < value_b:
                wins += 1
            else:
                losses += 1

        elif direction == "higher":

            if value_a > value_b:
                wins += 1
            else:
                losses += 1

        else:

            raise ValueError(
                f"Unknown direction: {direction}"
            )

    total = (
        wins
        +
        losses
        +
        ties
    )

    if total == 0:

        win_rate = None

    else:

        win_rate = (
            wins
            /
            total
        )

    return (
        wins,
        losses,
        ties,
        win_rate,
    )


# ==========================================================
# Analyze One Comparison
# ==========================================================

def analyze_comparison(
    index,
    task_count,
    load,
    baseline_method,
    metric,
):

    (
        ppo_values,
        baseline_values,
        seeds,
    ) = (
        get_paired_values(

            index=index,

            task_count=(
                task_count
            ),

            load=load,

            method_a=(
                PPO_METHOD
            ),

            method_b=(
                baseline_method
            ),

            metric=metric,
        )
    )

    differences = [
        ppo - baseline
        for ppo, baseline
        in zip(
            ppo_values,
            baseline_values,
        )
    ]

    ppo_mean = mean_or_none(
        ppo_values
    )

    baseline_mean = mean_or_none(
        baseline_values
    )

    difference_mean = mean_or_none(
        differences
    )

    (
        ci_low,
        ci_high,
    ) = (
        bootstrap_mean_ci(
            differences
        )
    )

    wilcoxon_p = (
        calculate_wilcoxon(
            ppo_values,
            baseline_values,
        )
    )

    effect_size = (
        paired_cohens_dz(
            differences
        )
    )

    (
        wins,
        losses,
        ties,
        win_rate,
    ) = (
        calculate_win_rate(

            ppo_values,

            baseline_values,

            METRICS[
                metric
            ],
        )
    )

    return {

        "task_count":
            task_count,

        "load":
            load,

        "comparison":
            (
                "PPO vs "
                +
                baseline_method
            ),

        "metric":
            metric,

        "direction":
            METRICS[
                metric
            ],

        "paired_samples":
            len(
                seeds
            ),

        "ppo_mean":
            ppo_mean,

        "baseline_mean":
            baseline_mean,

        "mean_difference_ppo_minus_baseline":
            difference_mean,

        "ci95_low":
            ci_low,

        "ci95_high":
            ci_high,

        "ppo_wins":
            wins,

        "ppo_losses":
            losses,

        "ties":
            ties,

        "ppo_win_rate":
            win_rate,

        "wilcoxon_p_value":
            wilcoxon_p,

        "paired_cohens_dz":
            effect_size,
    }


# ==========================================================
# Save CSV
# ==========================================================

def save_csv(
    rows,
):

    if not rows:

        return

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ==========================================================
# Display Helper
# ==========================================================

def fmt(
    value,
    digits=3,
):

    if value is None:

        return "N/A"

    return (
        f"{value:.{digits}f}"
    )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 120)

    print(
        "FULL COMPARISON STATISTICAL ANALYSIS"
    )

    print("=" * 120)

    print(
        "Input:",
        RAW_CSV,
    )

    print()

    rows = read_results()

    print(
        "Raw rows:",
        len(
            rows
        ),
    )

    if len(
        rows
    ) != 810:

        print(
            "WARNING: expected 810 raw rows."
        )

    index = build_index(
        rows
    )

    task_counts = sorted(
        {
            row[
                "task_count"
            ]
            for row
            in rows
        }
    )

    load_order = [
        "low",
        "medium",
        "high",
    ]

    baselines = [
        RULE_METHOD,
        NEAREST_METHOD,
    ]

    analysis_rows = []

    # ======================================================
    # Full Analysis
    # ======================================================

    for task_count in task_counts:

        for load in load_order:

            print()

            print("=" * 120)

            print(
                f"{task_count} TASKS | {load.upper()} LOAD"
            )

            print("=" * 120)

            # --------------------------------------------------
            # First print the main KPI:
            # average_waiting_time
            # --------------------------------------------------

            for baseline_method in baselines:

                result = (
                    analyze_comparison(

                        index=index,

                        task_count=(
                            task_count
                        ),

                        load=load,

                        baseline_method=(
                            baseline_method
                        ),

                        metric=(
                            "average_waiting_time"
                        ),
                    )
                )

                print(
                    f"PPO vs "
                    f"{baseline_method}"
                )

                print(
                    "  PPO mean       :",
                    fmt(
                        result[
                            "ppo_mean"
                        ]
                    ),
                )

                print(
                    "  Baseline mean  :",
                    fmt(
                        result[
                            "baseline_mean"
                        ]
                    ),
                )

                print(
                    "  Difference     :",
                    fmt(
                        result[
                            "mean_difference_ppo_minus_baseline"
                        ]
                    ),
                )

                print(
                    "  95% CI         :",
                    "["
                    +
                    fmt(
                        result[
                            "ci95_low"
                        ]
                    )
                    +
                    ", "
                    +
                    fmt(
                        result[
                            "ci95_high"
                        ]
                    )
                    +
                    "]",
                )

                print(
                    "  PPO W/L/T      :",
                    f"{result['ppo_wins']}"
                    f"/"
                    f"{result['ppo_losses']}"
                    f"/"
                    f"{result['ties']}",
                )

                print(
                    "  PPO win rate   :",
                    fmt(
                        result[
                            "ppo_win_rate"
                        ]
                        *
                        100.0
                    ),
                    "%",
                )

                print(
                    "  Wilcoxon p     :",
                    fmt(
                        result[
                            "wilcoxon_p_value"
                        ],
                        digits=6,
                    ),
                )

                print(
                    "  Cohen dz       :",
                    fmt(
                        result[
                            "paired_cohens_dz"
                        ]
                    ),
                )

                print()

            # --------------------------------------------------
            # All Metrics For CSV
            # --------------------------------------------------

            for baseline_method in baselines:

                for metric in METRICS:

                    result = (
                        analyze_comparison(

                            index=index,

                            task_count=(
                                task_count
                            ),

                            load=load,

                            baseline_method=(
                                baseline_method
                            ),

                            metric=metric,
                        )
                    )

                    analysis_rows.append(
                        result
                    )

    # ======================================================
    # Save
    # ======================================================

    save_csv(
        analysis_rows
    )

    print()

    print("=" * 120)

    print(
        "STATISTICAL ANALYSIS COMPLETED"
    )

    print("=" * 120)

    print(
        "Output:",
        OUTPUT_CSV,
    )

    print(
        "Analysis rows:",
        len(
            analysis_rows
        ),
    )


if __name__ == "__main__":
    main()