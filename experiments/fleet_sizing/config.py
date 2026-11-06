from pathlib import Path


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

NAV_GRAPH_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "my_hospital_rmf"
    / "nav_graphs"
    / "0.yaml"
)

ROBOT_PROFILES_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "my_hospital_rmf"
    / "config"
    / "robot_profiles.yaml"
)

TASK_PROFILES_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "src"
    / "my_hospital_rmf"
    / "config"
    / "task_profiles.yaml"
)

BATCH_ROUTE_RESULTS_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "batch_route_results.csv"
)

BATCH_ROUTE_SUMMARY_PATH = (
    PROJECT_ROOT
    / "ros2_ws"
    / "batch_route_summary.csv"
)

RESULTS_DIR = (
    Path(__file__).resolve().parent
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Simulation
# ============================================================

SIMULATION_DAYS = 7

SECONDS_PER_DAY = 24 * 60 * 60

SIMULATION_HORIZON_S = (
    SIMULATION_DAYS
    * SECONDS_PER_DAY
)

# Initial number of Monte Carlo replications.
#
# 30 replications are used for the current experiments.
# If confidence intervals are too wide later,
# the replication count can be increased.
INITIAL_REPLICATIONS = 30

# Target relative half-width for 95% confidence interval.
CI_RELATIVE_HALF_WIDTH_TARGET = 0.05


# ============================================================
# Fleet Sizing Criteria
# ============================================================

# At least 99% of generated tasks should be completed.
#
# This is an experimental criterion used in this study,
# not a universal clinical requirement.
COMPLETION_RATE_THRESHOLD = 0.99

# Worst replication should also maintain at least
# the same completion-rate requirement.
MIN_SEED_COMPLETION_RATE_THRESHOLD = 0.99

# Avoid operating the fleet close to saturation.
UTILIZATION_THRESHOLD = 0.90

# ------------------------------------------------------------
# Reference Service-Level Constraint
# ------------------------------------------------------------
#
# Under the original 1x base workload and the minimum
# structurally feasible heterogeneous fleet (1, 1, 1),
# the observed mean P95 source-response time was
# approximately 297.6 seconds.
#
# Therefore 300 seconds is used as the reference
# service-quality constraint during demand/fleet
# sensitivity analysis.
#
# IMPORTANT:
# This is an experimental reference service level.
# It is NOT claimed to be a universal clinical standard.
# ------------------------------------------------------------

P95_RESPONSE_TIME_THRESHOLD_S = 300.0


# ============================================================
# Robot Types
# ============================================================

ROBOT_TYPE_CLEAN = "clean"
ROBOT_TYPE_MEDICAL = "medical"
ROBOT_TYPE_WARD = "ward"

ROBOT_TYPES = (
    ROBOT_TYPE_CLEAN,
    ROBOT_TYPE_MEDICAL,
    ROBOT_TYPE_WARD,
)


# ============================================================
# Basic Fleet Candidates
# ============================================================
#
# Tuple order:
#
#   (
#       clean_count,
#       medical_count,
#       ward_count,
#   )
#
# These configurations are retained for the original
# basic fleet sweep.
#
# The final reference fleet is defined separately below
# based on the demand-scale sensitivity experiment.
# ============================================================

FLEET_CANDIDATES = [
    (1, 1, 1),

    (2, 1, 1),
    (1, 2, 1),
    (1, 1, 2),

    (2, 2, 1),
    (2, 1, 2),
    (1, 2, 2),

    (2, 2, 2),
]


# ============================================================
# Task Types
# ============================================================

TASK_WASTE = "waste_transport"

TASK_CLOTHES = "clothes_collection"

TASK_MEDICATION = "medication_delivery"

TASK_SPECIMEN = "specimen_delivery"

TASK_WARD = "ward_service"

TASK_TYPES = (
    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
)


# ============================================================
# Base Workload
# ============================================================
#
# These values describe the ORIGINAL base-demand model.
#
# They are expected task counts per day.
#
# Waste:
#   expected 11/day
#
# Clothes:
#   6 legal sources × Bernoulli(p=0.5)
#   = expected 3/day
#
# Medication:
#   expected 22/day
#
# Specimen:
#   expected 18/day
#
# Ward:
#   exactly 4/day under the base workload
#
# Total:
#   approximately 58 tasks/day
# ============================================================

NORMAL_WORKLOAD_PER_DAY = {
    TASK_WASTE: 11,
    TASK_CLOTHES: 3,
    TASK_MEDICATION: 22,
    TASK_SPECIMEN: 18,
    TASK_WARD: 4,
}

EXPECTED_TOTAL_TASKS_PER_DAY = sum(
    NORMAL_WORKLOAD_PER_DAY.values()
)


# ============================================================
# Legal Task Locations
# ============================================================

WASTE_SOURCES = [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "nurse_station",
    "blood_draw",
    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",
]

WASTE_DESTINATION = (
    "waste_return_2"
)


CLOTHES_SOURCES = [
    "ward_a_2",
    "ward_b_2",
    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",
]

CLOTHES_DESTINATION = (
    "clothes_return_2"
)


MEDICATION_SOURCE = (
    "pharmacy"
)

MEDICATION_DESTINATIONS = [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "nurse_station",
]


SPECIMEN_CLINICAL_LOCATIONS = [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "blood_draw",
]

SPECIMEN_LAB = (
    "lab"
)


WARD_SOURCE = (
    "nurse_station"
)

WARD_DESTINATIONS = [
    "ward_a_2",
    "ward_b_2",
]


CHARGING_WAYPOINT = (
    "charging_station_2"
)


# ============================================================
# Task Arrival Model
# ============================================================

# ------------------------------------------------------------
# Waste
# ------------------------------------------------------------
#
# Each legal source has a Poisson-like daily expected
# demand corresponding to approximately 1 task/source/day.
#
# Arrival time:
#   Uniform between 10:00 and 16:00.
# ------------------------------------------------------------

WASTE_ARRIVAL_WINDOW = {
    "start_hour": 10,
    "end_hour": 16,
}


# ------------------------------------------------------------
# Clothes
# ------------------------------------------------------------
#
# Each legal source produces a clothes task with:
#
#   Bernoulli(p=0.5)
#
# Expected total:
#
#   6 × 0.5 = 3/day
#
# Arrival time:
#   Uniform between 09:00 and 17:00.
# ------------------------------------------------------------

CLOTHES_DAILY_PROBABILITY_PER_SOURCE = 0.5

CLOTHES_ARRIVAL_WINDOW = {
    "start_hour": 9,
    "end_hour": 17,
}


# ------------------------------------------------------------
# Medication
# ------------------------------------------------------------
#
# 50% scheduled
# 50% on-demand
# ------------------------------------------------------------

MEDICATION_SCHEDULED_FRACTION = 0.50

MEDICATION_SCHEDULED_BASE_HOURS = [
    8,
    12,
    18,
    22,
]

MEDICATION_SCHEDULED_JITTER_MINUTES = 30

# On-demand medication task arrival distribution
# across four 6-hour time blocks.

MEDICATION_ON_DEMAND_TIME_WEIGHTS = {
    (0, 6): 0.10,
    (6, 12): 0.30,
    (12, 18): 0.35,
    (18, 24): 0.25,
}


# ------------------------------------------------------------
# Specimen
# ------------------------------------------------------------
#
# NHPP-like piecewise time-of-day demand profile.
# ------------------------------------------------------------

SPECIMEN_TIME_WEIGHTS = {
    (0, 6): 0.05,
    (6, 12): 0.40,
    (12, 18): 0.35,
    (18, 24): 0.20,
}

# Direction assumption:
#
# 70%:
#   clinical location -> lab
#
# 30%:
#   lab -> clinical location

SPECIMEN_CLINICAL_TO_LAB_PROBABILITY = 0.70


# ------------------------------------------------------------
# Ward Service
# ------------------------------------------------------------
#
# Two wards × two routine rounds:
#
#   08:00
#   20:00
#
# ±15-minute jitter.
#
# Base workload therefore produces exactly 4 ward
# service tasks per day.
# ------------------------------------------------------------

WARD_BASE_HOURS = [
    8,
    20,
]

WARD_JITTER_MINUTES = 15


# ============================================================
# Service Time Model
# ============================================================
#
# Uniform distributions are represented as:
#
#   (
#       minimum_seconds,
#       maximum_seconds,
#   )
# ============================================================

SERVICE_TIME_CONFIG = {

    TASK_WASTE: {

        "detect_s": (
            5,
            10,
        ),

        "pick_per_item_s": (
            8,
            15,
        ),

        "drop_per_item_s": (
            5,
            10,
        ),

        "item_count_probabilities": {
            1: 0.05,
            2: 0.10,
            3: 0.20,
            4: 0.25,
            5: 0.20,
            6: 0.08,
            7: 0.05,
            8: 0.03,
            9: 0.02,
            10: 0.02,
        },
    },


    TASK_CLOTHES: {

        "detect_s": (
            5,
            10,
        ),

        "pick_per_item_s": (
            12,
            20,
        ),

        "drop_per_item_s": (
            8,
            15,
        ),

        "item_count_probabilities": {
            1: 0.10,
            2: 0.20,
            3: 0.25,
            4: 0.20,
            5: 0.10,
            6: 0.07,
            7: 0.05,
            8: 0.03,
        },
    },


    TASK_MEDICATION: {

        "load_s": (
            20,
            40,
        ),

        "handoff_s": (
            10,
            30,
        ),
    },


    TASK_SPECIMEN: {

        "load_verify_s": (
            25,
            45,
        ),

        "receive_s": (
            15,
            30,
        ),
    },


    TASK_WARD: {

        "vital_sign_s": (
            212,
            238,
        ),
    },
}


# ============================================================
# Battery-aware Scheduling Model
# ============================================================

# Disabled by default so the original v1 experiments remain
# unchanged. Battery-aware v2 explicitly enables this model.
ENABLE_BATTERY_MODEL = False


# ------------------------------------------------------------
# State of Charge
# ------------------------------------------------------------

# Every robot starts an episode fully charged.
BATTERY_INITIAL_SOC = 1.0

# Experimental scheduling parameter:
# the robot must retain at least 15% SoC after the
# navigation energy committed to a candidate task.
BATTERY_MIN_RESERVE_SOC = 0.15

# Experimental charging policy:
# when an idle robot falls to or below 25% SoC,
# it should return to the charging station.
BATTERY_CHARGE_TRIGGER_SOC = 0.25

# Experimental charging policy:
# the robot becomes dispatchable again at 80% SoC.
BATTERY_RESUME_SOC = 0.80


# ------------------------------------------------------------
# Travel Energy Model
# ------------------------------------------------------------

# Reference:
# AGIBOT A2 official specification reports approximately
# 1.5 hours of continuous walking on flat ground.
#
# The simulator therefore normalizes one full battery to
# 1.5 hours of continuous navigation.
#
# Battery consumption uses observable / estimable travel
# time only. Realized service_time_s is NOT used by the
# scheduler.
BATTERY_TRAVEL_RUNTIME_FULL_S = (
    1.5
    * 60.0
    * 60.0
)

BATTERY_TRAVEL_DRAIN_PER_SECOND = (
    1.0
    / BATTERY_TRAVEL_RUNTIME_FULL_S
)


# ------------------------------------------------------------
# Charging Model
# ------------------------------------------------------------

# Reference:
# AGIBOT A2 official specification reports approximately
# 2 hours charging time.
BATTERY_FULL_CHARGE_TIME_S = (
    2.0
    * 60.0
    * 60.0
)

BATTERY_CHARGE_RATE_PER_SECOND = (
    1.0
    / BATTERY_FULL_CHARGE_TIME_S
)


# ------------------------------------------------------------
# Idle Robot Behavior
# ------------------------------------------------------------
#
# In the current fleet-sizing model:
#
# after completing a task, a robot remains at the task
# destination.
#
# It does NOT automatically return to the charging station.
#
# This keeps travel-time assumptions consistent with the
# fleet-sizing experiments already completed.
# ------------------------------------------------------------

RETURN_TO_CHARGE_WHEN_IDLE = False


# Retained for compatibility with code that may inspect
# this flag.
#
# Since RETURN_TO_CHARGE_WHEN_IDLE=False, this normally
# has no effect in the current experiment.

RETURNING_TO_CHARGE_IS_AVAILABLE = True


# Fleet-sizing assignment policy.
#
# Capability-compatible robots are candidates.
#
# Busy robots may receive future tasks.
#
# Selection is based on the projected earliest
# feasible availability / ETA logic.

ASSIGNMENT_POLICY = (
    "earliest_available_feasible"
)


# ============================================================
# Robot Capabilities
# ============================================================

ROBOT_CAPABILITIES = {

    ROBOT_TYPE_CLEAN: {
        TASK_WASTE,
        TASK_CLOTHES,
    },

    ROBOT_TYPE_MEDICAL: {
        TASK_MEDICATION,
        TASK_SPECIMEN,
    },

    ROBOT_TYPE_WARD: {
        TASK_MEDICATION,
        TASK_WARD,
    },
}


# ============================================================
# Task Priority
# ============================================================

PRIORITY_LOW = 0

PRIORITY_NORMAL = 1

PRIORITY_HIGH = 2

PRIORITY_EMERGENCY = 3

PRIORITY_LEVELS = (
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_HIGH,
    PRIORITY_EMERGENCY,
)


# ------------------------------------------------------------
# Priority distributions
# ------------------------------------------------------------
#
# These probabilities are simulation assumptions.
# They are NOT presented as universal hospital statistics.
#
# Waste / clothes are mostly routine.
#
# Medication / specimen contain a larger proportion of
# high-priority and emergency tasks.
# ------------------------------------------------------------

TASK_PRIORITY_DISTRIBUTIONS = {

    TASK_WASTE: {

        PRIORITY_LOW: 0.60,

        PRIORITY_NORMAL: 0.35,

        PRIORITY_HIGH: 0.05,

        PRIORITY_EMERGENCY: 0.00,
    },


    TASK_CLOTHES: {

        PRIORITY_LOW: 0.55,

        PRIORITY_NORMAL: 0.40,

        PRIORITY_HIGH: 0.05,

        PRIORITY_EMERGENCY: 0.00,
    },


    TASK_MEDICATION: {

        PRIORITY_LOW: 0.05,

        PRIORITY_NORMAL: 0.55,

        PRIORITY_HIGH: 0.30,

        PRIORITY_EMERGENCY: 0.10,
    },


    TASK_SPECIMEN: {

        PRIORITY_LOW: 0.05,

        PRIORITY_NORMAL: 0.50,

        PRIORITY_HIGH: 0.30,

        PRIORITY_EMERGENCY: 0.15,
    },


    TASK_WARD: {

        PRIORITY_LOW: 0.05,

        PRIORITY_NORMAL: 0.60,

        PRIORITY_HIGH: 0.30,

        PRIORITY_EMERGENCY: 0.05,
    },
}


# ============================================================
# Demand-Scale Scenarios
# ============================================================
#
# The original workload model is retained as the
# base-demand scenario.
#
# Sensitivity analysis scales arrival intensity while
# retaining:
#
#   - task-type structure
#   - legal source/destination pairs
#   - temporal demand patterns
#   - service-time model
#   - priority model
#
# Approximate observed tasks/day:
#
#   1x ->  58/day
#   3x -> 174/day
#   4x -> 231/day
#   5x -> 288/day
#   8x -> 463/day
#
# The 4x case is selected as the representative
# reference workload for subsequent scheduling
# experiments.
# ============================================================

WORKLOAD_SCENARIOS = {

    "base": 1.0,

    "moderate": 3.0,

    "reference": 4.0,

    "high": 5.0,

    "stress": 8.0,
}


# ============================================================
# Demand Sensitivity Experiment
# ============================================================

DEMAND_SENSITIVITY_MULTIPLIERS = (
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    8.0,
)


# ============================================================
# Final Reference Scenario
# ============================================================
#
# Base demand:
#
#   approximately 58 tasks/day
#
# Sensitivity analysis showed:
#
#   workload multiplier = 4.0
#   approximately 231 tasks/day
#
# Minimum heterogeneous fleet satisfying:
#
#   mean completion rate >= 99%
#
#   worst-seed completion rate >= 99%
#
#   maximum utilization < 90%
#
#   mean P95 source-response time <= 300 s
#
# was:
#
#   2 Clean
#   2 Medical
#   3 Ward
#
# Total:
#
#   7 robots
#
# Therefore this scenario is frozen as the primary
# reference environment for subsequent baseline and
# reinforcement-learning experiments.
# ============================================================

REFERENCE_WORKLOAD_MULTIPLIER = 4.0

REFERENCE_EXPECTED_TASKS_PER_DAY = (
    EXPECTED_TOTAL_TASKS_PER_DAY
    * REFERENCE_WORKLOAD_MULTIPLIER
)

REFERENCE_FLEET = (
    2,  # Clean
    2,  # Medical
    3,  # Ward
)

REFERENCE_CLEAN_COUNT = (
    REFERENCE_FLEET[0]
)

REFERENCE_MEDICAL_COUNT = (
    REFERENCE_FLEET[1]
)

REFERENCE_WARD_COUNT = (
    REFERENCE_FLEET[2]
)

REFERENCE_TOTAL_ROBOTS = sum(
    REFERENCE_FLEET
)


# ============================================================
# Reference Scenario Metadata
# ============================================================
#
# These constants are used for reporting and experiment
# configuration.
# ============================================================

REFERENCE_SCENARIO_NAME = (
    "reference"
)

REFERENCE_SCENARIO_DESCRIPTION = (
    "4x base hospital demand with "
    "2 Clean, 2 Medical, and 3 Ward robots"
)


# ============================================================
# Configuration Validation
# ============================================================

def validate_config() -> None:
    """
    Validate important experiment configuration assumptions.

    Raises:
        ValueError:
            If the configuration contains inconsistent values.
    """

    # --------------------------------------------------------
    # Priority distributions
    # --------------------------------------------------------

    for task_type, distribution in (
        TASK_PRIORITY_DISTRIBUTIONS.items()
    ):

        total_probability = sum(
            distribution.values()
        )

        if abs(
            total_probability - 1.0
        ) > 1e-9:

            raise ValueError(
                f"Priority distribution for "
                f"{task_type} does not sum to 1.0: "
                f"{total_probability}"
            )

    # --------------------------------------------------------
    # Workload scenario
    # --------------------------------------------------------

    if (
        WORKLOAD_SCENARIOS[
            REFERENCE_SCENARIO_NAME
        ]
        != REFERENCE_WORKLOAD_MULTIPLIER
    ):

        raise ValueError(
            "Reference workload multiplier is inconsistent "
            "with WORKLOAD_SCENARIOS."
        )

    # --------------------------------------------------------
    # Fleet
    # --------------------------------------------------------

    if (
        REFERENCE_TOTAL_ROBOTS
        != sum(REFERENCE_FLEET)
    ):

        raise ValueError(
            "REFERENCE_TOTAL_ROBOTS does not match "
            "REFERENCE_FLEET."
        )

    if any(
        count < 1
        for count in REFERENCE_FLEET
    ):

        raise ValueError(
            "Each robot type must have at least one robot "
            "in the reference heterogeneous fleet."
        )

    # --------------------------------------------------------
    # Fleet-sizing criteria
    # --------------------------------------------------------

    if not (
        0.0
        < COMPLETION_RATE_THRESHOLD
        <= 1.0
    ):

        raise ValueError(
            "COMPLETION_RATE_THRESHOLD must be "
            "within (0, 1]."
        )

    if not (
        0.0
        < MIN_SEED_COMPLETION_RATE_THRESHOLD
        <= 1.0
    ):

        raise ValueError(
            "MIN_SEED_COMPLETION_RATE_THRESHOLD must be "
            "within (0, 1]."
        )

    if not (
        0.0
        < UTILIZATION_THRESHOLD
        <= 1.0
    ):

        raise ValueError(
            "UTILIZATION_THRESHOLD must be "
            "within (0, 1]."
        )

    if (
        P95_RESPONSE_TIME_THRESHOLD_S
        <= 0.0
    ):

        raise ValueError(
            "P95_RESPONSE_TIME_THRESHOLD_S "
            "must be positive."
        )


validate_config()