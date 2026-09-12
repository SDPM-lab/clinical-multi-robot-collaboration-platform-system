#!/usr/bin/env python3

import argparse
import csv
import statistics
import time

from collections import defaultdict
from pathlib import Path

import numpy as np

from sb3_contrib import MaskablePPO

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.models import (
    BaselineMethod,
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

from rl_v2.env import (
    HospitalRLEnv,
)


# ==========================================================
# Constants
# ==========================================================

PPO_METHOD = "masked_ppo"

METHOD_NAMES = [
    method.value
    for method in BASELINE_METHODS
] + [
    PPO_METHOD
]


SUMMARY_METRICS = [
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


PAIRED_METRICS = [
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


# ==========================================================
# PPO Evaluation
# ==========================================================

def run_ppo_on_scenario(
    model: MaskablePPO,
    scenario,
    seed: int,
) -> tuple[
    BaselineRunResult,
    float,
]:
    """
    在指定 Scenario 上執行 deterministic PPO。

    回傳：
        BaselineRunResult
        average decision time (ms)

    Decision Time 定義：
        Action Mask
        +
        PPO inference

    env.step() 的 simulator execution
    不包含在 decision time。
    """

    env = HospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = (
        env.reset(
            seed=seed
        )
    )

    decision_times = []

    terminated = bool(
        env.kernel is not None
        and
        env.kernel.finished
    )

    truncated = False

    while not (
        terminated
        or
        truncated
    ):

        # ----------------------------------------------
        # Measure scheduling decision time
        # ----------------------------------------------

        decision_start = (
            time.perf_counter()
        )

        action_mask = (
            env.action_masks()
        )

        action, _ = (
            model.predict(
                observation,
                action_masks=(
                    action_mask
                ),
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

    simulation_result = (
        env.get_simulation_result()
    )

    metrics = calculate_metrics(
        simulation_result
    )

    if decision_times:

        average_decision_ms = (
            statistics.mean(
                decision_times
            )
            *
            1000.0
        )

    else:

        average_decision_ms = 0.0

    return (
        BaselineRunResult(
            method=PPO_METHOD,
            metrics=metrics,
        ),
        average_decision_ms,
    )


# ==========================================================
# One Seed
# ==========================================================

def run_one_seed(
    model: MaskablePPO,
    seed: int,
    task_count: int,
):
    """
    所有方法共用完全相同 Scenario。
    """

    scenario = (
        generate_hospital_scenario(
            seed=seed,
            task_count=task_count,
        )
    )

    results = []

    # ------------------------------------------------------
    # Baselines
    # ------------------------------------------------------

    for method in BASELINE_METHODS:

        result = run_baseline(
            scenario=scenario,
            method=method,
            seed=seed,
        )

        values = extract_metrics(
            result
        )

        results.append(
            (
                result.method,
                values,
            )
        )

    # ------------------------------------------------------
    # PPO
    # ------------------------------------------------------

    (
        ppo_result,
        ppo_decision_ms,
    ) = run_ppo_on_scenario(
        model=model,
        scenario=scenario,
        seed=seed,
    )

    ppo_values = extract_metrics(
        ppo_result
    )

    # RL env 內的 DecisionRecord
    # 目前不含 neural-network inference time，
    # 因此 evaluation 階段以實測值覆蓋。
    ppo_values[
        "decision_time_ms"
    ] = ppo_decision_ms

    results.append(
        (
            PPO_METHOD,
            ppo_values,
        )
    )

    return results


# ==========================================================
# Multi Seed
# ==========================================================

def run_evaluation(
    model,
    seed_start: int,
    seed_end: int,
    task_count: int,
):
    """
    seed_start / seed_end 都包含。
    """

    if seed_end < seed_start:

        raise ValueError(
            "seed_end must be >= seed_start"
        )

    raw_results = defaultdict(
        lambda: defaultdict(list)
    )

    rows = []

    total_seed_count = (
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
            f"[{index:>3}/{total_seed_count}] "
            f"seed={seed}"
        )

        seed_results = (
            run_one_seed(
                model=model,
                seed=seed,
                task_count=task_count,
            )
        )

        for (
            method,
            values,
        ) in seed_results:

            row = {
                "seed": seed,
                "method": method,
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
                    method
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
# Summary
# ==========================================================

def print_summary(
    raw_results,
):

    print()
    print(
        "=" * 110
    )
    print(
        "DEVELOPMENT COMPARISON"
    )
    print(
        "=" * 110
    )

    for metric_name in (
        SUMMARY_METRICS
    ):

        print()
        print(
            metric_name
        )

        print(
            "-" * 110
        )

        print(
            f"{'Method':<30}"
            f"{'Mean':>16}"
            f"{'Std':>16}"
            f"{'Median':>16}"
            f"{'N':>10}"
        )

        for method in METHOD_NAMES:

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
                f"{method:<30}"
                f"{summary['mean']:>16.3f}"
                f"{summary['std']:>16.3f}"
                f"{summary['median']:>16.3f}"
                f"{len(values):>10}"
            )

    print()
    print(
        "=" * 110
    )


# ==========================================================
# Compact Table
# ==========================================================

def print_compact_table(
    raw_results,
):

    print()
    print(
        "=" * 125
    )

    print(
        "COMPACT DEVELOPMENT TABLE"
    )

    print(
        "=" * 125
    )

    print(
        f"{'Method':<30}"
        f"{'Wait':>11}"
        f"{'Emer':>11}"
        f"{'Complete':>12}"
        f"{'Makespan':>12}"
        f"{'Distance':>12}"
        f"{'Success':>10}"
        f"{'Jain':>9}"
        f"{'Dec(ms)':>11}"
    )

    print(
        "-" * 125
    )

    for method in METHOD_NAMES:

        def mean_of(metric):

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

        print(
            f"{method:<30}"
            f"{mean_of('waiting_time'):>11.3f}"
            f"{mean_of('emergency_waiting_time'):>11.3f}"
            f"{mean_of('completion_time'):>12.3f}"
            f"{mean_of('makespan'):>12.3f}"
            f"{mean_of('travel_distance'):>12.3f}"
            f"{mean_of('success_rate'):>10.3f}"
            f"{mean_of('jain_fairness'):>9.3f}"
            f"{mean_of('decision_time_ms'):>11.3f}"
        )

    print(
        "=" * 125
    )


# ==========================================================
# PPO Paired Comparison
# ==========================================================

def print_ppo_paired_summary(
    rows,
):

    comparisons = [
        (
            PPO_METHOD,
            "dynamic_weighted_heuristic",
        ),
        (
            PPO_METHOD,
            "weighted_heuristic",
        ),
        (
            PPO_METHOD,
            "projected_nearest",
        ),
        (
            PPO_METHOD,
            "random_feasible",
        ),
    ]

    print()
    print(
        "=" * 135
    )

    print(
        "PPO PAIRED STATISTICAL COMPARISON"
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
            metric_name,
            lower_is_better,
        ) in PAIRED_METRICS:

            result = (
                compare_paired_metric(
                    rows=rows,
                    metric=(
                        metric_name
                    ),
                    method_a=(
                        method_a
                    ),
                    method_b=(
                        method_b
                    ),
                    lower_is_better=(
                        lower_is_better
                    ),
                )
            )

            if result.p_value is None:

                p_text = "N/A"

            elif (
                result.p_value
                <
                1e-6
            ):

                p_text = "<1e-6"

            else:

                p_text = (
                    f"{result.p_value:.6f}"
                )

            print(
                f"{metric_name:<30}"
                f"{result.mean_difference:>14.3f}"
                f"{result.median_difference:>16.3f}"
                f"{result.wins_a:>10}"
                f"{result.wins_b:>10}"
                f"{result.ties:>8}"
                f"{result.sample_count:>8}"
                f"{p_text:>14}"
            )

    print()
    print(
        "=" * 135
    )


# ==========================================================
# CSV
# ==========================================================

def save_csv(
    rows,
    output_path: str,
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
    ) as f:

        writer = csv.DictWriter(
            f,
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

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Maskable PPO "
            "against Scheduler v2 baselines."
        )
    )

    parser.add_argument(
        "--model",
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
        type=str,
        default=(
            "rl_v2/results/"
            "dev_comparison.csv"
        ),
    )

    args = parser.parse_args()

    print(
        "Loading PPO model:"
    )
    print(
        args.model
    )

    model = (
        MaskablePPO.load(
            args.model,
            device="cpu",
        )
    )

    print()
    print(
        "Evaluation settings"
    )

    print(
        f"Seeds : "
        f"{args.seed_start}"
        f" ~ "
        f"{args.seed_end}"
    )

    print(
        f"Tasks : "
        f"{args.tasks}"
    )

    print(
        "PPO   : deterministic"
    )

    print()

    (
        raw_results,
        rows,
    ) = run_evaluation(
        model=model,
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

    print_compact_table(
        raw_results
    )

    print_summary(
        raw_results
    )

    print_ppo_paired_summary(
        rows
    )

    save_csv(
        rows=rows,
        output_path=args.csv,
    )


if __name__ == "__main__":

    main()
