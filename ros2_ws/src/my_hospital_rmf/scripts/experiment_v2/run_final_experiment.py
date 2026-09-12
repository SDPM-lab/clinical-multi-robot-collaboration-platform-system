#!/usr/bin/env python3

import argparse
import csv
import statistics
import time

from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from sb3_contrib import MaskablePPO

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.paired_statistics import (
    compare_paired_metric,
)

from experiment_v2.run_baselines import (
    run_all_baselines,
)

from experiment_v2.run_multi_seed import (
    extract_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.reassignment_env import (
    ReassignmentHospitalRLEnv,
)


# ==========================================================
# Methods
# ==========================================================

PROPOSED_METHOD = (
    "proposed_rl"
)

METHOD_ORDER = (
    "random_feasible",
    "projected_nearest",
    "weighted_heuristic",
    "dynamic_weighted_heuristic",
    PROPOSED_METHOD,
)


# ==========================================================
# Metrics
# ==========================================================

MAIN_METRICS = (
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
)

DYNAMIC_METRICS = (
    "reassignment_decisions",
    "reassignment_count",
    "reassignment_rate",
    "average_reassignments_per_task",
    "max_reassignments_per_task",
    "max_cascade_depth",
)

PAIRED_METRICS = (
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
)


# ==========================================================
# Statistics
# ==========================================================

def summarize(
    values,
):

    values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not values:

        return {
            "mean": float("nan"),
            "std": float("nan"),
            "median": float("nan"),
            "n": 0,
        }

    return {
        "mean":
            statistics.mean(
                values
            ),

        "std":
            (
                statistics.stdev(
                    values
                )
                if len(values) > 1
                else 0.0
            ),

        "median":
            statistics.median(
                values
            ),

        "n":
            len(values),
    }


class TimedReassignmentHospitalRLEnv(
    ReassignmentHospitalRLEnv
):
    """
    只用於 Experiment evaluator。

    計算 Frozen Initial Assignment Policy
    的 action-selection latency。

    不包含 simulator 執行時間。
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        self.assignment_decision_times = []

        super().__init__(
            *args,
            **kwargs,
        )


    def _predict_assignment_action(
        self,
    ) -> int:

        start = (
            time.perf_counter()
        )

        try:

            return (
                super()
                ._predict_assignment_action()
            )

        finally:

            elapsed = (
                time.perf_counter()
                -
                start
            )

            self.assignment_decision_times.append(
                elapsed
            )


# ==========================================================
# Proposed RL Episode
# ==========================================================

def run_proposed_rl(
    *,
    seed,
    task_count,
    assignment_model,
    reassignment_model,
):

    scenario = (
        generate_hospital_scenario(
            seed=seed,
            task_count=task_count,
        )
    )

    env = (
        TimedReassignmentHospitalRLEnv(
            scenario=scenario,
            assignment_policy=(
                assignment_model
            ),
            seed=seed,
        )
    )

    (
        observation,
        info,
    ) = env.reset(
        seed=seed,
    )

    rl_steps = 0
    reassignment_decision_times = []

    while True:

        decision_start = (
            time.perf_counter()
        )

        # 將 Reassignment observation 建構、
        # safety/action mask 與 PPO inference
        # 都算入 scheduler decision latency。
        decision_observation = (
            env._get_observation()
        )

        mask = (
            env.action_masks()
        )

        action, _ = (
            reassignment_model.predict(
                decision_observation,
                action_masks=mask,
                deterministic=True,
            )
        )

        decision_elapsed = (
            time.perf_counter()
            -
            decision_start
        )

        reassignment_decision_times.append(
            decision_elapsed
        )

        action = int(
            np.asarray(
                action
            ).reshape(-1)[0]
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

        rl_steps += 1

        if (
            terminated
            or
            truncated
        ):

            break

    simulation_result = (
        env.get_simulation_result()
    )

    metrics = (
        calculate_metrics(
            simulation_result
        )
    )

    # Dedicated PPO 每個外部 step
    # 應該正好對應一次 Reassignment Decision。
    if (
        rl_steps
        !=
        metrics.reassignment_decision_count
    ):

        raise RuntimeError(
            "RL step count does not match "
            "reassignment decision count: "
            f"steps={rl_steps}, "
            "decisions="
            f"{metrics.reassignment_decision_count}"
        )

    wrapper = SimpleNamespace(
        metrics=metrics
    )

    values = extract_metrics(
        wrapper
    )

    all_decision_times = (
        list(
            env.assignment_decision_times
        )
        +
        reassignment_decision_times
    )

    if not all_decision_times:

        raise RuntimeError(
            "No Proposed RL decision "
            "latency was recorded"
        )

    values[
        "decision_time_ms"
    ] = (
        statistics.mean(
            all_decision_times
        )
        *
        1000.0
    )

    # 如果目前 extract_metrics
    # 有這個欄位，也一併修正。
    if (
        "max_decision_time_ms"
        in values
    ):

        values[
            "max_decision_time_ms"
        ] = (
            max(
                all_decision_times
            )
            *
            1000.0
        )

    env.close()

    return values


# ==========================================================
# One Seed
# ==========================================================

def run_one_seed(
    *,
    seed,
    task_count,
    assignment_model,
    reassignment_model,
):

    rows = []

    # ------------------------------------------------------
    # Four Baselines
    # ------------------------------------------------------

    baseline_results = (
        run_all_baselines(
            seed=seed,
            task_count=task_count,
        )
    )

    for result in baseline_results:

        values = (
            extract_metrics(
                result
            )
        )

        rows.append(
            {
                "seed":
                    seed,

                "method":
                    result.method,

                **values,
            }
        )

    # ------------------------------------------------------
    # Proposed RL
    # ------------------------------------------------------

    rl_values = (
        run_proposed_rl(
            seed=seed,
            task_count=task_count,
            assignment_model=(
                assignment_model
            ),
            reassignment_model=(
                reassignment_model
            ),
        )
    )

    rows.append(
        {
            "seed":
                seed,

            "method":
                PROPOSED_METHOD,

            **rl_values,
        }
    )

    return rows


# ==========================================================
# Summary
# ==========================================================

def build_summary_rows(
    rows,
):

    result = []

    all_metrics = (
        MAIN_METRICS
        +
        DYNAMIC_METRICS
    )

    for method in METHOD_ORDER:

        method_rows = [
            row
            for row in rows
            if (
                row["method"]
                ==
                method
            )
        ]

        for metric in all_metrics:

            summary = summarize(
                [
                    row.get(
                        metric
                    )
                    for row
                    in method_rows
                ]
            )

            result.append(
                {
                    "method":
                        method,

                    "metric":
                        metric,

                    **summary,
                }
            )

    return result


# ==========================================================
# Paired Statistics
# ==========================================================

def build_paired_rows(
    rows,
):

    # Proposed RL 是正式主要比較對象。
    #
    # Dynamic Weighted vs Weighted
    # 另外保留作為 Dynamic Baseline 的佐證。
    comparisons = (
        (
            PROPOSED_METHOD,
            "dynamic_weighted_heuristic",
        ),
        (
            PROPOSED_METHOD,
            "weighted_heuristic",
        ),
        (
            PROPOSED_METHOD,
            "projected_nearest",
        ),
        (
            PROPOSED_METHOD,
            "random_feasible",
        ),
        (
            "dynamic_weighted_heuristic",
            "weighted_heuristic",
        ),
    )

    paired_rows = []

    for (
        method_a,
        method_b,
    ) in comparisons:

        for (
            metric,
            lower_is_better,
        ) in PAIRED_METRICS:

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

            paired_rows.append(
                {
                    "method_a":
                        method_a,

                    "method_b":
                        method_b,

                    "metric":
                        metric,

                    "lower_is_better":
                        lower_is_better,

                    "mean_difference":
                        result.mean_difference,

                    "median_difference":
                        result.median_difference,

                    "wins_a":
                        result.wins_a,

                    "wins_b":
                        result.wins_b,

                    "ties":
                        result.ties,

                    "sample_count":
                        result.sample_count,

                    "p_value":
                        result.p_value,
                }
            )

    return paired_rows


# ==========================================================
# CSV
# ==========================================================

def write_csv(
    path,
    rows,
):

    if not rows:

        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = (
            csv.DictWriter(
                file,
                fieldnames=list(
                    rows[0].keys()
                ),
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ==========================================================
# Console Summary
# ==========================================================

def mean_for(
    rows,
    method,
    metric,
):

    values = [
        row[metric]
        for row in rows
        if (
            row["method"]
            ==
            method
            and
            row[metric]
            is not None
        )
    ]

    return (
        statistics.mean(
            values
        )
        if values
        else float("nan")
    )


def print_main_table(
    rows,
):

    print()
    print(
        "=" * 145
    )

    print(
        "EXPERIMENT I - FINAL ALGORITHM COMPARISON"
    )

    print(
        "=" * 145
    )

    print(
        f"{'Method':<32}"
        f"{'Wait':>10}"
        f"{'Emer':>10}"
        f"{'Complete':>11}"
        f"{'Makespan':>12}"
        f"{'Distance':>12}"
        f"{'Success':>10}"
        f"{'Jain':>9}"
        f"{'Dec(ms)':>11}"
        f"{'Reassign':>11}"
    )

    print(
        "-" * 145
    )

    for method in METHOD_ORDER:

        print(
            f"{method:<32}"

            f"{mean_for(rows, method, 'waiting_time'):>10.3f}"

            f"{mean_for(rows, method, 'emergency_waiting_time'):>10.3f}"

            f"{mean_for(rows, method, 'completion_time'):>11.3f}"

            f"{mean_for(rows, method, 'makespan'):>12.3f}"

            f"{mean_for(rows, method, 'travel_distance'):>12.3f}"

            f"{mean_for(rows, method, 'success_rate'):>10.3f}"

            f"{mean_for(rows, method, 'jain_fairness'):>9.3f}"

            f"{mean_for(rows, method, 'decision_time_ms'):>11.3f}"

            f"{mean_for(rows, method, 'reassignment_count'):>11.3f}"
        )

    print(
        "=" * 145
    )


def print_paired_table(
    paired_rows,
):

    print()
    print(
        "=" * 145
    )

    print(
        "PAIRED STATISTICAL COMPARISON"
    )

    print(
        "=" * 145
    )

    current_pair = None

    for row in paired_rows:

        pair = (
            row["method_a"],
            row["method_b"],
        )

        if pair != current_pair:

            current_pair = pair

            print()

            print(
                f"{pair[0]} vs {pair[1]}"
            )

            print(
                "-" * 145
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

        p_value = (
            row["p_value"]
        )

        if p_value is None:

            p_text = "N/A"

        elif p_value < 1e-6:

            p_text = "<1e-6"

        else:

            p_text = (
                f"{p_value:.6f}"
            )

        print(
            f"{row['metric']:<30}"
            f"{row['mean_difference']:>14.3f}"
            f"{row['median_difference']:>16.3f}"
            f"{row['wins_a']:>10}"
            f"{row['wins_b']:>10}"
            f"{row['ties']:>8}"
            f"{row['sample_count']:>8}"
            f"{p_text:>14}"
        )

    print()
    print(
        "=" * 145
    )


# ==========================================================
# Metadata
# ==========================================================

def write_metadata(
    path,
    *,
    seed_start,
    seed_end,
    task_count,
    assignment_model_path,
    reassignment_model_path,
):

    text = f"""Experiment I Final Algorithm Benchmark

Seed start              : {seed_start}
Seed end                : {seed_end}
Task count              : {task_count}

Methods:
- random_feasible
- projected_nearest
- weighted_heuristic
- dynamic_weighted_heuristic
- proposed_rl

Proposed RL:
Initial Assignment      : Frozen Long-Horizon Masked PPO
Assignment model        : {assignment_model_path}
Dynamic Reassignment    : Dedicated Masked PPO
Reassignment model      : {reassignment_model_path}
Inference               : deterministic
Training shaping weight : 0.25
Gamma                    : 1.0
GAE lambda               : 0.95
Reassignment penalty     : 0.0

Evaluation reward shaping:
Not used for metric calculation.
All reported results come from actual simulator outcomes.
"""

    path.write_text(
        text,
        encoding="utf-8",
    )


# ==========================================================
# Main
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Experiment I final paired "
            "algorithm benchmark."
        )
    )

    parser.add_argument(
        "--assignment-model",
        default=(
            "rl_v2/models/"
            "long_horizon_ppo_102k_seed42.zip"
        ),
    )

    parser.add_argument(
        "--reassignment-model",
        default=(
            "rl_v2/models/"
            "reassignment_ppo_shaping025_102k_seed42.zip"
        ),
    )

    # 預設故意不是 Final Seeds。
    #
    # 一定先 smoke test evaluator，
    # 才手動指定 9000~9029。
    parser.add_argument(
        "--seed-start",
        type=int,
        default=8000,
    )

    parser.add_argument(
        "--seed-end",
        type=int,
        default=8000,
    )

    parser.add_argument(
        "--tasks",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "experiment_v2/results/"
            "final_experiment"
        ),
    )

    args = parser.parse_args()

    if (
        args.seed_end
        <
        args.seed_start
    ):

        raise ValueError(
            "--seed-end must be >= "
            "--seed-start"
        )

    output_dir = Path(
        args.output_dir
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Loading frozen models..."
    )

    assignment_model = (
        MaskablePPO.load(
            args.assignment_model,
            device="cpu",
        )
    )

    reassignment_model = (
        MaskablePPO.load(
            args.reassignment_model,
            device="cpu",
        )
    )

    rows = []

    total_seeds = (
        args.seed_end
        -
        args.seed_start
        +
        1
    )

    for index, seed in enumerate(
        range(
            args.seed_start,
            args.seed_end + 1,
        ),
        start=1,
    ):

        seed_rows = (
            run_one_seed(
                seed=seed,
                task_count=args.tasks,
                assignment_model=(
                    assignment_model
                ),
                reassignment_model=(
                    reassignment_model
                ),
            )
        )

        rows.extend(
            seed_rows
        )

        proposed_row = next(
            row
            for row in seed_rows
            if (
                row["method"]
                ==
                PROPOSED_METHOD
            )
        )

        print(
            f"[{index:>2}/{total_seeds}] "
            f"seed={seed} "
            f"RL wait="
            f"{proposed_row['waiting_time']:.3f} "
            f"emer="
            f"{proposed_row['emergency_waiting_time']:.3f} "
            f"reassign="
            f"{proposed_row['reassignment_count']:.0f}"
        )

    summary_rows = (
        build_summary_rows(
            rows
        )
    )

    paired_rows = (
        build_paired_rows(
            rows
        )
    )

    raw_path = (
        output_dir
        /
        "per_seed_results.csv"
    )

    summary_path = (
        output_dir
        /
        "summary.csv"
    )

    paired_path = (
        output_dir
        /
        "paired_statistics.csv"
    )

    metadata_path = (
        output_dir
        /
        "experiment_config.txt"
    )

    write_csv(
        raw_path,
        rows,
    )

    write_csv(
        summary_path,
        summary_rows,
    )

    write_csv(
        paired_path,
        paired_rows,
    )

    write_metadata(
        metadata_path,
        seed_start=args.seed_start,
        seed_end=args.seed_end,
        task_count=args.tasks,
        assignment_model_path=(
            args.assignment_model
        ),
        reassignment_model_path=(
            args.reassignment_model
        ),
    )

    print_main_table(
        rows
    )

    print_paired_table(
        paired_rows
    )

    print()
    print(
        "Saved:"
    )

    print(
        "  ",
        raw_path,
    )

    print(
        "  ",
        summary_path,
    )

    print(
        "  ",
        paired_path,
    )

    print(
        "  ",
        metadata_path,
    )


if __name__ == "__main__":

    main()
