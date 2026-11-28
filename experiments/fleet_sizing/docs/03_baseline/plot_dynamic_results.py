from pathlib import Path
from collections import defaultdict

import csv
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data/calibration_v2/dynamic"

DIAGNOSTICS = (
    ROOT
    / "data/calibration_v2/diagnostics/dynamic_behavior"
)

OUTPUT = ROOT / "figures/dynamic"

OUTPUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# Style
# ============================================================

BLUE = "#2563EB"
DARK_BLUE = "#1D4ED8"
LIGHT_BLUE = "#93C5FD"
GRAY = "#CBD5E1"
BLACK = "#111111"
RED = "#DC2626"

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
# Read data
# ============================================================

runs = pd.read_csv(
    DATA / "runs.csv",
    float_precision="round_trip",
)

summary = pd.read_csv(
    DATA / "summary.csv",
    float_precision="round_trip",
)

ranking = pd.read_csv(
    DATA / "ranking.csv",
    float_precision="round_trip",
)

diagnostics = pd.read_csv(
    DIAGNOSTICS / "behavior_summary.csv"
)

with (DATA / "selected_parameters.json").open() as f:
    selection = json.load(f)

with (DATA / "experiment_metadata.json").open() as f:
    metadata = json.load(f)

SELECTED = (
    float(selection["selected_alpha_min"]),
    float(selection["selected_alpha_max"]),
)

ORIGINAL = tuple(
    selection["original_alpha_range"]
)

RESERVE = (
    metadata["battery_config"]
    ["BATTERY_MIN_RESERVE_SOC"]
    * 100
)

assert len(runs) == 550
assert len(summary) == 55
assert len(ranking) == 55
assert len(diagnostics) == 21

assert SELECTED == (0.4, 0.9)

assert not runs.duplicated(
    ["alpha_min", "alpha_max", "seed"]
).any()


PRIMARY_METRICS = {
    "average_waiting_time_s": -1,
    "p95_waiting_time_s": -1,
    "high_waiting_time_s": -1,
    "emergency_waiting_time_s": -1,
    "total_travel_time_s": -1,
    "jain_task_fairness": 1,
}


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


def pair_label(lo, hi):

    return f"[{lo:.1f}, {hi:.1f}]"


def pair_index(pair):

    lo, hi = pair

    return (
        round(lo * 10),
        round(hi * 10),
    )


def make_matrix(frame, field):

    matrix = np.full(
        (11, 11),
        np.nan,
    )

    for _, row in frame.iterrows():

        i, j = pair_index(
            (
                row["alpha_min"],
                row["alpha_max"],
            )
        )

        matrix[i, j] = float(
            row[field]
        )

    return matrix


def style_grid(ax):

    ax.set_xticks(range(11))

    ax.set_yticks(range(11))

    labels = [
        f"{i / 10:.1f}"
        for i in range(11)
    ]

    ax.set_xticklabels(labels)

    ax.set_yticklabels(labels)

    ax.set_xlabel("Alpha Max")

    ax.set_ylabel("Alpha Min")

    ax.set_xticks(
        np.arange(-0.5, 11, 1),
        minor=True,
    )

    ax.set_yticks(
        np.arange(-0.5, 11, 1),
        minor=True,
    )

    ax.grid(
        which="minor",
        color="white",
        linewidth=1,
    )

    ax.tick_params(
        which="minor",
        bottom=False,
        left=False,
    )


def mark_parameters(ax):

    for pair, style, color in (
        (ORIGINAL, "--", "#64748B"),
        (SELECTED, "-", BLACK),
    ):

        i, j = pair_index(pair)

        ax.add_patch(
            patches.Rectangle(
                (j - 0.48, i - 0.48),
                0.96,
                0.96,
                fill=False,
                linestyle=style,
                linewidth=2.0,
                edgecolor=color,
            )
        )

    ax.legend(
        handles=[
            patches.Patch(
                facecolor="none",
                edgecolor=BLACK,
                linewidth=2,
                label="Selected [0.4, 0.9]",
            ),
            patches.Patch(
                facecolor="none",
                edgecolor="#64748B",
                linestyle="--",
                linewidth=2,
                label="Original [0.4, 0.8]",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=2,
    )


# ============================================================
# Continuous heatmaps
# ============================================================

def heatmap(
    frame,
    field,
    title,
    colorbar_label,
    filename,
    higher_is_better=False,
    number_format=".1f",
    vmin=None,
    vmax=None,
):

    matrix = make_matrix(frame, field)

    cmap = plt.get_cmap(
        "Blues"
        if higher_is_better
        else "Blues_r"
    ).copy()

    cmap.set_bad("#F1F5F9")

    fig, ax = plt.subplots(
        figsize=(10.5, 8)
    )

    image = ax.imshow(
        np.ma.masked_invalid(matrix),
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        aspect="equal",
    )

    for i in range(11):

        for j in range(11):

            value = matrix[i, j]

            if not np.isfinite(value):
                continue

            rgba = cmap(
                image.norm(value)
            )

            luminance = (
                0.2126 * rgba[0]
                + 0.7152 * rgba[1]
                + 0.0722 * rgba[2]
            )

            text_color = (
                "white"
                if luminance < 0.48
                else BLACK
            )

            ax.text(
                j,
                i,
                format(value, number_format),
                ha="center",
                va="center",
                fontsize=7.5,
                color=text_color,
            )

    style_grid(ax)

    mark_parameters(ax)

    ax.set_title(title, pad=15)

    colorbar = fig.colorbar(
        image,
        ax=ax,
        shrink=0.80,
        pad=0.03,
    )

    colorbar.set_label(
        colorbar_label
    )

    save(fig, filename)


HEATMAPS = (
    (
        "mean_average_waiting_time_s",
        "Average Waiting Time",
        "Waiting Time (s)",
        "01_dynamic_average_wait",
        False,
        ".1f",
    ),
    (
        "mean_p95_waiting_time_s",
        "P95 Waiting Time",
        "Waiting Time (s)",
        "02_dynamic_p95_wait",
        False,
        ".1f",
    ),
    (
        "mean_high_waiting_time_s",
        "High Priority Waiting Time",
        "Waiting Time (s)",
        "03_dynamic_high_wait",
        False,
        ".1f",
    ),
    (
        "mean_emergency_waiting_time_s",
        "Emergency Waiting Time",
        "Waiting Time (s)",
        "04_dynamic_emergency_wait",
        False,
        ".1f",
    ),
    (
        "mean_total_travel_time_s",
        "Total Travel Time",
        "Travel Time (s)",
        "05_dynamic_total_travel",
        False,
        ",.0f",
    ),
    (
        "mean_jain_task_fairness",
        "Jain Task Fairness",
        "Jain Fairness Index",
        "06_dynamic_task_fairness",
        True,
        ".4f",
    ),
    (
        "mean_jain_utilization_fairness",
        "Jain Utilization Fairness",
        "Jain Fairness Index",
        "07_dynamic_utilization_fairness",
        True,
        ".4f",
    ),
)

for field, title, label, filename, higher, fmt in HEATMAPS:

    heatmap(
        summary,
        field,
        f"Dynamic Weight Sensitivity — {title}",
        label,
        filename,
        higher_is_better=higher,
        number_format=fmt,
    )


# ============================================================
# 08. Rank Sum
# ============================================================

heatmap(
    ranking,
    "rank_sum",
    "Dynamic Weight Selection — Rank Sum",
    "Rank Sum (Lower is Better)",
    "08_dynamic_rank_sum",
    number_format=".1f",
)


# ============================================================
# 09. Top 10 candidates
# ============================================================

top10 = ranking.head(10).copy()

labels = [
    pair_label(
        row.alpha_min,
        row.alpha_max,
    )
    for row in top10.itertuples()
]

colors = [
    DARK_BLUE if row.selected
    else LIGHT_BLUE if row.pareto_optimal
    else GRAY
    for row in top10.itertuples()
]

fig, ax = plt.subplots(
    figsize=(8.5, 5.8)
)

y = np.arange(len(top10))

bars = ax.barh(
    y,
    top10["rank_sum"],
    color=colors,
    height=0.65,
)

for bar, value in zip(
    bars,
    top10["rank_sum"],
):

    ax.text(
        bar.get_width() + 1,
        bar.get_y() + bar.get_height() / 2,
        f"{value:g}",
        va="center",
    )

ax.set_yticks(y)

ax.set_yticklabels(labels)

ax.invert_yaxis()

ax.set_xlim(
    0,
    top10["rank_sum"].max() * 1.17,
)

ax.set_xlabel("Rank Sum (Lower is Better)")

ax.set_title("Dynamic Weight Selection — Top 10")

ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25,
)

ax.set_axisbelow(True)

ax.legend(handles=[
    patches.Patch(
        color=DARK_BLUE,
        label="Selected",
    ),
    patches.Patch(
        color=LIGHT_BLUE,
        label="Pareto-optimal",
    ),
    patches.Patch(
        color=GRAY,
        label="Non-Pareto",
    ),
])

save(fig, "09_dynamic_top10_candidates")


# ============================================================
# 10. Original vs selected
# ============================================================

def get_summary(pair):

    return summary.loc[
        np.isclose(summary["alpha_min"], pair[0])
        &
        np.isclose(summary["alpha_max"], pair[1])
    ].iloc[0]


old = get_summary(ORIGINAL)

new = get_summary(SELECTED)

labels = [
    "Average Wait",
    "P95 Wait",
    "High Wait",
    "Emergency Wait",
    "Total Travel",
    "Jain Task Fairness",
]

improvements = []

for metric, direction in PRIMARY_METRICS.items():

    field = f"mean_{metric}"

    value = (
        direction
        * (new[field] - old[field])
        / old[field]
        * 100
    )

    improvements.append(value)

fig, ax = plt.subplots(
    figsize=(8.5, 5)
)

y = np.arange(len(labels))

ax.barh(
    y,
    improvements,
    color=[
        BLUE if v >= 0 else GRAY
        for v in improvements
    ],
    height=0.6,
)

for i, value in enumerate(improvements):

    ax.text(
        value + (0.15 if value >= 0 else -0.15),
        i,
        f"{value:+.4f}%",
        ha="left" if value >= 0 else "right",
        va="center",
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
    min(0, min(improvements)) - 0.5,
    max(improvements) + 3,
)

ax.set_xlabel(
    "Relative Improvement (%) — Positive is Better"
)

ax.set_title(
    "Dynamic Weight Comparison: "
    "[0.4, 0.8] vs. [0.4, 0.9]"
)

ax.grid(
    axis="x",
    linestyle="--",
    alpha=0.25,
)

ax.set_axisbelow(True)

save(
    fig,
    "10_dynamic_original_vs_selected",
)


# ============================================================
# 11. Dynamic alpha distribution
# ============================================================

behavior = (
    diagnostics.groupby(
        ["alpha_min", "alpha_max"]
    )[
        [
            "alpha_min_multi_pct",
            "alpha_intermediate_multi_pct",
            "alpha_max_multi_pct",
        ]
    ]
    .mean()
    .reset_index()
)

labels = [
    pair_label(
        row.alpha_min,
        row.alpha_max,
    )
    for row in behavior.itertuples()
]

fig, ax = plt.subplots(
    figsize=(9, 5.5)
)

y = np.arange(len(behavior))

left = np.zeros(len(behavior))

for field, color, label in (
    (
        "alpha_min_multi_pct",
        DARK_BLUE,
        "Alpha Min",
    ),
    (
        "alpha_intermediate_multi_pct",
        "#94A3B8",
        "Intermediate",
    ),
    (
        "alpha_max_multi_pct",
        LIGHT_BLUE,
        "Alpha Max",
    ),
):

    values = behavior[field].to_numpy()

    ax.barh(
        y,
        values,
        left=left,
        color=color,
        height=0.65,
        label=label,
    )

    for i, value in enumerate(values):

        if value >= 5:

            ax.text(
                left[i] + value / 2,
                i,
                f"{value:.1f}%",
                ha="center",
                va="center",
                color=(
                    "white"
                    if color == DARK_BLUE
                    else BLACK
                ),
                fontsize=10,
            )

    left += values

ax.set_yticks(y)

ax.set_yticklabels(labels)

ax.invert_yaxis()

ax.set_xlim(0, 100)

ax.set_xlabel("Multi-candidate Decisions (%)")

ax.set_title("Observed Dynamic Alpha Distribution")

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=3,
)

save(fig, "11_dynamic_alpha_distribution")


# ============================================================
# 12. Minimum battery SoC
# ============================================================

soc = (
    runs.groupby(
        ["alpha_min", "alpha_max"]
    )["minimum_robot_soc"]
    .min()
    .reset_index()
)

soc["minimum_soc_pct"] = (
    soc["minimum_robot_soc"] * 100
)

assert (
    soc["minimum_soc_pct"] >= RESERVE - 1e-7
).all()

heatmap(
    soc,
    "minimum_soc_pct",
    f"Minimum Battery SoC — Reserve {RESERVE:g}%",
    "Minimum SoC (%)",
    "12_dynamic_battery_soc",
    higher_is_better=True,
    number_format=".2f",
    vmin=RESERVE,
)


# ============================================================
# 13. Pareto front
# ============================================================

fig, ax = plt.subplots(
    figsize=(9, 8)
)

matrix = np.full(
    (11, 11),
    np.nan,
)

for row in ranking.itertuples():

    i, j = pair_index(
        (row.alpha_min, row.alpha_max)
    )

    matrix[i, j] = (
        2 if row.selected
        else 1 if row.pareto_optimal
        else 0
    )

cmap = mcolors.ListedColormap([
    GRAY,
    LIGHT_BLUE,
    DARK_BLUE,
])

cmap.set_bad("#F8FAFC")

ax.imshow(
    np.ma.masked_invalid(matrix),
    cmap=cmap,
    vmin=0,
    vmax=2,
)

style_grid(ax)

i, j = pair_index(SELECTED)

ax.text(
    j,
    i,
    "S",
    color="white",
    fontweight="bold",
    ha="center",
    va="center",
)

i, j = pair_index(ORIGINAL)

ax.add_patch(
    patches.Rectangle(
        (j - 0.48, i - 0.48),
        0.96,
        0.96,
        fill=False,
        linestyle="--",
        linewidth=2,
        edgecolor=BLACK,
    )
)

ax.set_title(
    "Dynamic Weight Selection — Pareto Front"
)

ax.legend(
    handles=[
        patches.Patch(
            color=DARK_BLUE,
            label="Selected",
        ),
        patches.Patch(
            color=LIGHT_BLUE,
            label="Other Pareto-optimal",
        ),
        patches.Patch(
            color=GRAY,
            label="Non-Pareto",
        ),
    ],
    loc="upper center",
    bbox_to_anchor=(0.5, -0.13),
    ncol=3,
)

save(fig, "13_dynamic_pareto_front")


# ============================================================
# 14. Parameter equivalence
# ============================================================

with (DATA / "runs.csv").open(
    encoding="utf-8-sig"
) as f:

    raw_rows = list(csv.DictReader(f))

grouped = defaultdict(list)

for row in raw_rows:

    pair = (
        float(row["alpha_min"]),
        float(row["alpha_max"]),
    )

    grouped[pair].append(row)

profiles = defaultdict(list)

fields = (
    *PRIMARY_METRICS,
    "completion_rate",
)

for pair, rows in sorted(grouped.items()):

    ordered = sorted(
        rows,
        key=lambda r: int(r["seed"]),
    )

    profile = tuple(
        (
            int(row["seed"]),
            *(float(row[field]) for field in fields),
        )
        for row in ordered
    )

    profiles[profile].append(pair)

equivalent_groups = [
    pairs
    for pairs in profiles.values()
    if len(pairs) > 1
]

assert len(profiles) == 27

assert len(equivalent_groups) == 7

matrix = np.full(
    (11, 11),
    np.nan,
)

for pair in grouped:

    i, j = pair_index(pair)

    matrix[i, j] = 0

for group_id, pairs in enumerate(
    equivalent_groups, 1
):

    for pair in pairs:

        i, j = pair_index(pair)

        matrix[i, j] = group_id

fig, ax = plt.subplots(
    figsize=(9, 8)
)

group_colors = [
    "#E2E8F0",
    "#1E40AF",
    "#2563EB",
    "#3B82F6",
    "#60A5FA",
    "#93C5FD",
    "#BFDBFE",
    "#DBEAFE",
]

cmap = mcolors.ListedColormap(
    group_colors
)

cmap.set_bad("#F8FAFC")

ax.imshow(
    np.ma.masked_invalid(matrix),
    cmap=cmap,
    vmin=-0.5,
    vmax=7.5,
)

for i in range(11):

    for j in range(11):

        value = matrix[i, j]

        if np.isfinite(value) and value > 0:

            ax.text(
                j,
                i,
                f"G{int(value)}",
                ha="center",
                va="center",
                fontsize=9,
                color=(
                    "white"
                    if value <= 3
                    else BLACK
                ),
            )

style_grid(ax)

mark_parameters(ax)

ax.set_title(
    "Dynamic Parameter Equivalence\n"
    "55 Candidates — 27 Unique Metric Profiles"
)

save(fig, "14_dynamic_parameter_equivalence")


# ============================================================
# Final check
# ============================================================

print()
print("===== DYNAMIC PLOTTING COMPLETE =====")
print("Original range:", ORIGINAL)
print("Selected range:", SELECTED)
print("Candidates:", len(summary))
print("Unique metric profiles:", len(profiles))
print("Equivalent groups:", len(equivalent_groups))
print("PNG figures:", len(list(OUTPUT.glob("*.png"))))
print("SVG figures:", len(list(OUTPUT.glob("*.svg"))))
print("Output directory:", OUTPUT)
