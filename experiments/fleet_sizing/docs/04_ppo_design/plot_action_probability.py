from pathlib import Path
import json
import csv
import os

import numpy as np

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

DATA = Path(os.environ.get(
    "PPO_DESIGN_DATA_DIR",
    str(ROOT / "data"),
))

OUTPUT = Path(os.environ.get(
    "PPO_DESIGN_FIGURE_DIR",
    str(ROOT / "figures"),
))

decision = json.loads(
    (DATA / "example_decision.json").read_text()
)

with (DATA / "action_mapping.csv").open() as f:
    mapping = list(csv.DictReader(f))

robots = [row["robot_id"] for row in mapping]

raw = np.array(
    decision["unmasked_action_probabilities"]
) * 100

masked = np.array(
    decision["masked_action_probabilities"]
) * 100

mask = np.array(decision["action_mask"], dtype=bool)

assert decision["model_seed"] == 7101
assert len(robots) == len(raw) == len(masked) == 7
assert np.isclose(raw.sum(), 100)
assert np.isclose(masked.sum(), 100)
assert np.allclose(masked[~mask], 0)

selected = decision["selected_action"]

assert selected == masked.argmax()
assert mask[selected]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",
})

fig, axes = plt.subplots(
    1, 2, figsize=(13, 6.3),
    sharey=True,
)

x = np.arange(7)

for ax, values, title, colors in [
    (
        axes[0], raw,
        "Before Action Mask",
        ["#AAAAAA"] * 7,
    ),
    (
        axes[1], masked,
        "After Action Mask",
        [
            "#2563EB" if valid else "#D4D4D4"
            for valid in mask
        ],
    ),
]:

    bars = ax.bar(
        x, values,
        color=colors,
        width=0.65,
        zorder=3,
    )

    ax.bar_label(
        bars,
        labels=[
            f"{v:.2f}%" if v >= 0.01
            else f"{v:.4f}%"
            for v in values
        ],
        padding=4,
        fontsize=9,
    )

    ax.set_xticks(
        x,
        [
            f"{robot}\n{'Valid' if valid else 'Invalid'}"
            for robot, valid in zip(robots, mask)
        ],
    )

    ax.set_ylim(0, 105)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Candidate Robot")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

axes[0].set_ylabel("Action Probability (%)")

fig.suptitle(
    "Actual Maskable PPO Action Distribution",
    fontsize=18,
    fontweight="bold",
)

fig.text(
    0.5, 0.91,
    "Nav2 Sweep 12 | Model Seed 7101 | "
    f"Task {decision['task_id']}",
    ha="center",
)

fig.text(
    0.5, 0.075,
    f"Selected action: {selected} | "
    f"Robot: {decision['selected_robot_id']} | "
    f"Masked probability: {masked[selected]:.2f}%",
    ha="center",
    fontweight="bold",
    color="#2563EB",
)

fig.text(
    0.5, 0.025,
    "Diagnostic unmasked distribution versus actual masked policy. "
    "Single inference; no environment step or training.",
    ha="center",
    fontsize=9,
)

fig.tight_layout(rect=[0, 0.12, 1, 0.88])

targets = [
    OUTPUT / f"06_action_probability_distribution.{ext}"
    for ext in ("png", "svg")
]

assert not any(p.exists() for p in targets)

for target in targets:
    fig.savefig(
        target,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    print("Saved:", target)

plt.close(fig)

print("Action probability figure: COMPLETE")
