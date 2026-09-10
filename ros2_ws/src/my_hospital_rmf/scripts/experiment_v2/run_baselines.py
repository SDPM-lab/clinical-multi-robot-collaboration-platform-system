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
    run_dynamic_weighted_simulation,
    run_static_simulation,
)


# ==========================================================
# Methods
# ==========================================================

BASELINE_METHODS = [
    BaselineMethod.RANDOM_FEASIBLE,
    BaselineMethod.PROJECTED_NEAREST,
    BaselineMethod.WEIGHTED_HEURISTIC,
    BaselineMethod.DYNAMIC_WEIGHTED_HEURISTIC,
]


# ==========================================================
# Result
# ==========================================================

@dataclass(frozen=True)
class BaselineRunResult:

    method: str

    metrics: ExperimentMetrics


# ==========================================================
# Run One Baseline
# ==========================================================

def run_baseline(
    scenario,
    method: BaselineMethod,
    seed: int,
) -> BaselineRunResult:
    """
    在既定 Scenario 上執行一種 Baseline。

    Static：
        Random
        Projected Nearest
        Weighted

    Dynamic：
        Dynamic Weighted
    """

    if (
        method
        ==
        BaselineMethod
        .DYNAMIC_WEIGHTED_HEURISTIC
    ):

        simulation_result = (
            run_dynamic_weighted_simulation(
                scenario=scenario,
                seed=seed,
            )
        )

    else:

        simulation_result = (
            run_static_simulation(
                scenario=scenario,
                method=method,
                seed=seed,
            )
        )

    metrics = calculate_metrics(
        simulation_result
    )

    return BaselineRunResult(
        method=method.value,
        metrics=metrics,
    )


# ==========================================================
# Run All Baselines
# ==========================================================

def run_all_baselines(
    seed: int,
    task_count: int = 50,
) -> list[BaselineRunResult]:
    """
    使用完全相同的 Scenario
    執行四個 Baseline。

    這是 paired experiment 的必要條件。
    """

    scenario = (
        generate_hospital_scenario(
            seed=seed,
            task_count=task_count,
        )
    )

    return [
        run_baseline(
            scenario=scenario,
            method=method,
            seed=seed,
        )
        for method
        in BASELINE_METHODS
    ]


# ==========================================================
# Formatting
# ==========================================================

def format_optional(
    value: float | None,
) -> str:

    if value is None:

        return "N/A"

    return f"{value:.3f}"


# ==========================================================
# Print
# ==========================================================

def print_results(
    results: list[BaselineRunResult],
) -> None:

    print()

    print(
        "=" * 170
    )

    print(
        "BASELINE COMPARISON"
    )

    print(
        "=" * 170
    )

    print(
        f"{'Method':<28}"
        f"{'Wait(s)':>11}"
        f"{'Emer(s)':>11}"
        f"{'Complete(s)':>13}"
        f"{'Makespan':>12}"
        f"{'Distance':>12}"
        f"{'Success':>10}"
        f"{'Jain':>9}"
        f"{'Decision(ms)':>14}"
        f"{'ReDec':>9}"
        f"{'Reassign':>10}"
        f"{'ReRate':>10}"
        f"{'Max/T':>8}"
        f"{'Depth':>8}"
    )

    print(
        "-" * 170
    )

    for result in results:

        metrics = result.metrics

        emergency_wait = (
            metrics
            .waiting_time_by_priority
            .get(3)
        )

        print(
            f"{result.method:<28}"

            f"{format_optional(
                metrics
                .average_task_waiting_time
            ):>11}"

            f"{format_optional(
                emergency_wait
            ):>11}"

            f"{format_optional(
                metrics
                .average_task_completion_time
            ):>13}"

            f"{format_optional(
                metrics.makespan
            ):>12}"

            f"{metrics.total_travel_distance:>12.3f}"

            f"{metrics.task_success_rate:>10.3f}"

            f"{metrics.jain_fairness_index:>9.3f}"

            f"{(
                metrics
                .average_decision_time_seconds
                *
                1000.0
            ):>14.3f}"

            f"{metrics.reassignment_decision_count:>9}"

            f"{metrics.reassignment_count:>10}"

            f"{metrics.reassignment_rate:>10.3f}"

            f"{metrics.max_reassignments_per_task:>8}"

            f"{metrics.max_cascade_depth:>8}"
        )

    print(
        "=" * 170
    )


# ==========================================================
# CLI
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run Scheduler v2 "
            "Baseline comparison."
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

    results = run_all_baselines(
        seed=args.seed,
        task_count=args.tasks,
    )

    print_results(
        results
    )


if __name__ == "__main__":

    main()