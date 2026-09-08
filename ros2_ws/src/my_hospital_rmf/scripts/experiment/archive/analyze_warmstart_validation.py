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

RESULT_DIR = os.path.join(
    SCRIPT_DIR,
    "results",
)

RAW_CSV = os.path.join(
    RESULT_DIR,
    "warmstart_validation_30seed_raw_results.csv",
)


# ==========================================================
# Methods
# ==========================================================

RULE_METHOD = (
    "Priority + Rule-based"
)

OLD_PPO_METHOD = (
    "Priority + PPO 33D Reward v3 50K"
)

WARMSTART_METHOD = (
    "Priority + PPO 33D Reward v3 Warm-start Balanced FT50K"
)


COMPARISONS = [

    (
        "Warm-start vs Old PPO",
        WARMSTART_METHOD,
        OLD_PPO_METHOD,
    ),

    (
        "Warm-start vs Rule-based",
        WARMSTART_METHOD,
        RULE_METHOD,
    ),

    (
        "Old PPO vs Rule-based",
        OLD_PPO_METHOD,
        RULE_METHOD,
    ),
]


# ==========================================================
# Metrics
#
# 這些全部都是「越低越好」
# ==========================================================

METRICS = [

    "average_waiting_time",

    "emergency_waiting_time",

    "makespan",

    "total_travel_distance",

    "task_load_std",
]


# ==========================================================
# Read CSV
# ==========================================================

def load_rows():

    with open(
        RAW_CSV,
        "r",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(
                file
            )
        )


# ==========================================================
# Convert Optional Float
# ==========================================================

def parse_float(
    value,
):

    if (
        value is None
        or value == ""
    ):

        return None

    return float(
        value
    )


# ==========================================================
# Get Paired Values
# ==========================================================

def get_paired_values(
    rows,
    task_count,
    load,
    method_a,
    method_b,
    metric,
):

    grouped = {}

    for row in rows:

        if int(
            row[
                "task_count"
            ]
        ) != task_count:

            continue

        if (
            row[
                "load"
            ]
            != load
        ):

            continue

        method = (
            row[
                "method"
            ]
        )

        if method not in (
            method_a,
            method_b,
        ):

            continue

        seed = int(
            row[
                "seed"
            ]
        )

        value = parse_float(
            row[
                metric
            ]
        )

        grouped.setdefault(
            seed,
            {},
        )

        grouped[
            seed
        ][
            method
        ] = value

    values_a = []
    values_b = []

    for seed in sorted(
        grouped
    ):

        data = (
            grouped[
                seed
            ]
        )

        if (
            method_a not in data
            or method_b not in data
        ):

            continue

        a = data[
            method_a
        ]

        b = data[
            method_b
        ]

        if (
            a is None
            or b is None
        ):

            continue

        values_a.append(
            a
        )

        values_b.append(
            b
        )

    return (
        values_a,
        values_b,
    )


# ==========================================================
# Bootstrap CI Of Paired Mean Difference
#
# diff = A - B
#
# negative:
# A better
#
# positive:
# A worse
# ==========================================================

def bootstrap_mean_diff_ci(
    differences,
    iterations=10000,
    seed=12345,
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

    lower_index = int(
        0.025
        *
        (
            iterations
            - 1
        )
    )

    upper_index = int(
        0.975
        *
        (
            iterations
            - 1
        )
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
# Paired Cohen's dz
# ==========================================================

def paired_cohen_dz(
    differences,
):

    if len(
        differences
    ) < 2:

        return None

    std_diff = statistics.stdev(
        differences
    )

    if std_diff == 0.0:

        return 0.0

    return (
        statistics.mean(
            differences
        )
        /
        std_diff
    )


# ==========================================================
# Analyze One Comparison
# ==========================================================

def analyze_pair(
    values_a,
    values_b,
):

    differences = [

        a - b

        for (
            a,
            b,
        ) in zip(
            values_a,
            values_b,
        )
    ]

    n = len(
        differences
    )

    if n == 0:

        return None

    mean_a = statistics.mean(
        values_a
    )

    mean_b = statistics.mean(
        values_b
    )

    mean_diff = statistics.mean(
        differences
    )

    (
        ci_low,
        ci_high,
    ) = bootstrap_mean_diff_ci(
        differences
    )

    # ======================================================
    # Lower is better
    # ======================================================

    wins = sum(
        1
        for diff in differences
        if diff < -1e-9
    )

    losses = sum(
        1
        for diff in differences
        if diff > 1e-9
    )

    ties = (
        n
        -
        wins
        -
        losses
    )

    win_rate = (
        wins
        /
        n
    )

    # ======================================================
    # Wilcoxon
    # ======================================================

    if all(
        abs(diff) <= 1e-12
        for diff in differences
    ):

        statistic = 0.0
        p_value = 1.0

    else:

        test = wilcoxon(
            values_a,
            values_b,
            alternative="two-sided",
            zero_method="wilcox",
        )

        statistic = float(
            test.statistic
        )

        p_value = float(
            test.pvalue
        )

    dz = paired_cohen_dz(
        differences
    )

    return {

        "n":
            n,

        "mean_a":
            mean_a,

        "mean_b":
            mean_b,

        "mean_diff":
            mean_diff,

        "ci_low":
            ci_low,

        "ci_high":
            ci_high,

        "wins":
            wins,

        "losses":
            losses,

        "ties":
            ties,

        "win_rate":
            win_rate,

        "wilcoxon_statistic":
            statistic,

        "p_value":
            p_value,

        "cohen_dz":
            dz,
    }


# ==========================================================
# Print Result
# ==========================================================

def print_result(
    comparison_name,
    task_count,
    load,
    metric,
    result,
):

    print(
        f"{task_count:>3} tasks"
        f" | {load:<6}"
        f" | {metric:<28}"
    )

    print(
        f"  {comparison_name}"
    )

    print(
        f"  A mean       : "
        f"{result['mean_a']:.4f}"
    )

    print(
        f"  B mean       : "
        f"{result['mean_b']:.4f}"
    )

    print(
        f"  A - B        : "
        f"{result['mean_diff']:+.4f}"
    )

    print(
        f"  Bootstrap CI : "
        f"["
        f"{result['ci_low']:+.4f}, "
        f"{result['ci_high']:+.4f}"
        f"]"
    )

    print(
        f"  W / L / T    : "
        f"{result['wins']}"
        f" / "
        f"{result['losses']}"
        f" / "
        f"{result['ties']}"
    )

    print(
        f"  Win rate     : "
        f"{result['win_rate'] * 100.0:.2f}%"
    )

    print(
        f"  Wilcoxon p   : "
        f"{result['p_value']:.6f}"
    )

    print(
        f"  Cohen dz     : "
        f"{result['cohen_dz']:+.4f}"
    )

    print()


# ==========================================================
# Main
# ==========================================================

def main():

    if not os.path.exists(
        RAW_CSV
    ):

        raise FileNotFoundError(
            RAW_CSV
        )

    rows = load_rows()

    print("=" * 120)

    print(
        "WARM-START 30-SEED PAIRED STATISTICAL ANALYSIS"
    )

    print("=" * 120)

    print(
        "Raw CSV:",
        RAW_CSV,
    )

    print()

    for metric in (
        METRICS
    ):

        print()
        print("#" * 120)
        print(
            "METRIC:",
            metric,
        )
        print("#" * 120)

        for (
            comparison_name,
            method_a,
            method_b,
        ) in COMPARISONS:

            print()
            print("=" * 120)
            print(
                comparison_name
            )
            print("=" * 120)

            for task_count in [
                20,
                50,
                100,
            ]:

                for load in [
                    "low",
                    "medium",
                    "high",
                ]:

                    (
                        values_a,
                        values_b,
                    ) = (
                        get_paired_values(

                            rows=rows,

                            task_count=(
                                task_count
                            ),

                            load=(
                                load
                            ),

                            method_a=(
                                method_a
                            ),

                            method_b=(
                                method_b
                            ),

                            metric=(
                                metric
                            ),
                        )
                    )

                    result = analyze_pair(
                        values_a,
                        values_b,
                    )

                    if result is None:
                        continue

                    print_result(

                        comparison_name=(
                            comparison_name
                        ),

                        task_count=(
                            task_count
                        ),

                        load=(
                            load
                        ),

                        metric=(
                            metric
                        ),

                        result=(
                            result
                        ),
                    )


if __name__ == "__main__":
    main()