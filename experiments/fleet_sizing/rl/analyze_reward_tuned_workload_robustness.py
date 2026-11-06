from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RESULTS_ROOT = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

INPUT_PATH = (
    RESULTS_ROOT
    / "reward_tuned_workload_robustness"
    / "comparison_runs.csv"
)

OUTPUT_PATH = (
    RESULTS_ROOT
    / "reward_tuned_workload_robustness"
    / "ppo_vs_dynamic_statistics.csv"
)

WORKLOADS = [
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
]

METRICS = {
    "average_waiting_time_s": "lower",
    "p95_waiting_time_s": "lower",
    "high_waiting_time_s": "lower",
    "emergency_waiting_time_s": "lower",
    "total_travel_time_s": "lower",
    "jain_task_fairness": "higher",
    "completion_rate": "higher",
}


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def mean(values):
    return float(np.mean(values))


def paired_ci(diff):
    diff = np.asarray(diff, dtype=float)

    n = len(diff)
    m = np.mean(diff)

    if n < 2:
        return float(m), float(m)

    sd = np.std(diff, ddof=1)
    se = sd / math.sqrt(n)

    tcrit = stats.t.ppf(
        0.975,
        df=n - 1,
    )

    return (
        float(m - tcrit * se),
        float(m + tcrit * se),
    )


def cohens_dz(diff):
    diff = np.asarray(diff, dtype=float)

    sd = np.std(diff, ddof=1)

    if sd == 0:
        return float("nan")

    return float(
        np.mean(diff) / sd
    )


def improvement_percent(
    ppo_mean,
    baseline_mean,
    direction,
):
    if baseline_mean == 0:
        return float("nan")

    if direction == "lower":
        return (
            baseline_mean - ppo_mean
        ) / baseline_mean * 100.0

    return (
        ppo_mean - baseline_mean
    ) / baseline_mean * 100.0


def main():

    rows = read_csv(INPUT_PATH)

    output_rows = []

    for workload in WORKLOADS:

        workload_rows = [
            row
            for row in rows
            if float(
                row["workload_multiplier"]
            ) == workload
        ]

        dynamic_rows = {
            int(row["seed"]): row
            for row in workload_rows
            if row["method"] == "dynamic_weighted"
        }

        ppo_rows = {}

        for row in workload_rows:

            if not row["method"].startswith("ppo_seed_"):
                continue

            seed = int(row["seed"])

            ppo_rows.setdefault(
                seed,
                [],
            ).append(row)

        expected_seeds = set(
            range(9201, 9231)
        )

        if set(dynamic_rows.keys()) != expected_seeds:
            raise RuntimeError(
                f"Workload {workload}: "
                "dynamic seeds incomplete"
            )

        if set(ppo_rows.keys()) != expected_seeds:
            raise RuntimeError(
                f"Workload {workload}: "
                "PPO seeds incomplete"
            )

        print()
        print("=" * 145)
        print(
            f"WORKLOAD {workload:.1f}x — "
            "PPO vs Dynamic Weighted"
        )
        print("=" * 145)

        print(
            f"{'Metric':<28}"
            f"{'PPO':>12}"
            f"{'Dynamic':>12}"
            f"{'Improve%':>12}"
            f"{'Diff':>12}"
            f"{'95% CI':>30}"
            f"{'p(t)':>12}"
            f"{'p(W)':>12}"
            f"{'dz':>10}"
        )

        print("-" * 145)

        for metric, direction in METRICS.items():

            ppo_values = []
            dynamic_values = []

            for seed in sorted(expected_seeds):

                seed_ppo_rows = ppo_rows[seed]

                if len(seed_ppo_rows) != 5:
                    raise RuntimeError(
                        f"Workload {workload}, "
                        f"seed {seed}: "
                        f"expected 5 PPO runs, "
                        f"got {len(seed_ppo_rows)}"
                    )

                ppo_value = mean(
                    [
                        float(row[metric])
                        for row in seed_ppo_rows
                    ]
                )

                dynamic_value = float(
                    dynamic_rows[seed][metric]
                )

                ppo_values.append(
                    ppo_value
                )

                dynamic_values.append(
                    dynamic_value
                )

            ppo_values = np.asarray(
                ppo_values,
                dtype=float,
            )

            dynamic_values = np.asarray(
                dynamic_values,
                dtype=float,
            )

            diff = (
                ppo_values
                - dynamic_values
            )

            ppo_mean = mean(
                ppo_values
            )

            dynamic_mean = mean(
                dynamic_values
            )

            diff_mean = mean(
                diff
            )

            ci_low, ci_high = (
                paired_ci(diff)
            )

            t_result = stats.ttest_rel(
                ppo_values,
                dynamic_values,
            )

            try:
                w_result = stats.wilcoxon(
                    ppo_values,
                    dynamic_values,
                    alternative="two-sided",
                    zero_method="wilcox",
                )

                wilcoxon_p = float(
                    w_result.pvalue
                )

            except ValueError:
                wilcoxon_p = float("nan")

            dz = cohens_dz(diff)

            improve = improvement_percent(
                ppo_mean,
                dynamic_mean,
                direction,
            )

            output_rows.append(
                {
                    "workload_multiplier":
                    workload,

                    "metric":
                    metric,

                    "n":
                    len(ppo_values),

                    "ppo_mean":
                    ppo_mean,

                    "dynamic_mean":
                    dynamic_mean,

                    "improvement_percent":
                    improve,

                    "mean_difference_ppo_minus_dynamic":
                    diff_mean,

                    "difference_ci95_low":
                    ci_low,

                    "difference_ci95_high":
                    ci_high,

                    "paired_t_pvalue":
                    float(t_result.pvalue),

                    "wilcoxon_pvalue":
                    wilcoxon_p,

                    "cohens_dz":
                    dz,
                }
            )

            ci_text = (
                f"[{ci_low:.2f}, "
                f"{ci_high:.2f}]"
            )

            print(
                f"{metric:<28}"
                f"{ppo_mean:>12.2f}"
                f"{dynamic_mean:>12.2f}"
                f"{improve:>11.2f}%"
                f"{diff_mean:>12.2f}"
                f"{ci_text:>30}"
                f"{t_result.pvalue:>12.3g}"
                f"{wilcoxon_p:>12.3g}"
                f"{dz:>10.3f}"
            )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                output_rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    print()
    print("Saved:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
