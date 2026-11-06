from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# ============================================================
# Paths
# ============================================================

RESULTS_RL_ROOT = (
    Path(__file__).resolve().parents[1]
    / "results_rl"
)

RUNS_PATH = (
    RESULTS_RL_ROOT
    / "multiseed_battery_v2"
    / "comparison_runs.csv"
)


# ============================================================
# Metrics
# ============================================================

METRICS = (
    "average_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
    "completion_rate",
)


# ============================================================
# Helpers
# ============================================================

def mean_ci_95(values):
    values = np.asarray(
        values,
        dtype=float,
    )

    mean = float(
        np.mean(values)
    )

    if len(values) < 2:
        return mean, np.nan, np.nan

    sem = stats.sem(
        values
    )

    ci = stats.t.interval(
        0.95,
        df=len(values) - 1,
        loc=mean,
        scale=sem,
    )

    return (
        mean,
        float(ci[0]),
        float(ci[1]),
    )


def cohens_dz(differences):
    differences = np.asarray(
        differences,
        dtype=float,
    )

    std = np.std(
        differences,
        ddof=1,
    )

    if std == 0:
        return np.nan

    return float(
        np.mean(differences)
        / std
    )


# ============================================================
# Main
# ============================================================

def main():

    df = pd.read_csv(
        RUNS_PATH
    )

    dynamic = (
        df[
            df["method"]
            == "dynamic_weighted"
        ]
        .copy()
        .sort_values("seed")
    )

    ppo = (
        df[
            df["method"]
            .str.startswith(
                "ppo_seed_"
            )
        ]
        .copy()
    )

    print(
        "=" * 100
    )
    print(
        "PPO VS DYNAMIC WEIGHTED "
        "STATISTICAL ANALYSIS"
    )
    print(
        "=" * 100
    )

    print(
        "Dynamic episodes:",
        len(dynamic),
    )

    print(
        "PPO episodes:",
        len(ppo),
    )

    print()

    rows = []

    for metric in METRICS:

        # ----------------------------------------------------
        # Average PPO result across the 5 training seeds
        # for each evaluation seed
        # ----------------------------------------------------

        ppo_by_eval_seed = (
            ppo
            .groupby("seed")[
                metric
            ]
            .mean()
            .sort_index()
        )

        dynamic_by_seed = (
            dynamic
            .set_index("seed")[
                metric
            ]
            .sort_index()
        )

        common_seeds = (
            dynamic_by_seed.index
            .intersection(
                ppo_by_eval_seed.index
            )
        )

        dynamic_values = (
            dynamic_by_seed
            .loc[common_seeds]
            .to_numpy(
                dtype=float
            )
        )

        ppo_values = (
            ppo_by_eval_seed
            .loc[common_seeds]
            .to_numpy(
                dtype=float
            )
        )

        differences = (
            ppo_values
            - dynamic_values
        )

        diff_mean, ci_low, ci_high = (
            mean_ci_95(
                differences
            )
        )

        # ----------------------------------------------------
        # Paired t-test
        # ----------------------------------------------------

        t_result = (
            stats.ttest_rel(
                ppo_values,
                dynamic_values,
            )
        )

        # ----------------------------------------------------
        # Wilcoxon signed-rank
        # ----------------------------------------------------

        try:
            w_result = (
                stats.wilcoxon(
                    ppo_values,
                    dynamic_values,
                )
            )

            wilcoxon_p = float(
                w_result.pvalue
            )

        except ValueError:
            wilcoxon_p = np.nan

        # ----------------------------------------------------
        # Effect size
        # ----------------------------------------------------

        dz = cohens_dz(
            differences
        )

        dynamic_mean = float(
            np.mean(
                dynamic_values
            )
        )

        ppo_mean = float(
            np.mean(
                ppo_values
            )
        )

        if dynamic_mean != 0:

            percent_change = (
                (
                    ppo_mean
                    - dynamic_mean
                )
                / dynamic_mean
                * 100.0
            )

        else:
            percent_change = np.nan

        row = {
            "metric":
            metric,

            "n":
            len(
                common_seeds
            ),

            "dynamic_mean":
            dynamic_mean,

            "ppo_mean":
            ppo_mean,

            "percent_change":
            percent_change,

            "mean_difference":
            diff_mean,

            "ci95_low":
            ci_low,

            "ci95_high":
            ci_high,

            "paired_t_p":
            float(
                t_result.pvalue
            ),

            "wilcoxon_p":
            wilcoxon_p,

            "cohens_dz":
            dz,
        }

        rows.append(
            row
        )

    results = pd.DataFrame(
        rows
    )

    print(
        results.to_string(
            index=False,
            float_format=(
                lambda x:
                f"{x:.6f}"
            ),
        )
    )

    output_path = (
        RESULTS_RL_ROOT
        / "multiseed_battery_v2"
        / "ppo_vs_dynamic_statistics.csv"
    )

    results.to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        "Saved:",
        output_path,
    )


if __name__ == "__main__":
    main()