#!/usr/bin/env python3

import argparse

from dataclasses import (
    dataclass,
)

from experiment_v2.metrics import (
    ExperimentMetrics,
    calculate_metrics,
)

from experiment_v2.models import (
    BaselineMethod,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from experiment_v2.simulator import (
    run_static_simulation,
)


# ==========================================================
# Result
# ==========================================================

@dataclass(frozen=True)
class BaselineRunResult:

    method: str

    metrics: ExperimentMetrics


# ==========================================================
# Run All Static Baselines
# ==========================================================

def run_all_static_baselines(
    seed: int,
    task_count: int = 50,
) -> list[BaselineRunResult]:
    """
    使用同一個 Scenario，
    分別執行三個 Static Baseline。
    """

    scenario = (
        generate_hospital_scenario(
            seed=seed,
            task_count=task_count,
        )
    )

    methods = [
        BaselineMethod
        .RANDOM_FEASIBLE,

        BaselineMethod
        .PROJECTED_NEAREST,

        BaselineMethod
        .WEIGHTED_HEURISTIC,
    ]

    results = []

    for method in methods:

        simulation_result = (
            run_static_simulation(
                scenario=scenario,
                method=method,

                # Random Feasible 使用此 seed。
                #
                # Nearest / Weighted 雖然不使用 RNG，
                # 仍統一傳入相同 seed。
                seed=seed,
            )
        )

        metrics = (
            calculate_metrics(
                simulation_result
            )
        )

        results.append(
            BaselineRunResult(
                method=method.value,
                metrics=metrics,
            )
        )

    return results


# ==========================================================
# Formatting
# ==========================================================

def format_optional(
    value: float | None,
) -> str:

    if value is None:

        return "N/A"

    return f"{value:.3f}"


def print_results(
    results: list[BaselineRunResult],
) -> None:

    print()

    print(
        "=" * 130
    )

    print(
        "STATIC BASELINE COMPARISON"
    )

    print(
        "=" * 130
    )

    header = (
        f"{'Method':<24}"
        f"{'Wait(s)':>12}"
        f"{'Emergency(s)':>16}"
        f"{'Completion(s)':>16}"
        f"{'Makespan(s)':>14}"
        f"{'Distance':>12}"
        f"{'Success':>10}"
        f"{'Jain':>10}"
        f"{'Decision(ms)':>16}"
    )

    print(
        header
    )

    print(
        "-" * 130
    )

    for result in results:

        metrics = (
            result.metrics
        )

        emergency_wait = (
            metrics
            .waiting_time_by_priority[
                3
            ]
        )

        print(
            f"{result.method:<24}"
            f"{format_optional(metrics.average_task_waiting_time):>12}"
            f"{format_optional(emergency_wait):>16}"
            f"{format_optional(metrics.average_task_completion_time):>16}"
            f"{format_optional(metrics.makespan):>14}"
            f"{metrics.total_travel_distance:>12.3f}"
            f"{metrics.task_success_rate:>10.3f}"
            f"{metrics.jain_fairness_index:>10.3f}"
            f"{metrics.average_decision_time_seconds * 1000.0:>16.3f}"
        )

    print(
        "=" * 130
    )


# ==========================================================
# CLI
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run Scheduler v2 "
            "Static Baseline comparison."
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=8000,
    )

    parser.add_argument(
        "--tasks",
        type=int,
        default=50,
    )

    args = parser.parse_args()

    results = (
        run_all_static_baselines(
            seed=args.seed,
            task_count=args.tasks,
        )
    )

    print_results(
        results
    )


if __name__ == "__main__":

    main()