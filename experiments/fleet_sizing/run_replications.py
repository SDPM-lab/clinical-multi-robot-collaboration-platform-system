from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, stdev
from math import sqrt
from typing import List, Tuple

from config import (
    INITIAL_REPLICATIONS,
)

from simulator import FleetSizingSimulator
from metrics import (
    SimulationMetrics,
    calculate_metrics,
)


@dataclass
class ReplicationSummary:
    fleet_configuration: Tuple[int, int, int]
    replications: int

    mean_completion_rate: float
    min_completion_rate: float

    mean_waiting_time_s: float
    mean_p95_waiting_time_s: float

    mean_source_arrival_time_s: float
    mean_p95_source_arrival_time_s: float

    mean_total_time_s: float
    mean_p95_total_time_s: float

    mean_robot_utilization: float
    mean_max_robot_utilization: float

    completion_rate_ci95_half_width: float
    source_arrival_ci95_half_width_s: float


def ci95_half_width(
    values: List[float],
) -> float:
    """
    95% confidence interval half-width.

    For >= 30 replications, use normal approximation:
        1.96 * s / sqrt(n)
    """

    if len(values) <= 1:
        return 0.0

    return (
        1.96
        * stdev(values)
        / sqrt(len(values))
    )


def run_replications(
    fleet_configuration: Tuple[int, int, int],
    replications: int = INITIAL_REPLICATIONS,
) -> ReplicationSummary:

    results: List[SimulationMetrics] = []

    for seed in range(replications):

        simulator = FleetSizingSimulator(
            fleet_configuration=fleet_configuration,
            seed=seed,
        )

        simulation_result = simulator.run()

        metrics = calculate_metrics(
            simulation_result
        )

        results.append(metrics)

        print(
            f"[{seed + 1:02d}/{replications}] "
            f"seed={seed} "
            f"completion={metrics.completion_rate * 100:.2f}% "
            f"avg_response="
            f"{metrics.average_source_arrival_time_s:.1f}s "
            f"p95_response="
            f"{metrics.p95_source_arrival_time_s:.1f}s "
            f"max_util="
            f"{metrics.max_robot_utilization * 100:.2f}%"
        )

    completion_rates = [
        m.completion_rate
        for m in results
    ]

    waiting_times = [
        m.average_waiting_time_s
        for m in results
    ]

    p95_waiting_times = [
        m.p95_waiting_time_s
        for m in results
    ]

    source_arrival_times = [
        m.average_source_arrival_time_s
        for m in results
    ]

    p95_source_arrival_times = [
        m.p95_source_arrival_time_s
        for m in results
    ]

    total_times = [
        m.average_total_time_s
        for m in results
    ]

    p95_total_times = [
        m.p95_total_time_s
        for m in results
    ]

    average_utilizations = [
        m.average_robot_utilization
        for m in results
    ]

    max_utilizations = [
        m.max_robot_utilization
        for m in results
    ]

    return ReplicationSummary(
        fleet_configuration=fleet_configuration,
        replications=replications,

        mean_completion_rate=mean(
            completion_rates
        ),

        min_completion_rate=min(
            completion_rates
        ),

        mean_waiting_time_s=mean(
            waiting_times
        ),

        mean_p95_waiting_time_s=mean(
            p95_waiting_times
        ),

        mean_source_arrival_time_s=mean(
            source_arrival_times
        ),

        mean_p95_source_arrival_time_s=mean(
            p95_source_arrival_times
        ),

        mean_total_time_s=mean(
            total_times
        ),

        mean_p95_total_time_s=mean(
            p95_total_times
        ),

        mean_robot_utilization=mean(
            average_utilizations
        ),

        mean_max_robot_utilization=mean(
            max_utilizations
        ),

        completion_rate_ci95_half_width=(
            ci95_half_width(
                completion_rates
            )
        ),

        source_arrival_ci95_half_width_s=(
            ci95_half_width(
                source_arrival_times
            )
        ),
    )


def print_summary(
    summary: ReplicationSummary,
) -> None:

    print()
    print("=" * 60)

    print(
        "Fleet:",
        summary.fleet_configuration,
    )

    print(
        "Replications:",
        summary.replications,
    )

    print("=" * 60)

    print(
        "Mean completion rate:",
        f"{summary.mean_completion_rate * 100:.3f}%"
    )

    print(
        "Minimum completion rate:",
        f"{summary.min_completion_rate * 100:.3f}%"
    )

    print(
        "Completion 95% CI half-width:",
        f"{summary.completion_rate_ci95_half_width * 100:.3f} percentage points"
    )

    print()

    print(
        "Mean average waiting time:",
        f"{summary.mean_waiting_time_s:.2f} s"
    )

    print(
        "Mean P95 waiting time:",
        f"{summary.mean_p95_waiting_time_s:.2f} s"
    )

    print()

    print(
        "Mean source-arrival time:",
        f"{summary.mean_source_arrival_time_s:.2f} s"
    )

    print(
        "Mean P95 source-arrival time:",
        f"{summary.mean_p95_source_arrival_time_s:.2f} s"
    )

    print(
        "Source-arrival 95% CI half-width:",
        f"{summary.source_arrival_ci95_half_width_s:.2f} s"
    )

    print()

    print(
        "Mean total task time:",
        f"{summary.mean_total_time_s:.2f} s"
    )

    print(
        "Mean P95 total task time:",
        f"{summary.mean_p95_total_time_s:.2f} s"
    )

    print()

    print(
        "Mean robot utilization:",
        f"{summary.mean_robot_utilization * 100:.2f}%"
    )

    print(
        "Mean maximum robot utilization:",
        f"{summary.mean_max_robot_utilization * 100:.2f}%"
    )


if __name__ == "__main__":

    summary = run_replications(
        fleet_configuration=(1, 1, 1),
        replications=INITIAL_REPLICATIONS,
    )

    print_summary(summary)