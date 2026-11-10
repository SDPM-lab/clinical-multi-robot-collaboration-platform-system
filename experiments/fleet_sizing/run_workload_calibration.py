from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import List

from simulator import FleetSizingSimulator
from metrics import calculate_metrics


REFERENCE_FLEET = (1, 1, 1)

MULTIPLIERS = [
    0.5,
    1.0,
    2.0,
    3.0,
    4.0,
    6.0,
    8.0,
    10.0,
]

REPLICATIONS = 30


@dataclass
class CalibrationResult:
    multiplier: float

    average_tasks_per_day: float

    mean_completion_rate: float
    min_completion_rate: float

    mean_waiting_time_s: float
    mean_p95_waiting_time_s: float

    mean_response_time_s: float
    mean_p95_response_time_s: float

    mean_max_utilization: float


def run_multiplier(
    multiplier: float,
) -> CalibrationResult:

    completion_rates = []
    waiting_times = []
    p95_waiting_times = []

    response_times = []
    p95_response_times = []

    max_utilizations = []

    task_counts = []

    for seed in range(REPLICATIONS):

        simulator = FleetSizingSimulator(
            fleet_configuration=(
                REFERENCE_FLEET
            ),
            seed=seed,
            workload_multiplier=multiplier,
        )

        result = simulator.run()

        metrics = calculate_metrics(
            result
        )

        completion_rates.append(
            metrics.completion_rate
        )

        waiting_times.append(
            metrics.average_waiting_time_s
        )

        p95_waiting_times.append(
            metrics.p95_waiting_time_s
        )

        response_times.append(
            metrics.average_source_arrival_time_s
        )

        p95_response_times.append(
            metrics.p95_source_arrival_time_s
        )

        max_utilizations.append(
            metrics.max_robot_utilization
        )

        task_counts.append(
            metrics.generated_tasks / 7.0
        )

    return CalibrationResult(
        multiplier=multiplier,

        average_tasks_per_day=mean(
            task_counts
        ),

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

        mean_response_time_s=mean(
            response_times
        ),

        mean_p95_response_time_s=mean(
            p95_response_times
        ),

        mean_max_utilization=mean(
            max_utilizations
        ),
    )


def main():

    results: List[CalibrationResult] = []

    for multiplier in MULTIPLIERS:

        print(
            f"Running workload "
            f"{multiplier:.1f}x ..."
        )

        result = run_multiplier(
            multiplier
        )

        results.append(result)

    print()
    print("=" * 115)
    print("WORKLOAD CALIBRATION")
    print("=" * 115)

    print(
        f"{'Load':<8}"
        f"{'Tasks/day':>12}"
        f"{'Mean Comp':>13}"
        f"{'Min Comp':>12}"
        f"{'Avg Wait':>12}"
        f"{'P95 Wait':>12}"
        f"{'Avg Resp':>12}"
        f"{'P95 Resp':>12}"
        f"{'Max Util':>12}"
    )

    print("-" * 115)

    for r in results:

        print(
            f"{r.multiplier:<8.1f}"
            f"{r.average_tasks_per_day:>12.1f}"
            f"{r.mean_completion_rate * 100:>12.2f}%"
            f"{r.min_completion_rate * 100:>11.2f}%"
            f"{r.mean_waiting_time_s:>11.1f}s"
            f"{r.mean_p95_waiting_time_s:>11.1f}s"
            f"{r.mean_response_time_s:>11.1f}s"
            f"{r.mean_p95_response_time_s:>11.1f}s"
            f"{r.mean_max_utilization * 100:>11.2f}%"
        )


if __name__ == "__main__":
    main()