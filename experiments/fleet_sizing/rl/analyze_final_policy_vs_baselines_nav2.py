from pathlib import Path

import numpy as np
import pandas as pd

ROOT = (
    Path(__file__).resolve().parents[1]
    / "results_rl"
    / "final_policy_vs_baselines_seed7104_nav2_final30"
)

RUNS = ROOT / "comparison_runs.csv"
OUTPUT = ROOT / "paired_bootstrap_results.csv"

PPO = "ppo_sweep27_seed7104"

BASELINES = (
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
)

METRICS = (
    "average_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
)

B = 10000

df = pd.read_csv(RUNS)

results = []

for workload in sorted(df["workload_multiplier"].unique()):

    subset = df[df["workload_multiplier"] == workload]

    print(f"\nWORKLOAD {workload:.1f}")

    for baseline in BASELINES:

        paired = subset[
            subset["method"].isin((PPO, baseline))
        ].pivot(
            index="seed",
            columns="method",
            values=list(METRICS),
        )

        if len(paired) != 30:
            raise ValueError("Expected exactly 30 paired seeds")

        if paired.isna().any().any():
            raise ValueError("Missing paired results")

        for metric_idx, metric in enumerate(METRICS):

            ppo_values = paired[(metric, PPO)].to_numpy()
            baseline_values = paired[(metric, baseline)].to_numpy()

            difference = ppo_values - baseline_values

            rng = np.random.default_rng(
                20261019 + metric_idx
            )

            indices = rng.integers(
                0,
                len(difference),
                size=(B, len(difference)),
            )

            bootstrap_means = difference[indices].mean(axis=1)

            low, high = np.percentile(
                bootstrap_means,
                (2.5, 97.5),
            )

            results.append({
                "workload": workload,
                "baseline": baseline,
                "metric": metric,
                "ppo_mean": float(ppo_values.mean()),
                "baseline_mean": float(baseline_values.mean()),
                "mean_difference": float(difference.mean()),
                "ci_95_low": float(low),
                "ci_95_high": float(high),
                "ci_excludes_zero": bool(
                    low > 0 or high < 0
                ),
            })

        print(f"  Completed: PPO vs {baseline}")

output_df = pd.DataFrame(results)

output_df.to_csv(
    OUTPUT,
    index=False,
)

print("\n" + "=" * 75)
print("PAIRED BOOTSTRAP ANALYSIS COMPLETE")
print("Comparison rows:", len(output_df))
print("Results:", OUTPUT)
print("=" * 75)
