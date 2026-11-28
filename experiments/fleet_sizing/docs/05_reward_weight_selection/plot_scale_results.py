from __future__ import annotations

import csv
import json
import hashlib

from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.patches import (
    FancyBboxPatch,
    FancyArrowPatch,
)


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data/scale_selection"

OUTPUT = ROOT / "figures/scale_selection"


# ============================================================
# Style
# ============================================================

BLUE = "#2563EB"
DARK_BLUE = "#1D4ED8"
NAVY = "#1E3A8A"
MID_BLUE = "#60A5FA"
LIGHT_BLUE = "#93C5FD"
PALE_BLUE = "#EFF6FF"

BLACK = "#111111"
GRAY = "#64748B"
LIGHT_GRAY = "#CBD5E1"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": BLACK,
    "axes.labelcolor": BLACK,
    "axes.edgecolor": BLACK,
    "axes.titleweight": "bold",
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",
})


METRICS = (
    (
        "avg_waiting_time_s",
        "Average Waiting Time",
        "Time (s)",
        False,
    ),
    (
        "p95_waiting_time_s",
        "P95 Waiting Time",
        "Time (s)",
        False,
    ),
    (
        "high_waiting_time_s",
        "High Waiting Time",
        "Time (s)",
        False,
    ),
    (
        "emergency_waiting_time_s",
        "Emergency Waiting Time",
        "Time (s)",
        False,
    ),
    (
        "total_travel",
        "Total Travel Time",
        "Time (s)",
        False,
    ),
    (
        "jain_fairness",
        "Jain Task Fairness",
        "Jain index",
        True,
    ),
)

SHORT_LABELS = (
    "Average Wait",
    "P95 Wait",
    "High Wait",
    "Emergency Wait",
    "Total Travel",
    "Jain Fairness",
)


# ============================================================
# Data loading and integrity
# ============================================================

def read_csv(relative_path):

    with (DATA / relative_path).open(
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(csv.DictReader(f))


def read_json(relative_path):

    return json.loads(
        (DATA / relative_path).read_text(
            encoding="utf-8"
        )
    )


def verify_archive():

    manifest = read_json(
        "archive_manifest.json"
    )

    assert manifest["copied_files"] == 48

    assert manifest["historical_episode_records"] == 1020

    assert manifest["historical_training_models"] == 29

    assert manifest[
        "full_reproduction_metric_matches"
    ] == 2100

    for row in manifest["files"]:

        path = DATA / row["archive"]

        actual = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        assert actual == row["sha256"], path

    print("Archived data SHA256: PASS")
    print("Verified files:", len(manifest["files"]))

    return manifest


# ============================================================
# Plot utilities
# ============================================================

def style_axis(ax):

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.65,
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    ax.ticklabel_format(
        axis="y",
        style="plain",
        useOffset=False,
    )


def format_value(value, higher):

    if higher:
        return f"{value:.4f}"

    if value >= 10000:
        return f"{value:,.0f}"

    return f"{value:.2f}"


def save(fig, name):

    for extension in ("png", "svg"):

        path = OUTPUT / f"{name}.{extension}"

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.25,
            facecolor=WHITE,
        )

        print("Saved:", path)

    plt.close(fig)


def six_metric_canvas(title, subtitle):

    fig, axes = plt.subplots(
        2, 3,
        figsize=(16, 9.5),
    )

    fig.suptitle(
        title,
        fontsize=22,
        fontweight="bold",
        y=0.98,
    )

    fig.text(
        0.5, 0.935,
        subtitle,
        ha="center",
        fontsize=11,
        color=GRAY,
    )

    fig.subplots_adjust(
        left=0.075,
        right=0.975,
        bottom=0.10,
        top=0.86,
        hspace=0.50,
        wspace=0.38,
    )

    return fig, axes.ravel()


def annotate_bars(
    ax,
    bars,
    values,
    higher,
    errors=None,
):

    if errors is None:
        errors = np.zeros(len(values))

    for bar, value, error in zip(
        bars, values, errors
    ):

        ax.annotate(
            format_value(value, higher),
            xy=(
                bar.get_x() + bar.get_width() / 2,
                value + error,
            ),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
        )


# ============================================================
# Figure 01 — Scale sensitivity
# ============================================================

def plot_sensitivity():

    rows = sorted(
        read_csv("sensitivity/summary.csv"),
        key=lambda row: int(row["scale"]),
    )

    scales = [
        int(row["scale"])
        for row in rows
    ]

    assert scales == [150, 200, 300, 600]

    fig, axes = six_metric_canvas(
        "Approach Scale Sensitivity Analysis",
        "4 scales | 1 model per scale | 30 scenarios per model",
    )

    for ax, specification in zip(
        axes, METRICS
    ):

        key, title, unit, higher = specification

        values = np.array([
            float(row[key])
            for row in rows
        ])

        best = (
            int(np.argmax(values))
            if higher
            else int(np.argmin(values))
        )

        colors = [
            DARK_BLUE if i == best else LIGHT_BLUE
            for i in range(len(values))
        ]

        bars = ax.bar(
            range(len(scales)),
            values,
            color=colors,
            width=0.65,
        )

        ax.set_xticks(
            range(len(scales)),
            scales,
        )

        ax.set_xlabel("Approach scale (s)")
        ax.set_ylabel(unit)

        ax.set_title(
            title + (
                " (higher is better)"
                if higher
                else " (lower is better)"
            ),
            fontsize=11,
        )

        ax.set_ylim(
            0,
            1.12 if higher else max(values) * 1.22,
        )

        annotate_bars(
            ax, bars, values, higher
        )

        style_axis(ax)

    fig.text(
        0.5, 0.025,
        "Dark blue indicates the best observed mean for each metric.",
        ha="center",
        color=GRAY,
    )

    save(fig, "01_scale_sensitivity")


# ============================================================
# Figure 02 — Scale confirmation
# ============================================================

def plot_confirmation():

    rows = sorted(
        read_csv(
            "confirmation/aggregate_summary.csv"
        ),
        key=lambda row: int(row["scale"]),
    )

    assert [
        int(row["scale"])
        for row in rows
    ] == [150, 200]

    fig, axes = six_metric_canvas(
        "Multi-seed Scale Confirmation",
        "2 scales | 5 model seeds | 30 scenarios per model",
    )

    for ax, specification in zip(
        axes, METRICS
    ):

        key, title, unit, higher = specification

        values = np.array([
            float(row[f"{key}_mean"])
            for row in rows
        ])

        errors = np.array([
            float(row[f"{key}_model_seed_std"])
            for row in rows
        ])

        bars = ax.bar(
            [0, 1],
            values,
            yerr=errors,
            capsize=6,
            width=0.55,
            color=[BLUE, LIGHT_BLUE],
            error_kw={
                "ecolor": BLACK,
                "elinewidth": 1.2,
            },
        )

        ax.set_xticks(
            [0, 1],
            ["150 s", "200 s"],
        )

        ax.set_title(title, fontsize=12)
        ax.set_ylabel(unit)

        ax.set_ylim(
            0,
            max(
                1.12 if higher else 0,
                max(values + errors) * 1.24,
            ),
        )

        annotate_bars(
            ax,
            bars,
            values,
            higher,
            errors,
        )

        style_axis(ax)

    fig.text(
        0.5, 0.025,
        "Mean +/- sample standard deviation across five trained models.",
        ha="center",
        color=GRAY,
    )

    save(fig, "02_scale_confirmation")


# ============================================================
# Figure 03 — Model-seed stability
# ============================================================

def plot_seed_stability():

    rows = read_csv(
        "confirmation/model_seed_summary.csv"
    )

    seeds = list(range(7101, 7106))

    indexed = {
        (
            int(row["scale"]),
            int(row["model_seed"]),
        ): row
        for row in rows
    }

    assert len(indexed) == 10

    fig, axes = six_metric_canvas(
        "Scale Sensitivity Across Model Seeds",
        "Each point represents the mean of 30 evaluation scenarios",
    )

    for ax, specification in zip(
        axes, METRICS
    ):

        key, title, unit, higher = specification

        for scale, color, marker in (
            (150, DARK_BLUE, "o"),
            (200, MID_BLUE, "s"),
        ):

            values = [
                float(indexed[(scale, seed)][key])
                for seed in seeds
            ]

            ax.plot(
                range(len(seeds)),
                values,
                color=color,
                marker=marker,
                markersize=6,
                linewidth=2,
                label=f"Scale {scale}",
            )

        ax.set_xticks(
            range(len(seeds)),
            seeds,
        )

        ax.set_xlabel("Model seed")
        ax.set_ylabel(unit)
        ax.set_title(title, fontsize=12)

        style_axis(ax)

    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.005),
    )

    save(fig, "03_scale_multiseed_stability")


# ============================================================
# Figures 04 and 05 — Decoupled comparisons
# ============================================================

def plot_decoupled(
    folder,
    scale_field,
    title,
    subtitle,
    filename,
):

    rows = sorted(
        read_csv(f"{folder}/aggregate_summary.csv"),
        key=lambda row: int(row[scale_field]),
    )

    assert [
        int(row[scale_field])
        for row in rows
    ] == [150, 600]

    improvements = []

    for key, _, _, higher in METRICS:

        old = float(rows[0][f"{key}_mean"])

        new = float(rows[1][f"{key}_mean"])

        difference = (
            new - old if higher else old - new
        )

        improvements.append(
            100 * difference / old
        )

    fig, ax = plt.subplots(
        figsize=(13, 6.8)
    )

    fig.suptitle(
        title,
        fontsize=22,
        fontweight="bold",
        y=0.98,
    )

    fig.text(
        0.5, 0.925,
        subtitle,
        ha="center",
        color=GRAY,
    )

    fig.subplots_adjust(
        left=0.22,
        right=0.91,
        bottom=0.15,
        top=0.83,
    )

    y = np.arange(len(METRICS))

    bars = ax.barh(
        y,
        improvements,
        color=[
            BLUE if value >= 0 else GRAY
            for value in improvements
        ],
        height=0.58,
    )

    ax.set_yticks(y, SHORT_LABELS)

    ax.invert_yaxis()

    ax.axvline(
        0,
        color=BLACK,
        linewidth=1,
    )

    ax.grid(
        axis="x",
        linestyle="--",
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    ax.set_xlim(
        min(-5, min(improvements) - 4),
        max(improvements) * 1.20 + 1,
    )

    for bar, value in zip(
        bars, improvements
    ):

        ax.annotate(
            f"{value:+.2f}%",
            xy=(
                value,
                bar.get_y() + bar.get_height() / 2,
            ),
            xytext=(
                6 if value >= 0 else -6,
                0,
            ),
            textcoords="offset points",
            ha="left" if value >= 0 else "right",
            va="center",
            fontweight="bold",
        )

    ax.set_xlabel(
        "Relative improvement from scale 150 to 600 (%)"
    )

    wins = sum(value > 0 for value in improvements)

    fig.text(
        0.5, 0.055,
        f"Scale 600: better observed means in {wins}/6 metrics.",
        ha="center",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
    )

    fig.text(
        0.5, 0.015,
        "Positive values indicate improvement; no significance claim.",
        ha="center",
        color=GRAY,
    )

    save(fig, filename)

    print(
        f"{filename}: "
        f"{wins}/6 better mean metrics"
    )


# ============================================================
# Figure 06 — Historical reproducibility
# ============================================================

def plot_reproducibility():

    pilot = {
        row["case"]: row
        for row in read_csv(
            "diagnostics/pilot/summary.csv"
        )
    }

    full = {
        row["case"]: row
        for row in read_csv(
            "diagnostics/full_reproduction/summary.csv"
        )
    }

    cases = (
        (
            "Pilot: mismatched O150",
            pilot["historical_behavior"],
        ),
        (
            "Pilot: corrected O600",
            pilot["corrected_behavior"],
        ),
        (
            "Pilot: reference control",
            pilot["reference_control"],
        ),
        (
            "Full: R150/O600",
            full["corrected_behavior"],
        ),
        (
            "Full: R600/O600",
            full["reference_control"],
        ),
    )

    matched = [
        int(row["historical_metrics_matched"])
        for _, row in cases
    ]

    totals = [
        int(row["episodes"]) * 7
        for _, row in cases
    ]

    assert matched == [
        6, 42, 42, 1050, 1050
    ]

    rates = [
        100 * a / b
        for a, b in zip(matched, totals)
    ]

    fig, ax = plt.subplots(
        figsize=(13, 6.5)
    )

    fig.suptitle(
        "Historical Result Reproducibility",
        fontsize=22,
        fontweight="bold",
        y=0.97,
    )

    fig.subplots_adjust(
        left=0.29,
        right=0.83,
        top=0.86,
        bottom=0.17,
    )

    y = np.arange(len(cases))

    ax.barh(
        y,
        [100] * len(cases),
        color="#E2E8F0",
        height=0.58,
    )

    bars = ax.barh(
        y,
        rates,
        color=[LIGHT_GRAY] + [BLUE] * 4,
        height=0.58,
    )

    ax.set_yticks(
        y,
        [label for label, _ in cases],
    )

    ax.invert_yaxis()

    ax.set_xlim(0, 100)

    ax.set_xticks(
        [0, 25, 50, 75, 100],
        ["0%", "25%", "50%", "75%", "100%"],
    )

    ax.set_xlabel(
        "Matched historical metric values"
    )

    for bar, a, b, rate in zip(
        bars, matched, totals, rates
    ):

        ax.annotate(
            f"{a:,}/{b:,} ({rate:.1f}%)",
            xy=(
                100,
                bar.get_y() + bar.get_height() / 2,
            ),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=11,
            fontweight="bold",
            annotation_clip=False,
        )

    fig.text(
        0.5, 0.045,
        "Full reproduction: 2,100/2,100 matched metric values.",
        ha="center",
        fontsize=12,
        fontweight="bold",
        color=NAVY,
    )

    save(fig, "06_historical_reproducibility")


# ============================================================
# Figure 07 — Normalization function
# ============================================================

def plot_normalization():

    rows = read_csv(
        "sensitivity/summary.csv"
    )

    scales = sorted(
        int(row["scale"])
        for row in rows
    )

    x = np.linspace(
        0, 900, 901
    )

    colors = (
        "#BFDBFE",
        "#93C5FD",
        "#60A5FA",
        "#1D4ED8",
    )

    styles = (
        "--",
        "-.",
        ":",
        "-",
    )

    fig, ax = plt.subplots(
        figsize=(11, 6.5)
    )

    for scale, color, linestyle in zip(
        scales, colors, styles
    ):

        y = np.minimum(
            x / scale,
            1.0,
        )

        ax.plot(
            x,
            y,
            label=f"Scale = {scale} s",
            color=color,
            linestyle=linestyle,
            linewidth=2.8,
        )

        ax.axvline(
            scale,
            color=color,
            alpha=0.30,
            linewidth=0.9,
            linestyle="--",
        )

    ax.set_title(
        "Approach Time Normalization",
        fontsize=20,
        pad=20,
    )

    ax.set_xlabel(
        "Projected approach time (s)"
    )

    ax.set_ylabel(
        "Normalized value"
    )

    ax.set_xlim(0, 900)
    ax.set_ylim(0, 1.12)

    ax.set_xticks(
        [0, 150, 200, 300, 450, 600, 750, 900]
    )

    ax.set_yticks(
        [0, 0.25, 0.50, 0.75, 1.00]
    )

    ax.legend(
        frameon=False,
        loc="lower right",
    )

    ax.grid(
        linestyle="--",
        alpha=0.25,
    )

    ax.text(
        0.04, 0.90,
        r"$\hat{x}=\min(x/S,1)$",
        transform=ax.transAxes,
        fontsize=17,
        color=NAVY,
    )

    fig.text(
        0.5, 0.015,
        "Analytical illustration of normalization, not measured performance.",
        ha="center",
        color=GRAY,
    )

    fig.tight_layout(
        rect=(0, 0.05, 1, 1)
    )

    save(fig, "07_normalization_function")


# ============================================================
# Figure 08 — Overall experiment flow
# ============================================================

def plot_overall_flow(manifest):

    fig, ax = plt.subplots(
        figsize=(13, 10)
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    fig.suptitle(
        "Approach Scale Sensitivity and Validation",
        fontsize=23,
        fontweight="bold",
        y=0.97,
    )

    fig.text(
        0.5, 0.925,
        "Post-selection analysis of the existing normalization settings",
        ha="center",
        color=GRAY,
    )

    fig.subplots_adjust(
        left=0.035,
        right=0.965,
        bottom=0.04,
        top=0.89,
    )

    def box(x, y, w, h, title, subtitle, selected=False):

        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.35,rounding_size=1.3",
                facecolor="#DBEAFE" if selected else PALE_BLUE,
                edgecolor=DARK_BLUE if selected else BLUE,
                linewidth=2 if selected else 1.4,
            )
        )

        ax.text(
            x + w / 2,
            y + h * 0.72,
            title,
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
        )

        ax.text(
            x + w / 2,
            y + h * 0.31,
            subtitle,
            ha="center",
            va="center",
            fontsize=11,
            color=GRAY,
            linespacing=1.4,
        )

    def arrow(start, end):

        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=16,
                color=BLUE,
                linewidth=1.8,
            )
        )

    def count_wins(folder, scale_field):

        rows = sorted(
            read_csv(f"{folder}/aggregate_summary.csv"),
            key=lambda row: int(row[scale_field]),
        )

        wins = 0

        for key, _, _, higher in METRICS:

            a = float(rows[0][f"{key}_mean"])
            b = float(rows[1][f"{key}_mean"])

            wins += int(
                b > a if higher else b < a
            )

        return wins

    reward_wins = count_wins(
        "decoupled_reward",
        "reward_scale",
    )

    observation_wins = count_wins(
        "decoupled_observation",
        "observation_scale",
    )

    box(
        20, 84, 60, 13,
        "A. Scale Sensitivity",
        "150 / 200 / 300 / 600 s\n"
        "4 models | 120 evaluations",
    )

    arrow((50, 84), (50, 78))

    box(
        20, 64, 60, 14,
        "B. Scale Confirmation",
        "150 vs. 200 s\n"
        "10 models | 300 evaluations",
    )

    ax.plot(
        [50, 50, 25],
        [64, 60, 60],
        color=BLUE,
        linewidth=1.8,
    )

    ax.plot(
        [50, 75],
        [60, 60],
        color=BLUE,
        linewidth=1.8,
    )

    arrow((25, 60), (25, 56))
    arrow((75, 60), (75, 56))

    box(
        2, 36, 46, 20,
        "C. Decoupled Reward",
        "R150 vs. R600 | Fixed O600\n"
        "10 models | 300 evaluations\n"
        f"R600: {reward_wins}/6 better mean metrics",
    )

    box(
        52, 36, 46, 20,
        "D. Decoupled Observation",
        "O150 vs. O600 | Fixed R600\n"
        "10 models | 300 evaluations\n"
        f"O600: {observation_wins}/6 better mean metrics",
    )

    ax.plot(
        [25, 25, 75, 75],
        [36, 32, 32, 36],
        color=BLUE,
        linewidth=1.8,
    )

    arrow((50, 32), (50, 28))

    box(
        20, 15, 60, 13,
        "Reproducibility Verification",
        (
            f'{manifest["pilot_diagnostic_episodes"]} diagnostic + '
            f'{manifest["full_reproduction_episodes"]} reproduction episodes\n'
            f'{manifest["full_reproduction_metric_matches"]:,} matched metric values'
        ),
    )

    arrow((50, 15), (50, 11))

    box(
        20, 0.5, 60, 10.5,
        "Retained Setting: R600 / O600",
        "Waiting scale: 600 s | Queue scale: 10 tasks",
        selected=True,
    )

    save(fig, "08_overall_scale_selection")


# ============================================================
# Main
# ============================================================

def main():

    print("===== SCALE FIGURE GENERATION =====")

    manifest = verify_archive()

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    plot_sensitivity()

    plot_confirmation()

    plot_seed_stability()

    plot_decoupled(
        "decoupled_reward",
        "reward_scale",
        "Decoupled Reward Approach Scale",
        "Observation approach scale fixed at 600 s | 5 models per setting",
        "04_decoupled_reward_scale",
    )

    plot_decoupled(
        "decoupled_observation",
        "observation_scale",
        "Decoupled Observation Approach Scale",
        "Reward approach scale fixed at 600 s | 5 models per setting",
        "05_decoupled_observation_scale",
    )

    plot_reproducibility()

    plot_normalization()

    plot_overall_flow(manifest)

    pngs = sorted(OUTPUT.glob("*.png"))
    svgs = sorted(OUTPUT.glob("*.svg"))

    assert len(pngs) == 8
    assert len(svgs) == 8

    assert {
        path.stem for path in pngs
    } == {
        path.stem for path in svgs
    }

    verify_archive()

    print()
    print("===== FINAL FIGURE CHECK =====")
    print("PNG figures:", len(pngs))
    print("SVG figures:", len(svgs))
    print("Total image files:", len(pngs) + len(svgs))
    print("Archived data modified: NO")
    print("New simulation runs: 0")
    print("Model retrained: NO")
    print("SCALE FIGURES: COMPLETE")


if __name__ == "__main__":

    main()
