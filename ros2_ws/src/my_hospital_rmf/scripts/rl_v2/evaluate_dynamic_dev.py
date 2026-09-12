#!/usr/bin/env python3

import argparse
import csv
import statistics
import time

from collections import (
    defaultdict,
)

from pathlib import Path

import numpy as np

from sb3_contrib import (
    MaskablePPO,
)

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.run_baselines import (
    BASELINE_METHODS,
    BaselineRunResult,
    run_baseline,
)

from experiment_v2.run_multi_seed import (
    extract_metrics,
    summarize_values,
)

from experiment_v2.paired_statistics import (
    compare_paired_metric,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.evaluate_dev import (
    run_ppo_on_scenario,
)

from rl_v2.dynamic_env import (
    DynamicHospitalRLEnv,
)


STATIC_PPO_METHOD = (
    "static_long_horizon_ppo"
)

DYNAMIC_PPO_METHOD = (
    "dynamic_masked_ppo"
)


METHODS = [
    "random_feasible",
    "projected_nearest",
    "weighted_heuristic",
    "dynamic_weighted_heuristic",
    STATIC_PPO_METHOD,
    DYNAMIC_PPO_METHOD,
]


PRIMARY_METRICS = [
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
]


# ==========================================================
# Dynamic PPO
# ==========================================================

def run_dynamic_ppo(
    model,
    scenario,
    seed: int,
):

    env = DynamicHospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = (
        env.reset(
            seed=seed
        )
    )

    terminated = False
    truncated = False

    decision_times = []

    assignment_decisions = 0
    reassignment_decisions = 0
    actual_reassignments = 0

    while not (
        terminated
        or
        truncated
    ):

        decision_start = (
            time.perf_counter()
        )

        mask = (
            env.action_masks()
        )

        action, _ = (
            model.predict(
                observation,
                action_masks=mask,
                deterministic=True,
            )
        )

        decision_duration = (
            time.perf_counter()
            -
            decision_start
        )

        decision_times.append(
            decision_duration
        )

        action = int(
            np.asarray(
                action
            )
            .reshape(-1)[0]
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        if (
            info["decision_type"]
            ==
            "assignment"
        ):

            assignment_decisions += 1

        elif (
            info["decision_type"]
            ==
            "reassignment"
        ):

            reassignment_decisions += 1

            if info["changed"]:

                actual_reassignments += 1

    result = (
        env.get_simulation_result()
    )

    metrics = (
        calculate_metrics(
            result
        )
    )

    values = extract_metrics(
        BaselineRunResult(
            method=(
                DYNAMIC_PPO_METHOD
            ),
            metrics=metrics,
        )
    )

    if decision_times:

        values[
            "decision_time_ms"
        ] = (
            statistics.mean(
                decision_times
            )
            *
            1000.0
        )

    values[
        "total_decisions"
    ] = float(
        metrics.total_decisions
    )

    values[
        "assignment_decisions"
    ] = float(
        assignment_decisions
    )

    # 另外存一次實際 loop count，
    # 應與 Metrics 對得上。
    values[
        "policy_reassignment_decisions"
    ] = float(
        reassignment_decisions
    )

    values[
        "policy_actual_reassignments"
    ] = float(
        actual_reassignments
    )

    return values


# ==========================================================
# Static PPO
# ==========================================================

def run_static_ppo(
    model,
    scenario,
    seed: int,
):

    (
        result,
        decision_time_ms,
    ) = run_ppo_on_scenario(
        model=model,
        scenario=scenario,
        seed=seed,
    )

    values = extract_metrics(
        result
    )

    values[
        "decision_time_ms"
    ] = decision_time_ms

    values[
        "total_decisions"
    ] = float(
        result
        .metrics
        .total_decisions
    )

    values[
        "assignment_decisions"
    ] = float(
        result
        .metrics
        .total_decisions
    )

    values[
        "policy_reassignment_decisions"
    ] = 0.0

    values[
        "policy_actual_reassignments"
    ] = 0.0

    return values


# ==========================================================
# Baseline
# ==========================================================

def baseline_values(
    scenario,
    method,
    seed: int,
):

    result = run_baseline(
        scenario=scenario,
        method=method,
        seed=seed,
    )

    values = extract_metrics(
        result
    )

    values[
        "total_decisions"
    ] = float(
        result
        .metrics
        .total_decisions
    )

    values[
        "assignment_decisions"
    ] = float(
        result
        .metrics
        .total_tasks
    )

    values[
        "policy_reassignment_decisions"
    ] = float(
        result
        .metrics
        .reassignment_decision_count
    )

    values[
        "policy_actual_reassignments"
    ] = float(
        result
        .metrics
        .reassignment_count
    )

    return (
        result.method,
        values,
    )


# ==========================================================
# Multi Seed
# ==========================================================

def run_evaluation(
    dynamic_model,
    static_model,
    seed_start: int,
    seed_end: int,
    task_count: int,
):

    raw_results = defaultdict(
        lambda: defaultdict(list)
    )

    rows = []

    total = (
        seed_end
        -
        seed_start
        +
        1
    )

    for index, seed in enumerate(
        range(
            seed_start,
            seed_end + 1,
        ),
        start=1,
    ):

        print(
            f"[{index:>3}/{total}] "
            f"seed={seed}"
        )

        scenario = (
            generate_hospital_scenario(
                seed=seed,
                task_count=task_count,
            )
        )

        seed_results = []

        # --------------------------------------------------
        # Four Baselines
        # --------------------------------------------------

        for method in BASELINE_METHODS:

            seed_results.append(
                baseline_values(
                    scenario=scenario,
                    method=method,
                    seed=seed,
                )
            )

        # --------------------------------------------------
        # Static Long-Horizon PPO
        # --------------------------------------------------

        static_values = (
            run_static_ppo(
                model=static_model,
                scenario=scenario,
                seed=seed,
            )
        )

        seed_results.append(
            (
                STATIC_PPO_METHOD,
                static_values,
            )
        )

        # --------------------------------------------------
        # Dynamic PPO
        # --------------------------------------------------

        dynamic_values = (
            run_dynamic_ppo(
                model=dynamic_model,
                scenario=scenario,
                seed=seed,
            )
        )

        seed_results.append(
            (
                DYNAMIC_PPO_METHOD,
                dynamic_values,
            )
        )

        # --------------------------------------------------
        # Store
        # --------------------------------------------------

        for (
            method_name,
            values,
        ) in seed_results:

            row = {
                "seed": seed,
                "method": method_name,
                **values,
            }

            rows.append(
                row
            )

            for (
                metric_name,
                value,
            ) in values.items():

                if value is None:
                    continue

                raw_results[
                    method_name
                ][
                    metric_name
                ].append(
                    float(value)
                )

    return (
        raw_results,
        rows,
    )


# ==========================================================
# Compact
# ==========================================================

def mean_value(
    raw_results,
    method,
    metric,
):

    values = (
        raw_results[
            method
        ][
            metric
        ]
    )

    if not values:
        return float("nan")

    return statistics.mean(
        values
    )


def print_compact(
    raw_results,
):

    print()
    print(
        "=" * 130
    )

    print(
        "DYNAMIC PPO DEVELOPMENT TABLE"
    )

    print(
        "=" * 130
    )

    print(
        f"{'Method':<30}"
        f"{'Wait':>10}"
        f"{'Emer':>10}"
        f"{'Complete':>11}"
        f"{'Makespan':>11}"
        f"{'Distance':>11}"
        f"{'Success':>9}"
        f"{'Jain':>9}"
        f"{'Dec(ms)':>10}"
        f"{'ReDec':>9}"
        f"{'Reassign':>10}"
    )

    print(
        "-" * 130
    )

    for method in METHODS:

        print(
            f"{method:<30}"

            f"{mean_value(
                raw_results,
                method,
                'waiting_time',
            ):>10.3f}"

            f"{mean_value(
                raw_results,
                method,
                'emergency_waiting_time',
            ):>10.3f}"

            f"{mean_value(
                raw_results,
                method,
                'completion_time',
            ):>11.3f}"

            f"{mean_value(
                raw_results,
                method,
                'makespan',
            ):>11.3f}"

            f"{mean_value(
                raw_results,
                method,
                'travel_distance',
            ):>11.3f}"

            f"{mean_value(
                raw_results,
                method,
                'success_rate',
            ):>9.3f}"

            f"{mean_value(
                raw_results,
                method,
                'jain_fairness',
            ):>9.3f}"

            f"{mean_value(
                raw_results,
                method,
                'decision_time_ms',
            ):>10.3f}"

            f"{mean_value(
                raw_results,
                method,
                'reassignment_decisions',
            ):>9.1f}"

            f"{mean_value(
                raw_results,
                method,
                'reassignment_count',
            ):>10.1f}"
        )

    print(
        "=" * 130
    )


# ==========================================================
# Dynamic Diagnostics
# ==========================================================

def print_dynamic_diagnostics(
    raw_results,
):

    print()
    print(
        "=" * 105
    )

    print(
        "DYNAMIC REASSIGNMENT DIAGNOSTICS"
    )

    print(
        "=" * 105
    )

    diagnostics = [
        "total_decisions",
        "reassignment_decisions",
        "reassignment_count",
        "reassignment_rate",
        "average_reassignments_per_task",
        "max_reassignments_per_task",
        "max_cascade_depth",
    ]

    for method in [
        "dynamic_weighted_heuristic",
        DYNAMIC_PPO_METHOD,
    ]:

        print()
        print(
            method
        )

        print(
            "-" * 105
        )

        print(
            f"{'Metric':<38}"
            f"{'Mean':>15}"
            f"{'Std':>15}"
            f"{'Median':>15}"
        )

        for metric in diagnostics:

            values = (
                raw_results[
                    method
                ][
                    metric
                ]
            )

            summary = (
                summarize_values(
                    values
                )
            )

            print(
                f"{metric:<38}"
                f"{summary['mean']:>15.3f}"
                f"{summary['std']:>15.3f}"
                f"{summary['median']:>15.3f}"
            )

    print(
        "=" * 105
    )


# ==========================================================
# Paired
# ==========================================================

def print_paired(
    rows,
):

    comparisons = [
        (
            DYNAMIC_PPO_METHOD,
            "dynamic_weighted_heuristic",
        ),
        (
            DYNAMIC_PPO_METHOD,
            STATIC_PPO_METHOD,
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
        "=" * 135
    )

    print(
        "DYNAMIC PPO PAIRED COMPARISON"
    )

    print(
        "=" * 135
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
            "-" * 135
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
                p_text = "N/A"

            elif result.p_value < 1e-6:
                p_text = "<1e-6"

            else:
                p_text = (
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
                f"{p_text:>14}"
            )

    print(
        "=" * 135
    )


# ==========================================================
# CSV
# ==========================================================

def save_csv(
    rows,
    output_path,
):

    output = Path(
        output_path
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not rows:
        return

    fieldnames = list(
        rows[0].keys()
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )

    print(
        f"CSV saved: {output}"
    )


# ==========================================================
# Main
# ==========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dynamic-model",
        required=True,
    )

    parser.add_argument(
        "--static-model",
        required=True,
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=7800,
    )

    parser.add_argument(
        "--seed-end",
        type=int,
        default=7819,
    )

    parser.add_argument(
        "--tasks",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--csv",
        default=(
            "rl_v2/results/"
            "dynamic_dev.csv"
        ),
    )

    args = parser.parse_args()

    print(
        "Loading models..."
    )

    dynamic_model = (
        MaskablePPO.load(
            args.dynamic_model,
            device="cpu",
        )
    )

    static_model = (
        MaskablePPO.load(
            args.static_model,
            device="cpu",
        )
    )

    print(
        f"Dynamic : "
        f"{args.dynamic_model}"
    )

    print(
        f"Static  : "
        f"{args.static_model}"
    )

    print(
        f"Seeds   : "
        f"{args.seed_start}"
        f" ~ "
        f"{args.seed_end}"
    )

    (
        raw_results,
        rows,
    ) = run_evaluation(
        dynamic_model=(
            dynamic_model
        ),
        static_model=(
            static_model
        ),
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

    print_compact(
        raw_results
    )

    print_dynamic_diagnostics(
        raw_results
    )

    print_paired(
        rows
    )

    save_csv(
        rows=rows,
        output_path=args.csv,
    )


if __name__ == "__main__":

    main()
