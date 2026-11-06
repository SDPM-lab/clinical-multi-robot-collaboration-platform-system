from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, List

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.config import (
    REFERENCE_FLEET,
    REFERENCE_WORKLOAD_MULTIPLIER,
)

from experiments.fleet_sizing.metrics import (
    calculate_metrics,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulationResult,
    SchedulingSimulator,
)


# ============================================================
# Experiment Configuration
# ============================================================

ADAPTIVE_RANGES = (
    (0.5, 0.7),
    (0.4, 0.8),
    (0.6, 0.8),
    (0.5, 0.9),
    (0.7, 0.9),
)

CALIBRATION_SEEDS = tuple(
    range(
        2001,
        2011,
    )
)

RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
)

RUNS_CSV = (
    RESULTS_DIR
    / "dynamic_weight_sensitivity_runs.csv"
)

SUMMARY_CSV = (
    RESULTS_DIR
    / "dynamic_weight_sensitivity_summary.csv"
)


# ============================================================
# Per-run Result
# ============================================================


@dataclass(frozen=True)
class SensitivityRunResult:
    alpha_min: float
    alpha_max: float
    seed: int

    generated_tasks: int
    completed_within_horizon: int
    completion_rate: float

    average_waiting_time_s: float
    p95_waiting_time_s: float

    average_source_arrival_time_s: float
    p95_source_arrival_time_s: float

    average_total_time_s: float
    p95_total_time_s: float

    average_robot_utilization: float
    max_robot_utilization: float

    jain_fairness: float

    total_approach_time_s: float
    total_task_travel_time_s: float
    total_travel_time_s: float

    busy_preassignment_rate: float


# ============================================================
# Summary Result
# ============================================================


@dataclass(frozen=True)
class SensitivitySummary:
    alpha_min: float
    alpha_max: float
    runs: int

    mean_completion_rate: float
    min_completion_rate: float

    mean_average_waiting_time_s: float
    mean_p95_waiting_time_s: float

    mean_average_source_arrival_time_s: float
    mean_p95_source_arrival_time_s: float

    mean_average_total_time_s: float
    mean_p95_total_time_s: float

    mean_average_robot_utilization: float
    mean_max_robot_utilization: float

    mean_jain_fairness: float

    mean_total_approach_time_s: float
    mean_total_task_travel_time_s: float
    mean_total_travel_time_s: float

    mean_busy_preassignment_rate: float

    std_p95_waiting_time_s: float
    std_total_travel_time_s: float


# ============================================================
# Jain Fairness
# ============================================================


def jain_fairness(
    values: Iterable[float],
) -> float:

    data = [
        float(value)
        for value
        in values
    ]

    if not data:
        return 1.0

    square_sum = sum(
        value * value
        for value
        in data
    )

    if square_sum == 0.0:
        return 1.0

    total = sum(
        data
    )

    return (
        total * total
        / (
            len(data)
            * square_sum
        )
    )


# ============================================================
# Travel Metrics
# ============================================================


def calculate_total_travel(
    result: SchedulingSimulationResult,
) -> tuple[
    float,
    float,
    float,
]:

    total_approach_time_s = sum(
        record.approach_time_s
        for record
        in result.assignments
    )

    total_task_travel_time_s = sum(
        record.task_travel_time_s
        for record
        in result.assignments
    )

    total_travel_time_s = (
        total_approach_time_s
        + total_task_travel_time_s
    )

    return (
        total_approach_time_s,
        total_task_travel_time_s,
        total_travel_time_s,
    )


# ============================================================
# Single Run
# ============================================================


def run_single(
    alpha_min: float,
    alpha_max: float,
    seed: int,
) -> SensitivityRunResult:

    scheduler = (
        DynamicWeightedScheduler(
            alpha_min=alpha_min,
            alpha_max=alpha_max,
        )
    )

    simulator = (
        SchedulingSimulator(
            fleet_configuration=(
                REFERENCE_FLEET
            ),

            seed=seed,

            workload_multiplier=(
                REFERENCE_WORKLOAD_MULTIPLIER
            ),

            scheduler=scheduler,
        )
    )

    result = simulator.run()

    metrics = calculate_metrics(
        result
    )

    (
        total_approach_time_s,
        total_task_travel_time_s,
        total_travel_time_s,
    ) = calculate_total_travel(
        result
    )

    fairness = jain_fairness(
        metrics.robot_utilization.values()
    )

    return SensitivityRunResult(
        alpha_min=alpha_min,
        alpha_max=alpha_max,
        seed=seed,

        generated_tasks=(
            metrics.generated_tasks
        ),

        completed_within_horizon=(
            metrics.completed_within_horizon
        ),

        completion_rate=(
            metrics.completion_rate
        ),

        average_waiting_time_s=(
            metrics.average_waiting_time_s
        ),

        p95_waiting_time_s=(
            metrics.p95_waiting_time_s
        ),

        average_source_arrival_time_s=(
            metrics.average_source_arrival_time_s
        ),

        p95_source_arrival_time_s=(
            metrics.p95_source_arrival_time_s
        ),

        average_total_time_s=(
            metrics.average_total_time_s
        ),

        p95_total_time_s=(
            metrics.p95_total_time_s
        ),

        average_robot_utilization=(
            metrics.average_robot_utilization
        ),

        max_robot_utilization=(
            metrics.max_robot_utilization
        ),

        jain_fairness=fairness,

        total_approach_time_s=(
            total_approach_time_s
        ),

        total_task_travel_time_s=(
            total_task_travel_time_s
        ),

        total_travel_time_s=(
            total_travel_time_s
        ),

        busy_preassignment_rate=(
            metrics.busy_preassignment_rate
        ),
    )


# ============================================================
# Run All
# ============================================================


def run_all() -> List[
    SensitivityRunResult
]:

    results: List[
        SensitivityRunResult
    ] = []

    total_runs = (
        len(ADAPTIVE_RANGES)
        * len(CALIBRATION_SEEDS)
    )

    run_index = 0

    print(
        "========================================"
    )

    print(
        "Dynamic Weighted Sensitivity Analysis"
    )

    print(
        "========================================"
    )

    print(
        "Fleet:",
        REFERENCE_FLEET,
    )

    print(
        "Workload multiplier:",
        REFERENCE_WORKLOAD_MULTIPLIER,
    )

    print(
        "Adaptive ranges:",
        ADAPTIVE_RANGES,
    )

    print(
        "Calibration seeds:",
        CALIBRATION_SEEDS,
    )

    print(
        "Total runs:",
        total_runs,
    )

    print()

    for (
        alpha_min,
        alpha_max,
    ) in ADAPTIVE_RANGES:

        for seed in CALIBRATION_SEEDS:

            run_index += 1

            print(
                f"[{run_index:02d}/{total_runs}] "
                f"range=[{alpha_min:.1f}, "
                f"{alpha_max:.1f}], "
                f"seed={seed}"
            )

            result = run_single(
                alpha_min=alpha_min,
                alpha_max=alpha_max,
                seed=seed,
            )

            results.append(
                result
            )

            print(
                "    completion="
                f"{result.completion_rate * 100:.2f}%"
                " | "
                "avg_wait="
                f"{result.average_waiting_time_s:.2f}s"
                " | "
                "p95_wait="
                f"{result.p95_waiting_time_s:.2f}s"
                " | "
                "travel="
                f"{result.total_travel_time_s:.2f}s"
                " | "
                "fairness="
                f"{result.jain_fairness:.4f}"
            )

    return results


# ============================================================
# Summary
# ============================================================


def summarize(
    results: List[
        SensitivityRunResult
    ],
) -> List[
    SensitivitySummary
]:

    summaries: List[
        SensitivitySummary
    ] = []

    for (
        alpha_min,
        alpha_max,
    ) in ADAPTIVE_RANGES:

        range_results = [
            result
            for result
            in results
            if (
                result.alpha_min
                == alpha_min
                and
                result.alpha_max
                == alpha_max
            )
        ]

        if not range_results:
            continue

        summaries.append(
            SensitivitySummary(
                alpha_min=alpha_min,
                alpha_max=alpha_max,

                runs=len(
                    range_results
                ),

                mean_completion_rate=mean(
                    result.completion_rate
                    for result
                    in range_results
                ),

                min_completion_rate=min(
                    result.completion_rate
                    for result
                    in range_results
                ),

                mean_average_waiting_time_s=mean(
                    result.average_waiting_time_s
                    for result
                    in range_results
                ),

                mean_p95_waiting_time_s=mean(
                    result.p95_waiting_time_s
                    for result
                    in range_results
                ),

                mean_average_source_arrival_time_s=mean(
                    result.average_source_arrival_time_s
                    for result
                    in range_results
                ),

                mean_p95_source_arrival_time_s=mean(
                    result.p95_source_arrival_time_s
                    for result
                    in range_results
                ),

                mean_average_total_time_s=mean(
                    result.average_total_time_s
                    for result
                    in range_results
                ),

                mean_p95_total_time_s=mean(
                    result.p95_total_time_s
                    for result
                    in range_results
                ),

                mean_average_robot_utilization=mean(
                    result.average_robot_utilization
                    for result
                    in range_results
                ),

                mean_max_robot_utilization=mean(
                    result.max_robot_utilization
                    for result
                    in range_results
                ),

                mean_jain_fairness=mean(
                    result.jain_fairness
                    for result
                    in range_results
                ),

                mean_total_approach_time_s=mean(
                    result.total_approach_time_s
                    for result
                    in range_results
                ),

                mean_total_task_travel_time_s=mean(
                    result.total_task_travel_time_s
                    for result
                    in range_results
                ),

                mean_total_travel_time_s=mean(
                    result.total_travel_time_s
                    for result
                    in range_results
                ),

                mean_busy_preassignment_rate=mean(
                    result.busy_preassignment_rate
                    for result
                    in range_results
                ),

                std_p95_waiting_time_s=pstdev(
                    result.p95_waiting_time_s
                    for result
                    in range_results
                ),

                std_total_travel_time_s=pstdev(
                    result.total_travel_time_s
                    for result
                    in range_results
                ),
            )
        )

    return summaries


# ============================================================
# CSV Writers
# ============================================================


def write_runs_csv(
    results: List[
        SensitivityRunResult
    ],
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(
        SensitivityRunResult
        .__dataclass_fields__
        .keys()
    )

    with RUNS_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:

            writer.writerow(
                {
                    field:
                    getattr(
                        result,
                        field,
                    )
                    for field
                    in fieldnames
                }
            )


def write_summary_csv(
    summaries: List[
        SensitivitySummary
    ],
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(
        SensitivitySummary
        .__dataclass_fields__
        .keys()
    )

    with SUMMARY_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for summary in summaries:

            writer.writerow(
                {
                    field:
                    getattr(
                        summary,
                        field,
                    )
                    for field
                    in fieldnames
                }
            )


# ============================================================
# Console Summary
# ============================================================


def print_summary_table(
    summaries: List[
        SensitivitySummary
    ],
) -> None:

    print()

    print(
        "=================================================================="
    )

    print(
        "Dynamic Weighted Sensitivity Summary"
    )

    print(
        "=================================================================="
    )

    print(
        f"{'range':>11} "
        f"{'comp%':>8} "
        f"{'min%':>8} "
        f"{'avgWait':>10} "
        f"{'p95Wait':>10} "
        f"{'travel':>12} "
        f"{'maxUtil%':>10} "
        f"{'fairness':>10}"
    )

    for summary in summaries:

        range_text = (
            f"[{summary.alpha_min:.1f},"
            f"{summary.alpha_max:.1f}]"
        )

        print(
            f"{range_text:>11} "
            f"{summary.mean_completion_rate * 100:>8.2f} "
            f"{summary.min_completion_rate * 100:>8.2f} "
            f"{summary.mean_average_waiting_time_s:>10.2f} "
            f"{summary.mean_p95_waiting_time_s:>10.2f} "
            f"{summary.mean_total_travel_time_s:>12.2f} "
            f"{summary.mean_max_robot_utilization * 100:>10.2f} "
            f"{summary.mean_jain_fairness:>10.4f}"
        )

    print()

    print(
        "Runs CSV:"
    )

    print(
        RUNS_CSV
    )

    print(
        "Summary CSV:"
    )

    print(
        SUMMARY_CSV
    )


# ============================================================
# Main
# ============================================================


def main() -> None:

    results = run_all()

    summaries = summarize(
        results
    )

    write_runs_csv(
        results
    )

    write_summary_csv(
        summaries
    )

    print_summary_table(
        summaries
    )


if __name__ == "__main__":
    main()