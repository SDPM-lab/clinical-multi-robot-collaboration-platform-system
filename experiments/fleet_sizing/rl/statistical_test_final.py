from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

from scipy.stats import wilcoxon


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

INPUT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "comparison_final"
    / "final_runs.csv"
)


BASELINE = "dynamic_weighted"
PROPOSED = "maskable_ppo_180k"


METRICS = {
    "average_waiting_time_s":
        "Average Waiting",

    "p95_waiting_time_s":
        "P95 Waiting",

    "high_waiting_time_s":
        "High Waiting",

    "emergency_waiting_time_s":
        "Emergency Waiting",

    "total_travel_time_s":
        "Total Travel",

    "jain_task_fairness":
        "Jain Fairness",
}


def load_rows():

    rows = []

    with INPUT_PATH.open(
        newline="",
        encoding="utf-8",
    ) as file:

        for row in csv.DictReader(
            file
        ):

            rows.append(
                row
            )

    return rows


def build_seed_map(
    rows,
    method,
):

    result = {}

    for row in rows:

        if (
            row["method"]
            != method
        ):
            continue

        seed = int(
            row["seed"]
        )

        result[
            seed
        ] = row

    return result


def cohens_dz(
    differences,
):

    if len(
        differences
    ) < 2:
        return 0.0

    std = statistics.stdev(
        differences
    )

    if std == 0.0:
        return 0.0

    return (
        statistics.mean(
            differences
        )
        / std
    )


def holm_adjust(
    p_values,
):

    count = len(
        p_values
    )

    indexed = sorted(
        enumerate(
            p_values
        ),
        key=lambda item:
            item[1],
    )

    adjusted = [
        0.0
    ] * count

    running_max = 0.0

    for rank, (
        original_index,
        p_value,
    ) in enumerate(
        indexed
    ):

        multiplier = (
            count
            - rank
        )

        value = min(
            1.0,
            p_value
            * multiplier,
        )

        running_max = max(
            running_max,
            value,
        )

        adjusted[
            original_index
        ] = running_max

    return adjusted


def main():

    rows = load_rows()

    baseline_rows = (
        build_seed_map(
            rows,
            BASELINE,
        )
    )

    proposed_rows = (
        build_seed_map(
            rows,
            PROPOSED,
        )
    )

    seeds = sorted(
        set(
            baseline_rows
        )
        &
        set(
            proposed_rows
        )
    )

    print(
        "=" * 118
    )

    print(
        "FINAL PAIRED STATISTICAL TEST"
    )

    print(
        "=" * 118
    )

    print(
        "Baseline:",
        BASELINE,
    )

    print(
        "Proposed:",
        PROPOSED,
    )

    print(
        "Paired seeds:",
        len(
            seeds
        ),
    )

    print(
        "Seed range:",
        f"{seeds[0]}–{seeds[-1]}",
    )

    print()

    results = []

    raw_p_values = []

    for metric, label in (
        METRICS.items()
    ):

        baseline_values = [
            float(
                baseline_rows[
                    seed
                ][
                    metric
                ]
            )
            for seed
            in seeds
        ]

        proposed_values = [
            float(
                proposed_rows[
                    seed
                ][
                    metric
                ]
            )
            for seed
            in seeds
        ]

        differences = [
            proposed
            - baseline
            for proposed, baseline
            in zip(
                proposed_values,
                baseline_values,
            )
        ]

        baseline_mean = (
            statistics.mean(
                baseline_values
            )
        )

        proposed_mean = (
            statistics.mean(
                proposed_values
            )
        )

        mean_difference = (
            statistics.mean(
                differences
            )
        )

        relative_difference = (
            (
                mean_difference
                / baseline_mean
            )
            * 100.0
            if baseline_mean
            != 0.0
            else math.nan
        )

        try:

            test = wilcoxon(
                proposed_values,
                baseline_values,
                alternative="two-sided",
                zero_method="wilcox",
            )

            statistic = float(
                test.statistic
            )

            p_value = float(
                test.pvalue
            )

        except ValueError:

            statistic = 0.0
            p_value = 1.0

        effect_size = (
            cohens_dz(
                differences
            )
        )

        raw_p_values.append(
            p_value
        )

        results.append(
            {
                "metric":
                    label,

                "baseline_mean":
                    baseline_mean,

                "proposed_mean":
                    proposed_mean,

                "difference":
                    mean_difference,

                "relative_difference":
                    relative_difference,

                "statistic":
                    statistic,

                "p_value":
                    p_value,

                "cohens_dz":
                    effect_size,
            }
        )

    adjusted = (
        holm_adjust(
            raw_p_values
        )
    )

    print(
        f"{'Metric':<22}"
        f"{'Dynamic':>12}"
        f"{'PPO':>12}"
        f"{'Diff':>12}"
        f"{'Diff %':>10}"
        f"{'p':>12}"
        f"{'Holm p':>12}"
        f"{'dz':>10}"
    )

    print(
        "-" * 118
    )

    for (
        result,
        adjusted_p,
    ) in zip(
        results,
        adjusted,
    ):

        print(
            f"{result['metric']:<22}"
            f"{result['baseline_mean']:>12.3f}"
            f"{result['proposed_mean']:>12.3f}"
            f"{result['difference']:>12.3f}"
            f"{result['relative_difference']:>10.2f}"
            f"{result['p_value']:>12.5f}"
            f"{adjusted_p:>12.5f}"
            f"{result['cohens_dz']:>10.3f}"
        )

    print(
        "=" * 118
    )

    print()
    print(
        "Interpretation:"
    )

    print(
        "Holm p < 0.05 -> "
        "significant after multiple-comparison correction."
    )

    print(
        "For waiting/travel metrics: "
        "negative Diff favors PPO."
    )

    print(
        "For Jain Fairness: "
        "positive Diff favors PPO."
    )


if __name__ == "__main__":
    main()