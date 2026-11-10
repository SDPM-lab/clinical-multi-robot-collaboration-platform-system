from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.config import (
    REFERENCE_FLEET,
    REFERENCE_WORKLOAD_MULTIPLIER,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
)


# ============================================================
# Configuration
# ============================================================

ADAPTIVE_RANGES = (
    (0.5, 0.7),
    (0.4, 0.8),
    (0.6, 0.8),
    (0.5, 0.9),
    (0.7, 0.9),
)

CALIBRATION_SEEDS = tuple(
    range(2001, 2011)
)

PRIORITY_HIGH = 2
PRIORITY_EMERGENCY = 3

RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
)

RUNS_CSV = (
    RESULTS_DIR
    / "dynamic_weight_priority_runs.csv"
)

SUMMARY_CSV = (
    RESULTS_DIR
    / "dynamic_weight_priority_summary.csv"
)


# ============================================================
# Helpers
# ============================================================


def percentile(
    values: Iterable[float],
    q: float,
) -> float:

    data = sorted(
        float(value)
        for value in values
    )

    if not data:
        return 0.0

    if len(data) == 1:
        return data[0]

    position = (
        (len(data) - 1)
        * q
    )

    lower = int(position)
    upper = min(
        lower + 1,
        len(data) - 1,
    )

    fraction = (
        position - lower
    )

    return (
        data[lower]
        * (1.0 - fraction)
        +
        data[upper]
        * fraction
    )


def calculate_waiting_times(
    tasks,
    accepted_priorities: set[int],
) -> list[float]:

    waits = []

    for task in tasks:

        if (
            task.priority
            not in accepted_priorities
        ):
            continue

        if task.start_time_s is None:
            continue

        waits.append(
            max(
                0.0,
                task.start_time_s
                - task.arrival_time_s,
            )
        )

    return waits


def calculate_source_response_times(
    tasks,
    accepted_priorities: set[int],
) -> list[float]:

    values = []

    for task in tasks:

        if (
            task.priority
            not in accepted_priorities
        ):
            continue

        if (
            task.source_arrival_time_s
            is None
        ):
            continue

        values.append(
            max(
                0.0,
                task.source_arrival_time_s
                - task.arrival_time_s,
            )
        )

    return values


# ============================================================
# Result Models
# ============================================================


@dataclass(frozen=True)
class PriorityRunResult:
    alpha_min: float
    alpha_max: float
    seed: int

    emergency_count: int

    emergency_avg_wait_s: float
    emergency_p95_wait_s: float

    emergency_avg_source_response_s: float
    emergency_p95_source_response_s: float

    high_emergency_count: int

    high_emergency_avg_wait_s: float
    high_emergency_p95_wait_s: float

    high_emergency_avg_source_response_s: float
    high_emergency_p95_source_response_s: float


@dataclass(frozen=True)
class PrioritySummary:
    alpha_min: float
    alpha_max: float
    runs: int

    mean_emergency_count: float

    mean_emergency_avg_wait_s: float
    mean_emergency_p95_wait_s: float

    mean_emergency_avg_source_response_s: float
    mean_emergency_p95_source_response_s: float

    mean_high_emergency_count: float

    mean_high_emergency_avg_wait_s: float
    mean_high_emergency_p95_wait_s: float

    mean_high_emergency_avg_source_response_s: float
    mean_high_emergency_p95_source_response_s: float


# ============================================================
# Single Run
# ============================================================


def run_single(
    alpha_min: float,
    alpha_max: float,
    seed: int,
) -> PriorityRunResult:

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

    emergency_priorities = {
        PRIORITY_EMERGENCY
    }

    high_emergency_priorities = {
        PRIORITY_HIGH,
        PRIORITY_EMERGENCY,
    }

    emergency_tasks = [
        task
        for task in result.tasks
        if (
            task.priority
            == PRIORITY_EMERGENCY
        )
    ]

    high_emergency_tasks = [
        task
        for task in result.tasks
        if (
            task.priority
            in high_emergency_priorities
        )
    ]

    emergency_waits = (
        calculate_waiting_times(
            result.tasks,
            emergency_priorities,
        )
    )

    emergency_source = (
        calculate_source_response_times(
            result.tasks,
            emergency_priorities,
        )
    )

    high_emergency_waits = (
        calculate_waiting_times(
            result.tasks,
            high_emergency_priorities,
        )
    )

    high_emergency_source = (
        calculate_source_response_times(
            result.tasks,
            high_emergency_priorities,
        )
    )

    return PriorityRunResult(
        alpha_min=alpha_min,
        alpha_max=alpha_max,
        seed=seed,

        emergency_count=len(
            emergency_tasks
        ),

        emergency_avg_wait_s=(
            mean(emergency_waits)
            if emergency_waits
            else 0.0
        ),

        emergency_p95_wait_s=(
            percentile(
                emergency_waits,
                0.95,
            )
        ),

        emergency_avg_source_response_s=(
            mean(emergency_source)
            if emergency_source
            else 0.0
        ),

        emergency_p95_source_response_s=(
            percentile(
                emergency_source,
                0.95,
            )
        ),

        high_emergency_count=len(
            high_emergency_tasks
        ),

        high_emergency_avg_wait_s=(
            mean(high_emergency_waits)
            if high_emergency_waits
            else 0.0
        ),

        high_emergency_p95_wait_s=(
            percentile(
                high_emergency_waits,
                0.95,
            )
        ),

        high_emergency_avg_source_response_s=(
            mean(high_emergency_source)
            if high_emergency_source
            else 0.0
        ),

        high_emergency_p95_source_response_s=(
            percentile(
                high_emergency_source,
                0.95,
            )
        ),
    )


# ============================================================
# Run All
# ============================================================


def run_all() -> list[
    PriorityRunResult
]:

    results = []

    total_runs = (
        len(ADAPTIVE_RANGES)
        * len(CALIBRATION_SEEDS)
    )

    run_index = 0

    print(
        "========================================"
    )
    print(
        "Dynamic Weighted Priority Check"
    )
    print(
        "========================================"
    )

    for (
        alpha_min,
        alpha_max,
    ) in ADAPTIVE_RANGES:

        for seed in CALIBRATION_SEEDS:

            run_index += 1

            print(
                f"[{run_index:02d}/{total_runs}] "
                f"range=[{alpha_min:.1f},"
                f"{alpha_max:.1f}] "
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
                "    Emergency:"
                f" avg={result.emergency_avg_wait_s:.2f}s"
                f" p95={result.emergency_p95_wait_s:.2f}s"
                " | High+:"
                f" avg={result.high_emergency_avg_wait_s:.2f}s"
                f" p95={result.high_emergency_p95_wait_s:.2f}s"
            )

    return results


# ============================================================
# Summary
# ============================================================


def summarize(
    results: list[
        PriorityRunResult
    ],
) -> list[
    PrioritySummary
]:

    summaries = []

    for (
        alpha_min,
        alpha_max,
    ) in ADAPTIVE_RANGES:

        group = [
            result
            for result in results
            if (
                result.alpha_min
                == alpha_min
                and
                result.alpha_max
                == alpha_max
            )
        ]

        summaries.append(
            PrioritySummary(
                alpha_min=alpha_min,
                alpha_max=alpha_max,
                runs=len(group),

                mean_emergency_count=mean(
                    r.emergency_count
                    for r in group
                ),

                mean_emergency_avg_wait_s=mean(
                    r.emergency_avg_wait_s
                    for r in group
                ),

                mean_emergency_p95_wait_s=mean(
                    r.emergency_p95_wait_s
                    for r in group
                ),

                mean_emergency_avg_source_response_s=mean(
                    r.emergency_avg_source_response_s
                    for r in group
                ),

                mean_emergency_p95_source_response_s=mean(
                    r.emergency_p95_source_response_s
                    for r in group
                ),

                mean_high_emergency_count=mean(
                    r.high_emergency_count
                    for r in group
                ),

                mean_high_emergency_avg_wait_s=mean(
                    r.high_emergency_avg_wait_s
                    for r in group
                ),

                mean_high_emergency_p95_wait_s=mean(
                    r.high_emergency_p95_wait_s
                    for r in group
                ),

                mean_high_emergency_avg_source_response_s=mean(
                    r.high_emergency_avg_source_response_s
                    for r in group
                ),

                mean_high_emergency_p95_source_response_s=mean(
                    r.high_emergency_p95_source_response_s
                    for r in group
                ),
            )
        )

    return summaries


# ============================================================
# CSV
# ============================================================


def write_csv(
    path: Path,
    rows,
    model_class,
) -> None:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(
        model_class
        .__dataclass_fields__
        .keys()
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                {
                    field:
                    getattr(
                        row,
                        field,
                    )
                    for field
                    in fieldnames
                }
            )


# ============================================================
# Console Summary
# ============================================================


def print_summary(
    summaries: list[
        PrioritySummary
    ],
) -> None:

    print()
    print(
        "=============================================================="
    )
    print(
        "Priority-Aware Summary"
    )
    print(
        "=============================================================="
    )

    print(
        f"{'range':>11} "
        f"{'E-Avg':>9} "
        f"{'E-P95':>9} "
        f"{'E-Src95':>9} "
        f"{'H+-Avg':>9} "
        f"{'H+-P95':>9} "
        f"{'H+-Src95':>10}"
    )

    for summary in summaries:

        range_text = (
            f"[{summary.alpha_min:.1f},"
            f"{summary.alpha_max:.1f}]"
        )

        print(
            f"{range_text:>11} "
            f"{summary.mean_emergency_avg_wait_s:>9.2f} "
            f"{summary.mean_emergency_p95_wait_s:>9.2f} "
            f"{summary.mean_emergency_p95_source_response_s:>9.2f} "
            f"{summary.mean_high_emergency_avg_wait_s:>9.2f} "
            f"{summary.mean_high_emergency_p95_wait_s:>9.2f} "
            f"{summary.mean_high_emergency_p95_source_response_s:>10.2f}"
        )


# ============================================================
# Main
# ============================================================


def main() -> None:

    results = run_all()

    summaries = summarize(
        results
    )

    write_csv(
        RUNS_CSV,
        results,
        PriorityRunResult,
    )

    write_csv(
        SUMMARY_CSV,
        summaries,
        PrioritySummary,
    )

    print_summary(
        summaries
    )

    print()
    print(
        "Runs CSV:",
        RUNS_CSV,
    )
    print(
        "Summary CSV:",
        SUMMARY_CSV,
    )


if __name__ == "__main__":
    main()