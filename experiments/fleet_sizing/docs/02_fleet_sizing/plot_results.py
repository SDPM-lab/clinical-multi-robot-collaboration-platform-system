from pathlib import Path
import csv
import math

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

BLUE = "#2563EB"
DARK_BLUE = "#1D4ED8"
LIGHT_BLUE = "#93C5FD"
GRAY = "#CBD5E1"
THRESHOLD = 300.0

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "axes.labelsize": 13,
    "axes.labelcolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "text.color": "black",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

def read_csv(name):
    with (DATA / name).open(
        encoding="utf-8-sig"
    ) as f:
        return list(csv.DictReader(f))

def val(r, key):
    return float(r[key])

def fleet(r):
    return tuple(
        int(r[k])
        for k in [
            "clean_count",
            "medical_count",
            "ward_count",
        ]
    )

def label(r):
    return "(" + ",".join(map(str, fleet(r))) + ")"

def p95(r):
    return val(r, "mean_p95_response_time_s")

def feasible(r):
    return (
        val(r, "mean_completion_rate") >= 0.99
        and val(r, "min_completion_rate") >= 0.99
        and val(r, "mean_max_utilization") < 0.90
        and p95(r) <= THRESHOLD
    )

def rank(r):
    return (
        int(r["total_robots"]),
        p95(r),
        val(r, "mean_max_utilization"),
        *fleet(r),
    )

def finish(fig, name):
    fig.tight_layout()

    for ext in ["png", "svg"]:
        path = OUT / f"{name}.{ext}"

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
        )

        print("Saved:", path)

    plt.close(fig)

def style(ax, axis="y"):
    ax.grid(
        axis=axis,
        linestyle="--",
        linewidth=0.7,
        alpha=0.25,
    )
    ax.set_axisbelow(True)

def threshold(ax, horizontal=False):
    if horizontal:
        ax.axvline(
            THRESHOLD,
            color="#64748B",
            linestyle="--",
            linewidth=1.4,
            label="300 s threshold",
        )
    else:
        ax.axhline(
            THRESHOLD,
            color="#64748B",
            linestyle="--",
            linewidth=1.4,
            label="300 s threshold",
        )

rows = read_csv(
    "demand_fleet_sensitivity_all.csv"
)

selected = read_csv(
    "demand_fleet_sensitivity_selected.csv"
)

assert len(rows) == 483

keys = {
    (val(r, "workload_multiplier"), fleet(r))
    for r in rows
}

assert len(keys) == 483
assert len({fleet(r) for r in rows}) == 69
assert {int(r["replications"]) for r in rows} == {30}

assert all(
    feasible(r) ==
    (r["feasible"].strip().lower() == "true")
    for r in rows
)

data = [
    r for r in rows
    if val(r, "workload_multiplier") == 4.0
]

sizes = sorted({
    int(r["total_robots"]) for r in data
})

groups = {
    n: [
        r for r in data
        if int(r["total_robots"]) == n
    ]
    for n in sizes
}

best_by_size = [
    min(groups[n], key=rank)
    for n in sizes
]

seven = sorted(groups[7], key=rank)

seven_pass = [
    r for r in seven if feasible(r)
]

final = min(
    [r for r in data if feasible(r)],
    key=rank,
)

assert len(data) == 69
assert len(seven) == 15
assert len(seven_pass) == 3
assert fleet(final) == (2, 2, 3)

# ==================================================
# Figure 1: Minimum fleet size by workload
# ==================================================

selected.sort(
    key=lambda r: val(r, "workload_multiplier")
)

x = [
    val(r, "workload_multiplier")
    for r in selected
]

y = [
    int(r["total_robots"])
    for r in selected
]

fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(
    x, y,
    color=BLUE,
    marker="o",
    linewidth=2.5,
    markersize=7,
)

for a, b in zip(x, y):
    ax.annotate(
        str(b),
        (a, b),
        xytext=(0, 9),
        textcoords="offset points",
        ha="center",
        fontweight="bold",
    )

ax.scatter(
    [4], [7],
    s=140,
    color=DARK_BLUE,
    edgecolor="white",
    zorder=5,
)

ax.set_title(
    "Minimum Feasible Fleet Size by Workload"
)

ax.set_xlabel("Workload Multiplier")
ax.set_ylabel("Number of Robots")

ax.set_xticks(x)
ax.set_xticklabels([f"{v:g}x" for v in x])
ax.set_yticks(range(0, 12))
ax.set_ylim(0, 11)

style(ax)
finish(fig, "01_workload_minimum_fleet")

# ==================================================
# Figure 2: Different total fleet sizes
# ==================================================

fig, ax = plt.subplots(figsize=(8, 5.5))

y = [p95(r) for r in best_by_size]

ax.plot(
    sizes,
    y,
    color=BLUE,
    linewidth=2.5,
)

for n, r in zip(sizes, best_by_size):

    passed = feasible(r)

    ax.scatter(
        n,
        p95(r),
        s=100 if n == 7 else 55,
        facecolor=BLUE if passed else "white",
        edgecolor=BLUE,
        linewidth=1.8,
        zorder=4,
    )

    ax.annotate(
        f"{p95(r):.1f}",
        (n, p95(r)),
        xytext=(0, 10 if n != 7 else -22),
        textcoords="offset points",
        ha="center",
        fontsize=11,
        fontweight="bold" if n == 7 else "normal",
    )

threshold(ax)

ax.annotate(
    "Selected: 7 robots",
    xy=(7, p95(final)),
    xytext=(7.5, 650),
    ha="center",
    color=DARK_BLUE,
    fontweight="bold",
    arrowprops={
        "arrowstyle": "->",
        "color": DARK_BLUE,
    },
)

ax.set_title(
    "Fleet Size Sensitivity (4.0x Workload)"
)

ax.set_xlabel("Total Number of Robots")
ax.set_ylabel("Mean P95 Response Time (s)")

ax.set_xticks(sizes)
ax.set_ylim(0, 1800)

handles = [
    Line2D(
        [0], [0],
        marker="o",
        color=BLUE,
        markerfacecolor="white",
        label="Infeasible",
    ),
    Line2D(
        [0], [0],
        marker="o",
        color=BLUE,
        markerfacecolor=BLUE,
        label="Feasible",
    ),
    Line2D(
        [0], [0],
        color="#64748B",
        linestyle="--",
        label="300 s threshold",
    ),
]

ax.legend(handles=handles, loc="upper right")

style(ax)
finish(fig, "02_fleet_size_comparison_4x")

# ==================================================
# Figure 3: All 15 seven-robot configurations
# ==================================================

fig, ax = plt.subplots(figsize=(8, 7))

colors = [
    DARK_BLUE if fleet(r) == fleet(final)
    else LIGHT_BLUE if feasible(r)
    else GRAY
    for r in seven
]

bars = ax.barh(
    [label(r) for r in seven],
    [p95(r) for r in seven],
    color=colors,
    height=0.65,
)

ax.bar_label(
    bars,
    fmt="%.1f",
    padding=5,
    fontsize=10,
)

ax.invert_yaxis()
threshold(ax, horizontal=True)

ax.set_xlim(
    0,
    max(p95(r) for r in seven) * 1.15,
)

ax.set_title(
    "Seven-Robot Configurations (4.0x Workload)"
)

ax.set_xlabel("Mean P95 Response Time (s)")
ax.set_ylabel("Fleet Configuration (C, M, W)")

handles = [
    Patch(color=DARK_BLUE, label="Selected"),
    Patch(color=LIGHT_BLUE, label="Feasible"),
    Patch(color=GRAY, label="Infeasible"),
    Line2D(
        [0], [0],
        color="#64748B",
        linestyle="--",
        label="300 s threshold",
    ),
]

ax.legend(handles=handles, loc="upper right")

style(ax, axis="x")

finish(
    fig,
    "03_all_seven_robot_configurations",
)

# ==================================================
# Figure 4: Three feasible configurations
# ==================================================

fig, ax = plt.subplots(figsize=(8, 5.5))

bars = ax.bar(
    [label(r) for r in seven_pass],
    [p95(r) for r in seven_pass],
    color=[
        DARK_BLUE if fleet(r) == fleet(final)
        else LIGHT_BLUE
        for r in seven_pass
    ],
    width=0.52,
)

ax.bar_label(
    bars,
    fmt="%.2f",
    padding=6,
    fontsize=13,
    fontweight="bold",
)

threshold(ax)

ax.set_title(
    "Feasible Seven-Robot Configurations"
)

ax.set_xlabel("Fleet Configuration (C, M, W)")
ax.set_ylabel("Mean P95 Response Time (s)")
ax.set_ylim(0, 350)

ax.legend(
    loc="upper right",
    frameon=False,
)

style(ax)

finish(
    fig,
    "04_feasible_seven_robot_configurations",
)

# ==================================================
# Save plotting source data
# ==================================================

tables = {
    "fleet_size_comparison_4x.csv": best_by_size,
    "seven_robot_comparison_4x.csv": seven,
    "seven_robot_feasible_4x.csv": seven_pass,
}

for name, records in tables.items():

    with (DATA / name).open(
        "w", newline="", encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(records[0].keys()),
        )

        writer.writeheader()
        writer.writerows(records)

    print("Saved:", DATA / name)

print()
print("Data validation: PASS")
print("Selected fleet:", fleet(final))
print("P95 response:", p95(final))
print("Feasible seven-robot configurations:",
      len(seven_pass))
print("All figures generated successfully.")
