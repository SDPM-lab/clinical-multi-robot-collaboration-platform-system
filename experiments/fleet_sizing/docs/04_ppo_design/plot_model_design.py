from __future__ import annotations

import csv
import json
import os
import re

from pathlib import Path
from collections import Counter

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.patches import (
    FancyBboxPatch,
    FancyArrowPatch,
    Rectangle,
)


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA = Path(
    os.environ.get(
        "PPO_DESIGN_DATA_DIR",
        str(ROOT / "data"),
    )
).resolve()

OUTPUT = Path(
    os.environ.get(
        "PPO_DESIGN_FIGURE_DIR",
        str(ROOT / "figures"),
    )
).resolve()

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Style
# ============================================================

BLUE = "#2563EB"
DARK_BLUE = "#1D4ED8"
NAVY = "#1E3A8A"
LIGHT_BLUE = "#DBEAFE"
PALE_BLUE = "#EFF6FF"
MID_BLUE = "#93C5FD"

BLACK = "#111111"
GRAY = "#64748B"
LIGHT_GRAY = "#E2E8F0"
PALE_GRAY = "#F8FAFC"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": BLACK,
    "axes.labelcolor": BLACK,
    "figure.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "svg.fonttype": "none",
    "mathtext.fontset": "dejavusans",
})


# ============================================================
# Read exported model data
# ============================================================

def read_json(name):

    return json.loads(
        (DATA / name).read_text(
            encoding="utf-8"
        )
    )


def read_csv(name):

    with (DATA / name).open(
        encoding="utf-8-sig"
    ) as f:

        return list(csv.DictReader(f))


layout = read_csv("observation_layout.csv")

mapping = read_csv("action_mapping.csv")

example_obs = read_csv(
    "example_observation.csv"
)

example = read_json("example_decision.json")

architecture = read_json(
    "model_architecture.json"
)

reward = read_json("reward_config.json")

training = read_json(
    "ppo_hyperparameters.json"
)

assert len(layout) == 98

assert len(example_obs) == 98

assert len(mapping) == 7

assert architecture["observation_shape"] == [98]

assert architecture["action_count"] == 7

assert architecture["total_parameters"] == 21512

assert example["action_mask"][
    example["selected_action"]
] == 1

assert mapping[
    example["selected_action"]
]["robot_id"] == example["selected_robot_id"]

counts = Counter(
    row["group"]
    for row in layout
)

robot_ids = [
    row["robot_id"]
    for row in mapping
]

weights = {
    "W": reward["waiting_weight"],
    "A": reward["approach_weight"],
    "Q": reward["queue_weight"],
    "I": reward["imbalance_weight"],
}

assert abs(sum(weights.values()) - 1) < 1e-9


# ============================================================
# Drawing utilities
# ============================================================

def canvas(title, subtitle="", figsize=(13, 8)):

    fig, ax = plt.subplots(
        figsize=figsize
    )

    fig.subplots_adjust(
        left=0.035,
        right=0.965,
        bottom=0.035,
        top=0.88,
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    fig.text(
        0.5, 0.955,
        title,
        ha="center",
        fontsize=23,
        fontweight="bold",
    )

    if subtitle:

        fig.text(
            0.5, 0.915,
            subtitle,
            ha="center",
            fontsize=11,
            color=GRAY,
        )

    return fig, ax


def text(
    ax, x, y, value,
    size=11,
    color=BLACK,
    weight="normal",
    ha="center",
):

    ax.text(
        x, y,
        value,
        ha=ha,
        va="center",
        fontsize=size,
        color=color,
        fontweight=weight,
        linespacing=1.45,
    )


def box(
    ax,
    x, y, w, h,
    title,
    subtitle="",
    fill=WHITE,
    edge=BLUE,
    title_color=BLACK,
    title_size=13,
    subtitle_size=10,
):

    patch = FancyBboxPatch(
        (x, y),
        w, h,
        boxstyle=(
            "round,pad=0.35,"
            "rounding_size=1.3"
        ),
        facecolor=fill,
        edgecolor=edge,
        linewidth=1.6,
    )

    ax.add_patch(patch)

    text(
        ax,
        x + w / 2,
        y + h * (
            0.65 if subtitle else 0.5
        ),
        title,
        size=title_size,
        color=title_color,
        weight="bold",
    )

    if subtitle:

        text(
            ax,
            x + w / 2,
            y + h * 0.28,
            subtitle,
            size=subtitle_size,
            color=GRAY,
        )


def arrow(
    ax,
    start,
    end,
    color=BLUE,
    dashed=False,
):

    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=1.7,
        color=color,
        linestyle="--" if dashed else "-",
        shrinkA=2,
        shrinkB=2,
    )

    ax.add_patch(patch)


def route(
    ax,
    points,
    color=BLUE,
    dashed=False,
):

    if len(points) > 2:

        xs, ys = zip(*points[:-1])

        ax.plot(
            xs, ys,
            color=color,
            linewidth=1.7,
            linestyle=(
                "--" if dashed else "-"
            ),
        )

    arrow(
        ax,
        points[-2],
        points[-1],
        color=color,
        dashed=dashed,
    )


def save(fig, name):

    for extension in ("png", "svg"):

        path = OUTPUT / (
            f"{name}.{extension}"
        )

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.25,
            facecolor=WHITE,
        )

        print("Saved:", path)

    plt.close(fig)


# ============================================================
# Figure 01 — Environment interaction
# ============================================================

def plot_environment_flow():

    fig, ax = canvas(
        "Maskable PPO Training Framework",
        "Event-driven hospital scheduling environment",
        figsize=(14, 8),
    )

    box(
        ax, 3, 70, 28, 24,
        "Hospital Environment",
        "Tasks, robot states,\nqueues and battery",
        fill=PALE_BLUE,
    )

    box(
        ax, 37, 81, 25, 13,
        "Observation",
        "98-dimensional vector",
    )

    box(
        ax, 37, 64, 25, 13,
        "Action Mask",
        "7 feasibility flags",
    )

    box(
        ax, 69, 70, 28, 24,
        "Maskable PPO",
        "Actor and Critic\nLearned dispatch policy",
        fill=LIGHT_BLUE,
        edge=DARK_BLUE,
    )

    route(
        ax,
        [(31, 87), (34, 87), (37, 87)],
    )

    route(
        ax,
        [(31, 74), (34, 74), (34, 70), (37, 70)],
    )

    arrow(ax, (62, 87), (69, 87))

    route(
        ax,
        [(62, 70), (65, 70), (65, 76), (69, 76)],
    )

    box(
        ax, 69, 43, 28, 16,
        "Select Robot",
        "One valid action",
    )

    arrow(ax, (83, 70), (83, 59))

    box(
        ax, 37, 43, 25, 16,
        "Apply Assignment",
        "Queue placement and\nbattery-aware repair",
    )

    arrow(ax, (69, 51), (62, 51))

    box(
        ax, 3, 43, 28, 16,
        "Advance Events",
        "Task execution and\ncharging lifecycle",
    )

    arrow(ax, (37, 51), (31, 51))

    arrow(
        ax, (17, 59), (17, 70),
        color=GRAY,
    )

    text(
        ax, 17, 64.5,
        "Next state",
        size=9,
        color=GRAY,
    )

    box(
        ax, 3, 15, 28, 18,
        "Waiting Reward",
        "Realized waiting time\nand priority multiplier",
        fill=PALE_BLUE,
    )

    arrow(ax, (17, 43), (17, 33))

    box(
        ax, 37, 15, 25, 18,
        "Assignment Reward",
        "Approach, queue and\nload imbalance penalties",
        fill=PALE_BLUE,
    )

    arrow(ax, (49.5, 43), (49.5, 33))

    box(
        ax, 69, 15, 28, 18,
        "Rollout and Update",
        (
            f'{training["samples_per_rollout"]} steps / rollout\n'
            f'{training["settings"]["n_epochs"]} epochs'
        ),
        fill=LIGHT_BLUE,
    )

    route(
        ax,
        [(31, 19), (34, 19), (34, 9),
         (83, 9), (83, 15)],
    )

    arrow(ax, (62, 24), (69, 24))

    route(
        ax,
        [(97, 24), (99, 24),
         (99, 82), (97, 82)],
        dashed=True,
    )

    text(
        ax, 50, 2.5,
        "Policy updates occur during training only.",
        size=11,
        color=GRAY,
    )

    save(
        fig,
        "01_rl_environment_flow",
    )


# ============================================================
# Figure 02 — Observation structure
# ============================================================

def plot_observation_structure():

    fig, ax = canvas(
        "98-dimensional Observation Structure",
        "Battery-aware state representation",
        figsize=(14, 9),
    )

    groups = [
        ("Task Type", counts["task_type"]),
        ("Priority", counts["priority"]),
        ("Source", counts["source"]),
        ("Destination", counts["destination"]),
    ]

    task_total = sum(
        count for _, count in groups
    )

    robot_total = counts["robot"]

    global_total = counts["global"]

    assert (
        task_total,
        robot_total,
        global_total,
    ) == (41, 56, 1)

    box(
        ax, 3, 77, 39, 18,
        f"Task Features: {task_total}",
        "One-hot encoded",
        fill=LIGHT_BLUE,
    )

    box(
        ax, 46, 77, 39, 18,
        f"Robot Features: {robot_total}",
        "7 robots x 8 features",
        fill=LIGHT_BLUE,
    )

    box(
        ax, 89, 77, 8, 18,
        "1",
        "Global",
        fill=PALE_BLUE,
        title_size=18,
        subtitle_size=9,
    )

    for i, (name, count) in enumerate(
        groups
    ):

        y = 62 - i * 13

        box(
            ax, 3, y, 39, 10,
            name,
            f"{count} dimensions",
            fill=PALE_BLUE,
            title_size=12,
            subtitle_size=9,
        )

    robot_features = [
        row["feature"]
        for row in layout
        if row["group"] == "robot"
        and row["robot_id"] == robot_ids[0]
    ]

    labels = [
        "Capability Match",
        "Assignable",
        "Busy",
        "Observable Load",
        "Projected Approach",
        "Tasks Ahead",
        "Battery SoC",
        "Battery Unavailable",
    ]

    assert len(robot_features) == len(labels) == 8

    for i, label in enumerate(labels):

        y = 69 - i * 6.4

        ax.add_patch(
            Rectangle(
                (47, y),
                37, 5.3,
                facecolor=(
                    LIGHT_BLUE
                    if i >= 6
                    else PALE_BLUE
                ),
                edgecolor=MID_BLUE,
                linewidth=0.8,
            )
        )

        text(
            ax, 49, y + 2.65,
            f"{i + 1}. {label}",
            size=10,
            ha="left",
        )

    text(
        ax, 93, 60,
        "Load\nImbalance",
        size=10,
        weight="bold",
    )

    text(
        ax, 93, 47,
        "Index\n97",
        size=9,
        color=GRAY,
    )

    for i, robot_id in enumerate(
        robot_ids
    ):

        x = 46 + i * 5.6

        box(
            ax, x, 11, 5.1, 7.5,
            robot_id,
            fill=LIGHT_BLUE,
            title_size=9,
        )

    text(
        ax, 65.5, 7,
        "Fixed robot order",
        size=10,
        color=GRAY,
    )

    text(
        ax, 22.5, 13,
        "Indices 0-40",
        size=11,
        color=GRAY,
    )

    text(
        ax, 65.5, 20.5,
        "Indices 41-96",
        size=10,
        color=GRAY,
    )

    text(
        ax, 50, 1.5,
        "41 + (7 x 8) + 1 = 98 features",
        size=17,
        weight="bold",
        color=NAVY,
    )

    save(
        fig,
        "02_observation_structure",
    )


# ============================================================
# Figure 03 — Actual Actor-Critic architecture
# ============================================================

def extract_linear_layers(network):

    return [
        (
            int(in_features),
            int(out_features),
        )
        for in_features, out_features in
        re.findall(
            r"Linear\(in_features=(\d+), "
            r"out_features=(\d+)",
            network,
        )
    ]


def plot_actor_critic():

    actor_layers = extract_linear_layers(
        architecture["actor_network"]
    )

    critic_layers = extract_linear_layers(
        architecture["critic_network"]
    )

    actor_output = extract_linear_layers(
        architecture["actor_output"]
    )

    critic_output = extract_linear_layers(
        architecture["critic_output"]
    )

    assert actor_layers == [
        (98, 64),
        (64, 64),
    ]

    assert critic_layers == actor_layers

    assert actor_output == [(64, 7)]

    assert critic_output == [(64, 1)]

    assert architecture["actor_network"].count(
        "Tanh()"
    ) == 2

    assert architecture["critic_network"].count(
        "Tanh()"
    ) == 2

    fig, ax = canvas(
        "Maskable PPO Actor-Critic Architecture",
        "Formal Nav2 model: Sweep 12, Model Seed 7101",
        figsize=(13, 10),
    )

    box(
        ax, 30, 88, 40, 10,
        "Observation: 98 Features",
        fill=LIGHT_BLUE,
    )

    box(
        ax, 35, 76, 30, 7,
        "FlattenExtractor",
        fill=PALE_GRAY,
        edge=GRAY,
        title_size=11,
    )

    arrow(ax, (50, 88), (50, 83))

    route(
        ax,
        [(50, 76), (50, 71),
         (24, 71), (24, 65)],
    )

    route(
        ax,
        [(50, 76), (50, 71),
         (76, 71), (76, 65)],
        color=GRAY,
    )

    for x, title, output, nparams in (
        (
            3,
            "Actor Network",
            "7 action logits",
            architecture["actor_parameters"],
        ),
        (
            55,
            "Critic Network",
            "1 state value",
            architecture["critic_parameters"],
        ),
    ):

        text(
            ax, x + 21, 68,
            title,
            size=15,
            weight="bold",
            color=NAVY,
        )

        box(
            ax, x, 53, 42, 12,
            "Linear: 98 -> 64",
            "Tanh activation",
            fill=PALE_BLUE,
        )

        box(
            ax, x, 37, 42, 12,
            "Linear: 64 -> 64",
            "Tanh activation",
            fill=PALE_BLUE,
        )

        arrow(
            ax,
            (x + 21, 53),
            (x + 21, 49),
        )

        box(
            ax, x, 21, 42, 12,
            (
                "Linear: 64 -> 7"
                if x == 3
                else "Linear: 64 -> 1"
            ),
            output,
            fill=LIGHT_BLUE,
        )

        arrow(
            ax,
            (x + 21, 37),
            (x + 21, 33),
        )

        text(
            ax, x + 21, 17.5,
            f"{nparams:,} parameters",
            size=11,
            color=GRAY,
        )

    box(
        ax, 3, 3, 42, 9,
        "Masked Action Distribution",
        fill=LIGHT_BLUE,
        title_size=11,
    )

    arrow(ax, (24, 16), (24, 12))

    box(
        ax, 51, 3, 22, 9,
        "Action Mask (7)",
        fill=WHITE,
        title_size=10,
    )

    arrow(ax, (51, 7.5), (45, 7.5))

    text(
        ax, 86, 7.5,
        f'{architecture["total_parameters"]:,}\ntrainable parameters',
        size=12,
        weight="bold",
        color=NAVY,
    )

    save(
        fig,
        "03_actor_critic_architecture",
    )


# ============================================================
# Figure 04 — Real inference example
# ============================================================

def plot_action_mask():

    fig, ax = canvas(
        "Battery-aware Action Mask and PPO Inference",
        (
            f'Actual task {example["task_id"]}'
            f' | Scenario Seed {example["scenario_seed"]}'
        ),
        figsize=(14, 8),
    )

    box(
        ax, 16, 82, 68, 14,
        example["task_type"].replace("_", " ").title(),
        (
            f'{example["source"]} -> '
            f'{example["destination"]}'
            f'  |  Priority: {["Low", "Normal", "High", "Emergency"][example["priority"]]}'
        ),
        fill=PALE_BLUE,
    )

    arrow(ax, (50, 82), (50, 76))

    box(
        ax, 16, 64, 68, 12,
        "Feasibility Filtering",
        "Capability, robot status and battery feasibility",
    )

    arrow(ax, (50, 64), (50, 58))

    mask = example["action_mask"]

    selected = example["selected_action"]

    for i, robot_id in enumerate(robot_ids):

        x = 3 + i * 13.6

        valid = bool(mask[i])

        box(
            ax, x, 38, 12, 17,
            robot_id,
            f"Action {i}",
            fill=(
                LIGHT_BLUE
                if valid
                else PALE_GRAY
            ),
            edge=(
                BLUE
                if valid
                else LIGHT_GRAY
            ),
            title_size=13,
        )

        ax.add_patch(
            Rectangle(
                (x, 30),
                12, 6,
                facecolor=(
                    BLUE
                    if valid
                    else LIGHT_GRAY
                ),
            )
        )

        text(
            ax, x + 6, 33,
            str(mask[i]),
            size=13,
            color=WHITE if valid else GRAY,
            weight="bold",
        )

    for i in example["valid_actions"]:

        x = 9 + i * 13.6

        route(
            ax,
            [(x, 30), (x, 25),
             (50, 25), (50, 20)],
        )

    box(
        ax, 30, 10, 40, 10,
        "Maskable PPO",
        "Deterministic action selection",
        fill=LIGHT_BLUE,
    )

    arrow(ax, (50, 10), (50, 6))

    text(
        ax, 50, 2.5,
        (
            f'Selected Action: {selected}'
            f'  |  Robot: {example["selected_robot_id"]}'
        ),
        size=17,
        weight="bold",
        color=DARK_BLUE,
    )

    save(
        fig,
        "04_action_mask_flow",
    )


# ============================================================
# Figure 05 — Reward structure
# ============================================================

def plot_reward_structure():

    fig, ax = canvas(
        "Multi-objective Reward Function",
        "Nav2 Sweep 12: assignment-time and realized waiting penalties",
        figsize=(14, 9),
    )

    labels = {
        "W": "Waiting",
        "A": "Approach",
        "Q": "Queue",
        "I": "Imbalance",
    }

    colors = {
        "W": NAVY,
        "A": BLUE,
        "Q": MID_BLUE,
        "I": LIGHT_BLUE,
    }

    x = 3

    for key in ("W", "A", "Q", "I"):

        w = 94 * weights[key]

        ax.add_patch(
            Rectangle(
                (x, 84),
                w, 11,
                facecolor=colors[key],
                edgecolor=WHITE,
                linewidth=1.2,
            )
        )

        text(
            ax, x + w / 2, 89.5,
            f'{weights[key]:.0%}',
            size=13 if key != "I" else 9,
            weight="bold",
            color=(
                WHITE
                if key in ("W", "A")
                else BLACK
            ),
        )

        x += w

    for i, key in enumerate(
        ("W", "A", "Q", "I")
    ):

        x = 5 + i * 24

        ax.add_patch(
            Rectangle(
                (x, 77),
                2.5, 3,
                facecolor=colors[key],
            )
        )

        text(
            ax, x + 4, 78.5,
            f"{key}: {labels[key]}",
            size=11,
            ha="left",
        )

    box(
        ax, 3, 57, 45, 15,
        "Assignment-time Reward",
        "Calculated after robot assignment",
        fill=PALE_BLUE,
    )

    box(
        ax, 52, 57, 45, 15,
        "Realized Waiting Reward",
        "Calculated when a task starts",
        fill=PALE_BLUE,
    )

    approach_scale = reward[
        "approach_scale_s"
    ]

    waiting_scale = reward[
        "waiting_scale_s"
    ]

    queue_scale = reward[
        "tasks_ahead_scale"
    ]

    text(
        ax, 25.5, 49,
        (
            r"$\hat{A}="
            r"\min(T_{\mathrm{approach}}/"
            f"{approach_scale:g}"
            r",1)$"
        ),
        size=13,
    )

    text(
        ax, 25.5, 42,
        (
            r"$\hat{Q}="
            r"\min(N_{\mathrm{ahead}}/"
            f"{queue_scale:g}"
            r",1)$"
        ),
        size=13,
    )

    text(
        ax, 25.5, 35,
        (
            r"$I_{\mathrm{post}}="
            r"(L_{\max}-L_{\min})/L_{\max}$"
        ),
        size=13,
    )

    text(
        ax, 25.5, 29,
        "Zero imbalance if all loads are zero",
        size=9,
        color=GRAY,
    )

    text(
        ax, 25.5, 20,
        (
            r"$R_{\mathrm{assign}}=-("
            f'{weights["A"]:.2f}'
            r"\hat{A}+"
            f'{weights["Q"]:.2f}'
            r"\hat{Q}+"
            f'{weights["I"]:.2f}'
            r"I_{\mathrm{post}})$"
        ),
        size=14,
        color=NAVY,
        weight="bold",
    )

    text(
        ax, 74.5, 49,
        (
            r"$\hat{W}="
            r"\min(T_{\mathrm{wait}}/"
            f"{waiting_scale:g}"
            r",1)$"
        ),
        size=13,
    )

    priorities = [
        (
            "Low",
            reward["low_priority_weight"],
        ),
        (
            "Normal",
            reward["normal_priority_weight"],
        ),
        (
            "High",
            reward["high_priority_weight"],
        ),
        (
            "Emergency",
            reward["emergency_priority_weight"],
        ),
    ]

    for i, (name, value) in enumerate(
        priorities
    ):

        y = 41 - i * 4.5

        text(
            ax, 54, y,
            name,
            size=10,
            ha="left",
        )

        ax.add_patch(
            Rectangle(
                (71, y - 1.4),
                value / 4 * 18,
                2.8,
                facecolor=(
                    BLUE
                    if name == "Emergency"
                    else MID_BLUE
                ),
            )
        )

        text(
            ax, 92, y,
            f"x{value:.1f}",
            size=10,
            weight="bold",
        )

    text(
        ax, 74.5, 20,
        (
            r"$R_{\mathrm{wait}}=-"
            f'{weights["W"]:.2f}'
            r"\hat{W}\cdot P$"
        ),
        size=15,
        color=NAVY,
        weight="bold",
    )

    route(
        ax,
        [(25.5, 16), (25.5, 12),
         (50, 12), (50, 9)],
    )

    route(
        ax,
        [(74.5, 16), (74.5, 12),
         (50, 12), (50, 9)],
    )

    text(
        ax, 50, 4.5,
        (
            r"$r_t=R_{\mathrm{assign},t}"
            r"+\sum_{j\in B_t}R_{\mathrm{wait},j}$"
        ),
        size=17,
        weight="bold",
        color=NAVY,
    )

    save(
        fig,
        "05_reward_structure",
    )


# ============================================================
# Main
# ============================================================

def main():

    print("===== MODEL DESIGN FIGURES =====")

    print("Observation features:", len(layout))
    print("Robot IDs:", robot_ids)
    print("Reward weights:", weights)
    print("Model parameters:", architecture["total_parameters"])
    print("Actual training steps:", training["actual_timesteps"])
    print("Selected action:", example["selected_action"])
    print("Selected robot:", example["selected_robot_id"])

    plot_environment_flow()

    plot_observation_structure()

    plot_actor_critic()

    plot_action_mask()

    plot_reward_structure()

    print()
    print("===== FINAL PLOTTING CHECK =====")

    pngs = sorted(OUTPUT.glob("*.png"))
    svgs = sorted(OUTPUT.glob("*.svg"))

    assert len(pngs) == 5
    assert len(svgs) == 5

    print("PNG figures:", len(pngs))
    print("SVG figures:", len(svgs))
    print("Training performed: NO")
    print("Model modified: NO")
    print("PPO DESIGN FIGURES: COMPLETE")


if __name__ == "__main__":

    main()
