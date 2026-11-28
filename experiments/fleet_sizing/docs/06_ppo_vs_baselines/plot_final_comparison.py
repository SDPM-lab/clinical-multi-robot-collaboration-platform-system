from pathlib import Path
from datetime import datetime
import hashlib
import json

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import PercentFormatter


# ============================================================
# Configuration
# ============================================================

DOC = Path(__file__).resolve().parent
DATA = DOC / "data"
FIGURES = DOC / "figures"

PPO = "ppo_sweep12_seed7101"

METHODS = [
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
    PPO,
]

BASELINES = METHODS[:-1]

WORKLOADS = [3.0, 3.5, 4.0, 4.5, 5.0]

LABELS = {
    "random_feasible": "Random Feasible",
    "projected_nearest": "Projected Nearest",
    "static_weighted": "Static Weighted",
    "dynamic_weighted": "Dynamic Weighted",
    PPO: "Maskable PPO",
}

SHORT = {
    "random_feasible": "Random",
    "projected_nearest": "Nearest",
    "static_weighted": "Static",
    "dynamic_weighted": "Dynamic",
    PPO: "PPO",
}

BLUE = "#2563EB"

COLORS = dict(zip(
    METHODS,
    ["#B0B0B0", "#333333", "#777777", "#A0A0A0", BLUE],
))

STYLES = dict(zip(
    METHODS,
    ["--", "-", "-.", ":", "-"],
))

MARKERS = dict(zip(
    METHODS,
    ["o", "s", "^", "D", "o"],
))

PRIMARY = {
    "average_waiting_time_s": "Average Waiting Time",
    "p95_waiting_time_s": "P95 Waiting Time",
    "high_waiting_time_s": "High Priority Waiting Time",
    "emergency_waiting_time_s": "Emergency Waiting Time",
    "total_travel_time_s": "Total Travel Time",
    "jain_task_fairness": "Jain Task Fairness",
}

SECONDARY = {
    "low_waiting_time_s": "Low Waiting Time",
    "normal_waiting_time_s": "Normal Waiting Time",
    "average_response_time_s": "Average Response Time",
    "p95_response_time_s": "P95 Response Time",
    "average_total_time_s": "Average Total Time",
    "p95_total_time_s": "P95 Total Time",
    "total_approach_time_s": "Total Approach Time",
}

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.edgecolor": "#333333",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#D8D8D8",
    "grid.alpha": 0.7,
    "grid.linestyle": "--",
    "legend.frameon": False,
    "legend.fontsize": 9,
    "text.color": "#111111",
    "axes.labelcolor": "#111111",
    "xtick.color": "#111111",
    "ytick.color": "#111111",
    "svg.fonttype": "none",
})


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


# ============================================================
# 1. Source integrity
# ============================================================

archive = read_json(
    DATA / "archive_manifest.json"
)

assert archive["file_count"] == 25

for item in archive["files"]:

    path = DOC / item["archive"]

    assert path.is_file(), path
    assert sha(path) == item["sha256"], path

print("Archived data integrity: PASS")

runs = pd.read_csv(
    DATA / "evaluation/comparison_runs.csv"
)

summary = pd.read_csv(
    DATA / "evaluation/comparison_summary.csv"
)

stats = pd.read_csv(
    DATA / "analysis/paired_bootstrap_results.csv"
)

best = pd.read_csv(
    DATA / "analysis/best_baseline_comparison.csv"
)

history = pd.read_csv(
    DATA / "analysis/historical_reproducibility.csv"
)

aux = pd.read_csv(
    DATA / "secondary_analysis/secondary_paired_bootstrap.csv"
)

aux_best = pd.read_csv(
    DATA / "secondary_analysis/secondary_best_baseline.csv"
)

priority = pd.read_csv(
    DATA / "secondary_analysis/priority_waiting_summary.csv"
)

travel = pd.read_csv(
    DATA / "secondary_analysis/travel_decomposition.csv"
)

utilization = pd.read_csv(
    DATA / "secondary_analysis/utilization_summary.csv"
)

battery = pd.read_csv(
    DATA / "secondary_analysis/battery_charging_summary.csv"
)

evaluation = read_json(
    DATA / "evaluation/experiment_metadata.json"
)

assert len(runs) == 750
assert len(summary) == 25
assert len(stats) == 120
assert len(aux) == 140

assert not runs.duplicated([
    "workload_multiplier", "method", "seed",
]).any()

assert stats["bootstrap_verdict"].value_counts().to_dict() == {
    "ppo_better": 91,
    "ppo_worse": 16,
    "ci_crosses_zero": 13,
}

assert aux["bootstrap_verdict"].value_counts().to_dict() == {
    "ppo_better": 93,
    "ppo_worse": 16,
    "ci_includes_zero": 31,
}

# Do not silently overwrite existing generated figures.

if FIGURES.exists() and any(FIGURES.rglob("*.png")):
    raise RuntimeError(
        "Existing PNG figures detected. "
        "Preserve them before regeneration."
    )

if FIGURES.exists() and any(FIGURES.rglob("*.svg")):
    raise RuntimeError(
        "Existing SVG figures detected. "
        "Preserve them before regeneration."
    )

FIGURES.mkdir(parents=True, exist_ok=True)

registry = []


# ============================================================
# 2. Shared plotting utilities
# ============================================================

def save(fig, folder, name, sources):

    directory = FIGURES / folder
    directory.mkdir(parents=True, exist_ok=True)

    paths = []

    for ext in ("png", "svg"):

        path = directory / f"{name}.{ext}"

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.15,
        )

        paths.append({
            "file": str(path.relative_to(DOC)),
            "sha256": sha(path),
            "size_bytes": path.stat().st_size,
        })

    registry.append({
        "name": name,
        "sources": [
            {
                "file": source,
                "sha256": sha(DOC / source),
            }
            for source in sources
        ],
        "outputs": paths,
    })

    plt.close(fig)

    print(f"{name}: PNG + SVG PASS")


def footer(fig, text):

    fig.text(
        0.5, 0.015,
        text,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#555555",
    )


def legend(fig, handles, labels):

    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=3,
    )


def workload_axis(ax):

    ax.set_xticks(WORKLOADS)

    ax.set_xticklabels([
        f"{w:.1f}x" for w in WORKLOADS
    ])

    ax.set_xlabel("Workload Multiplier")

    ax.set_axisbelow(True)


def draw_line(
    ax,
    metric,
    title,
    ylabel,
    scale=1.0,
    show_sd=True,
):

    for method in METHODS:

        group = summary.loc[
            summary["method"] == method
        ].sort_values("workload_multiplier")

        x = group["workload_multiplier"].to_numpy()

        y = (
            group[metric + "_mean"].to_numpy()
            * scale
        )

        sd = (
            group[metric + "_std"].to_numpy()
            * scale
        )

        if show_sd:

            ax.errorbar(
                x, y, yerr=sd,
                label=LABELS[method],
                color=COLORS[method],
                linestyle=STYLES[method],
                marker=MARKERS[method],
                linewidth=2.5 if method == PPO else 1.5,
                markersize=6 if method == PPO else 5,
                capsize=3,
                elinewidth=0.9,
                alpha=1.0,
                zorder=5 if method == PPO else 2,
            )

        else:

            ax.plot(
                x, y,
                label=LABELS[method],
                color=COLORS[method],
                linestyle=STYLES[method],
                marker=MARKERS[method],
                linewidth=2.5 if method == PPO else 1.5,
                zorder=5 if method == PPO else 2,
            )

    ax.set_title(title)
    ax.set_ylabel(ylabel)

    workload_axis(ax)


def simple_metric(
    number,
    metric,
    title,
    ylabel,
    scale=1.0,
    show_sd=True,
):

    fig, ax = plt.subplots(
        figsize=(10, 6)
    )

    draw_line(
        ax, metric, title, ylabel,
        scale, show_sd,
    )

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
    )

    footer(
        fig,
        "30 evaluation seeds per point"
        + (
            " | Error bars: mean +/- sample SD"
            if show_sd else ""
        ),
    )

    fig.tight_layout(rect=[0, 0.055, 1, 1])

    save(
        fig,
        "primary_metrics",
        f"{number:02d}_{metric}",
        ["data/evaluation/comparison_summary.csv"],
    )


# ============================================================
# Figure 01: Experimental Setup
# ============================================================

fig, ax = plt.subplots(figsize=(12, 7))

ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis("off")

fig.suptitle(
    "Final Evaluation Framework",
    fontsize=18,
    fontweight="bold",
)


def block(x, y, width, height, title, text, color):

    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.06",
        facecolor="white",
        edgecolor=color,
        linewidth=1.6,
    )

    ax.add_patch(patch)

    ax.text(
        x + width / 2,
        y + height * 0.72,
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=color,
    )

    ax.text(
        x + width / 2,
        y + height * 0.32,
        text,
        ha="center",
        va="center",
        fontsize=10,
    )


block(
    2, 5.5, 8, 1.1,
    "Nav2-Calibrated Scheduling Environment",
    "7 robots (2, 2, 3) | Battery model enabled",
    BLUE,
)

block(
    0.4, 3.3, 5.3, 1.5,
    "Four Baseline Schedulers",
    "Random / Projected Nearest\n"
    "Static alpha = 0.6\n"
    "Dynamic alpha = [0.4, 0.9]",
    "#555555",
)

block(
    6.3, 3.3, 5.3, 1.5,
    "Maskable PPO",
    "Nav2 Sweep 12 | Model seed 7101\n"
    "Reward: W/A/Q/I = 0.40/0.35/0.15/0.10",
    BLUE,
)

block(
    2, 1.5, 8, 1.1,
    "750 Evaluation Episodes",
    "5 methods x 5 workloads x 30 seeds\n"
    "Evaluation seeds: 9601-9630",
    "#333333",
)

block(
    2, 0.1, 8, 0.95,
    "Primary and Exploratory Secondary Analysis",
    "22 original metrics + 4 derived metrics\n"
    "120 primary + 140 exploratory comparisons",
    "#333333",
)

for x1, y1, x2, y2 in [
    (6, 5.5, 3, 4.85),
    (6, 5.5, 9, 4.85),
    (3, 3.3, 6, 2.65),
    (9, 3.3, 6, 2.65),
    (6, 1.5, 6, 1.1),
]:

    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={
            "arrowstyle": "->",
            "color": "#555555",
            "lw": 1.4,
        },
    )

save(
    fig,
    "overview",
    "01_experimental_setup",
    [
        "data/archive_manifest.json",
        "data/evaluation/experiment_metadata.json",
    ],
)


# ============================================================
# Figures 02-08: Primary metrics
# ============================================================

for number, metric in enumerate(PRIMARY, start=2):

    ylabel = (
        "Jain Fairness Index"
        if metric == "jain_task_fairness"
        else "Time (hours)"
        if metric == "total_travel_time_s"
        else "Time (seconds)"
    )

    scale = (
        1 / 3600
        if metric == "total_travel_time_s"
        else 1
    )

    if metric == "total_travel_time_s":

        fig, axes = plt.subplots(
            1, 2,
            figsize=(14, 6),
        )

        draw_line(
            axes[0],
            metric,
            "Total Travel Time",
            "Time (hours)",
            scale=1 / 3600,
        )

        axes[0].legend(loc="upper left")

        group = stats.loc[
            stats["metric"] == metric
        ]

        for baseline in BASELINES:

            rows = group.loc[
                group["baseline"] == baseline
            ].sort_values("workload")

            axes[1].plot(
                rows["workload"],
                -rows["relative_improvement_pct"],
                label=SHORT[baseline],
                color=COLORS[baseline],
                linestyle=STYLES[baseline],
                marker=MARKERS[baseline],
                linewidth=1.8,
            )

        axes[1].axhline(
            0,
            color=BLUE,
            linestyle="--",
            linewidth=1.2,
        )

        workload_axis(axes[1])

        axes[1].set_title(
            "PPO Additional Travel Cost"
        )

        axes[1].set_ylabel(
            "Relative Travel Increase (%)"
        )

        axes[1].legend(loc="best")

        fig.suptitle(
            "Total Travel Time and Cost Trade-off",
            fontsize=17,
            fontweight="bold",
        )

        footer(
            fig,
            "Left: mean +/- sample SD. "
            "Right: positive values indicate additional PPO travel."
        )

        fig.tight_layout(
            rect=[0, 0.05, 1, 0.94]
        )

        save(
            fig,
            "primary_metrics",
            "06_total_travel_time_s",
            [
                "data/evaluation/comparison_summary.csv",
                "data/analysis/paired_bootstrap_results.csv",
            ],
        )

    else:

        simple_metric(
            number,
            metric,
            PRIMARY[metric],
            ylabel,
            scale,
        )

fig, ax = plt.subplots(
    figsize=(10, 6)
)

rates = []
completed = []
episode_counts = []

for method in METHODS:

    group = runs.loc[
        runs["method"] == method
    ]

    assert len(group) == 150

    rates.append(
        100 * group["completion_rate"].mean()
    )

    completed.append(
        int((group["completion_rate"] == 1).sum())
    )

    episode_counts.append(len(group))

x = np.arange(len(METHODS))

bars = ax.bar(
    x,
    rates,
    width=0.6,
    color=[COLORS[m] for m in METHODS],
)

ax.set_xticks(
    x,
    [SHORT[m] for m in METHODS],
)

ax.set_ylim(0, 100)

ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.yaxis.set_major_formatter(
    PercentFormatter(xmax=100)
)

ax.set_ylabel("Mean Task Completion Rate")
ax.set_title("Task Completion Rate", pad=28)

ax.set_axisbelow(True)
ax.grid(axis="x", visible=False)

for i, bar in enumerate(bars):

    ax.annotate(
        f"{rates[i]:.0f}%",
        (
            bar.get_x() + bar.get_width() / 2,
            rates[i],
        ),
        xytext=(0, 5),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontweight="bold",
        annotation_clip=False,
    )

    ax.text(
        i, rates[i] * 0.5,
        f"{completed[i]}/{episode_counts[i]}",
        ha="center",
        va="center",
        color=(
            "#111111"
            if METHODS[i] == "random_feasible"
            else "white"
        ),
        fontweight="bold",
    )

footer(
    fig,
    "Bar labels: fully completed episodes / evaluated episodes. "
    "All methods completed every generated task."
)

fig.tight_layout(
    rect=[0, 0.055, 1, 1]
)

save(
    fig,
    "primary_metrics",
    "08_completion_rate",
    ["data/evaluation/comparison_runs.csv"],
)


# ============================================================
# Shared heatmap utility
# ============================================================

def improvement_heatmap(
    table,
    metrics,
    name,
    folder,
    title,
    source,
    best_only=False,
):

    rows = []
    values = []

    for metric, label in metrics.items():

        if best_only:

            group = table.loc[
                table["metric"] == metric
            ].set_index("workload").reindex(WORKLOADS)

            rows.append(label)

            values.append(
                group["relative_improvement_pct"].to_numpy()
            )

        else:

            for baseline in BASELINES:

                group = table.loc[
                    (table["metric"] == metric)
                    &
                    (table["baseline"] == baseline)
                ].set_index("workload").reindex(WORKLOADS)

                rows.append(
                    f"{label} | {SHORT[baseline]}"
                )

                values.append(
                    group[
                        "relative_improvement_pct"
                    ].to_numpy()
                )

    values = np.asarray(values)

    assert np.isfinite(values).all()

    limit = max(
        1, np.abs(values).max()
    )

    fig, ax = plt.subplots(
        figsize=(10, max(5, len(rows) * 0.36 + 2)),
    )

    im = ax.imshow(
        values,
        cmap="RdBu",
        norm=TwoSlopeNorm(
            vmin=-limit,
            vcenter=0,
            vmax=limit,
        ),
        aspect="auto",
    )

    ax.grid(False)

    ax.set_xticks(
        range(len(WORKLOADS)),
        [f"{w:.1f}x" for w in WORKLOADS],
    )

    ax.set_yticks(
        range(len(rows)),
        rows,
    )

    ax.set_title(title, pad=15)
    ax.set_xlabel("Workload Multiplier")

    for i in range(len(rows)):

        for j in range(len(WORKLOADS)):

            value = values[i, j]

            ax.text(
                j, i,
                f"{value:+.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color=(
                    "white"
                    if abs(value) > limit * 0.6
                    else "#111111"
                ),
            )

    if not best_only:

        for boundary in range(
            len(BASELINES),
            len(rows),
            len(BASELINES),
        ):

            ax.axhline(
                boundary - 0.5,
                color="white",
                linewidth=2.5,
            )

    fig.colorbar(
        im,
        ax=ax,
        shrink=0.8,
        label="Relative Improvement (%)",
    )

    footer(
        fig,
        "Positive = PPO better; negative = PPO worse. "
        "Based on observed means.",
    )

    fig.tight_layout(rect=[0, 0.045, 1, 1])

    save(fig, folder, name, [source])


# ============================================================
# Figures 09-10: Relative improvement
# ============================================================

improvement_heatmap(
    stats,
    PRIMARY,
    "09_primary_relative_improvement",
    "statistical_analysis",
    "PPO Relative Improvement over Each Baseline",
    "data/analysis/paired_bootstrap_results.csv",
)

improvement_heatmap(
    best,
    PRIMARY,
    "10_best_baseline_comparison",
    "statistical_analysis",
    "PPO vs. Best Observed Baseline",
    "data/analysis/best_baseline_comparison.csv",
    best_only=True,
)


# ============================================================
# Statistical count utility
# ============================================================

def count_bars(ax, counts, labels, title):

    colors = [
        BLUE,
        "#C47A65",
        "#D4D4D4",
    ]

    names = [
        "PPO Better",
        "PPO Worse",
        "Inconclusive / Not Significant",
    ]

    y = np.arange(len(labels))
    left = np.zeros(len(labels))

    for j in range(3):

        vals = counts[:, j]

        ax.barh(
            y,
            vals,
            left=left,
            color=colors[j],
            label=names[j],
        )

        for i, value in enumerate(vals):

            if value > 0:

                ax.text(
                    left[i] + value / 2,
                    i,
                    str(int(value)),
                    ha="center",
                    va="center",
                    fontsize=10,
                    color=(
                        "white"
                        if j < 2 else "#111111"
                    ),
                )

        left += vals

    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.set_xlabel("Number of Comparisons")
    ax.set_axisbelow(True)
    ax.grid(axis="y", visible=False)


def metric_counts(table, metric_map, column, neutral):

    result = []

    for metric in metric_map:

        group = table.loc[
            table["metric"] == metric
        ]

        counts = group[column].value_counts()

        result.append([
            counts.get("ppo_better", 0),
            counts.get("ppo_worse", 0),
            counts.get(neutral, 0),
        ])

    return np.asarray(result)


# ============================================================
# Figure 11: Primary bootstrap
# ============================================================

fig, ax = plt.subplots(figsize=(10, 5.8))

counts = metric_counts(
    stats,
    PRIMARY,
    "bootstrap_verdict",
    "ci_crosses_zero",
)

count_bars(
    ax,
    counts,
    list(PRIMARY.values()),
    "Primary Paired Bootstrap Results",
)

ax.set_xlim(0, 20)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.16),
    ncol=3,
)

footer(
    fig,
    "91 better / 16 worse / 13 include zero"
    " | Individual 95% confidence intervals",
)

fig.tight_layout(rect=[0, 0.08, 1, 1])

save(
    fig,
    "statistical_analysis",
    "11_primary_bootstrap_results",
    ["data/analysis/paired_bootstrap_results.csv"],
)


# ============================================================
# Figure 12: Holm-corrected results
# ============================================================

fig, ax = plt.subplots(figsize=(10, 4.8))

overall = []

for column in [
    "bootstrap_verdict",
    "holm_t_p_verdict",
    "holm_wilcoxon_p_verdict",
]:

    c = stats[column].value_counts()

    better = c.get("ppo_better", 0)
    worse = c.get("ppo_worse", 0)

    overall.append([
        better,
        worse,
        len(stats) - better - worse,
    ])

count_bars(
    ax,
    np.asarray(overall),
    [
        "Paired Bootstrap",
        "Holm Paired t-test",
        "Holm Wilcoxon",
    ],
    "Primary Statistical Results",
)

ax.set_xlim(0, 120)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.21),
    ncol=3,
)

footer(
    fig,
    f"{archive['statistical_agreement']['all_three_better']}/120 "
    "comparisons classified as PPO better by all three methods.\n"
    "Holm correction per test family; "
    "Wilcoxon direction uses mean-difference sign.",
)

fig.tight_layout(rect=[0, 0.15, 1, 1])

save(
    fig,
    "statistical_analysis",
    "12_holm_corrected_results",
    ["data/analysis/paired_bootstrap_results.csv"],
)


# ============================================================
# Figure 13: Paired confidence intervals
# ============================================================

fig, axes = plt.subplots(
    3, 2,
    figsize=(14, 12),
)

for ax, (metric, label) in zip(
    axes.flat,
    PRIMARY.items(),
):

    group = stats.loc[
        (stats["workload"] == 4.0)
        &
        (stats["metric"] == metric)
    ].set_index("baseline").reindex(BASELINES)

    center = group[
        "mean_difference"
    ].to_numpy()

    lower = group[
        "ci_95_low"
    ].to_numpy()

    upper = group[
        "ci_95_high"
    ].to_numpy()

    ax.axvline(
        0, color="#333333",
        linestyle="--",
        linewidth=1.2,
    )

    for i in range(len(group)):

        color = (
            BLUE
            if lower[i] > 0
            else "#C47A65"
            if upper[i] < 0
            else "#888888"
        )

        ax.hlines(
            i,
            lower[i],
            upper[i],
            color=color,
            linewidth=2,
        )

        ax.scatter(
            center[i], i,
            color=color,
            s=40,
            zorder=4,
        )

    ax.set_yticks(
        range(4),
        [SHORT[b] for b in BASELINES],
    )

    ax.invert_yaxis()
    ax.set_title(label)

    ax.set_xlabel(
        "Jain Index Difference"
        if metric == "jain_task_fairness"
        else "Time Difference (s)"
    )

fig.suptitle(
    "Paired 95% Confidence Intervals at Workload 4.0x",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "Positive = PPO better. "
    "10,000 paired bootstrap resamples; individual intervals.",
)

fig.tight_layout(rect=[0, 0.045, 1, 0.95])

save(
    fig,
    "statistical_analysis",
    "13_paired_confidence_intervals",
    ["data/analysis/paired_bootstrap_results.csv"],
)


# ============================================================
# Figure 14: Performance trade-off
# ============================================================

fig, axes = plt.subplots(
    1, 2,
    figsize=(13, 6),
)

group = summary.loc[
    summary["workload_multiplier"] == 4.0
].set_index("method").reindex(METHODS)

for ax, metric, title in [
    (
        axes[0],
        "average_waiting_time_s",
        "Average Waiting vs. Travel",
    ),
    (
        axes[1],
        "emergency_waiting_time_s",
        "Emergency Waiting vs. Travel",
    ),
]:

    for method in METHODS:

        x = (
            group.loc[
                method,
                "total_travel_time_s_mean",
            ] / 3600
        )

        y = group.loc[
            method, metric + "_mean"
        ]

        ax.scatter(
            x, y,
            s=130 if method == PPO else 80,
            color=COLORS[method],
            marker=MARKERS[method],
            edgecolors="#333333",
            linewidths=0.6,
        )

        offsets = {
            "random_feasible": (-8, 12),
            "projected_nearest": (8, 8),
            "static_weighted": (-10, -15),
            "dynamic_weighted": (10, 12),
            PPO: (-10, -16),
        }

        offset = offsets[method]

        ax.annotate(
            SHORT[method],
            (x, y),
            xytext=offset,
            textcoords="offset points",
            ha="right" if offset[0] < 0 else "left",
            fontsize=10,
            color=BLUE if method == PPO else "#333333",
            fontweight="bold" if method == PPO else "normal",
        )

    ax.set_xlabel(
        "Total Task-related Travel Time (hours)"
    )

    ax.set_ylabel("Waiting Time (seconds)")
    ax.set_title(title)
    ax.margins(0.18)

fig.suptitle(
    "Scheduling Performance Trade-off",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "Workload 4.0x | 30-seed means | Lower-left is preferable.\n"
    "PPO vs. Static: emergency waiting "
    f"{100 * (group.loc[PPO, 'emergency_waiting_time_s_mean'] / group.loc['static_weighted', 'emergency_waiting_time_s_mean'] - 1):+.2f}%; "
    "total travel "
    f"{100 * (group.loc[PPO, 'total_travel_time_s_mean'] / group.loc['static_weighted', 'total_travel_time_s_mean'] - 1):+.2f}%.",
)

fig.tight_layout(rect=[0, 0.10, 1, 0.94])

save(
    fig,
    "statistical_analysis",
    "14_performance_tradeoff",
    ["data/evaluation/comparison_summary.csv"],
)


# ============================================================
# Figure 15: Historical reproducibility
# ============================================================

fig, ax = plt.subplots(figsize=(12, 6))

x = np.arange(len(METHODS))
width = 0.12

for i, (metric, label) in enumerate(
    PRIMARY.items()
):

    group = history.loc[
        history["metric"] == metric
    ].set_index("method").reindex(METHODS)

    ax.bar(
        x + (i - 2.5) * width,
        group["matched_episodes"],
        width=width,
        label=label,
        color=plt.cm.Greys(0.3 + i * 0.11),
    )

ax.set_xticks(
    x,
    [SHORT[m] for m in METHODS],
)

ax.set_ylim(0, 165)

ax.set_ylabel("Matching Episodes")
ax.set_title("Historical Result Reproducibility")

ax.axhline(
    150,
    color=BLUE,
    linestyle="--",
)

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.12),
    ncol=3,
)

footer(
    fig,
    "150 episodes per method. Static and Dynamic weights "
    "were intentionally changed.",
)

fig.tight_layout(rect=[0, 0.12, 1, 1])

save(
    fig,
    "reproducibility",
    "15_historical_reproducibility",
    ["data/analysis/historical_reproducibility.csv"],
)


# ============================================================
# Figure 16: Priority analysis
# ============================================================

fig, axes = plt.subplots(
    2, 3,
    figsize=(16, 9),
)

priorities = [
    "low", "normal", "high", "emergency"
]

x = np.arange(4)
width = 0.15

for ax, workload in zip(
    axes.flat,
    WORKLOADS,
):

    for i, method in enumerate(METHODS):

        group = priority.loc[
            (priority["workload"] == workload)
            &
            (priority["method"] == method)
        ].set_index("priority").reindex(priorities)

        ax.bar(
            x + (i - 2) * width,
            group["mean_wait_s"],
            width=width,
            color=COLORS[method],
            label=LABELS[method],
        )

    ax.set_xticks(
        x,
        [p.title() for p in priorities],
    )

    ax.set_title(f"Workload {workload:.1f}x")
    ax.set_ylabel("Mean Waiting Time (s)")

axes.flat[-1].axis("off")

handles, labels = axes.flat[0].get_legend_handles_labels()

axes.flat[-1].legend(
    handles,
    labels,
    loc="center",
    fontsize=12,
)

fig.suptitle(
    "Waiting Time by Task Priority",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "30 evaluation seeds per method and workload.",
)

fig.tight_layout(rect=[0, 0.04, 1, 0.95])

save(
    fig,
    "secondary_metrics",
    "16_waiting_time_by_priority",
    [
        "data/secondary_analysis/priority_waiting_summary.csv",
    ],
)


# ============================================================
# Figures 17-18: Response and total time
# ============================================================

for number, prefix, title in [
    (17, "response", "Task Response Time"),
    (18, "total", "Task Total Time"),
]:

    fig, axes = plt.subplots(
        1, 2,
        figsize=(13, 6),
    )

    draw_line(
        axes[0],
        f"average_{prefix}_time_s",
        "Average " + title,
        "Time (seconds)",
    )

    draw_line(
        axes[1],
        f"p95_{prefix}_time_s",
        "P95 " + title,
        "Time (seconds)",
    )

    handles, labels = axes[0].get_legend_handles_labels()

    legend(fig, handles, labels)

    fig.suptitle(
        title + " Analysis",
        fontsize=17,
        fontweight="bold",
    )

    footer(
        fig,
        "30 evaluation seeds | Error bars: mean +/- sample SD.",
    )

    fig.tight_layout(
        rect=[0, 0.05, 1, 0.83]
    )

    save(
        fig,
        "secondary_metrics",
        f"{number:02d}_{prefix}_time_analysis",
        ["data/evaluation/comparison_summary.csv"],
    )


# ============================================================
# Figure 19: Travel decomposition
# ============================================================

fig, axes = plt.subplots(
    1, 2,
    figsize=(14, 6),
)

group = summary.loc[
    summary["workload_multiplier"] == 4.0
].set_index("method").reindex(METHODS)

approach = (
    group["total_approach_time_s_mean"].to_numpy()
    / 3600
)

task_travel = (
    group["total_task_travel_time_s_mean"].to_numpy()
    / 3600
)

x = np.arange(len(METHODS))

axes[0].bar(
    x,
    task_travel,
    color="#D0D0D0",
    label="Task Travel",
)

axes[0].bar(
    x,
    approach,
    bottom=task_travel,
    color=[COLORS[m] for m in METHODS],
    label="Approach",
)

axes[0].set_xticks(
    x,
    [SHORT[m] for m in METHODS],
)

axes[0].set_ylabel("Travel Time (hours)")
axes[0].set_title("Travel Components at 4.0x")
axes[0].legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.12),
    ncol=2,
)

for baseline in BASELINES:

    group = travel.loc[
        travel["baseline"] == baseline
    ].sort_values("workload")

    axes[1].plot(
        group["workload"],
        group["approach_difference_s"] / 3600,
        color=COLORS[baseline],
        linestyle=STYLES[baseline],
        marker=MARKERS[baseline],
        label=SHORT[baseline],
        linewidth=1.8,
    )

axes[1].axhline(
    0,
    color=BLUE,
    linestyle="--",
)

axes[1].set_ylabel(
    "PPO - Baseline Approach Time (hours)"
)

axes[1].set_title("Additional Approach Cost")

workload_axis(axes[1])
axes[1].legend()

fig.suptitle(
    "Travel Time Decomposition",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    f"{travel['identical_task_travel_seeds'].sum()}/600 "
    "paired task travel totals matched. "
    "Travel differences originate from approach time.",
)

fig.tight_layout(rect=[0, 0.12, 1, 0.94])

save(
    fig,
    "secondary_metrics",
    "19_travel_time_decomposition",
    [
        "data/evaluation/comparison_summary.csv",
        "data/secondary_analysis/travel_decomposition.csv",
    ],
)


# ============================================================
# Generic descriptive line utility
# ============================================================

def descriptive_line(
    ax,
    table,
    metric,
    title,
    ylabel,
    scale=1,
):

    for method in METHODS:

        group = table.loc[
            table["method"] == method
        ].sort_values("workload")

        ax.plot(
            group["workload"],
            group[metric] * scale,
            label=LABELS[method],
            color=COLORS[method],
            linestyle=STYLES[method],
            marker=MARKERS[method],
            linewidth=2.5 if method == PPO else 1.5,
        )

    ax.set_title(title)
    ax.set_ylabel(ylabel)

    workload_axis(ax)


# ============================================================
# Figure 20: Utilization
# ============================================================

fig, axes = plt.subplots(
    2, 2,
    figsize=(13, 10),
)

for ax, config in zip(
    axes.flat,
    [
        (
            "average_utilization_mean",
            "Average Robot Utilization",
            "Utilization (%)",
            100,
        ),
        (
            "max_utilization_mean",
            "Maximum Robot Utilization",
            "Utilization (%)",
            100,
        ),
        (
            "utilization_gap_mean",
            "Utilization Gap",
            "Percentage Points",
            100,
        ),
        (
            "jain_task_fairness_mean",
            "Jain Task Fairness",
            "Jain Index",
            1,
        ),
    ],
):

    descriptive_line(
        ax, utilization, *config
    )

handles, labels = axes.flat[0].get_legend_handles_labels()

legend(fig, handles, labels)

fig.suptitle(
    "Robot Utilization and Load Distribution",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "Descriptive analysis. "
    "Utilization and task-count fairness measure different properties.",
)

fig.tight_layout(rect=[0, 0.045, 1, 0.86])

save(
    fig,
    "secondary_metrics",
    "20_robot_utilization_analysis",
    ["data/secondary_analysis/utilization_summary.csv"],
)


# ============================================================
# Figure 21: Battery analysis
# ============================================================

fig, axes = plt.subplots(
    2, 2,
    figsize=(13, 10),
)

for ax, config in zip(
    axes.flat,
    [
        (
            "lowest_observed_soc",
            "Lowest Observed SOC",
            "SOC (%)",
            100,
        ),
        (
            "average_final_soc_mean",
            "Average Final SOC",
            "SOC (%)",
            100,
        ),
        (
            "charging_count_mean",
            "Mean Charging Count",
            "Charging Events",
            1,
        ),
        (
            "charging_per_100_tasks_mean",
            "Charging per 100 Tasks",
            "Charging Events",
            1,
        ),
    ],
):

    descriptive_line(
        ax, battery, *config
    )

reserve = battery["reserve_soc"].iloc[0]

assert (
    battery["reserve_soc"] == reserve
).all()

axes.flat[0].axhline(
    reserve * 100,
    linestyle="--",
    color="#C47A65",
    linewidth=1.6,
)

axes.flat[0].text(
    3.03,
    reserve * 100 + 0.12,
    f"Reserve threshold: {reserve:.0%}",
    color="#A44C3B",
    fontsize=9,
)

axes.flat[0].set_ylim(14.5, 20)

handles, labels = axes.flat[0].get_legend_handles_labels()

legend(fig, handles, labels)

fig.suptitle(
    "Battery and Charging Behavior",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "0/750 episodes below reserve. "
    "Lowest observed SOC: "
    f"{battery['lowest_observed_soc'].min():.2%}. "
    "Simulation records only.",
)

fig.tight_layout(rect=[0, 0.045, 1, 0.86])

save(
    fig,
    "secondary_metrics",
    "21_battery_charging_analysis",
    ["data/secondary_analysis/battery_charging_summary.csv"],
)


# ============================================================
# Figure 22: Secondary improvement heatmap
# ============================================================

improvement_heatmap(
    aux_best,
    SECONDARY,
    "22_secondary_relative_improvement",
    "secondary_metrics",
    "Secondary Metrics vs. Best Observed Baseline",
    "data/secondary_analysis/secondary_best_baseline.csv",
    best_only=True,
)


# ============================================================
# Figure 23: Secondary statistical analysis
# ============================================================

fig, axes = plt.subplots(
    1, 2,
    figsize=(15, 6),
)

counts_boot = metric_counts(
    aux,
    SECONDARY,
    "bootstrap_verdict",
    "ci_includes_zero",
)

counts_holm = metric_counts(
    aux,
    SECONDARY,
    "holm_t_verdict",
    "not_significant",
)

count_bars(
    axes[0],
    counts_boot,
    list(SECONDARY.values()),
    "Paired Bootstrap",
)

count_bars(
    axes[1],
    counts_holm,
    list(SECONDARY.values()),
    "Holm Paired t-test",
)

for ax in axes:

    ax.set_xlim(0, 20)

axes[1].tick_params(
    axis="y",
    labelleft=False,
    left=False,
)

handles, labels = axes[0].get_legend_handles_labels()

legend(fig, handles, labels)

fig.suptitle(
    "Exploratory Secondary Statistical Analysis",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "140 exploratory comparisons | Separate Holm family. "
    "Bootstrap: 93/16/31 | Holm t-test: 67/15/58.\n"
    f"Holm Wilcoxon: {int(aux['holm_wilcoxon_significant'].sum())}/140 "
    "significant comparisons (direction not pooled).",
)

fig.tight_layout(rect=[0, 0.10, 1, 0.84])

save(
    fig,
    "statistical_analysis",
    "23_secondary_statistical_analysis",
    ["data/secondary_analysis/secondary_paired_bootstrap.csv"],
)


# ============================================================
# Figure manifest
# ============================================================

assert len(registry) == 23

pngs = list(FIGURES.rglob("*.png"))
svgs = list(FIGURES.rglob("*.svg"))

assert len(pngs) == 23
assert len(svgs) == 23

manifest = {
    "created_at": datetime.now().astimezone().isoformat(),
    "figure_count": len(registry),
    "png_count": len(pngs),
    "svg_count": len(svgs),
    "png_dpi": 300,
    "matplotlib_version": matplotlib.__version__,
    "archive_manifest_sha256": sha(
        DATA / "archive_manifest.json"
    ),
    "plot_script_sha256": sha(
        Path(__file__)
    ),
    "style": {
        "background": "white",
        "text": "black",
        "ppo": BLUE,
        "baselines": "grayscale",
        "language": "English",
    },
    "figures": registry,
}

(
    FIGURES / "figure_manifest.json"
).write_text(
    json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== FINAL FIGURE REPORT =====")
print("Figure groups:", len(registry))
print("PNG files:", len(pngs))
print("SVG files:", len(svgs))
print("Source data integrity: PASS")
print("Original data modified: NO")
print("New simulations: 0")
print("Figures: COMPLETE")
