from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data" / "calibration_v2" / "static"

OUTPUT = ROOT / "figures" / "static"

OUTPUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# Style
# ============================================================

BLUE = "#2563EB"
DARK_BLUE = "#1D4ED8"
LIGHT_BLUE = "#93C5FD"
GRAY = "#CBD5E1"
RED = "#DC2626"
BLACK = "#111111"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.labelsize": 12,
    "axes.labelcolor": BLACK,
    "axes.edgecolor": BLACK,
    "text.color": BLACK,
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "svg.fonttype": "none",
})


# ============================================================
# Read validated data
# ============================================================

runs = pd.read_csv(DATA / "runs.csv")

summary = pd.read_csv(
    DATA / "summary.csv"
).sort_values("alpha")

ranking = pd.read_csv(
    DATA / "ranking.csv"
).sort_values("alpha")

with (DATA / "selected_parameters.json").open() as f:
    selected = json.load(f)

ALPHA = float(selected["selected_alpha"])

ORIGINAL = float(selected["original_alpha"])

assert len(runs) == 110
assert len(summary) == 11
assert len(ranking) == 11

assert not runs.duplicated(
    ["alpha", "seed"]
).any()

assert set(summary["alpha"]) == {
    i / 10 for i in range(11)
}

assert ALPHA == 0.6

x = summary["alpha"].to_numpy()


# ============================================================
# Helpers
# ============================================================

def save(fig, name):

    fig.tight_layout()

    for ext in ("png", "svg"):

        path = OUTPUT / f"{name}.{ext}"

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
        )

        print("Saved:", path)

    plt.close(fig)


def style_axis(ax, ylabel):

    ax.set_xlabel("Static Weight (α)")
    ax.set_ylabel(ylabel)

    ax.set_xticks(x)

    ax.set_xlim(-0.04, 1.04)

    ax.grid(
        axis="y",
        alpha=0.25,
        linestyle="--",
    )

    ax.set_axisbelow(True)


def selected_line(ax):

    ax.axvline(
        ALPHA,
        color=DARK_BLUE,
        linestyle="--",
        linewidth=1.2,
        alpha=0.75,
        label=f"Selected α = {ALPHA:.1f}",
    )


def plot_line(ax, column, label, color):

    ax.plot(
        x,
        summary[column],
        marker="o",
        markersize=5,
        linewidth=2,
        color=color,
        label=label,
    )

    row = summary.loc[
        np.isclose(summary["alpha"], ALPHA)
    ].iloc[0]

    ax.scatter(
        [ALPHA],
        [row[column]],
        s=95,
        facecolor=color,
        edgecolor="white",
        linewidth=1.5,
        zorder=5,
    )


# ============================================================
# 01. Waiting Time
# ============================================================

fig, ax = plt.subplots(figsize=(8.5, 5))

plot_line(
    ax,
    "mean_average_waiting_time_s",
    "Average Waiting Time",
    LIGHT_BLUE,
)

plot_line(
    ax,
    "mean_p95_waiting_time_s",
    "P95 Waiting Time",
    BLUE,
)

selected_line(ax)

style_axis(ax, "Waiting Time (s)")

ax.set_ylim(bottom=0)

ax.set_title(
    "Static Weight Sensitivity — Waiting Time"
)

ax.legend()

save(fig, "01_static_waiting_time")


# ============================================================
# 02. Priority Waiting Time
# ============================================================

fig, ax = plt.subplots(figsize=(8.5, 5))

plot_line(
    ax,
    "mean_high_waiting_time_s",
    "High",
    BLUE,
)

plot_line(
    ax,
    "mean_emergency_waiting_time_s",
    "Emergency",
    LIGHT_BLUE,
)

selected_line(ax)

style_axis(ax, "Average Waiting Time (s)")

ax.set_ylim(bottom=0)

ax.set_title(
    "Static Weight Sensitivity — Priority Waiting Time"
)

ax.legend()

save(fig, "02_static_priority_waiting_time")


# ============================================================
# 03. Total Travel Time
# ============================================================

fig, ax = plt.subplots(figsize=(8.5, 5))

plot_line(
    ax,
    "mean_total_travel_time_s",
    "Total Travel Time",
    BLUE,
)

selected_line(ax)

style_axis(ax, "Total Travel Time (s)")

ax.ticklabel_format(
    style="plain",
    axis="y",
    useOffset=False,
)

ax.set_title(
    "Static Weight Sensitivity — Total Travel Time"
)

ax.legend()

save(fig, "03_static_total_travel")


# ============================================================
# 04. Fairness
# ============================================================

fig, ax = plt.subplots(figsize=(8.5, 5))

plot_line(
    ax,
    "mean_jain_task_fairness",
    "Jain Task Fairness",
    BLUE,
)

plot_line(
    ax,
    "mean_jain_utilization_fairness",
    "Jain Utilization Fairness",
    LIGHT_BLUE,
)

selected_line(ax)

style_axis(ax, "Jain Fairness Index")

ax.set_ylim(0, 1.02)

ax.set_title(
    "Static Weight Sensitivity — Fairness"
)

ax.legend()

save(fig, "04_static_fairness")


# ============================================================
# 05. Rank Sum
# ============================================================

fig, ax = plt.subplots(figsize=(8.5, 5))

colors = []

for _, row in ranking.iterrows():

    if np.isclose(row["alpha"], ALPHA):
        colors.append(DARK_BLUE)

    elif not row["pareto_optimal"]:
        colors.append(GRAY)

    else:
        colors.append(LIGHT_BLUE)

bars = ax.bar(
    ranking["alpha"],
    ranking["rank_sum"],
    width=0.065,
    color=colors,
)

for bar, value in zip(
    bars,
    ranking["rank_sum"],
):

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.6,
        f"{value:g}",
        ha="center",
        fontsize=10,
    )

style_axis(ax, "Rank Sum (Lower is Better)")

ax.set_ylim(
    0,
    ranking["rank_sum"].max() * 1.18,
)

ax.set_title(
    "Static Weight Selection — Rank Sum"
)

from matplotlib.patches import Patch

ax.legend(handles=[
    Patch(
        color=DARK_BLUE,
        label=f"Selected α = {ALPHA:.1f}",
    ),
    Patch(
        color=LIGHT_BLUE,
        label="Pareto-optimal",
    ),
    Patch(
        color=GRAY,
        label="Non-Pareto",
    ),
])

save(fig, "05_static_rank_sum")


# ============================================================
# 06. Battery SoC
# ============================================================

minimum_soc = (
    runs.groupby("alpha")["minimum_robot_soc"]
    .min()
    .sort_index()
    * 100
)

fig, ax = plt.subplots(figsize=(8.5, 5))

colors = [
    DARK_BLUE if np.isclose(a, ALPHA)
    else LIGHT_BLUE
    for a in minimum_soc.index
]

bars = ax.bar(
    minimum_soc.index,
    minimum_soc.values,
    width=0.065,
    color=colors,
)

for bar, value in zip(
    bars,
    minimum_soc.values,
):

    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.35,
        f"{value:.2f}",
        ha="center",
        fontsize=9,
    )

ax.axhline(
    15,
    color=RED,
    linestyle="--",
    linewidth=1.5,
    label="Minimum Reserve: 15%",
)

style_axis(ax, "Minimum Battery SoC (%)")

ax.set_ylim(0, 25)

ax.set_title(
    "Static Weight Sensitivity — Battery Reserve"
)

ax.legend()

save(fig, "06_static_battery_soc")


# ============================================================
# 07. Original vs Selected
# ============================================================

old = summary.loc[
    np.isclose(summary["alpha"], ORIGINAL)
].iloc[0]

new = summary.loc[
    np.isclose(summary["alpha"], ALPHA)
].iloc[0]

metrics = [
    ("Average Wait", "mean_average_waiting_time_s", -1),
    ("P95 Wait", "mean_p95_waiting_time_s", -1),
    ("High Wait", "mean_high_waiting_time_s", -1),
    ("Emergency Wait", "mean_emergency_waiting_time_s", -1),
    ("Total Travel", "mean_total_travel_time_s", -1),
    ("Jain Task Fairness", "mean_jain_task_fairness", 1),
]

labels = []
improvements = []

for label, field, direction in metrics:

    value = (
        direction
        * (new[field] - old[field])
        / old[field]
        * 100
    )

    labels.append(label)
    improvements.append(value)

fig, ax = plt.subplots(figsize=(8.5, 5))

y = np.arange(len(labels))

colors = [
    BLUE if value >= 0 else "#94A3B8"
    for value in improvements
]

ax.barh(
    y,
    improvements,
    color=colors,
    height=0.6,
)

for i, value in enumerate(improvements):

    ax.text(
        value + (0.2 if value >= 0 else -0.2),
        i,
        f"{value:+.2f}%",
        va="center",
        ha="left" if value >= 0 else "right",
        fontsize=11,
    )

ax.axvline(
    0,
    color=BLACK,
    linewidth=1,
)

ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.invert_yaxis()

ax.set_xlim(
    min(improvements) - 3,
    max(improvements) + 3,
)

ax.set_xlabel(
    "Relative Improvement (%) — Positive is Better"
)

ax.set_title(
    f"Static Weight Comparison: "
    f"α = {ORIGINAL:.1f} vs. {ALPHA:.1f}"
)

ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25,
)

ax.set_axisbelow(True)

save(fig, "07_static_original_vs_selected")


print()
print("===== PLOTTING COMPLETE =====")
print("Selected alpha:", ALPHA)
print("Original alpha:", ORIGINAL)
print("Figures:", 7)
print("Output formats: PNG, SVG")
print("Output directory:", OUTPUT)
