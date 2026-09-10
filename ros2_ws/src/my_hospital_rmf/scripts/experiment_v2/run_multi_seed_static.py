#!/usr/bin/env python3

import argparse
import statistics

from collections import (
    defaultdict,
)

from experiment_v2.run_static_baselines import (
    run_all_static_baselines,
)

from experiment_v2.paired_statistics import (
    compare_paired_metric,
)


# ==========================================================
# Metric Extraction
# ==========================================================

def extract_metrics(
    result,
) -> dict[str, float | None]:

    metrics = result.metrics

    return {
        "waiting_time": (
            metrics
            .average_task_waiting_time
        ),

        "emergency_waiting_time": (
            metrics
            .waiting_time_by_priority[
                3
            ]
        ),

        "completion_time": (
            metrics
            .average_task_completion_time
        ),

        "makespan": (
            metrics.makespan
        ),

        "travel_distance": (
            metrics
            .total_travel_distance
        ),

        "success_rate": (
            metrics
            .task_success_rate
        ),

        "jain_fairness": (
            metrics
            .jain_fairness_index
        ),

        "decision_time_ms": (
            metrics
            .average_decision_time_seconds
            *
            1000.0
        ),
    }


# ==========================================================
# Statistics
# ==========================================================

def summarize_values(
    values: list[float],
) -> dict[str, float]:

    if not values:

        return {
            "mean": float("nan"),
            "std": float("nan"),
            "median": float("nan"),
        }

    if len(values) == 1:

        std = 0.0

    else:

        std = statistics.stdev(
            values
        )

    return {
        "mean": statistics.mean(
            values
        ),

        "std": std,

        "median": statistics.median(
            values
        ),
    }


# ==========================================================
# Multi-Seed Run
# ==========================================================

def run_multi_seed_static(
    seed_start: int,
    seed_end: int,
    task_count: int,
):
    """
    對每一個 seed 使用同一 Scenario
    跑三個 Static Baseline。

    seed_start / seed_end 都包含。
    """

    if seed_end < seed_start:

        raise ValueError(
            "seed_end must be >= seed_start"
        )

    raw_results = defaultdict(
        lambda: defaultdict(list)
    )

    per_seed_rows = []

    for seed in range(
        seed_start,
        seed_end + 1,
    ):

        baseline_results = (
            run_all_static_baselines(
                seed=seed,
                task_count=task_count,
            )
        )

        for result in baseline_results:

            values = (
                extract_metrics(
                    result
                )
            )

            row = {
                "seed": seed,
                "method": result.method,
                **values,
            }

            per_seed_rows.append(
                row
            )

            for metric_name, value in (
                values.items()
            ):

                if value is None:

                    continue

                raw_results[
                    result.method
                ][
                    metric_name
                ].append(
                    float(value)
                )

    return (
        raw_results,
        per_seed_rows,
    )


# ==========================================================
# Print Summary
# ==========================================================

def print_summary(
    raw_results,
):

    metrics_to_print = [
        "waiting_time",
        "emergency_waiting_time",
        "completion_time",
        "makespan",
        "travel_distance",
        "success_rate",
        "jain_fairness",
        "decision_time_ms",
    ]

    methods = [
        "random_feasible",
        "projected_nearest",
        "weighted_heuristic",
    ]

    print()

    print(
        "=" * 100
    )

    print(
        "MULTI-SEED STATIC BASELINE SUMMARY"
    )

    print(
        "=" * 100
    )

    for metric_name in metrics_to_print:

        print()

        print(
            metric_name
        )

        print(
            "-" * 100
        )

        print(
            f"{'Method':<26}"
            f"{'Mean':>14}"
            f"{'Std':>14}"
            f"{'Median':>14}"
            f"{'N':>10}"
        )

        for method in methods:

            values = (
                raw_results[
                    method
                ][
                    metric_name
                ]
            )

            summary = (
                summarize_values(
                    values
                )
            )

            print(
                f"{method:<26}"
                f"{summary['mean']:>14.3f}"
                f"{summary['std']:>14.3f}"
                f"{summary['median']:>14.3f}"
                f"{len(values):>10}"
            )

    print()

    print(
        "=" * 100
    )


# ==========================================================
# Paired Summary
# ==========================================================

def print_paired_summary(
    rows,
):

    comparisons = [
        (
            "weighted_heuristic",
            "random_feasible",
        ),
        (
            "weighted_heuristic",
            "projected_nearest",
        ),
    ]

    metric_definitions = [
        (
            "waiting_time",
            True,
        ),
        (
            "emergency_waiting_time",
            True,
        ),
        (
            "completion_time",
            True,
        ),
        (
            "makespan",
            True,
        ),
        (
            "travel_distance",
            True,
        ),
        (
            "success_rate",
            False,
        ),
        (
            "jain_fairness",
            False,
        ),
    ]

    print()

    print(
        "=" * 120
    )

    print(
        "PAIRED STATISTICAL COMPARISON"
    )

    print(
        "=" * 120
    )

    for method_a, method_b in comparisons:

        print()

        print(
            f"{method_a} vs {method_b}"
        )

        print(
            "-" * 120
        )

        print(
            f"{'Metric':<28}"
            f"{'Mean Diff':>14}"
            f"{'Median Diff':>16}"
            f"{'A Wins':>10}"
            f"{'B Wins':>10}"
            f"{'Ties':>8}"
            f"{'N':>8}"
            f"{'p-value':>14}"
        )

        for (
            metric,
            lower_is_better,
        ) in metric_definitions:

            result = (
                compare_paired_metric(
                    rows=rows,
                    metric=metric,
                    method_a=method_a,
                    method_b=method_b,
                    lower_is_better=(
                        lower_is_better
                    ),
                )
            )

            if result.p_value is None:

                p_value_text = "N/A"

            else:

                if result.p_value < 1e-6:

                    p_value_text = "<1e-6"

                else:

                    p_value_text = (
                        f"{result.p_value:.6f}"
                    )

            print(
                f"{metric:<28}"
                f"{result.mean_difference:>14.3f}"
                f"{result.median_difference:>16.3f}"
                f"{result.wins_a:>10}"
                f"{result.wins_b:>10}"
                f"{result.ties:>8}"
                f"{result.sample_count:>8}"
                f"{p_value_text:>14}"
            )

    print()

    print(
        "=" * 120
    )


# ==========================================================
# CLI
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run paired multi-seed "
            "Static Baseline experiments."
        )
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=8100,
    )

    parser.add_argument(
        "--seed-end",
        type=int,
        default=8129,
    )

    parser.add_argument(
        "--tasks",
        type=int,
        default=50,
    )

    args = (
        parser.parse_args()
    )

    raw_results, rows = (
        run_multi_seed_static(
            seed_start=(
                args.seed_start
            ),
            seed_end=(
                args.seed_end
            ),
            task_count=(
                args.tasks
            ),
        )
    )

    print_summary(
        raw_results
    )

    print_paired_summary(
        rows
    )


if __name__ == "__main__":

    main()