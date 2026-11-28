from pathlib import Path

# ============================================================
# Paths
# ============================================================

FLEET_SIZING_ROOT = Path(__file__).resolve().parents[1]

PROJECT_ROOT = FLEET_SIZING_ROOT.parents[1]

RESULTS_ROOT = (
    FLEET_SIZING_ROOT
    / "results"
    / "battery_baseline_calibration_v2"
)

STATIC_OUTPUT_DIR = RESULTS_ROOT / "static"

DYNAMIC_OUTPUT_DIR = RESULTS_ROOT / "dynamic"

SMOKE_OUTPUT_DIR = RESULTS_ROOT / "smoke"


# ============================================================
# Shared Experimental Environment
# ============================================================

FLEET_CONFIGURATION = (2, 2, 3)

WORKLOAD_MULTIPLIER = 4.0

SIMULATION_DAYS = 7

ENABLE_BATTERY_MODEL = True

CALIBRATION_SEEDS = tuple(range(3001, 3011))


# ============================================================
# Static Weighted Calibration
# ============================================================

STATIC_ALPHAS = (
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
)

ORIGINAL_STATIC_ALPHA = 0.5


# ============================================================
# Dynamic Weighted Calibration
# ============================================================

DYNAMIC_ALPHA_RANGES = tuple(
    (i / 10, j / 10)
    for i in range(11)
    for j in range(i + 1, 11)
)

ORIGINAL_DYNAMIC_ALPHA_RANGE = (0.4, 0.8)


# ============================================================
# Primary Metrics
# ============================================================

# -1: lower is better
# +1: higher is better

PRIMARY_METRICS = {
    "average_waiting_time_s": -1,
    "p95_waiting_time_s": -1,
    "high_waiting_time_s": -1,
    "emergency_waiting_time_s": -1,
    "total_travel_time_s": -1,
    "jain_task_fairness": 1,
}

MIN_MEAN_COMPLETION_RATE = 0.99

MIN_SEED_COMPLETION_RATE = 0.99


# ============================================================
# Rank-Sum Tie Breakers
# ============================================================

TIE_BREAK_METRICS = (
    "emergency_waiting_time_s",
    "high_waiting_time_s",
    "p95_waiting_time_s",
    "average_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
)


# ============================================================
# Frozen PPO Model
# ============================================================

PPO_MODEL_PATH = (
    FLEET_SIZING_ROOT
    / "results_rl"
    / "models"
    / "reward_confirm_sweep27_w50_a30_q15_i05_seed7104_200k"
    / "final_model.zip"
)

PPO_MODEL_SHA256 = (
    "ba278857a1042ed58ae38e9522c7a962d"
    "73abd467d539de9479773cf96fe55e0"
)


# ============================================================
# Frozen Navigation Data
# ============================================================

NAV_GRAPH_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "my_hospital_rmf"
    / "nav_graphs"
    / "0.yaml"
)

NAV_GRAPH_SHA256 = (
    "91c491b860ce97036ecceba4cf2460085"
    "baf9169d22484c1328cd722dc94bf79"
)

ROUTE_SUMMARY_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "batch_route_summary_nav2.csv"
)

ROUTE_SUMMARY_SHA256 = (
    "0baf6a695bacd2dac8f99a9e1b540dbb3"
    "0901dfff0086afb93a0666acf030399"
)

ROUTE_RESULTS_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "batch_route_results_nav2.csv"
)

ROUTE_RESULTS_SHA256 = (
    "2afdbdf57e8f5f0ffe6d318ec689c10b8"
    "b638477476ea63e56483b3ef6377b4a"
)
