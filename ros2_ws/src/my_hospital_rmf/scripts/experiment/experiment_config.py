#!/usr/bin/env python3


# ==========================================================
# Experiment Scale
# ==========================================================

TASK_COUNTS = [
    20,
    50,
    100,
]


# ==========================================================
# Load Profiles Used In Formal Experiments
# ==========================================================

LOADS = [
    "low",
    "medium",
    "high",
]


# ==========================================================
# Random Seeds
#
# 0 ~ 29
# 共 30 個 seeds
# ==========================================================

SEEDS = list(
    range(30)
)


# ==========================================================
# Robot Initial State Profiles
# ==========================================================

BATTERY_PROFILE = (
    "stress"
)

CAPABILITY_PROFILE = (
    "competitive"
)


# ==========================================================
# Simulator Parameters
# ==========================================================

ROBOT_SPEED = (
    1.0
)

SERVICE_TIME = (
    5.0
)


# ==========================================================
# Priority Definition
# ==========================================================

PRIORITY_LOW = 0
PRIORITY_NORMAL = 1
PRIORITY_HIGH = 2
PRIORITY_EMERGENCY = 3


# ==========================================================
# Experiment Metadata
# ==========================================================

EXPERIMENT_NAME = (
    "formal_scheduler_comparison"
)


# ==========================================================
# Helper
# ==========================================================

def print_experiment_config():

    print("=" * 100)
    print("EXPERIMENT CONFIG")
    print("=" * 100)

    print(
        "Experiment Name:",
        EXPERIMENT_NAME,
    )

    print(
        "Task Counts:",
        TASK_COUNTS,
    )

    print(
        "Loads:",
        LOADS,
    )

    print(
        "Seeds:",
        f"{SEEDS[0]} ~ {SEEDS[-1]}",
    )

    print(
        "Seed Count:",
        len(
            SEEDS
        ),
    )

    print(
        "Battery Profile:",
        BATTERY_PROFILE,
    )

    print(
        "Capability Profile:",
        CAPABILITY_PROFILE,
    )

    print(
        "Robot Speed:",
        ROBOT_SPEED,
    )

    print(
        "Service Time:",
        SERVICE_TIME,
    )

    print("=" * 100)