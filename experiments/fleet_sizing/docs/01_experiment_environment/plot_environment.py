from pathlib import Path
from datetime import datetime
import ast
import hashlib
import json

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import ListedColormap
from matplotlib.ticker import PercentFormatter

DOC = Path(__file__).resolve().parent
DATA = DOC / "data"
FIG = DOC / "figures"

BLUE = "#2563EB"
LIGHT_BLUE = "#A6BAD4"
GRAY = "#D4D4D4"

CONFIG_FILE = DATA / "environment_config.json"
ARCHIVE_FILE = DATA / "environment_manifest.json"
ROUTE_FILE = (
    DATA / "nav2_calibration"
    / "batch_route_summary_nav2.csv"
)


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


config = json.loads(CONFIG_FILE.read_text())
archive = json.loads(ARCHIVE_FILE.read_text())

assert archive["file_count"] == 19
assert len(archive["files"]) == 19
assert len(config) == 82

assert sha(CONFIG_FILE) == archive[
    "configuration_sha256"
]

for record in archive["files"]:
    path = DOC / record["archive"]
    assert sha(path) == record["sha256"], path

print("Environment archive integrity: PASS")

if FIG.exists():
    assert not any(FIG.rglob("*.png"))
    assert not any(FIG.rglob("*.svg"))

FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.5,
    "grid.linestyle": "--",
    "legend.frameon": False,
    "svg.fonttype": "none",
})

TASKS = config["TASK_TYPES"]
ROBOTS = config["ROBOT_TYPES"]

NAMES = dict(zip(
    TASKS,
    ["Waste", "Clothes", "Medication",
     "Specimen", "Ward"],
))

records = []


def save(fig, name, sources):

    outputs = []

    for ext in ("png", "svg"):

        path = FIG / f"{name}.{ext}"

        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            pad_inches=0.15,
        )

        outputs.append({
            "file": str(path.relative_to(DOC)),
            "sha256": sha(path),
            "size_bytes": path.stat().st_size,
        })

    records.append({
        "name": name,
        "sources": [
            {
                "file": str(p.relative_to(DOC)),
                "sha256": sha(p),
            }
            for p in sources
        ],
        "outputs": outputs,
    })

    plt.close(fig)

    print(name, "| PNG + SVG PASS")


def footer(fig, text):

    fig.text(
        0.5, 0.015, text,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#555555",
    )


def block(ax, x, y, w, h, title, detail,
          color=BLUE):

    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04",
        facecolor="white",
        edgecolor=color,
        linewidth=1.6,
    )

    ax.add_patch(patch)

    ax.text(
        x + w/2, y + h*0.72,
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=color,
    )

    ax.text(
        x + w/2, y + h*0.30,
        detail,
        ha="center",
        va="center",
        fontsize=10,
    )


def arrow(ax, x1, y1, x2, y2):

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


def diagram(title, width=12, height=7):

    fig, ax = plt.subplots(figsize=(width, height))

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    fig.suptitle(
        title,
        fontsize=18,
        fontweight="bold",
    )

    return fig, ax


# ============================================================
# Figure 01: Environment Architecture
# ============================================================

fig, ax = diagram(
    "Hospital Scheduling Simulation Architecture"
)

block(
    ax, 0.3, 5.3, 5.4, 1.3,
    "Task Generation",
    "Workload / Arrival time / Priority\n"
    "Task type / Source / Destination",
)

block(
    ax, 6.3, 5.3, 5.4, 1.3,
    "Navigation Cost Model",
    "Nav2 empirical travel times\n"
    "Directed graph fallback",
)

block(
    ax, 2, 3.4, 8, 1.3,
    "Event-driven Scheduling Simulator",
    "Robot state / Task queue / Service time\n"
    "Battery and charging lifecycle",
)

block(
    ax, 0.3, 1.55, 5.4, 1.2,
    "Baseline Schedulers",
    "Random / Nearest / Static / Dynamic",
    "#555555",
)

block(
    ax, 6.3, 1.55, 5.4, 1.2,
    "Maskable PPO",
    "Observation / Action mask / Robot selection",
)

block(
    ax, 2, 0.1, 8, 0.9,
    "Evaluation Metrics",
    "Waiting / Response / Travel / Fairness / Battery",
    "#333333",
)

for coordinates in [
    (3, 5.3, 4.5, 4.75),
    (9, 5.3, 7.5, 4.75),
    (4, 3.4, 3, 2.8),
    (8, 3.4, 9, 2.8),
    (3, 1.55, 4.5, 1.05),
    (9, 1.55, 7.5, 1.05),
]:
    arrow(ax, *coordinates)

save(
    fig,
    "01_environment_architecture",
    [
        CONFIG_FILE,
        DOC / "scripts/scheduling_simulator.py",
        DOC / "scripts/rl/environment.py",
        DOC / "scripts/travel_time.py",
    ],
)


# ============================================================
# Figure 02: Experiment Version Evolution
# ============================================================

fig, ax = diagram(
    "Experimental Environment Evolution"
)

stages = [
    (
        0.25,
        "Historical Fleet Sizing",
        "Original travel calibration\n"
        "Battery disabled\n\n"
        "Reference fleet selection",
        "#777777",
    ),
    (
        4.35,
        "Battery-aware V2",
        "Original travel calibration\n"
        "Battery enabled\n\n"
        "Early reward screening",
        "#6596DB",
    ),
    (
        8.45,
        "Nav2-calibrated V2",
        "Nav2 travel calibration\n"
        "Battery enabled\n\n"
        "Final training and evaluation",
        BLUE,
    ),
]

for x, title, detail, color in stages:

    block(
        ax, x, 2.4, 3.3, 2.8,
        title, detail, color,
    )

arrow(ax, 3.6, 3.8, 4.3, 3.8)
arrow(ax, 7.7, 3.8, 8.4, 3.8)

ax.text(
    6, 1.35,
    "Reference fleet retained: (2, 2, 3)",
    ha="center",
    fontsize=13,
    fontweight="bold",
)

ax.text(
    6, 0.7,
    "Fleet size was not re-optimized after Nav2 calibration.",
    ha="center",
    fontsize=11,
)

save(
    fig,
    "02_experiment_version_evolution",
    [CONFIG_FILE, ARCHIVE_FILE],
)


# ============================================================
# Figure 03: Capability Matrix
# ============================================================

matrix = np.array([
    [
        int(task in config[
            "ROBOT_CAPABILITIES"
        ][robot])
        for task in TASKS
    ]
    for robot in ROBOTS
])

fig, ax = plt.subplots(figsize=(10, 4.8))

ax.imshow(
    matrix,
    cmap=ListedColormap(
        ["#EEEEEE", BLUE]
    ),
    vmin=0,
    vmax=1,
    aspect="auto",
)

ax.grid(False)

ax.set_xticks(
    range(len(TASKS)),
    [NAMES[t] for t in TASKS],
)

ax.set_yticks(
    range(len(ROBOTS)),
    [
        f"{robot.title()} "
        f"({config['REFERENCE_FLEET'][i]} robots)"
        for i, robot in enumerate(ROBOTS)
    ],
)

for i in range(matrix.shape[0]):

    for j in range(matrix.shape[1]):

        available = bool(matrix[i, j])

        ax.text(
            j, i,
            "Feasible" if available else "-",
            ha="center",
            va="center",
            color="white" if available else "#777777",
            fontweight="bold" if available else "normal",
        )

ax.set_title("Heterogeneous Robot Capability Matrix")

footer(
    fig,
    "Medication delivery can be handled by Medical or Ward robots.",
)

fig.tight_layout(rect=[0, 0.05, 1, 1])

save(
    fig,
    "03_robot_capability_matrix",
    [CONFIG_FILE],
)


# ============================================================
# Figure 04: Base Workload Distribution
# ============================================================

base = [
    config["NORMAL_WORKLOAD_PER_DAY"][t]
    for t in TASKS
]

multiplier = config[
    "REFERENCE_WORKLOAD_MULTIPLIER"
]

scaled = [v * multiplier for v in base]

x = np.arange(len(TASKS))

fig, ax = plt.subplots(figsize=(10, 6))

bars1 = ax.bar(
    x - 0.18, base,
    width=0.36,
    color=GRAY,
    label="Base workload (1x)",
)

bars2 = ax.bar(
    x + 0.18, scaled,
    width=0.36,
    color=BLUE,
    label=f"Reference workload ({multiplier:.0f}x)",
)

ax.bar_label(bars1, fmt="%.0f", padding=3)
ax.bar_label(bars2, fmt="%.0f", padding=3)

ax.set_xticks(
    x,
    [NAMES[t] for t in TASKS],
)

ax.set_ylabel("Expected Tasks per Day")
ax.set_ylim(0, max(scaled)*1.2)

ax.set_title("Base and Reference Workload")
ax.legend()

footer(
    fig,
    f"Nominal totals: {sum(base):.0f}/day at 1x; "
    f"{sum(scaled):.0f}/day at {multiplier:.0f}x. "
    "Actual task counts are stochastic.",
)

fig.tight_layout(rect=[0, 0.06, 1, 1])

save(
    fig,
    "04_base_workload_distribution",
    [CONFIG_FILE],
)


# ============================================================
# Figure 05: Temporal Demand Distribution
# ============================================================

def temporal_values(key):

    values = []

    for label, weight in config[key].items():

        start, end = ast.literal_eval(label)

        values.append(
            (start, end, float(weight))
        )

    return sorted(values)


medication = temporal_values(
    "MEDICATION_ON_DEMAND_TIME_WEIGHTS"
)

specimen = temporal_values(
    "SPECIMEN_TIME_WEIGHTS"
)

assert [
    r[:2] for r in medication
] == [
    r[:2] for r in specimen
]

x = np.arange(len(medication))

fig, ax = plt.subplots(figsize=(10, 6))

b1 = ax.bar(
    x - 0.18,
    [r[2] for r in medication],
    width=0.36,
    color=LIGHT_BLUE,
    label="On-demand Medication",
)

b2 = ax.bar(
    x + 0.18,
    [r[2] for r in specimen],
    width=0.36,
    color=BLUE,
    label="Specimen",
)

ax.bar_label(
    b1,
    labels=[f"{r[2]:.0%}" for r in medication],
    padding=3,
)

ax.bar_label(
    b2,
    labels=[f"{r[2]:.0%}" for r in specimen],
    padding=3,
)

ax.set_xticks(
    x,
    [
        f"{r[0]:02d}:00-{r[1]:02d}:00"
        for r in medication
    ],
)

ax.set_ylim(0, 0.5)
ax.yaxis.set_major_formatter(PercentFormatter(1))

ax.set_ylabel("Demand Probability")
ax.set_xlabel("Time of Day")

ax.set_title("Time-of-day Demand Distribution")
ax.legend()

footer(
    fig,
    "Medication profile applies only to the on-demand portion.",
)

fig.tight_layout(rect=[0, 0.05, 1, 1])

save(
    fig,
    "05_temporal_demand_distribution",
    [CONFIG_FILE],
)


# ============================================================
# Figure 06: Task Priority Distribution
# ============================================================

fig, ax = plt.subplots(figsize=(10, 5.8))

priority_names = [
    "Low", "Normal", "High", "Emergency"
]

colors = [
    "#D4D4D4",
    "#A6BAD4",
    "#6596DB",
    BLUE,
]

left = np.zeros(len(TASKS))

for p, label in enumerate(priority_names):

    values = np.array([
        config["TASK_PRIORITY_DISTRIBUTIONS"][
            t
        ][str(p)]
        for t in TASKS
    ])

    ax.barh(
        range(len(TASKS)),
        values,
        left=left,
        color=colors[p],
        label=label,
    )

    for i, value in enumerate(values):

        if value >= 0.05:

            ax.text(
                left[i] + value/2,
                i,
                f"{value:.0%}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if p >= 2 else "#111111",
            )

    left += values

assert np.allclose(left, 1)

ax.set_yticks(
    range(len(TASKS)),
    [NAMES[t] for t in TASKS],
)

ax.invert_yaxis()

ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(PercentFormatter(1))

ax.set_title("Task Priority Distribution")
ax.set_xlabel("Probability")

ax.legend(
    loc="upper center",
    bbox_to_anchor=(0.5, -0.14),
    ncol=4,
)

ax.grid(axis="y", visible=False)

footer(
    fig,
    "Priority probabilities are simulation assumptions.",
)

fig.tight_layout(rect=[0, 0.12, 1, 1])

save(
    fig,
    "06_task_priority_distribution",
    [CONFIG_FILE],
)


# ============================================================
# Figure 07: Service Time Model
# ============================================================

service = config["SERVICE_TIME_CONFIG"]

rows = []

for task in TASKS:

    for component, limits in service[task].items():

        if not component.endswith("_s"):
            continue

        rows.append((
            NAMES[task],
            component.removesuffix("_s")
            .replace("_", " ").title(),
            limits[0],
            limits[1],
        ))

fig, axes = plt.subplots(
    1, 2,
    figsize=(15, 7),
    gridspec_kw={"width_ratios": [1.6, 1]},
)

ax = axes[0]

for i, (task, component, low, high) in enumerate(rows):

    ax.hlines(
        i, low, high,
        color=BLUE,
        linewidth=5,
    )

    ax.scatter(
        [low, high], [i, i],
        color=BLUE,
        s=25,
    )

    ax.text(
        high + 4, i,
        f"{low}-{high}",
        va="center",
        fontsize=9,
    )

ax.set_yticks(
    range(len(rows)),
    [f"{r[0]}: {r[1]}" for r in rows],
)

ax.set_xlim(
    0,
    max(r[3] for r in rows) + 40,
)

ax.invert_yaxis()
ax.set_title("Uniform Service Time Ranges")
ax.set_xlabel("Seconds")

ax = axes[1]

counts = np.arange(1, 11)

for i, task in enumerate(TASKS[:2]):

    probabilities = service[task][
        "item_count_probabilities"
    ]

    ax.bar(
        counts + (i-0.5)*0.35,
        [
            probabilities.get(str(n), 0)
            for n in counts
        ],
        width=0.35,
        label=NAMES[task],
        color=[LIGHT_BLUE, BLUE][i],
    )

ax.set_xticks(counts)
ax.yaxis.set_major_formatter(PercentFormatter(1))

ax.set_title("Item Count Distribution")
ax.set_xlabel("Number of Items")
ax.set_ylabel("Probability")
ax.legend()

fig.suptitle(
    "Task Service Time Model",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "Pick and drop durations are per item. "
    "Service time excludes navigation.",
)

fig.tight_layout(rect=[0, 0.055, 1, 0.94])

save(
    fig,
    "07_service_time_model",
    [CONFIG_FILE, DOC / "scripts/service_time.py"],
)


# ============================================================
# Figure 08: Nav2 Route Calibration
# ============================================================

routes = pd.read_csv(ROUTE_FILE)

assert len(routes) == 31
assert routes["n"].sum() == 155
assert (routes["n"] == 5).all()

assert not routes.duplicated(
    ["source", "destination"]
).any()

routes = routes.sort_values(
    "mean_travel_time_s"
).reset_index(drop=True)

speed = routes.loc[
    routes["mean_average_speed_mps"] > 0,
    "mean_average_speed_mps"
].mean()

assert np.isclose(
    speed,
    0.3289677419354839,
)

labels = [
    f"{r.source} -> {r.destination}"
    for r in routes.itertuples()
]

fig, ax = plt.subplots(figsize=(12, 12))

y = np.arange(len(routes))

ax.barh(
    y,
    routes["mean_travel_time_s"],
    xerr=routes["sd_travel_time_s"],
    color=BLUE,
    alpha=0.85,
    capsize=2,
    error_kw={
        "elinewidth": 1,
        "ecolor": "#333333",
    },
)

ax.set_yticks(y, labels, fontsize=9)

ax.set_xlabel("Travel Time (seconds)")

ax.set_title(
    "Nav2 Empirical Route Calibration"
)

ax.grid(axis="y", visible=False)

footer(
    fig,
    f"31 directed routes | 155 trials | Mean +/- SD | "
    f"Effective speed: {speed:.4f} m/s\n"
    "The scheduling model uses route means, "
    "not random travel-time samples.",
)

fig.tight_layout(rect=[0, 0.07, 1, 1])

save(
    fig,
    "08_nav2_route_calibration",
    [
        ROUTE_FILE,
        DOC / "scripts/travel_time.py",
    ],
)


# ============================================================
# Figure 09: Battery Lifecycle
# ============================================================

fig, ax = diagram(
    "Battery-aware Robot Lifecycle"
)

initial = config["BATTERY_INITIAL_SOC"]
trigger = config["BATTERY_CHARGE_TRIGGER_SOC"]
resume = config["BATTERY_RESUME_SOC"]
reserve = config["BATTERY_MIN_RESERVE_SOC"]

block(
    ax, 3.5, 5.85, 5, 0.85,
    "Idle / Available",
    f"Initial SOC = {initial:.0%}",
)

block(
    ax, 3.5, 4.5, 5, 0.9,
    "Execute Task",
    "Reserve approach and task travel energy",
)

block(
    ax, 3.5, 3.05, 5, 0.9,
    "Task Completion",
    "Check remaining SOC",
)

block(
    ax, 0.25, 1.55, 5, 0.9,
    "Remain Available",
    f"Post-task SOC >= {trigger:.0%}",
    "#555555",
)

block(
    ax, 6.75, 1.55, 5, 0.9,
    "Return to Charging Station",
    f"Post-task SOC < {trigger:.0%}",
)

block(
    ax, 6.75, 0.1, 5, 0.9,
    "Charging",
    f"Restore availability at {resume:.0%}",
)

for coordinates in [
    (6, 5.85, 6, 5.45),
    (6, 4.5, 6, 4.0),
    (5, 3.05, 2.75, 2.5),
    (7, 3.05, 9.25, 2.5),
    (9.25, 1.55, 9.25, 1.05),
]:

    arrow(ax, *coordinates)

ax.plot(
    [0.25, 0.05, 0.05, 3.45],
    [2, 2, 6.27, 6.27],
    color="#777777",
    linestyle="--",
)

arrow(ax, 3.25, 6.27, 3.48, 6.27)

ax.plot(
    [11.75, 11.95, 11.95, 8.55],
    [0.55, 0.55, 6.27, 6.27],
    color=BLUE,
    linestyle="--",
)

arrow(ax, 8.8, 6.27, 8.52, 6.27)

ax.text(
    2.75, 0.65,
    f"Task feasibility reserve: {reserve:.0%}\n"
    "Navigation energy model only",
    ha="center",
    va="center",
    fontsize=10,
)

footer(
    fig,
    "Post-task charging branch only; "
    "additional queue-repair conditions are not shown.",
)

save(
    fig,
    "09_battery_aware_lifecycle",
    [
        CONFIG_FILE,
        DOC / "scripts/scheduling_simulator.py",
    ],
)


# ============================================================
# Figure 10: Metric Definitions
# ============================================================

fig, ax = plt.subplots(figsize=(12, 5.8))

ax.axis("off")

cells = [
    [
        "Completion Rate",
        "Completed within horizon\n"
        "/ Generated tasks",
        "Final completed tasks\n"
        "/ Generated tasks",
    ],
    [
        "Busy Time",
        "Task execution intervals\n"
        "clipped to 7-day horizon",
        "Accumulated approach + task travel\n"
        "+ service time",
    ],
    [
        "Utilization Denominator",
        "7-day horizon\n"
        "604,800 seconds",
        "Makespan\n"
        "Latest task completion time",
    ],
    [
        "Battery Model",
        "Disabled",
        "Enabled",
    ],
    [
        "Evaluation Function",
        "calculate_metrics()",
        "calculate_episode_metrics()",
    ],
]

table = ax.table(
    cellText=cells,
    colLabels=[
        "Metric",
        "Historical Fleet Sizing",
        "Formal PPO Evaluation",
    ],
    cellLoc="center",
    colLoc="center",
    colWidths=[0.25, 0.36, 0.39],
    loc="center",
)

table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 3.2)

for (row, col), cell in table.get_celld().items():

    cell.set_edgecolor("#C0C0C0")

    if row == 0:

        cell.set_facecolor(
            BLUE if col == 2 else "#555555"
        )

        cell.set_text_props(
            color="white",
            fontweight="bold",
        )

    elif col == 0:

        cell.set_facecolor("#EEEEEE")

        cell.set_text_props(
            fontweight="bold"
        )

    elif col == 2:

        cell.set_facecolor("#EFF6FF")

    else:

        cell.set_facecolor("white")

fig.suptitle(
    "Evaluation Metric Definitions Across Stages",
    fontsize=17,
    fontweight="bold",
)

footer(
    fig,
    "Completion and utilization values are not directly "
    "comparable across the two experimental stages.",
)

fig.tight_layout(rect=[0, 0.06, 1, 0.91])

save(
    fig,
    "10_evaluation_metric_definitions",
    [
        DOC / "scripts/metrics.py",
        DOC / "scripts/scheduling_simulator.py",
        DOC / "scripts/rl/"
        "evaluate_reward_tuned_workload_robustness.py",
        CONFIG_FILE,
    ],
)


# ============================================================
# Figure Manifest
# ============================================================

assert len(records) == 10
assert len(list(FIG.glob("*.png"))) == 10
assert len(list(FIG.glob("*.svg"))) == 10

manifest = {
    "created_at": datetime.now().astimezone().isoformat(),
    "figure_count": 10,
    "png_count": 10,
    "svg_count": 10,
    "png_dpi": 300,
    "environment_manifest_sha256": sha(ARCHIVE_FILE),
    "configuration_sha256": sha(CONFIG_FILE),
    "plot_script_sha256": sha(Path(__file__)),
    "matplotlib_version": matplotlib.__version__,
    "figures": records,
}

(FIG / "figure_manifest.json").write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== ENVIRONMENT FIGURE REPORT =====")
print("Figure groups: 10")
print("PNG files: 10")
print("SVG files: 10")
print("Source integrity: PASS")
print("Original experiment data modified: NO")
print("New simulations: 0")
print("Figures: COMPLETE")
