from pathlib import Path
from itertools import product
from collections import Counter
from importlib.metadata import version

import hashlib
import json

import numpy as np
import pandas as pd

from scipy.stats import ttest_rel, wilcoxon


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "results_rl"
    / "final_nav2_calibrated_baselines_sweep12_seed7101"
    / "full"
)

OUTPUT = SOURCE.parent / "analysis"

OLD = (
    ROOT / "results_rl"
    / "final_policy_vs_baselines_sweep12_seed7101_nav2_final30"
    / "comparison_runs.csv"
)

PPO = "ppo_sweep12_seed7101"

BASELINES = (
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
)

METHODS = (*BASELINES, PPO)

WORKLOADS = (3.0, 3.5, 4.0, 4.5, 5.0)

SEEDS = tuple(range(9601, 9631))

METRICS = {
    "average_waiting_time_s": -1,
    "p95_waiting_time_s": -1,
    "high_waiting_time_s": -1,
    "emergency_waiting_time_s": -1,
    "total_travel_time_s": -1,
    "jain_task_fairness": 1,
}

BOOTSTRAP_ITERATIONS = 10000
BOOTSTRAP_SEED = 20261127

KEYS = [
    "workload_multiplier",
    "method",
    "seed",
]


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def holm_adjust(pvalues):

    p = np.asarray(pvalues, dtype=float)

    assert np.isfinite(p).all()

    order = np.argsort(p)

    adjusted = np.empty_like(p)

    ranked = p[order]

    corrected = np.maximum.accumulate(
        ranked * (len(p) - np.arange(len(p)))
    )

    adjusted[order] = np.minimum(
        corrected, 1.0
    )

    return adjusted


def main():

    print("===== 1. SOURCE INTEGRITY =====")

    metadata = json.loads(
        (SOURCE / "experiment_metadata.json")
        .read_text()
    )

    assert metadata["status"] == "complete"

    for name, expected in (
        metadata["output_sha256"].items()
    ):

        assert sha256(
            SOURCE / name
        ) == expected, name

    assert metadata["baseline_parameters"] == {
        "static_alpha": 0.6,
        "dynamic_alpha_min": 0.4,
        "dynamic_alpha_max": 0.9,
    }

    assert metadata["fleet"] == [2, 2, 3]
    assert metadata["model_seed"] == 7101

    runs = pd.read_csv(
        SOURCE / "comparison_runs.csv"
    )

    summary = pd.read_csv(
        SOURCE / "comparison_summary.csv"
    )

    runtime = pd.read_csv(
        SOURCE / "runtime_nav2_checks.csv"
    )

    expected_keys = set(product(
        WORKLOADS,
        METHODS,
        SEEDS,
    ))

    actual_keys = set(
        runs[KEYS].itertuples(
            index=False,
            name=None,
        )
    )

    assert len(runs) == 750
    assert actual_keys == expected_keys
    assert not runs.duplicated(KEYS).any()

    assert len(summary) == 25
    assert not summary.duplicated(
        KEYS[:2]
    ).any()

    assert (summary["seed_count"] == 30).all()

    assert len(runtime) == 750
    assert not runtime.duplicated(KEYS).any()

    assert set(
        runtime[KEYS].itertuples(
            index=False,
            name=None,
        )
    ) == expected_keys

    assert runtime[
        "nav2_verified"
    ].astype(str).str.lower().eq("true").all()

    assert (runs["completion_rate"] == 1).all()

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

    print("750 episodes: PASS")
    print("25 summary groups: PASS")
    print("750 runtime checks: PASS")
    print("Input hashes: PASS")

    # --------------------------------------------------------
    # Recompute all historical summary statistics
    # --------------------------------------------------------

    print()
    print("===== 2. SUMMARY RECOMPUTATION =====")

    checked = 0

    for _, row in summary.iterrows():

        group = runs.loc[
            (runs["method"] == row["method"])
            &
            (
                runs["workload_multiplier"]
                == row["workload_multiplier"]
            )
        ]

        assert len(group) == 30

        for column in summary.columns:

            for suffix in (
                "_mean",
                "_std",
                "_median",
            ):

                if not column.endswith(suffix):
                    continue

                metric = column.removesuffix(
                    suffix
                )

                assert metric in group.columns

                values = group[metric].to_numpy(
                    dtype=float
                )

                assert np.isfinite(values).all()

                expected = {
                    "_mean": values.mean(),
                    "_std": values.std(ddof=1),
                    "_median": np.median(values),
                }[suffix]

                assert np.isclose(
                    float(row[column]),
                    expected,
                    rtol=1e-9,
                    atol=1e-8,
                ), (
                    row["method"],
                    row["workload_multiplier"],
                    column,
                )

                checked += 1

    print("Numeric values checked:", checked)
    print("Summary statistics: PASS")

    # --------------------------------------------------------
    # Historical reproducibility
    # --------------------------------------------------------

    print()
    print("===== 3. HISTORICAL REPRODUCIBILITY =====")

    old = pd.read_csv(OLD)

    merged = runs.merge(
        old,
        on=KEYS,
        suffixes=("_new", "_old"),
        validate="one_to_one",
    )

    assert len(merged) == 750

    reproducibility = []

    for method in METHODS:

        group = merged.loc[
            merged["method"] == method
        ]

        assert len(group) == 150

        changed = np.zeros(
            len(group), dtype=bool
        )

        for metric in METRICS:

            matched = np.isclose(
                group[f"{metric}_new"],
                group[f"{metric}_old"],
                rtol=1e-9,
                atol=1e-8,
            )

            changed |= ~matched

            reproducibility.append({
                "method": method,
                "metric": metric,
                "matched_episodes": int(
                    matched.sum()
                ),
                "different_episodes": int(
                    (~matched).sum()
                ),
            })

        print(
            method,
            "| identical episodes:",
            int((~changed).sum()),
            "/ 150",
        )

    # --------------------------------------------------------
    # Paired bootstrap and statistical tests
    # --------------------------------------------------------

    print()
    print("===== 4. PAIRED STATISTICAL ANALYSIS =====")

    rng = np.random.default_rng(
        BOOTSTRAP_SEED
    )

    records = []

    for workload in WORKLOADS:

        # Shared resampling indices for comparisons
        # within each workload.

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

            for metric, direction in METRICS.items():

                p = ppo[metric].to_numpy(
                    dtype=float
                )

                b = base[metric].to_numpy(
                    dtype=float
                )

                # Positive always means PPO better.
                difference = direction * (p - b)

                assert np.isfinite(difference).all()

                mean_difference = float(
                    difference.mean()
                )

                bootstrap = difference[
                    indices
                ].mean(axis=1)

                low, high = np.percentile(
                    bootstrap,
                    [2.5, 97.5],
                )

                if low > 0:
                    verdict = "ppo_better"

                elif high < 0:
                    verdict = "ppo_worse"

                else:
                    verdict = "ci_crosses_zero"

                if np.all(difference == 0):

                    t_p = 1.0
                    w_p = 1.0

                else:

                    if np.std(
                        difference, ddof=1
                    ) == 0:

                        t_p = 0.0

                    else:

                        t_p = float(
                            ttest_rel(p, b).pvalue
                        )

                    w_p = float(
                        wilcoxon(
                            difference,
                            alternative="two-sided",
                            zero_method="wilcox",
                            method="auto",
                        ).pvalue
                    )

                tie = np.isclose(
                    difference,
                    0,
                    atol=1e-8,
                    rtol=0,
                )

                wins = int(
                    ((difference > 0) & ~tie).sum()
                )

                losses = int(
                    ((difference < 0) & ~tie).sum()
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

                    "mean_difference": mean_difference,

                    "relative_improvement_pct": (
                        100 * mean_difference / b.mean()
                        if b.mean() != 0
                        else float("nan")
                    ),

                    "ci_95_low": float(low),
                    "ci_95_high": float(high),

                    "bootstrap_verdict": verdict,

                    "paired_t_p": t_p,
                    "wilcoxon_p": w_p,

                    "wins": wins,
                    "ties": int(tie.sum()),
                    "losses": losses,
                })

    stats = pd.DataFrame(records)

    assert len(stats) == 120

    assert (
        stats["wins"]
        + stats["ties"]
        + stats["losses"]
        == 30
    ).all()

    # Holm correction across all 120 comparisons,
    # separately for each statistical test family.

    stats["holm_t_p"] = holm_adjust(
        stats["paired_t_p"]
    )

    stats["holm_wilcoxon_p"] = holm_adjust(
        stats["wilcoxon_p"]
    )

    for column in (
        "paired_t_p",
        "wilcoxon_p",
        "holm_t_p",
        "holm_wilcoxon_p",
    ):

        stats[column + "_verdict"] = np.where(
            stats[column] < 0.05,

            np.where(
                stats["mean_difference"] > 0,
                "ppo_better",
                np.where(
                    stats["mean_difference"] < 0,
                    "ppo_worse",
                    "not_significant",
                ),
            ),

            "not_significant",
        )

    # --------------------------------------------------------
    # Aggregate statistical conclusions
    # --------------------------------------------------------

    print()
    print("===== 5. BOOTSTRAP RESULTS =====")

    verdict_counts = pd.crosstab(
        stats["metric"],
        stats["bootstrap_verdict"],
    ).reindex(
        index=list(METRICS),
        columns=[
            "ppo_better",
            "ppo_worse",
            "ci_crosses_zero",
        ],
        fill_value=0,
    )

    print(verdict_counts.to_string())

    print()
    print("Overall:")
    print(verdict_counts.sum().to_string())

    print()
    print("===== 6. HOLM-CORRECTED RESULTS =====")

    for name in (
        "holm_t_p_verdict",
        "holm_wilcoxon_p_verdict",
    ):

        print()
        print(name)

        print(
            pd.crosstab(
                stats["metric"],
                stats[name],
            ).to_string()
        )

        print(
            stats[name].value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # Best baseline descriptive comparison
    # --------------------------------------------------------

    best_records = []

    for (workload, metric), group in stats.groupby(
        ["workload", "metric"],
        sort=False,
    ):

        direction = METRICS[metric]

        index = (
            group["baseline_mean"].idxmin()
            if direction == -1
            else group["baseline_mean"].idxmax()
        )

        best_records.append(
            group.loc[index].to_dict()
        )

    best = pd.DataFrame(best_records)

    assert len(best) == 30

    print()
    print("===== 7. BEST BASELINE COMPARISON =====")

    columns = [
        "workload",
        "metric",
        "baseline",
        "baseline_mean",
        "ppo_mean",
        "relative_improvement_pct",
        "bootstrap_verdict",
    ]

    print(
        best[columns].to_string(
            index=False,
            float_format=lambda v: f"{v:.4f}",
        )
    )

    # --------------------------------------------------------
    # Export without overwriting previous results
    # --------------------------------------------------------

    if OUTPUT.exists() and any(
        OUTPUT.iterdir()
    ):

        raise RuntimeError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    stats.to_csv(
        OUTPUT / "paired_bootstrap_results.csv",
        index=False,
    )

    stats[[
        "workload",
        "baseline",
        "metric",
        "ppo_mean",
        "baseline_mean",
        "mean_difference",
        "relative_improvement_pct",
    ]].to_csv(
        OUTPUT / "relative_improvements.csv",
        index=False,
    )

    best.to_csv(
        OUTPUT / "best_baseline_comparison.csv",
        index=False,
    )

    verdict_counts.to_csv(
        OUTPUT / "bootstrap_summary_by_metric.csv"
    )

    pd.DataFrame(
        reproducibility
    ).to_csv(
        OUTPUT / "historical_reproducibility.csv",
        index=False,
    )

    manifest = {
        "source_metadata_sha256": sha256(
            SOURCE / "experiment_metadata.json"
        ),

        "source_runs_sha256": sha256(
            SOURCE / "comparison_runs.csv"
        ),

        "source_summary_sha256": sha256(
            SOURCE / "comparison_summary.csv"
        ),

        "analysis_script_sha256": sha256(
            Path(__file__)
        ),

        "comparison_count": 120,

        "paired_seeds_per_comparison": 30,

        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,

        "bootstrap_seed": BOOTSTRAP_SEED,

        "bootstrap_method":
            "Paired percentile bootstrap over evaluation seeds",

        "difference_direction":
            "Positive always means PPO better",

        "confidence_level": 0.95,

        "confidence_intervals":
            "Individual, not multiplicity-adjusted",

        "multiple_testing":
            "Holm across 120 comparisons per test family",

        "bootstrap_counts": {
            str(k): int(v)
            for k, v in Counter(
                stats["bootstrap_verdict"]
            ).items()
        },

        "best_baseline_comparison":
            "Descriptive, selected by observed mean",

        "task_sequence_check":
            "Equal generated counts verified; full sequences not verified here",

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
        OUTPUT / "analysis_metadata.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n"
    )

    print()
    print("===== FINAL ANALYSIS COMPLETE =====")
    print("Comparisons:", len(stats))
    print("Bootstrap iterations:", BOOTSTRAP_ITERATIONS)
    print("Best baseline comparisons:", len(best))
    print("Output:", OUTPUT)
    print("Original results modified: NO")
    print("New simulations: 0")
    print("PPO retrained: NO")
    print("Analysis: PASS")


if __name__ == "__main__":
    main()

