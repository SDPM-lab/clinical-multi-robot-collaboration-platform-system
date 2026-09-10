#!/usr/bin/env python3

import argparse
import statistics

from collections import (
    defaultdict,
)

from experiment_v2.run_baselines import (
    BASELINE_METHODS,
    run_all_baselines,
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

    waiting_by_priority = (
        metrics.waiting_time_by_priority
    )

    return {
        # --------------------------------------------------
        # Waiting
        # --------------------------------------------------

        "waiting_time": (
            metrics
            .average_task_waiting_time
        ),

        "low_waiting_time": (
            waiting_by_priority.get(0)
        ),

        "normal_waiting_time": (
            waiting_by_priority.get(1)
        ),

        "high_waiting_time": (
            waiting_by_priority.get(2)
        ),

        "emergency_waiting_time": (
            waiting_by_priority.get(3)
        ),

        # --------------------------------------------------
        # Scheduling Performance
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Decision Time
        # --------------------------------------------------

        "decision_time_ms": (
            metrics
            .average_decision_time_seconds
            *
            1000.0
        ),

        # --------------------------------------------------
        # Dynamic Diagnostics
        # --------------------------------------------------

        "reassignment_decisions": float(
            metrics
            .reassignment_decision_count
        ),

        "reassignment_count": float(
            metrics.reassignment_count
        ),

        "reassignment_rate": (
            metrics.reassignment_rate
        ),

        "average_reassignments_per_task": (
            metrics
            .average_reassignments_per_task
        ),

        "max_reassignments_per_task": float(
            metrics
            .max_reassignments_per_task
        ),

        "max_cascade_depth": float(
            metrics.max_cascade_depth
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
# Multi-Seed
# ==========================================================

def run_multi_seed(
    seed_start: int,
    seed_end: int,
    task_count: int,
):
    """
    對每個 Seed 建立一份 Scenario，
    再讓四個 Baseline 共用該 Scenario。

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
            run_all_baselines(
                seed=seed,
                task_count=task_count,
            )
        )

        for result in baseline_results:

            values = extract_metrics(
                result
            )

            row = {
                "seed": seed,
                "method": result.method,
                **values,
            }

            per_seed_rows.append(
                row
            )

            for (
                metric_name,
                value,
            ) in values.items():

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
# Summary
# ==========================================================

def print_summary(
    raw_results,
):

    metrics_to_print = [
        "waiting_time",
        "low_waiting_time",
        "normal_waiting_time",
        "high_waiting_time",
        "emergency_waiting_time",
        "completion_time",
        "makespan",
        "travel_distance",
        "success_rate",
        "jain_fairness",
        "decision_time_ms",
    ]

    methods = [
        method.value
        for method
        in BASELINE_METHODS
    ]

    print()

    print(
        "=" * 105
    )

    print(
        "MULTI-SEED BASELINE SUMMARY"
    )

    print(
        "=" * 105
    )

    for metric_name in metrics_to_print:

        print()

        print(
            metric_name
        )

        print(
            "-" * 105
        )

        print(
            f"{'Method':<30}"
            f"{'Mean':>15}"
            f"{'Std':>15}"
            f"{'Median':>15}"
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

            summary = summarize_values(
                values
            )

            print(
                f"{method:<30}"
                f"{summary['mean']:>15.3f}"
                f"{summary['std']:>15.3f}"
                f"{summary['median']:>15.3f}"
                f"{len(values):>10}"
            )

    print()

    print(
        "=" * 105
    )


# ==========================================================
# Dynamic Diagnostics
# ==========================================================

def print_dynamic_summary(
    raw_results,
):

    method = (
        "dynamic_weighted_heuristic"
    )

    metrics = [
        "reassignment_decisions",
        "reassignment_count",
        "reassignment_rate",
        "average_reassignments_per_task",
        "max_reassignments_per_task",
        "max_cascade_depth",
    ]

    print()

    print(
        "=" * 105
    )

    print(
        "DYNAMIC REASSIGNMENT SUMMARY"
    )

    print(
        "=" * 105
    )

    print(
        f"{'Metric':<38}"
        f"{'Mean':>15}"
        f"{'Std':>15}"
        f"{'Median':>15}"
        f"{'N':>10}"
    )

    print(
        "-" * 105
    )

    for metric_name in metrics:

        values = (
            raw_results[
                method
            ][
                metric_name
            ]
        )

        summary = summarize_values(
            values
        )

        print(
            f"{metric_name:<38}"
            f"{summary['mean']:>15.3f}"
            f"{summary['std']:>15.3f}"
            f"{summary['median']:>15.3f}"
            f"{len(values):>10}"
        )

    print(
        "=" * 105
    )


# ==========================================================
# Paired Comparison
# ==========================================================

def print_paired_summary(
    rows,
):

    # ------------------------------------------------------
    # Main comparison：
    #
    # Dynamic Weighted vs Static Weighted
    #
    # 另外保留對 Random / Nearest 的比較，
    # 方便完整 Baseline Table。
    # ------------------------------------------------------

    comparisons = [
        (
            "dynamic_weighted_heuristic",
            "weighted_heuristic",
        ),
        (
            "dynamic_weighted_heuristic",
            "random_feasible",
        ),
        (
            "dynamic_weighted_heuristic",
            "projected_nearest",
        ),
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
            "low_waiting_time",
            True,
        ),
        (
            "normal_waiting_time",
            True,
        ),
        (
            "high_waiting_time",
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
        "=" * 130
    )

    print(
        "PAIRED STATISTICAL COMPARISON"
    )

    print(
        "=" * 130
    )

    for (
        method_a,
        method_b,
    ) in comparisons:

        print()

        print(
            f"{method_a} vs {method_b}"
        )

        print(
            "-" * 130
        )

        print(
            f"{'Metric':<30}"
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

            elif result.p_value < 1e-6:

                p_value_text = "<1e-6"

            else:

                p_value_text = (
                    f"{result.p_value:.6f}"
                )

            print(
                f"{metric:<30}"
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
        "=" * 130
    )


# ==========================================================
# CLI
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run paired multi-seed "
            "Scheduler v2 Baseline experiments."
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

    args = parser.parse_args()

    raw_results, rows = (
        run_multi_seed(
            seed_start=args.seed_start,
            seed_end=args.seed_end,
            task_count=args.tasks,
        )
    )

    print_summary(
        raw_results
    )

    print_dynamic_summary(
        raw_results
    )

    print_paired_summary(
        rows
    )


if __name__ == "__main__":

    main()