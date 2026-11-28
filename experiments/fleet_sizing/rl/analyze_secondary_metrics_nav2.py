from __future__ import annotations

import hashlib
import json

from pathlib import Path
from itertools import product
from datetime import datetime
from importlib.metadata import version

import numpy as np
import pandas as pd

from scipy.stats import ttest_rel, wilcoxon

from experiments.fleet_sizing.rl.analyze_final_nav2_calibrated_baselines import (
    holm_adjust,
)


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RESULT = (
    ROOT / "results_rl"
    / "final_nav2_calibrated_baselines_sweep12_seed7101"
)

SOURCE = RESULT / "full"

PRIMARY = RESULT / "analysis"

OUTPUT = RESULT / "secondary_analysis"

PPO = "ppo_sweep12_seed7101"

BASELINES = (
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
)

METHODS = (*BASELINES, PPO)

WORKLOADS = (
    3.0, 3.5, 4.0, 4.5, 5.0
)

SEEDS = tuple(range(9601, 9631))

BOOTSTRAP_ITERATIONS = 10000
BOOTSTRAP_SEED = 20261128

RESERVE_SOC = 0.15

KEYS = [
    "workload_multiplier",
    "method",
    "seed",
]

GROUP_KEYS = [
    "workload_multiplier",
    "method",
]

SECONDARY_METRICS = (
    "low_waiting_time_s",
    "normal_waiting_time_s",

    "average_response_time_s",
    "p95_response_time_s",

    "average_total_time_s",
    "p95_total_time_s",

    "total_approach_time_s",
    "total_task_travel_time_s",

    "makespan_s",

    "average_robot_utilization",
    "max_robot_utilization",

    "total_return_to_charge_count",
    "total_charging_count",

    "minimum_robot_soc",
    "average_final_soc",
)

INFERENCE_METRICS = (
    "low_waiting_time_s",
    "normal_waiting_time_s",

    "average_response_time_s",
    "p95_response_time_s",

    "average_total_time_s",
    "p95_total_time_s",

    "total_approach_time_s",
)

DERIVED_METRICS = (
    "approach_time_ratio",
    "utilization_gap",
    "charging_per_100_tasks",
    "battery_reserve_margin",
)


def sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


# ============================================================
# 1. Verify source data
# ============================================================

def load_data():

    evaluation = read_json(
        SOURCE / "experiment_metadata.json"
    )

    primary = read_json(
        PRIMARY / "analysis_metadata.json"
    )

    assert evaluation["status"] == "complete"

    assert evaluation["completed_episodes"] == 750

    assert evaluation["fleet"] == [2, 2, 3]

    assert evaluation["baseline_parameters"] == {
        "static_alpha": 0.6,
        "dynamic_alpha_min": 0.4,
        "dynamic_alpha_max": 0.9,
    }

    assert evaluation["model_seed"] == 7101

    assert primary["bootstrap_counts"] == {
        "ppo_better": 91,
        "ppo_worse": 16,
        "ci_crosses_zero": 13,
    }

    for name, expected in evaluation[
        "output_sha256"
    ].items():

        assert sha256(
            SOURCE / name
        ) == expected, name

    for name, expected in primary[
        "output_sha256"
    ].items():

        assert sha256(
            PRIMARY / name
        ) == expected, name

    assert sha256(
        SOURCE / "comparison_runs.csv"
    ) == primary["source_runs_sha256"]

    runs = pd.read_csv(
        SOURCE / "comparison_runs.csv"
    )

    expected = set(
        product(
            WORKLOADS,
            METHODS,
            SEEDS,
        )
    )

    actual = set(
        runs[KEYS].itertuples(
            index=False,
            name=None,
        )
    )

    assert len(runs) == 750
    assert actual == expected

    assert not runs.duplicated(
        KEYS
    ).any()

    assert set(
        SECONDARY_METRICS
    ).issubset(runs.columns)

    assert np.isfinite(
        runs[list(SECONDARY_METRICS)]
        .to_numpy(dtype=float)
    ).all()

    assert (
        runs["completion_rate"] == 1
    ).all()

    assert (
        runs["completed_tasks"] > 0
    ).all()

    assert (
        runs["generated_tasks"]
        == runs["completed_tasks"]
    ).all()

    assert (
        runs.groupby([
            "workload_multiplier",
            "seed",
        ])["generated_tasks"].nunique() == 1
    ).all()

    assert np.allclose(
        runs["total_travel_time_s"],
        runs["total_approach_time_s"]
        + runs["total_task_travel_time_s"],
        rtol=1e-9,
        atol=1e-8,
    )

    assert (
        runs["total_travel_time_s"] > 0
    ).all()

    print("===== SOURCE INTEGRITY =====")
    print("750 episodes: PASS")
    print("15 secondary metrics: PASS")
    print("Primary results preserved: PASS")
    print("Travel decomposition identity: PASS")

    return runs


# ============================================================
# 2. Derived metrics
# ============================================================

def add_derived_metrics(runs):

    runs = runs.copy()

    runs["approach_time_ratio"] = (
        runs["total_approach_time_s"]
        / runs["total_travel_time_s"]
    )

    runs["utilization_gap"] = (
        runs["max_robot_utilization"]
        - runs["average_robot_utilization"]
    )

    runs["charging_per_100_tasks"] = (
        100
        * runs["total_charging_count"]
        / runs["completed_tasks"]
    )

    runs["battery_reserve_margin"] = (
        runs["minimum_robot_soc"]
        - RESERVE_SOC
    )

    assert (
        runs["utilization_gap"] >= -1e-10
    ).all()

    return runs


# ============================================================
# 3. Descriptive statistics
# ============================================================

def descriptive_statistics(runs):

    records = []

    metrics = (
        *SECONDARY_METRICS,
        *DERIVED_METRICS,
    )

    for (workload, method), group in runs.groupby(
        GROUP_KEYS,
        sort=False,
    ):

        assert len(group) == 30

        for metric in metrics:

            values = group[metric].to_numpy(
                dtype=float
            )

            records.append({
                "workload": workload,
                "method": method,
                "metric": metric,

                "metric_type": (
                    "secondary"
                    if metric in SECONDARY_METRICS
                    else "derived"
                ),

                "seed_count": len(values),
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=1)),
                "median": float(np.median(values)),
                "min": float(values.min()),
                "max": float(values.max()),
            })

    result = pd.DataFrame(records)

    assert len(result) == 475

    return result


# ============================================================
# 4. Verify descriptive summaries
# ============================================================

def verify_original_summary(descriptive):

    summary = pd.read_csv(
        SOURCE / "comparison_summary.csv"
    )

    checks = 0

    for _, row in descriptive.iterrows():

        metric = row["metric"]

        if metric not in SECONDARY_METRICS:

            continue

        original = summary.loc[
            (
                summary["method"]
                == row["method"]
            )
            &
            (
                summary["workload_multiplier"]
                == row["workload"]
            )
        ]

        assert len(original) == 1

        original = original.iloc[0]

        for key, suffix in [
            ("mean", "_mean"),
            ("sd", "_std"),
            ("median", "_median"),
        ]:

            assert np.isclose(
                row[key],
                original[metric + suffix],
                rtol=1e-9,
                atol=1e-8,
            ), (metric, key)

            checks += 1

    print()
    print("===== SUMMARY VERIFICATION =====")
    print("Numeric values checked:", checks)
    print("Secondary summaries: PASS")

    return checks


# ============================================================
# 5. Exploratory paired inference
# ============================================================

def paired_analysis(runs):

    rng = np.random.default_rng(
        BOOTSTRAP_SEED
    )

    records = []

    for workload in WORKLOADS:

        indices = rng.integers(
            0,
            len(SEEDS),
            size=(
                BOOTSTRAP_ITERATIONS,
                len(SEEDS),
            ),
        )

        subset = runs.loc[
            runs["workload_multiplier"]
            == workload
        ]

        ppo = subset.loc[
            subset["method"] == PPO
        ].set_index("seed").sort_index()

        assert tuple(ppo.index) == SEEDS

        for baseline in BASELINES:

            base = subset.loc[
                subset["method"] == baseline
            ].set_index("seed").sort_index()

            assert tuple(base.index) == SEEDS

            for metric in INFERENCE_METRICS:

                p = ppo[metric].to_numpy(
                    dtype=float
                )

                b = base[metric].to_numpy(
                    dtype=float
                )

                # All seven metrics: lower is better.
                # Positive difference means PPO better.

                d = b - p

                boot = d[
                    indices
                ].mean(axis=1)

                low, high = np.percentile(
                    boot, [2.5, 97.5]
                )

                mean_d = float(d.mean())

                if low > 0:

                    verdict = "ppo_better"

                elif high < 0:

                    verdict = "ppo_worse"

                else:

                    verdict = "ci_includes_zero"

                if np.all(d == 0):

                    t_p = 1.0
                    w_p = 1.0

                else:

                    if np.std(d, ddof=1) == 0:

                        t_p = 0.0

                    else:

                        t_p = float(
                            ttest_rel(b, p).pvalue
                        )

                    w_p = float(
                        wilcoxon(
                            d,
                            alternative="two-sided",
                            zero_method="wilcox",
                            method="auto",
                        ).pvalue
                    )

                tie = np.isclose(
                    d, 0,
                    rtol=0,
                    atol=1e-8,
                )

                records.append({
                    "workload": workload,
                    "baseline": baseline,
                    "metric": metric,

                    "paired_seeds": len(SEEDS),

                    "ppo_mean": float(p.mean()),
                    "ppo_sd": float(p.std(ddof=1)),

                    "baseline_mean": float(b.mean()),
                    "baseline_sd": float(b.std(ddof=1)),

                    "mean_difference": mean_d,

                    "median_difference": float(
                        np.median(d)
                    ),

                    "relative_improvement_pct": (
                        100 * mean_d / b.mean()
                        if b.mean() != 0
                        else np.nan
                    ),

                    "ci_95_low": float(low),
                    "ci_95_high": float(high),

                    "bootstrap_verdict": verdict,

                    "paired_t_p": t_p,
                    "wilcoxon_p": w_p,

                    "wins": int(
                        ((d > 0) & ~tie).sum()
                    ),

                    "ties": int(tie.sum()),

                    "losses": int(
                        ((d < 0) & ~tie).sum()
                    ),
                })

    stats = pd.DataFrame(records)

    assert len(stats) == 140

    assert (
        stats["wins"]
        + stats["ties"]
        + stats["losses"]
        == 30
    ).all()

    stats["holm_t_p"] = holm_adjust(
        stats["paired_t_p"]
    )

    stats["holm_wilcoxon_p"] = holm_adjust(
        stats["wilcoxon_p"]
    )

    stats["holm_t_verdict"] = np.where(
        stats["holm_t_p"] >= 0.05,
        "not_significant",
        np.where(
            stats["mean_difference"] > 0,
            "ppo_better",
            np.where(
                stats["mean_difference"] < 0,
                "ppo_worse",
                "direction_unclear",
            ),
        ),
    )

    # Wilcoxon is not a test of mean differences.
    # Keep significance separate from mean direction.

    stats["holm_wilcoxon_significant"] = (
        stats["holm_wilcoxon_p"] < 0.05
    )

    stats["wilcoxon_median_direction"] = np.where(
        stats["median_difference"] > 0,
        "positive",
        np.where(
            stats["median_difference"] < 0,
            "negative",
            "zero",
        ),
    )

    counts = pd.crosstab(
        stats["metric"],
        stats["bootstrap_verdict"],
    ).reindex(
        index=list(INFERENCE_METRICS),
        columns=[
            "ppo_better",
            "ppo_worse",
            "ci_includes_zero",
        ],
        fill_value=0,
    )

    return stats, counts


# ============================================================
# 6. Best baseline comparison
# ============================================================

def best_baseline_comparison(stats):

    records = []

    for _, group in stats.groupby([
        "workload",
        "metric",
    ]):

        index = group[
            "baseline_mean"
        ].idxmin()

        records.append(
            group.loc[index].to_dict()
        )

    best = pd.DataFrame(records)

    assert len(best) == 35

    return best


# ============================================================
# 7. Priority analysis
# ============================================================

def priority_analysis(runs):

    records = []

    priorities = {
        "low": "low_waiting_time_s",
        "normal": "normal_waiting_time_s",
        "high": "high_waiting_time_s",
        "emergency": "emergency_waiting_time_s",
    }

    for (workload, method), group in runs.groupby(
        GROUP_KEYS,
        sort=False,
    ):

        for priority, metric in priorities.items():

            records.append({
                "workload": workload,
                "method": method,
                "priority": priority,
                "seed_count": len(group),
                "mean_wait_s": group[metric].mean(),
                "sd_wait_s": group[metric].std(ddof=1),
                "median_wait_s": group[metric].median(),
            })

    result = pd.DataFrame(records)

    assert len(result) == 100

    return result


# ============================================================
# 8. Travel decomposition
# ============================================================

def travel_analysis(runs):

    records = []

    for workload in WORKLOADS:

        subset = runs.loc[
            runs["workload_multiplier"]
            == workload
        ]

        ppo = subset.loc[
            subset["method"] == PPO
        ].set_index("seed").sort_index()

        for baseline in BASELINES:

            base = subset.loc[
                subset["method"] == baseline
            ].set_index("seed").sort_index()

            assert tuple(ppo.index) == tuple(
                base.index
            )

            approach_diff = (
                ppo["total_approach_time_s"]
                - base["total_approach_time_s"]
            )

            task_diff = (
                ppo["total_task_travel_time_s"]
                - base["total_task_travel_time_s"]
            )

            total_diff = (
                ppo["total_travel_time_s"]
                - base["total_travel_time_s"]
            )

            assert np.allclose(
                total_diff,
                approach_diff + task_diff,
                rtol=1e-9,
                atol=1e-8,
            )

            task_match = np.isclose(
                ppo["total_task_travel_time_s"],
                base["total_task_travel_time_s"],
                rtol=1e-9,
                atol=1e-8,
            )

            records.append({
                "workload": workload,
                "baseline": baseline,

                "ppo_approach_mean_s": (
                    ppo["total_approach_time_s"].mean()
                ),

                "baseline_approach_mean_s": (
                    base["total_approach_time_s"].mean()
                ),

                "ppo_task_travel_mean_s": (
                    ppo["total_task_travel_time_s"].mean()
                ),

                "baseline_task_travel_mean_s": (
                    base["total_task_travel_time_s"].mean()
                ),

                "approach_difference_s": (
                    approach_diff.mean()
                ),

                "task_travel_difference_s": (
                    task_diff.mean()
                ),

                "total_travel_difference_s": (
                    total_diff.mean()
                ),

                "identical_task_travel_seeds": int(
                    task_match.sum()
                ),

                "paired_seeds": len(ppo),
            })

    result = pd.DataFrame(records)

    assert len(result) == 20

    return result


# ============================================================
# 9. Utilization analysis
# ============================================================

def utilization_analysis(runs):

    records = []

    for (workload, method), group in runs.groupby(
        GROUP_KEYS,
        sort=False,
    ):

        records.append({
            "workload": workload,
            "method": method,

            "average_utilization_mean": (
                group["average_robot_utilization"]
                .mean()
            ),

            "max_utilization_mean": (
                group["max_robot_utilization"]
                .mean()
            ),

            "utilization_gap_mean": (
                group["utilization_gap"].mean()
            ),

            "utilization_gap_sd": (
                group["utilization_gap"].std(ddof=1)
            ),

            "jain_task_fairness_mean": (
                group["jain_task_fairness"].mean()
            ),

            "makespan_mean_s": (
                group["makespan_s"].mean()
            ),
        })

    return pd.DataFrame(records)


# ============================================================
# 10. Battery and charging analysis
# ============================================================

def battery_analysis(runs):

    records = []

    for (workload, method), group in runs.groupby(
        GROUP_KEYS,
        sort=False,
    ):

        soc = group["minimum_robot_soc"]

        assert soc.between(
            0, 1
        ).all()

        assert group[
            "average_final_soc"
        ].between(0, 1).all()

        below = soc < (
            RESERVE_SOC - 1e-9
        )

        records.append({
            "workload": workload,
            "method": method,
            "seed_count": len(group),

            "reserve_soc": RESERVE_SOC,

            "minimum_soc_mean": soc.mean(),

            "lowest_observed_soc": soc.min(),

            "episodes_below_reserve": int(
                below.sum()
            ),

            "minimum_reserve_margin": (
                group["battery_reserve_margin"]
                .min()
            ),

            "average_final_soc_mean": (
                group["average_final_soc"].mean()
            ),

            "return_to_charge_mean": (
                group["total_return_to_charge_count"]
                .mean()
            ),

            "charging_count_mean": (
                group["total_charging_count"]
                .mean()
            ),

            "charging_per_100_tasks_mean": (
                group["charging_per_100_tasks"]
                .mean()
            ),

            "charging_per_100_tasks_sd": (
                group["charging_per_100_tasks"]
                .std(ddof=1)
            ),

            "return_charge_count_equal_episodes": int(
                (
                    group["total_return_to_charge_count"]
                    == group["total_charging_count"]
                ).sum()
            ),
        })

    return pd.DataFrame(records)


# ============================================================
# 11. Console summary
# ============================================================

def show_table(title, df):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    print(
        df.to_string(
            index=False,
            float_format=lambda x: f"{x:.5f}",
        )
    )


# ============================================================
# Main
# ============================================================

def main():

    if OUTPUT.exists() and any(
        OUTPUT.iterdir()
    ):

        raise RuntimeError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    runs = load_data()

    runs = add_derived_metrics(runs)

    descriptive = descriptive_statistics(runs)

    checked = verify_original_summary(
        descriptive
    )

    stats, counts = paired_analysis(runs)

    best = best_baseline_comparison(stats)

    priority = priority_analysis(runs)

    travel = travel_analysis(runs)

    utilization = utilization_analysis(runs)

    battery = battery_analysis(runs)

    print()
    print("===== SECONDARY BOOTSTRAP RESULTS =====")

    print(counts.to_string())

    print()
    print("Overall:")
    print(counts.sum().to_string())

    print()
    print("===== SECONDARY HOLM T-TEST =====")

    print(
        pd.crosstab(
            stats["metric"],
            stats["holm_t_verdict"],
        ).to_string()
    )

    print(
        stats["holm_t_verdict"]
        .value_counts()
        .to_string()
    )

    print()
    print("===== SECONDARY HOLM WILCOXON =====")

    print(
        pd.crosstab(
            stats["metric"],
            stats["holm_wilcoxon_significant"],
        ).to_string()
    )

    print(
        "Significant comparisons:",
        int(
            stats[
                "holm_wilcoxon_significant"
            ].sum()
        ),
    )

    show_table(
        "BEST BASELINE - SECONDARY METRICS",

        best[[
            "workload",
            "metric",
            "baseline",
            "baseline_mean",
            "ppo_mean",
            "relative_improvement_pct",
            "bootstrap_verdict",
        ]],
    )

    show_table(
        "PRIORITY ANALYSIS - WORKLOAD 4.0",

        priority.loc[
            priority["workload"] == 4.0
        ],
    )

    show_table(
        "TRAVEL DECOMPOSITION - ALL WORKLOADS",

        travel[[
            "workload",
            "baseline",
            "approach_difference_s",
            "task_travel_difference_s",
            "total_travel_difference_s",
            "identical_task_travel_seeds",
        ]],
    )

    show_table(
        "UTILIZATION - WORKLOAD 4.0",

        utilization.loc[
            utilization["workload"] == 4.0
        ],
    )

    show_table(
        "BATTERY - WORKLOAD 4.0",

        battery.loc[
            battery["workload"] == 4.0
        ],
    )

    print()
    print("===== BATTERY RESERVE CHECK =====")

    print(
        "Lowest observed SOC:",
        battery["lowest_observed_soc"].min(),
    )

    print(
        "Episodes below reserve:",
        int(
            battery["episodes_below_reserve"].sum()
        ),
    )

    print(
        "Identical task travel comparisons:",
        int(
            travel[
                "identical_task_travel_seeds"
            ].sum()
        ),
        "/ 600",
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    outputs = {
        "secondary_descriptive_summary.csv":
            descriptive,

        "secondary_paired_bootstrap.csv":
            stats,

        "secondary_best_baseline.csv":
            best,

        "priority_waiting_summary.csv":
            priority,

        "travel_decomposition.csv":
            travel,

        "utilization_summary.csv":
            utilization,

        "battery_charging_summary.csv":
            battery,
    }

    for name, table in outputs.items():

        table.to_csv(
            OUTPUT / name,
            index=False,
        )

    counts.to_csv(
        OUTPUT / "secondary_bootstrap_counts.csv"
    )

    runs[
        KEYS + list(DERIVED_METRICS)
    ].to_csv(
        OUTPUT / "derived_episode_metrics.csv",
        index=False,
    )

    manifest = {
        "created_at": (
            datetime.now().astimezone().isoformat()
        ),

        "scope": "Exploratory secondary metrics",

        "source_runs_sha256": sha256(
            SOURCE / "comparison_runs.csv"
        ),

        "source_summary_sha256": sha256(
            SOURCE / "comparison_summary.csv"
        ),

        "primary_analysis_metadata_sha256": sha256(
            PRIMARY / "analysis_metadata.json"
        ),

        "analysis_script_sha256": sha256(
            Path(__file__)
        ),

        "evaluation_episodes": 750,

        "secondary_metric_count": 15,

        "derived_metric_count": 4,

        "secondary_inference_metric_count": 7,

        "comparison_count": 140,

        "summary_values_verified": checked,

        "bootstrap_iterations": (
            BOOTSTRAP_ITERATIONS
        ),

        "bootstrap_seed": BOOTSTRAP_SEED,

        "paired_seeds_per_comparison": 30,

        "confidence_level": 0.95,

        "confidence_intervals":
            "Individual, unadjusted",

        "difference_direction":
            "Positive means PPO better for seven inference metrics",

        "travel_decomposition_direction":
            "PPO minus baseline; positive means additional travel",

        "multiple_testing":
            "Separate Holm family of 140 comparisons per test",

        "wilcoxon_interpretation":
            "Two-sided signed-rank test; significance and median direction reported separately",

        "best_baseline":
            "Descriptive selection using observed means",

        "task_sequence_check":
            "Equal task counts verified; full sequence not established by this script",

        "battery_reserve_soc": RESERVE_SOC,

        "bootstrap_counts": {
            str(k): int(v)
            for k, v in counts.sum().items()
        },

        "primary_results_modified": False,

        "new_simulations": 0,

        "models_retrained": False,

        "packages": {
            name: version(name)
            for name in [
                "numpy",
                "pandas",
                "scipy",
            ]
        },

        "output_sha256": {
            path.name: sha256(path)
            for path in sorted(
                OUTPUT.glob("*.csv")
            )
        },
    }

    (
        OUTPUT / "secondary_analysis_metadata.json"
    ).write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print()
    print("===== SECONDARY ANALYSIS COMPLETE =====")
    print("Source episodes: 750")
    print("Secondary metrics: 15")
    print("Derived metrics: 4")
    print("Descriptive rows:", len(descriptive))
    print("Paired comparisons:", len(stats))
    print("Summary values verified:", checked)
    print("Output:", OUTPUT)
    print("Primary results modified: NO")
    print("New simulations: 0")
    print("PPO retrained: NO")
    print("Analysis: PASS")


if __name__ == "__main__":

    main()

