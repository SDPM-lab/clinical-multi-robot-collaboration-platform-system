#!/usr/bin/env python3

import csv
import os
import random
import statistics

from scipy.stats import wilcoxon


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
    "final_test_30seed_raw_results.csv",
)

OUTPUT_CSV = os.path.join(
    RESULT_DIR,
    "final_test_paired_statistics.csv",
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


COMPARISONS = [
    (
        "PPO vs Rule-based",
        PPO_METHOD,
        RULE_METHOD,
    ),
    (
        "PPO vs Nearest",
        PPO_METHOD,
        NEAREST_METHOD,
    ),
    (
        "Rule-based vs Nearest",
        RULE_METHOD,
        NEAREST_METHOD,
    ),
]


# ==========================================================
# Metrics
#
# 全部都是越低越好
# ==========================================================

METRICS = [
    "average_waiting_time",
    "emergency_waiting_time",
    "makespan",
    "total_travel_distance",
    "task_load_std",
]


TASK_COUNTS = [
    20,
    50,
    100,
]

LOADS = [
    "low",
    "medium",
    "high",
]


# ==========================================================
# Helpers
# ==========================================================

def parse_float(value):

    if value is None or value == "":
        return None

    return float(value)


def load_rows():

    with open(
        RAW_CSV,
        "r",
        encoding="utf-8",
    ) as f:

        return list(
            csv.DictReader(f)
        )


# ==========================================================
# Get paired samples
# ==========================================================

def get_pairs(
    rows,
    task_count,
    load,
    method_a,
    method_b,
    metric,
):

    by_seed = {}

    for row in rows:

        if int(row["task_count"]) != task_count:
            continue

        if row["load"] != load:
            continue

        method = row["method"]

        if method not in (
            method_a,
            method_b,
        ):
            continue

        seed = int(
            row["seed"]
        )

        value = parse_float(
            row[metric]
        )

        by_seed.setdefault(
            seed,
            {},
        )

        by_seed[seed][method] = value

    values_a = []
    values_b = []

    for seed in sorted(by_seed):

        item = by_seed[seed]

        if (
            method_a not in item
            or method_b not in item
        ):
            continue

        a = item[method_a]
        b = item[method_b]

        if (
            a is None
            or b is None
        ):
            continue

        values_a.append(a)
        values_b.append(b)

    return (
        values_a,
        values_b,
    )


# ==========================================================
# Bootstrap CI
#
# difference = A - B
#
# negative -> A better
# positive -> A worse
# ==========================================================

def bootstrap_ci(
    differences,
    iterations=10000,
    random_seed=12345,
):

    rng = random.Random(
        random_seed
    )

    n = len(
        differences
    )

    samples = []

    for _ in range(iterations):

        sample = [
            differences[
                rng.randrange(n)
            ]
            for _ in range(n)
        ]

        samples.append(
            statistics.mean(sample)
        )

    samples.sort()

    lower_index = int(
        0.025
        *
        (iterations - 1)
    )

    upper_index = int(
        0.975
        *
        (iterations - 1)
    )

    return (
        samples[lower_index],
        samples[upper_index],
    )


# ==========================================================
# Paired Cohen's dz
# ==========================================================

def cohen_dz(
    differences,
):

    if len(differences) < 2:
        return None

    std = statistics.stdev(
        differences
    )

    if std == 0:
        return 0.0

    return (
        statistics.mean(
            differences
        )
        /
        std
    )


# ==========================================================
# Holm correction
#
# 對同一 metric 的全部 27 個檢定修正
# ==========================================================

def holm_adjust(
    p_values,
):

    m = len(
        p_values
    )

    order = sorted(
        range(m),
        key=lambda i: p_values[i],
    )

    adjusted = [
        1.0
    ] * m

    previous = 0.0

    for rank, index in enumerate(order):

        factor = (
            m
            -
            rank
        )

        value = min(
            1.0,
            p_values[index]
            *
            factor,
        )

        value = max(
            value,
            previous,
        )

        adjusted[index] = value

        previous = value

    return adjusted


# ==========================================================
# Analyze one pair
# ==========================================================

def analyze_pair(
    values_a,
    values_b,
):

    differences = [
        a - b
        for a, b
        in zip(
            values_a,
            values_b,
        )
    ]

    n = len(
        differences
    )

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
    ) = bootstrap_ci(
        differences
    )

    wins = sum(
        diff < -1e-9
        for diff in differences
    )

    losses = sum(
        diff > 1e-9
        for diff in differences
    )

    ties = (
        n
        -
        wins
        -
        losses
    )

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
            wins / n,

        "wilcoxon_statistic":
            statistic,

        "p_raw":
            p_value,

        "cohen_dz":
            cohen_dz(
                differences
            ),
    }


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

    results = []

    # ======================================================
    # Calculate all tests
    # ======================================================

    for metric in METRICS:

        metric_results = []

        for (
            comparison_name,
            method_a,
            method_b,
        ) in COMPARISONS:

            for task_count in (
                TASK_COUNTS
            ):

                for load in (
                    LOADS
                ):

                    (
                        values_a,
                        values_b,
                    ) = get_pairs(
                        rows=rows,
                        task_count=task_count,
                        load=load,
                        method_a=method_a,
                        method_b=method_b,
                        metric=metric,
                    )

                    if not values_a:
                        continue

                    result = analyze_pair(
                        values_a,
                        values_b,
                    )

                    row = {
                        "metric":
                            metric,

                        "comparison":
                            comparison_name,

                        "method_a":
                            method_a,

                        "method_b":
                            method_b,

                        "task_count":
                            task_count,

                        "load":
                            load,

                        **result,
                    }

                    metric_results.append(
                        row
                    )

        # ==================================================
        # Holm correction:
        # 每個 metric 共有最多 27 tests
        # ==================================================

        adjusted = holm_adjust(
            [
                row["p_raw"]
                for row
                in metric_results
            ]
        )

        for row, p_holm in zip(
            metric_results,
            adjusted,
        ):

            row[
                "p_holm"
            ] = p_holm

            row[
                "significant_holm"
            ] = (
                p_holm < 0.05
            )

            if row[
                "mean_diff"
            ] < 0:

                row[
                    "direction"
                ] = "A better"

            elif row[
                "mean_diff"
            ] > 0:

                row[
                    "direction"
                ] = "B better"

            else:

                row[
                    "direction"
                ] = "Tie"

        results.extend(
            metric_results
        )

    # ======================================================
    # Save CSV
    # ======================================================

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=(
                results[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    # ======================================================
    # Print
    # ======================================================

    print("=" * 140)

    print(
        "FINAL TEST PAIRED STATISTICAL ANALYSIS"
    )

    print("=" * 140)

    print(
        "Lower is better."
    )

    print(
        "A-B < 0 => A better."
    )

    print(
        "Holm correction applied within each metric."
    )

    print()

    current_metric = None
    current_comparison = None

    for row in results:

        if (
            row["metric"]
            != current_metric
        ):

            current_metric = (
                row["metric"]
            )

            current_comparison = None

            print()
            print("#" * 140)
            print(
                "METRIC:",
                current_metric,
            )
            print("#" * 140)

        if (
            row["comparison"]
            != current_comparison
        ):

            current_comparison = (
                row["comparison"]
            )

            print()
            print(
                current_comparison
            )
            print("-" * 140)

        sig = (
            "YES"
            if row[
                "significant_holm"
            ]
            else "NO"
        )

        print(
            f"{row['task_count']:>3} "
            f"{row['load']:<6}"
            f" | A={row['mean_a']:>9.3f}"
            f" | B={row['mean_b']:>9.3f}"
            f" | diff={row['mean_diff']:>+9.3f}"
            f" | CI=["
            f"{row['ci_low']:>+8.3f},"
            f"{row['ci_high']:>+8.3f}]"
            f" | W/L/T="
            f"{row['wins']:>2}/"
            f"{row['losses']:>2}/"
            f"{row['ties']:>2}"
            f" | p={row['p_raw']:.5f}"
            f" | Holm={row['p_holm']:.5f}"
            f" | sig={sig}"
            f" | dz={row['cohen_dz']:+.3f}"
        )

    print()

    print("=" * 140)

    print(
        "Saved:",
        OUTPUT_CSV,
    )

    print(
        "Tests:",
        len(
            results
        ),
    )

    print("=" * 140)


if __name__ == "__main__":
    main()