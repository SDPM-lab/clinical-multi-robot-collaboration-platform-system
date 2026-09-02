#!/usr/bin/env python3

import os

import pandas as pd
import matplotlib.pyplot as plt


# ==========================================================
# Path
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RESULT_DIR = os.path.join(
    SCRIPT_DIR,
    "results",
)

SUMMARY_CSV = os.path.join(
    RESULT_DIR,
    "baseline_summary.csv",
)

PLOT_DIR = os.path.join(
    RESULT_DIR,
    "plots",
)


# ==========================================================
# Plot Config
# ==========================================================

BASELINE_ORDER = [
    "FCFS + Nearest",
    "FCFS + Rule-based",
    "Priority + Nearest",
    "Priority + Rule-based",
]

LOAD_ORDER = [
    "low",
    "medium",
    "high",
]

TASK_COUNT_ORDER = [
    20,
    50,
    100,
]


# ==========================================================
# Load Data
# ==========================================================

def load_summary():

    if not os.path.exists(
        SUMMARY_CSV
    ):

        raise FileNotFoundError(
            "Summary CSV not found: "
            f"{SUMMARY_CSV}"
        )

    df = pd.read_csv(
        SUMMARY_CSV
    )

    return df


# ==========================================================
# Plot Metric
# ==========================================================

def plot_metric(
    df,
    metric_mean,
    metric_std,
    ylabel,
    title,
    filename,
):

    os.makedirs(
        PLOT_DIR,
        exist_ok=True,
    )

    # ------------------------------------------------------
    # 每種 Load 分開畫一張 Figure
    # ------------------------------------------------------

    for load in LOAD_ORDER:

        load_df = df[
            df["load"] == load
        ]

        plt.figure(
            figsize=(10, 6)
        )

        for baseline in BASELINE_ORDER:

            baseline_df = load_df[
                load_df["baseline"]
                == baseline
            ].copy()

            baseline_df = (
                baseline_df
                .sort_values(
                    "task_count"
                )
            )

            x = (
                baseline_df[
                    "task_count"
                ]
            )

            y = (
                baseline_df[
                    metric_mean
                ]
            )

            yerr = (
                baseline_df[
                    metric_std
                ]
            )

            plt.errorbar(
                x,
                y,
                yerr=yerr,
                marker="o",
                capsize=4,
                label=baseline,
            )

        plt.xlabel(
            "Task Count"
        )

        plt.ylabel(
            ylabel
        )

        plt.title(
            f"{title} - "
            f"{load.capitalize()} Load"
        )

        plt.xticks(
            TASK_COUNT_ORDER
        )

        plt.grid(
            True,
            alpha=0.3,
        )

        plt.legend()

        plt.tight_layout()

        output_path = os.path.join(
            PLOT_DIR,
            f"{filename}_{load}.png",
        )

        plt.savefig(
            output_path,
            dpi=200,
        )

        plt.close()

        print(
            "Saved:",
            output_path,
        )


# ==========================================================
# Main
# ==========================================================

def main():

    df = load_summary()

    print("=" * 100)
    print("Baseline Analysis")
    print("=" * 100)

    print(
        "Rows:",
        len(df),
    )

    print(
        "Loads:",
        sorted(
            df["load"].unique()
        ),
    )

    print(
        "Task Counts:",
        sorted(
            df[
                "task_count"
            ].unique()
        ),
    )

    print(
        "Baselines:",
        sorted(
            df[
                "baseline"
            ].unique()
        ),
    )

    print()

    # ======================================================
    # 1. Average Waiting Time
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "average_waiting_time_mean"
        ),

        metric_std=(
            "average_waiting_time_std"
        ),

        ylabel=(
            "Average Waiting Time (s)"
        ),

        title=(
            "Average Waiting Time"
        ),

        filename=(
            "average_waiting_time"
        ),
    )

    # ======================================================
    # 2. Emergency Waiting Time
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "emergency_waiting_time_mean"
        ),

        metric_std=(
            "emergency_waiting_time_std"
        ),

        ylabel=(
            "Emergency Waiting Time (s)"
        ),

        title=(
            "Emergency Waiting Time"
        ),

        filename=(
            "emergency_waiting_time"
        ),
    )

    # ======================================================
    # 3. Average Completion Time
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "average_completion_time_mean"
        ),

        metric_std=(
            "average_completion_time_std"
        ),

        ylabel=(
            "Average Completion Time (s)"
        ),

        title=(
            "Average Completion Time"
        ),

        filename=(
            "average_completion_time"
        ),
    )

    # ======================================================
    # 4. Total Travel Distance
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "total_travel_distance_mean"
        ),

        metric_std=(
            "total_travel_distance_std"
        ),

        ylabel=(
            "Total Travel Distance"
        ),

        title=(
            "Total Travel Distance"
        ),

        filename=(
            "total_travel_distance"
        ),
    )

    # ======================================================
    # 5. Makespan
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "makespan_mean"
        ),

        metric_std=(
            "makespan_std"
        ),

        ylabel=(
            "Makespan (s)"
        ),

        title=(
            "Makespan"
        ),

        filename=(
            "makespan"
        ),
    )

    # ======================================================
    # 6. Average Robot Utilization
    # ======================================================

    plot_metric(

        df,

        metric_mean=(
            "average_robot_utilization_mean"
        ),

        metric_std=(
            "average_robot_utilization_std"
        ),

        ylabel=(
            "Average Robot Utilization"
        ),

        title=(
            "Average Robot Utilization"
        ),

        filename=(
            "average_robot_utilization"
        ),
    )

    print()
    print("=" * 100)
    print("Analysis completed")
    print("=" * 100)

    print(
        "Plots directory:",
        PLOT_DIR,
    )


if __name__ == "__main__":
    main()