from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, Patch
import numpy as np
import pandas as pd


# ============================================================
# Paths and input data
# ============================================================

DOC = Path(__file__).resolve().parent
DATA = DOC / "data"
FIGURES = DOC / "figures"

S1 = DATA / "stage1_initial_sweep"
S2 = DATA / "stage2_pareto_confirmation"
S3 = DATA / "stage3_nav2_confirmation"
S4 = DATA / "stage4_final_selection"

BLUE = "#3276D5"
DARK_BLUE = "#174F91"
LIGHT_BLUE = "#91B9ED"
GRAY = "#B8BEC7"
LIGHT_GRAY = "#E8EBEF"
DARK_GRAY = "#626B78"
BLACK = "#202124"

METRICS = [
    "average_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
]

LABELS = [
    "Average Waiting Time (s)",
    "P95 Waiting Time (s)",
    "High Priority Waiting Time (s)",
    "Emergency Waiting Time (s)",
    "Total Travel Time (s)",
    "Jain Task Fairness",
]

WEIGHTS = [
    "waiting_weight",
    "approach_weight",
    "queue_weight",
    "imbalance_weight",
]

WEIGHT_COLORS = [
    DARK_BLUE,
    BLUE,
    LIGHT_BLUE,
    GRAY,
]

generated = []


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


# Verify input files before plotting.

archive_manifest_path = (
    DATA / "reward_selection_manifest.json"
)

analysis_manifest_path = (
    DATA / "reward_selection_analysis_manifest.json"
)

archive_manifest = json.loads(
    archive_manifest_path.read_text()
)

analysis_manifest = json.loads(
    analysis_manifest_path.read_text()
)

assert sha256(archive_manifest_path) == (
    analysis_manifest["archive_manifest_sha256"]
)

for entry in archive_manifest["files"]:

    path = DOC / entry["archive"]

    assert sha256(path) == entry["sha256"], path

for name, record in (
    analysis_manifest["generated_files"].items()
):

    assert sha256(DOC / name) == (
        record["sha256"]
    ), name

print("Input archive and analysis integrity: PASS")


stage1 = pd.read_csv(
    S1 / "pareto_analysis.csv"
)

stage2 = pd.read_csv(
    S2 / "pareto_analysis.csv"
)

stage3 = pd.read_csv(
    S3 / "pareto_analysis.csv"
)

stats = pd.read_csv(
    S4 / "final_candidate_statistics.csv"
)

emergency = pd.read_csv(
    S4 / "emergency_wait_by_seed.csv"
)

representative = pd.read_csv(
    S4 / "representative_model_selection.csv"
)

routes = pd.read_csv(
    DATA / "nav2_calibration"
    / "batch_route_summary_nav2.csv"
)


# ============================================================
# Shared style
# ============================================================

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "axes.titleweight": "semibold",
    "axes.edgecolor": BLACK,
    "axes.labelcolor": BLACK,
    "text.color": BLACK,
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "grid.color": "#DDE2E8",
    "grid.alpha": 0.8,
    "legend.frameon": False,
    "savefig.facecolor": "white",
    "svg.hashsalt": "reward-selection-v1",
})


def save(fig, folder, name):

    target = FIGURES / folder

    target.mkdir(
        parents=True,
        exist_ok=True
    )

    for suffix in ["png", "svg"]:

        path = target / f"{name}.{suffix}"

        options = {
            "bbox_inches": "tight",
            "pad_inches": 0.2,
            "facecolor": "white",
        }

        if suffix == "png":
            options["dpi"] = 300

        else:
            options["metadata"] = {
                "Date": None
            }

        fig.savefig(path, **options)

        generated.append({
            "file": str(path.relative_to(DOC)),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })

        print("Saved:", path.relative_to(DOC))

    plt.close(fig)


def config_labels(df):

    return [
        str(x).replace("sweep", "S")
        for x in df["config"]
    ]


def bool_column(series):

    return (
        series.astype(str)
        .str.lower()
        .eq("true")
        .to_numpy()
    )


def selection_colors(df):

    selected = bool_column(
        df["selected_for_next_stage"]
    )

    return [
        BLUE if value else GRAY
        for value in selected
    ]


# ============================================================
# Figure 01: Overall workflow
# ============================================================

fig, ax = plt.subplots(
    figsize=(11, 11)
)

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

workflow = [
    (
        "33 configurations",
        "Stage 1 - Initial reward sweep",
        "33 models | 50k steps | 660 episodes",
    ),
    (
        "15 configurations",
        "Stage 2 - Multi-seed confirmation",
        "75 models | 200k steps | 1,500 episodes",
    ),
    (
        "7 configurations",
        "Stage 3 - Nav2-calibrated training",
        "35 models | 200k steps | 1,050 episodes",
    ),
    (
        "2 final candidates",
        "Stage 4 - Final candidate comparison",
        "Sweep 12 and Sweep 25",
    ),
    (
        "Sweep 12",
        "Final reward configuration",
        "Emergency-task priority",
    ),
    (
        "Seed 7101",
        "Representative evaluation model",
        "Closest to configuration mean",
    ),
]

ys = np.linspace(
    0.86, 0.12, len(workflow)
)

for i, (count, title, detail) in enumerate(workflow):

    y = ys[i]

    highlight = i >= 2

    box = FancyBboxPatch(
        (0.11, y - 0.052),
        0.78,
        0.104,
        boxstyle="round,pad=0.012",
        facecolor=(
            "#F0F6FF"
            if highlight
            else "#F6F7F9"
        ),
        edgecolor=(
            BLUE if highlight else GRAY
        ),
        linewidth=1.4,
    )

    ax.add_patch(box)

    ax.text(
        0.5, y + 0.025,
        count,
        ha="center",
        va="center",
        fontsize=17,
        weight="bold",
        color=(
            DARK_BLUE
            if highlight
            else DARK_GRAY
        ),
    )

    ax.text(
        0.5, y - 0.005,
        title,
        ha="center",
        va="center",
        fontsize=11,
        weight="semibold",
    )

    ax.text(
        0.5, y - 0.028,
        detail,
        ha="center",
        va="center",
        fontsize=10,
    )

    if i < len(workflow) - 1:

        ax.annotate(
            "",
            xy=(0.5, ys[i + 1] + 0.068),
            xytext=(0.5, y - 0.068),
            arrowprops={
                "arrowstyle": "->",
                "color": DARK_GRAY,
                "lw": 1.5,
            },
        )

ax.set_title(
    "Reward Weight and Model Selection Workflow",
    fontsize=18,
    pad=18,
)

ax.text(
    0.5, 0.015,
    "143 training models and 3,210 unique evaluation episodes",
    ha="center",
    fontsize=10,
    color=DARK_GRAY,
)

save(
    fig, "overview",
    "01_reward_selection_workflow"
)


# ============================================================
# Figure 02: 33 reward weight configurations
# ============================================================

df = stage1.sort_values(
    "config"
).reset_index(drop=True)

fig, ax = plt.subplots(
    figsize=(15, 6)
)

x = np.arange(len(df))
bottom = np.zeros(len(df))

for column, label, color in zip(
    WEIGHTS,
    [
        "Waiting (W)",
        "Approach (A)",
        "Queue (Q)",
        "Imbalance (I)",
    ],
    WEIGHT_COLORS,
):

    values = df[column].to_numpy(
        dtype=float
    )

    ax.bar(
        x,
        values,
        bottom=bottom,
        color=color,
        width=0.82,
        label=label,
    )

    bottom += values

assert np.allclose(bottom, 1)

ax.set_xticks(
    x, config_labels(df),
    rotation=45
)

ax.set_ylim(0, 1.05)

ax.set_ylabel("Reward Weight")

ax.set_title(
    "33 Feasible Reward Weight Configurations"
)

ax.legend(
    ncol=4,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.17),
)

ax.grid(axis="y")

fig.tight_layout()

save(
    fig, "stage1",
    "02_reward_weight_configurations"
)


# ============================================================
# Shared six-metric performance chart
# ============================================================

def performance_figure(
    df,
    title,
    subtitle,
    folder,
    filename,
    show_std=False,
):

    df = df.sort_values(
        "config"
    ).reset_index(drop=True)

    fig, axes = plt.subplots(
        3, 2,
        figsize=(16, 12),
        constrained_layout=True,
    )

    x = np.arange(len(df))

    colors = selection_colors(df)

    for ax, metric, label in zip(
        axes.flat, METRICS, LABELS
    ):

        values = df[
            f"{metric}_mean"
        ].to_numpy(dtype=float)

        errors = (
            df[f"{metric}_std"].to_numpy(
                dtype=float
            )
            if show_std
            else None
        )

        ax.bar(
            x,
            values,
            color=colors,
            width=0.76,
            yerr=errors,
            capsize=2 if show_std else 0,
            error_kw={
                "elinewidth": 1,
                "ecolor": DARK_GRAY,
            },
        )

        ax.set_title(label)

        ax.set_xticks(
            x,
            config_labels(df),
            rotation=60 if len(df) > 10 else 0,
            fontsize=8 if len(df) > 15 else 10,
        )

        ax.grid(axis="y")

        if metric == "jain_task_fairness":

            ax.set_ylim(0, 1.1)

        if metric == "total_travel_time_s":

            ax.ticklabel_format(
                axis="y",
                style="sci",
                scilimits=(0, 0),
            )

    fig.suptitle(
        title + "\n" + subtitle,
        fontsize=16,
        weight="bold",
    )

    fig.legend(
        handles=[
            Patch(
                color=BLUE,
                label="Selected for next stage",
            ),
            Patch(
                color=GRAY,
                label="Other configurations",
            ),
        ],
        loc="outside lower center",
        ncol=2,
    )

    save(fig, folder, filename)


# ============================================================
# Figure 03: Stage 1 performance
# ============================================================

performance_figure(
    stage1,
    "Stage 1 - Initial Reward Sweep",
    "Preliminary environment | 33 configurations | 20 evaluation seeds",
    "stage1",
    "03_stage1_performance",
    show_std=False,
)


# ============================================================
# Shared Pareto dominance matrix
# ============================================================

def dominance_figure(
    df,
    title,
    folder,
    filename,
):

    df = df.sort_values(
        "config"
    ).reset_index(drop=True)

    names = df["config"].tolist()

    n = len(df)

    lookup = {
        name: i
        for i, name in enumerate(names)
    }

    matrix = np.zeros(
        (n, n),
        dtype=int
    )

    for j, row in df.iterrows():

        text = row["dominated_by"]

        if pd.isna(text):

            continue

        for dominator in str(text).split(";"):

            if dominator:

                matrix[
                    lookup[dominator], j
                ] = 1

    size = (
        12 if n > 20 else 8
    )

    fig, ax = plt.subplots(
        figsize=(size, size)
    )

    ax.imshow(
        matrix,
        cmap=ListedColormap(
            ["#F5F6F8", BLUE]
        ),
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )

    labels = config_labels(df)

    ax.set_xticks(
        np.arange(n),
        labels,
        rotation=90,
        fontsize=9,
    )

    ax.set_yticks(
        np.arange(n),
        labels,
        fontsize=9,
    )

    selected = bool_column(
        df["is_pareto"]
    )

    for tick, flag in zip(
        ax.get_xticklabels(),
        selected,
    ):

        if flag:
            tick.set_color(DARK_BLUE)
            tick.set_weight("bold")

    for tick, flag in zip(
        ax.get_yticklabels(),
        selected,
    ):

        if flag:
            tick.set_color(DARK_BLUE)
            tick.set_weight("bold")

    ax.set_xticks(
        np.arange(-0.5, n, 1),
        minor=True,
    )

    ax.set_yticks(
        np.arange(-0.5, n, 1),
        minor=True,
    )

    ax.grid(
        which="minor",
        color="white",
        linewidth=0.6,
    )

    ax.tick_params(
        which="minor",
        bottom=False,
        left=False,
    )

    ax.set_xlabel(
        "Dominated Configuration"
    )

    ax.set_ylabel(
        "Dominating Configuration"
    )

    ax.set_title(
        title
        + f"\n{selected.sum()} of {n} configurations are non-dominated",
        pad=16,
    )

    ax.legend(
        handles=[
            Patch(
                color=BLUE,
                label="Row dominates column",
            ),
            Patch(
                color="#F5F6F8",
                label="No dominance",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
    )

    fig.tight_layout()

    save(fig, folder, filename)


# ============================================================
# Figure 04: Stage 1 Pareto
# ============================================================

dominance_figure(
    stage1,
    "Stage 1 - Six-objective Pareto Analysis (33 to 15)",
    "stage1",
    "04_stage1_pareto_analysis",
)


# ============================================================
# Figure 05: Stage 2 performance
# ============================================================

performance_figure(
    stage2,
    "Stage 2 - Multi-seed Confirmation",
    "Preliminary environment | Mean +/- SD across 5 model seeds",
    "stage2",
    "05_stage2_multiseed_performance",
    show_std=True,
)


# ============================================================
# Figure 06: Stage 2 Pareto
# ============================================================

dominance_figure(
    stage2,
    "Stage 2 - Six-objective Pareto Analysis (15 to 7)",
    "stage2",
    "06_stage2_pareto_analysis",
)


# ============================================================
# Figure 07: Nav2 route calibration
# ============================================================

df = routes.copy()

df["route_label"] = (
    df["source"]
    + " -> "
    + df["destination"]
)

df = df.sort_values(
    ["task_type", "route_id"]
).reset_index(drop=True)

effective_speed = df.loc[
    df["mean_average_speed_mps"] > 0,
    "mean_average_speed_mps"
].mean()

fig, ax = plt.subplots(
    figsize=(13, 13)
)

y = np.arange(len(df))

ax.barh(
    y,
    df["mean_travel_time_s"],
    xerr=df["sd_travel_time_s"],
    color=BLUE,
    alpha=0.9,
    capsize=3,
    error_kw={
        "ecolor": DARK_GRAY,
        "elinewidth": 1,
    },
)

ax.set_yticks(
    y,
    df["route_label"],
    fontsize=9,
)

ax.invert_yaxis()

ax.set_xlabel(
    "Measured Travel Time (s)"
)

ax.set_title(
    "Nav2 Route Calibration\n"
    f"{len(df)} routes | {int(df['n'].sum())} trials"
    f" | Effective speed = {effective_speed:.4f} m/s",
    pad=16,
)

ax.grid(axis="x")

for i in range(1, len(df)):

    if (
        df.loc[i, "task_type"]
        != df.loc[i - 1, "task_type"]
    ):

        ax.axhline(
            i - 0.5,
            color=DARK_GRAY,
            lw=0.8,
        )

ax.text(
    0.99, -0.055,
    "Bars: mean travel time; error bars: standard deviation",
    transform=ax.transAxes,
    ha="right",
    color=DARK_GRAY,
    fontsize=10,
)

fig.tight_layout()

save(
    fig, "stage3",
    "07_nav2_route_calibration"
)


# ============================================================
# Figure 08: Stage 3 Nav2 performance
# ============================================================

performance_figure(
    stage3,
    "Stage 3 - Nav2-calibrated Reward Confirmation",
    "7 configurations | Mean +/- SD across 5 model seeds",
    "stage3",
    "08_stage3_nav2_performance",
    show_std=True,
)


# ============================================================
# Figure 09: Stage 3 Rank Sum
# ============================================================

df = stage3.sort_values(
    ["rank_sum", "config"]
).reset_index(drop=True)

fig, ax = plt.subplots(
    figsize=(10, 5.5)
)

bars = ax.barh(
    config_labels(df),
    df["rank_sum"],
    color=selection_colors(df),
    height=0.65,
)

ax.invert_yaxis()

ax.bar_label(
    bars,
    fmt="%.0f",
    padding=5,
)

ax.set_xlim(
    0,
    df["rank_sum"].max() * 1.15
)

ax.set_xlabel(
    "Rank Sum (Lower is Better)"
)

ax.set_title(
    "Stage 3 - Overall Reward Configuration Ranking"
)

ax.grid(axis="x")

ax.legend(
    handles=[
        Patch(
            color=BLUE,
            label="Final candidates",
        ),
        Patch(
            color=GRAY,
            label="Other configurations",
        ),
    ],
    loc="lower right",
)

fig.tight_layout()

save(
    fig, "stage3",
    "09_stage3_rank_sum"
)


# ============================================================
# Figure 10: Final candidate comparison
# ============================================================

fig, axes = plt.subplots(
    2, 3,
    figsize=(15, 9),
    constrained_layout=True,
)

for ax, metric, label in zip(
    axes.flat, METRICS, LABELS
):

    row = stats.loc[
        stats["metric"] == metric
    ].iloc[0]

    means = [
        row["sweep12_mean"],
        row["sweep25_mean"],
    ]

    errors = [
        row["sweep12_sd"],
        row["sweep25_sd"],
    ]

    bars = ax.bar(
        ["Sweep 12", "Sweep 25"],
        means,
        yerr=errors,
        color=[BLUE, GRAY],
        width=0.55,
        capsize=5,
        error_kw={
            "ecolor": DARK_GRAY,
            "elinewidth": 1.2,
        },
    )

    upper = max(
        m + e
        for m, e in zip(means, errors)
    )

    ax.set_ylim(
        0, upper * 1.2
    )

    decimals = (
        4 if metric == "jain_task_fairness"
        else 2
    )

    for i, (m, e) in enumerate(
        zip(means, errors)
    ):

        ax.text(
            i,
            m + e + upper * 0.035,
            f"{m:,.{decimals}f}",
            ha="center",
            fontsize=10,
        )

    ax.set_title(label)

    ax.grid(axis="y")

fig.suptitle(
    "Final Candidate Comparison: Sweep 12 vs Sweep 25\n"
    "Mean +/- SD across 5 model seeds",
    fontsize=16,
    weight="bold",
)

save(
    fig, "stage4",
    "10_final_candidate_comparison"
)


# ============================================================
# Figure 11: Emergency wait by model seed
# ============================================================

df = emergency.sort_values(
    "model_seed"
).reset_index(drop=True)

x = np.arange(len(df))
width = 0.32

fig, ax = plt.subplots(
    figsize=(10, 6)
)

b1 = ax.bar(
    x - width / 2,
    df["sweep12_emergency_wait_s"],
    width,
    color=BLUE,
    label="Sweep 12",
)

b2 = ax.bar(
    x + width / 2,
    df["sweep25_emergency_wait_s"],
    width,
    color=GRAY,
    label="Sweep 25",
)

ax.bar_label(
    b1, fmt="%.2f",
    fontsize=9,
    padding=3,
)

ax.bar_label(
    b2, fmt="%.2f",
    fontsize=9,
    padding=3,
)

for i, row in df.iterrows():

    top = max(
        row["sweep12_emergency_wait_s"],
        row["sweep25_emergency_wait_s"],
    )

    ax.text(
        i,
        top + 4,
        f"-{row['improvement_pct']:.1f}%",
        color=DARK_BLUE,
        ha="center",
        fontsize=10,
        weight="bold",
    )

ax.set_xticks(
    x,
    df["model_seed"].astype(str),
)

ax.set_ylim(
    0,
    df["sweep25_emergency_wait_s"].max()
    * 1.28,
)

ax.set_xlabel("Model Seed")

ax.set_ylabel(
    "Emergency Waiting Time (s)"
)

ax.set_title(
    "Emergency Waiting Time by Paired Model Seed"
)

ax.legend()

ax.grid(axis="y")

fig.tight_layout()

save(
    fig, "stage4",
    "11_emergency_wait_by_model_seed"
)


# ============================================================
# Figure 12: Bootstrap confidence intervals
# ============================================================

fig, axes = plt.subplots(
    3, 2,
    figsize=(14, 11),
    constrained_layout=True,
)

for ax, metric, label in zip(
    axes.flat, METRICS, LABELS
):

    row = stats.loc[
        stats["metric"] == metric
    ].iloc[0]

    mean = row["observed_difference"]

    intervals = [
        (
            row["historical_ci95_low"],
            row["historical_ci95_high"],
        ),
        (
            row["crossed_ci95_low"],
            row["crossed_ci95_high"],
        ),
    ]

    for y, (lo, hi), color in zip(
        [1, 0],
        intervals,
        [BLUE, DARK_GRAY],
    ):

        ax.hlines(
            y,
            lo,
            hi,
            color=color,
            lw=2,
        )

        ax.vlines(
            [lo, hi],
            y - 0.07,
            y + 0.07,
            color=color,
            lw=1.5,
        )

        ax.scatter(
            mean, y,
            color=color,
            s=45,
            zorder=3,
        )

    ax.axvline(
        0,
        color=BLACK,
        linestyle="--",
        lw=1,
    )

    ax.set_yticks(
        [1, 0],
        ["Hierarchical", "Crossed"],
    )

    ax.set_ylim(-0.5, 1.5)

    ax.set_title(label)

    ax.set_xlabel(
        "Difference (Positive = Sweep 12 Better)"
    )

    ax.grid(axis="x")

    ax.margins(x=0.15)

fig.suptitle(
    "Final Candidate Bootstrap Comparison\n"
    "Pointwise 95% confidence intervals; independent metric scales",
    fontsize=16,
    weight="bold",
)

save(
    fig, "stage4",
    "12_bootstrap_confidence_intervals"
)


# ============================================================
# Figure 13: Representative model selection
# ============================================================

df = representative.sort_values(
    "representativeness_rank"
).reset_index(drop=True)

labels = df["model_seed"].astype(str)

colors = [
    BLUE if seed == 7101 else GRAY
    for seed in df["model_seed"]
]

fig, axes = plt.subplots(
    1, 2,
    figsize=(13, 5.5),
    constrained_layout=True,
)

b1 = axes[0].barh(
    labels,
    df["within_config_rank_sum"],
    color=colors,
)

axes[0].invert_yaxis()

axes[0].bar_label(
    b1, fmt="%.0f",
    padding=5,
)

axes[0].set_xlim(
    0,
    df["within_config_rank_sum"].max() * 1.2,
)

axes[0].set_xlabel(
    "Rank Sum (Lower is Better)"
)

axes[0].set_title(
    "Overall Model Performance"
)

axes[0].grid(axis="x")

b2 = axes[1].barh(
    labels,
    df["standardized_distance_to_mean"],
    color=colors,
)

axes[1].invert_yaxis()

axes[1].bar_label(
    b2, fmt="%.4f",
    padding=5,
)

axes[1].set_xlim(
    0,
    df["standardized_distance_to_mean"].max() * 1.2,
)

axes[1].set_xlabel(
    "Standardized Distance (Lower is Closer)"
)

axes[1].set_title(
    "Representativeness"
)

axes[1].grid(axis="x")

fig.suptitle(
    "Sweep 12 - Representative Model Selection\n"
    "Blue: formal evaluation model (Seed 7101)",
    fontsize=16,
    weight="bold",
)

save(
    fig, "stage4",
    "13_representative_model_selection"
)


# ============================================================
# Figure manifest
# ============================================================

assert len(generated) == 26

manifest = {
    "figure_count": 13,
    "png_count": 13,
    "svg_count": 13,

    "analysis_manifest_sha256": (
        sha256(analysis_manifest_path)
    ),

    "plot_script_sha256": (
        sha256(Path(__file__))
    ),

    "matplotlib_version": (
        matplotlib.__version__
    ),

    "style": {
        "background": "white",
        "primary_color": BLUE,
        "comparison_color": GRAY,
        "png_dpi": 300,
    },

    "files": generated,
}

manifest_path = (
    DATA / "reward_selection_figure_manifest.json"
)

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== REWARD SELECTION FIGURES COMPLETE =====")
print("Figure groups:", 13)
print("PNG files:", 13)
print("SVG files:", 13)
print("Total generated figure files:", len(generated))
print("Manifest:", manifest_path)
print("Original experiment files modified: NO")
print("Scale figures modified: NO")
print("Models retrained: NO")
print("New simulation runs: 0")

