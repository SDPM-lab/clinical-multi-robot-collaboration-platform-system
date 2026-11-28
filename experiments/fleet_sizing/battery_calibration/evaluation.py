from __future__ import annotations

import hashlib
import math
from statistics import mean

import numpy as np

from experiments.fleet_sizing import config as base_config

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
)

from experiments.fleet_sizing.baseline.static_weighted import (
    StaticWeightedScheduler,
)

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.baseline.random_feasible import (
    RandomFeasibleScheduler,
)

from experiments.fleet_sizing.baseline.projected_nearest import (
    ProjectedNearestScheduler,
)

from experiments.fleet_sizing.rl.evaluate_reward_tuned_workload_robustness import (
    calculate_episode_metrics,
)

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)


# ============================================================
# Environment Integrity
# ============================================================

def sha256_file(path):

    if not path.is_file():
        raise FileNotFoundError(path)

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def validate_environment():

    checks = (
        (
            "Nav Graph",
            cfg.NAV_GRAPH_PATH,
            cfg.NAV_GRAPH_SHA256,
        ),
        (
            "Route Summary",
            cfg.ROUTE_SUMMARY_PATH,
            cfg.ROUTE_SUMMARY_SHA256,
        ),
        (
            "Route Results",
            cfg.ROUTE_RESULTS_PATH,
            cfg.ROUTE_RESULTS_SHA256,
        ),
        (
            "PPO Model",
            cfg.PPO_MODEL_PATH,
            cfg.PPO_MODEL_SHA256,
        ),
    )

    for name, path, expected in checks:

        actual = sha256_file(path)

        if actual != expected:
            raise RuntimeError(
                f"{name} SHA256 mismatch\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )

        print(f"{name}: PASS")

    if tuple(base_config.REFERENCE_FLEET) != (
        cfg.FLEET_CONFIGURATION
    ):
        raise RuntimeError("Fleet configuration mismatch")

    if base_config.SIMULATION_DAYS != cfg.SIMULATION_DAYS:
        raise RuntimeError("Simulation horizon mismatch")

    if base_config.REFERENCE_WORKLOAD_MULTIPLIER != (
        cfg.WORKLOAD_MULTIPLIER
    ):
        raise RuntimeError("Workload configuration mismatch")

    if base_config.NAV_GRAPH_PATH.resolve() != (
        cfg.NAV_GRAPH_PATH.resolve()
    ):
        raise RuntimeError("Nav graph path mismatch")

    if base_config.BATCH_ROUTE_SUMMARY_PATH.resolve() != (
        cfg.ROUTE_SUMMARY_PATH.resolve()
    ):
        raise RuntimeError("Route summary path mismatch")

    if not cfg.ENABLE_BATTERY_MODEL:
        raise RuntimeError("Battery model must be enabled")

    print("Shared experiment configuration: PASS")


# ============================================================
# Additional Metrics
# ============================================================

def jain_fairness(values):

    values = [float(v) for v in values]

    if not values:
        return 1.0

    square_sum = sum(v * v for v in values)

    if square_sum == 0.0:
        return 1.0

    return (
        sum(values) ** 2
        / (len(values) * square_sum)
    )


def safe_mean(values):

    values = list(values)

    return mean(values) if values else 0.0


def safe_p95(values):

    values = list(values)

    return (
        float(np.percentile(values, 95))
        if values
        else 0.0
    )


def get_priority_metrics(tasks, priorities, prefix):

    relevant = [
        task
        for task in tasks
        if int(task.priority) in priorities
    ]

    waits = [
        max(
            0.0,
            float(task.start_time_s)
            - float(task.arrival_time_s),
        )
        for task in relevant
        if task.start_time_s is not None
    ]

    responses = [
        max(
            0.0,
            float(task.source_arrival_time_s)
            - float(task.arrival_time_s),
        )
        for task in relevant
        if task.source_arrival_time_s is not None
    ]

    return {
        f"{prefix}_generated_count": len(relevant),
        f"{prefix}_started_count": len(waits),
        f"{prefix}_source_arrival_count": len(responses),
        f"{prefix}_avg_wait_s": safe_mean(waits),
        f"{prefix}_p95_wait_s": safe_p95(waits),
        f"{prefix}_avg_source_response_s":
            safe_mean(responses),
        f"{prefix}_p95_source_response_s":
            safe_p95(responses),
    }


def calculate_unified_metrics(
    *,
    method,
    seed,
    tasks,
    robots,
    assignments,
    episode_reward=None,
):

    # Reuse the existing formal PPO evaluation metrics.
    metrics = calculate_episode_metrics(
        method=method,
        seed=seed,
        tasks=tasks,
        robots=robots,
        assignments=assignments,
        episode_reward=episode_reward,
    )

    makespan_s = float(metrics["makespan_s"])

    utilizations = [
        (
            float(robot.busy_time_s) / makespan_s
            if makespan_s > 0.0
            else 0.0
        )
        for robot in robots
    ]

    metrics["jain_utilization_fairness"] = (
        jain_fairness(utilizations)
    )

    metrics.update(
        get_priority_metrics(
            tasks=tasks,
            priorities={2},
            prefix="high_only",
        )
    )

    metrics.update(
        get_priority_metrics(
            tasks=tasks,
            priorities={3},
            prefix="emergency",
        )
    )

    metrics.update(
        get_priority_metrics(
            tasks=tasks,
            priorities={2, 3},
            prefix="high_emergency",
        )
    )

    return metrics


# ============================================================
# Baseline Scheduler Factory
# ============================================================

def create_scheduler(
    *,
    method,
    seed,
    alpha=None,
    alpha_min=None,
    alpha_max=None,
):

    if method == "random_feasible":
        return RandomFeasibleScheduler(seed=seed)

    if method == "projected_nearest":
        return ProjectedNearestScheduler()

    if method == "static_weighted":

        if alpha is None:
            raise ValueError("Static alpha is required")

        return StaticWeightedScheduler(
            alpha=alpha,
        )

    if method == "dynamic_weighted":

        if alpha_min is None or alpha_max is None:
            raise ValueError(
                "Dynamic alpha range is required"
            )

        return DynamicWeightedScheduler(
            alpha_min=alpha_min,
            alpha_max=alpha_max,
        )

    raise ValueError(
        f"Unsupported method: {method}"
    )


# ============================================================
# Single Baseline Episode
# ============================================================

def run_baseline_episode(
    *,
    method,
    seed,
    workload_multiplier=cfg.WORKLOAD_MULTIPLIER,
    alpha=None,
    alpha_min=None,
    alpha_max=None,
):

    scheduler = create_scheduler(
        method=method,
        seed=seed,
        alpha=alpha,
        alpha_min=alpha_min,
        alpha_max=alpha_max,
    )

    simulator = SchedulingSimulator(
        fleet_configuration=cfg.FLEET_CONFIGURATION,
        seed=seed,
        scheduler=scheduler,
        workload_multiplier=workload_multiplier,
        enable_battery_model=True,
    )

    if not simulator.enable_battery_model:
        raise RuntimeError("Battery model is disabled")

    if simulator.travel_model.summary_csv_path.resolve() != (
        cfg.ROUTE_SUMMARY_PATH.resolve()
    ):
        raise RuntimeError("Unexpected route summary")

    if simulator.travel_model.nav_graph.yaml_path.resolve() != (
        cfg.NAV_GRAPH_PATH.resolve()
    ):
        raise RuntimeError("Unexpected navigation graph")

    result = simulator.run()

    metrics = calculate_unified_metrics(
        method=method,
        seed=seed,
        tasks=result.tasks,
        robots=result.robots,
        assignments=result.assignments,
    )

    metrics["workload_multiplier"] = workload_multiplier
    metrics["battery_enabled"] = True

    if method == "static_weighted":
        metrics["alpha"] = alpha

    if method == "dynamic_weighted":
        metrics["alpha_min"] = alpha_min
        metrics["alpha_max"] = alpha_max

    validate_metrics(metrics)

    return metrics


# ============================================================
# Metric Validation
# ============================================================

def validate_metrics(metrics):

    required = [
        *cfg.PRIMARY_METRICS,
        "completion_rate",
        "jain_utilization_fairness",
    ]

    for field in required:

        if field not in metrics:
            raise KeyError(
                f"Missing metric: {field}"
            )

        value = float(metrics[field])

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid metric: {field}={value}"
            )

        if value < 0.0:
            raise ValueError(
                f"Negative metric: {field}={value}"
            )

    for field in (
        "completion_rate",
        "jain_task_fairness",
        "jain_utilization_fairness",
    ):

        if not 0.0 <= float(metrics[field]) <= 1.0 + 1e-12:
            raise ValueError(
                f"Metric out of range: {field}"
            )

    if not metrics["battery_enabled"]:
        raise RuntimeError("Battery model is disabled")
