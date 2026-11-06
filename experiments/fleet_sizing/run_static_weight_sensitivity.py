from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, List

from experiments.fleet_sizing.baseline.static_weighted import (
    StaticWeightedScheduler,
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

ALPHAS = (
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
)

# Important:
# These seeds are used ONLY for Static Weighted calibration.
# Do not reuse the final formal evaluation seeds here.
CALIBRATION_SEEDS = tuple(
    range(
        1001,
        1011,
    )
)

RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
)

RUNS_CSV = (
    RESULTS_DIR
    / "static_weight_sensitivity_runs.csv"
)

SUMMARY_CSV = (
    RESULTS_DIR
    / "static_weight_sensitivity_summary.csv"
)


# ============================================================
# Per-run Result
# ============================================================


@dataclass(frozen=True)
class SensitivityRunResult:
    alpha: float
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
    alpha: float
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
    """
    Jain's fairness index:

        J(x)
        =
        (sum(x))^2
        /
        (n * sum(x^2))

    Range:
        0 < J <= 1

    1.0 means perfectly balanced.

    Here x is per-robot utilization.
    """

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
    """
    Returns:

        total_approach_time
        total_task_travel_time
        total_travel_time

    total_travel =
        robot -> source
        +
        source -> destination
    """

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
    alpha: float,
    seed: int,
) -> SensitivityRunResult:

    scheduler = (
        StaticWeightedScheduler(
            alpha=alpha
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
        alpha=alpha,
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
        len(ALPHAS)
        * len(CALIBRATION_SEEDS)
    )

    run_index = 0

    print(
        "========================================"
    )

    print(
        "Static Weighted Sensitivity Analysis"
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
        "Alphas:",
        ALPHAS,
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

    for alpha in ALPHAS:

        for seed in CALIBRATION_SEEDS:

            run_index += 1

            print(
                f"[{run_index:02d}/{total_runs}] "
                f"alpha={alpha:.1f}, "
                f"seed={seed}"
            )

            result = run_single(
                alpha=alpha,
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

    for alpha in ALPHAS:

        alpha_results = [
            result
            for result
            in results
            if result.alpha == alpha
        ]

        if not alpha_results:
            continue

        summaries.append(
            SensitivitySummary(
                alpha=alpha,

                runs=len(
                    alpha_results
                ),

                mean_completion_rate=mean(
                    result.completion_rate
                    for result
                    in alpha_results
                ),

                min_completion_rate=min(
                    result.completion_rate
                    for result
                    in alpha_results
                ),

                mean_average_waiting_time_s=mean(
                    result.average_waiting_time_s
                    for result
                    in alpha_results
                ),

                mean_p95_waiting_time_s=mean(
                    result.p95_waiting_time_s
                    for result
                    in alpha_results
                ),

                mean_average_source_arrival_time_s=mean(
                    result.average_source_arrival_time_s
                    for result
                    in alpha_results
                ),

                mean_p95_source_arrival_time_s=mean(
                    result.p95_source_arrival_time_s
                    for result
                    in alpha_results
                ),

                mean_average_total_time_s=mean(
                    result.average_total_time_s
                    for result
                    in alpha_results
                ),

                mean_p95_total_time_s=mean(
                    result.p95_total_time_s
                    for result
                    in alpha_results
                ),

                mean_average_robot_utilization=mean(
                    result.average_robot_utilization
                    for result
                    in alpha_results
                ),

                mean_max_robot_utilization=mean(
                    result.max_robot_utilization
                    for result
                    in alpha_results
                ),

                mean_jain_fairness=mean(
                    result.jain_fairness
                    for result
                    in alpha_results
                ),

                mean_total_approach_time_s=mean(
                    result.total_approach_time_s
                    for result
                    in alpha_results
                ),

                mean_total_task_travel_time_s=mean(
                    result.total_task_travel_time_s
                    for result
                    in alpha_results
                ),

                mean_total_travel_time_s=mean(
                    result.total_travel_time_s
                    for result
                    in alpha_results
                ),

                mean_busy_preassignment_rate=mean(
                    result.busy_preassignment_rate
                    for result
                    in alpha_results
                ),

                std_p95_waiting_time_s=pstdev(
                    result.p95_waiting_time_s
                    for result
                    in alpha_results
                ),

                std_total_travel_time_s=pstdev(
                    result.total_travel_time_s
                    for result
                    in alpha_results
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
        "============================================================"
    )

    print(
        "Sensitivity Summary"
    )

    print(
        "============================================================"
    )

    print(
        f"{'alpha':>5} "
        f"{'comp%':>8} "
        f"{'min%':>8} "
        f"{'avgWait':>10} "
        f"{'p95Wait':>10} "
        f"{'travel':>12} "
        f"{'maxUtil%':>10} "
        f"{'fairness':>10}"
    )

    for summary in summaries:

        print(
            f"{summary.alpha:>5.1f} "
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