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

PPO_PATH = (
    RESULTS_ROOT
    / "reward_tuned_final"
    / "final_episode_runs.csv"
)

BASELINE_PATH = (
    RESULTS_ROOT
    / "comparison_final_battery_v2"
    / "comparison_runs.csv"
)

OUTPUT_DIR = (
    RESULTS_ROOT
    / "reward_tuned_final"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "ppo_vs_baselines_statistics.csv"
)


METRICS = {
    "average_waiting_time_s": "lower",
    "p95_waiting_time_s": "lower",
    "high_waiting_time_s": "lower",
    "emergency_waiting_time_s": "lower",
    "total_travel_time_s": "lower",
    "jain_task_fairness": "higher",
    "completion_rate": "higher",
}


BASELINES = [
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
]


def read_csv(path: Path):
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        return list(
            csv.DictReader(f)
        )


def mean(values):
    return float(
        np.mean(values)
    )


def sample_std(values):
    return float(
        np.std(
            values,
            ddof=1,
        )
    )


def paired_ci(diff):
    diff = np.asarray(
        diff,
        dtype=float,
    )

    n = len(diff)
    m = np.mean(diff)

    if n < 2:
        return float(m), float(m)

    sd = np.std(
        diff,
        ddof=1,
    )

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
    diff = np.asarray(
        diff,
        dtype=float,
    )

    sd = np.std(
        diff,
        ddof=1,
    )

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
            baseline_mean
            - ppo_mean
        ) / baseline_mean * 100.0

    return (
        ppo_mean
        - baseline_mean
    ) / baseline_mean * 100.0


def main():

    ppo_rows = read_csv(
        PPO_PATH
    )

    baseline_rows = read_csv(
        BASELINE_PATH
    )

    # ---------------------------------------------------------
    # PPO:
    # For each scenario seed, average across five model seeds.
    # This gives 30 paired PPO scenario-level observations.
    # ---------------------------------------------------------

    ppo_by_seed = {}

    for row in ppo_rows:

        scenario_seed = int(
            row["seed"]
        )

        ppo_by_seed.setdefault(
            scenario_seed,
            [],
        ).append(
            row
        )

    ppo_scenario = {}

    for (
        scenario_seed,
        rows,
    ) in sorted(
        ppo_by_seed.items()
    ):

        if len(rows) != 5:
            raise RuntimeError(
                f"Seed {scenario_seed}: "
                f"expected 5 PPO model runs, "
                f"got {len(rows)}"
            )

        ppo_scenario[
            scenario_seed
        ] = {
            metric:
            mean(
                [
                    float(
                        row[metric]
                    )
                    for row in rows
                ]
            )
            for metric in METRICS
        }

    # ---------------------------------------------------------
    # Baselines:
    # One result per method × scenario seed.
    # ---------------------------------------------------------

    baseline_data = {
        method: {}
        for method in BASELINES
    }

    for row in baseline_rows:

        method = row[
            "method"
        ]

        if method not in BASELINES:
            continue

        scenario_seed = int(
            row["seed"]
        )

        baseline_data[
            method
        ][
            scenario_seed
        ] = row

    expected_seeds = set(
        range(
            9001,
            9031,
        )
    )

    if set(
        ppo_scenario.keys()
    ) != expected_seeds:

        raise RuntimeError(
            "PPO final seeds are not exactly 9001-9030."
        )

    output_rows = []

    print()
    print(
        "=" * 145
    )

    print(
        "FINAL PPO VS BASELINES — PAIRED STATISTICAL ANALYSIS"
    )

    print(
        "=" * 145
    )

    print(
        "PPO value per scenario = mean across 5 PPO model seeds"
    )

    print(
        "Paired final scenarios = 9001-9030 (n=30)"
    )

    for baseline in BASELINES:

        if set(
            baseline_data[
                baseline
            ].keys()
        ) != expected_seeds:

            raise RuntimeError(
                f"{baseline}: "
                "final seeds are not exactly 9001-9030."
            )

        print()
        print(
            "#" * 145
        )

        print(
            "PPO vs",
            baseline,
        )

        print(
            "#" * 145
        )

        print(
            f"{'Metric':<28}"
            f"{'PPO':>12}"
            f"{'Baseline':>12}"
            f"{'Improve%':>12}"
            f"{'Diff':>12}"
            f"{'95% CI':>30}"
            f"{'p(t)':>12}"
            f"{'p(W)':>12}"
            f"{'dz':>10}"
        )

        print(
            "-" * 145
        )

        for (
            metric,
            direction,
        ) in METRICS.items():

            ppo_values = np.asarray(
                [
                    ppo_scenario[
                        seed
                    ][metric]
                    for seed
                    in sorted(
                        expected_seeds
                    )
                ],
                dtype=float,
            )

            baseline_values = np.asarray(
                [
                    float(
                        baseline_data[
                            baseline
                        ][
                            seed
                        ][metric]
                    )
                    for seed
                    in sorted(
                        expected_seeds
                    )
                ],
                dtype=float,
            )

            # Difference is always PPO - baseline.
            diff = (
                ppo_values
                - baseline_values
            )

            ppo_mean = mean(
                ppo_values
            )

            baseline_mean = mean(
                baseline_values
            )

            diff_mean = mean(
                diff
            )

            ci_low, ci_high = (
                paired_ci(
                    diff
                )
            )

            # Paired t-test
            t_result = stats.ttest_rel(
                ppo_values,
                baseline_values,
            )

            # Wilcoxon can fail if all paired
            # differences are zero (e.g. completion).
            try:
                w_result = (
                    stats.wilcoxon(
                        ppo_values,
                        baseline_values,
                        alternative="two-sided",
                        zero_method="wilcox",
                    )
                )

                wilcoxon_p = float(
                    w_result.pvalue
                )

            except ValueError:
                wilcoxon_p = float(
                    "nan"
                )

            dz = cohens_dz(
                diff
            )

            improve = (
                improvement_percent(
                    ppo_mean,
                    baseline_mean,
                    direction,
                )
            )

            output_rows.append(
                {
                    "baseline":
                    baseline,

                    "metric":
                    metric,

                    "n":
                    len(
                        ppo_values
                    ),

                    "ppo_mean":
                    ppo_mean,

                    "ppo_scenario_std":
                    sample_std(
                        ppo_values
                    ),

                    "baseline_mean":
                    baseline_mean,

                    "baseline_std":
                    sample_std(
                        baseline_values
                    ),

                    "improvement_percent":
                    improve,

                    "mean_difference_ppo_minus_baseline":
                    diff_mean,

                    "difference_ci95_low":
                    ci_low,

                    "difference_ci95_high":
                    ci_high,

                    "paired_t_statistic":
                    float(
                        t_result.statistic
                    ),

                    "paired_t_pvalue":
                    float(
                        t_result.pvalue
                    ),

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
                f"{baseline_mean:>12.2f}"
                f"{improve:>11.2f}%"
                f"{diff_mean:>12.2f}"
                f"{ci_text:>30}"
                f"{t_result.pvalue:>12.3g}"
                f"{wilcoxon_p:>12.3g}"
                f"{dz:>10.3f}"
            )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
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
    print(
        "=" * 145
    )

    print(
        "Saved:",
        OUTPUT_PATH,
    )

    print(
        "=" * 145
    )


if __name__ == "__main__":
    main()
