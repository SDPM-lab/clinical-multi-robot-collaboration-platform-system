from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, List, Tuple

from config import (
    SIMULATION_DAYS,
    SECONDS_PER_DAY,
)

from models import (
    RobotState,
    TaskState,
)

from simulator import (
    AssignmentRecord,
    SimulationResult,
)


# ============================================================
# Metrics Result
# ============================================================

@dataclass
class SimulationMetrics:
    fleet_configuration: Tuple[int, int, int]
    seed: int

    generated_tasks: int
    assigned_tasks: int

    completed_within_horizon: int
    completed_after_horizon: int
    unserved_tasks: int

    completion_rate: float

    average_waiting_time_s: float
    p95_waiting_time_s: float

    average_source_arrival_time_s: float
    p95_source_arrival_time_s: float

    average_total_time_s: float
    p95_total_time_s: float

    average_robot_utilization: float
    max_robot_utilization: float

    robot_utilization: Dict[str, float]
    robot_type_utilization: Dict[str, float]

    busy_preassignments: int
    busy_preassignment_rate: float


# ============================================================
# Helpers
# ============================================================

def percentile(
    values: List[float],
    p: float,
) -> float:
    """
    Linear interpolation percentile.

    p must be between 0 and 100.
    """

    if not values:
        return 0.0

    if not 0 <= p <= 100:
        raise ValueError(
            f"Percentile must be in [0, 100], got {p}"
        )

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        (len(ordered) - 1)
        * (p / 100.0)
    )

    lower_index = int(position)
    upper_index = min(
        lower_index + 1,
        len(ordered) - 1,
    )

    fraction = (
        position - lower_index
    )

    lower = ordered[lower_index]
    upper = ordered[upper_index]

    return (
        lower
        + fraction * (upper - lower)
    )


# ============================================================
# Main Metrics Calculator
# ============================================================

def calculate_metrics(
    result: SimulationResult,
) -> SimulationMetrics:

    horizon_s = (
        SIMULATION_DAYS
        * SECONDS_PER_DAY
    )

    tasks = result.tasks
    robots = result.robots
    assignments = result.assignments

    generated_tasks = len(tasks)

    assigned_tasks = sum(
        1
        for task in tasks
        if task.assigned_robot is not None
    )

    unserved_tasks = sum(
        1
        for task in tasks
        if task.assigned_robot is None
    )

    completed_within_horizon_tasks = [
        task
        for task in tasks
        if (
            task.completion_time_s
            is not None
            and task.completion_time_s
            <= horizon_s
        )
    ]

    completed_after_horizon_tasks = [
        task
        for task in tasks
        if (
            task.completion_time_s
            is not None
            and task.completion_time_s
            > horizon_s
        )
    ]

    completed_within_horizon = len(
        completed_within_horizon_tasks
    )

    completed_after_horizon = len(
        completed_after_horizon_tasks
    )

    if generated_tasks > 0:
        completion_rate = (
            completed_within_horizon
            / generated_tasks
        )
    else:
        completion_rate = 1.0

    # ========================================================
    # Waiting Time
    #
    # Definition:
    # task arrival
    # -> robot begins executing this task
    #
    # For busy pre-assigned robots this includes queue delay.
    # ========================================================

    waiting_times = [
        task.start_time_s
        - task.arrival_time_s
        for task in tasks
        if task.start_time_s is not None
    ]

    average_waiting_time_s = (
        mean(waiting_times)
        if waiting_times
        else 0.0
    )

    p95_waiting_time_s = percentile(
        waiting_times,
        95,
    )

    # ========================================================
    # Source Arrival / Response Time
    #
    # task arrival
    # -> robot reaches task source
    #
    # This includes:
    # queue delay + approach travel.
    # ========================================================

    source_arrival_times = [
        (
            record.source_arrival_time_s
            - record.task_arrival_time_s
        )
        for record in assignments
    ]

    average_source_arrival_time_s = (
        mean(source_arrival_times)
        if source_arrival_times
        else 0.0
    )

    p95_source_arrival_time_s = percentile(
        source_arrival_times,
        95,
    )

    # ========================================================
    # Total Task Time
    #
    # task arrival -> task completion
    # ========================================================

    total_times = [
        task.completion_time_s
        - task.arrival_time_s
        for task in tasks
        if task.completion_time_s is not None
    ]

    average_total_time_s = (
        mean(total_times)
        if total_times
        else 0.0
    )

    p95_total_time_s = percentile(
        total_times,
        95,
    )

    # ========================================================
    # Robot Utilization
    #
    # Important:
    # Only busy time that occurs INSIDE the 7-day horizon
    # should count toward utilization.
    #
    # Current robot.busy_time_s may include work scheduled
    # after the horizon, so calculate from assignment records.
    # ========================================================

    robot_busy_within_horizon: Dict[
        str,
        float
    ] = {
        robot.robot_id: 0.0
        for robot in robots
    }

    for record in assignments:

        start = (
            record.dispatch_start_time_s
        )

        end = (
            record.completion_time_s
        )

        clipped_start = max(
            0.0,
            start,
        )

        clipped_end = min(
            horizon_s,
            end,
        )

        if clipped_end <= clipped_start:
            continue

        robot_busy_within_horizon[
            record.robot_id
        ] += (
            clipped_end
            - clipped_start
        )

    robot_utilization = {}

    for robot in robots:

        utilization = (
            robot_busy_within_horizon[
                robot.robot_id
            ]
            / horizon_s
        )

        robot_utilization[
            robot.robot_id
        ] = utilization

    if robot_utilization:

        average_robot_utilization = mean(
            robot_utilization.values()
        )

        max_robot_utilization = max(
            robot_utilization.values()
        )

    else:
        average_robot_utilization = 0.0
        max_robot_utilization = 0.0

    # ========================================================
    # Robot Type Utilization
    # ========================================================

    type_utilization_values: Dict[
        str,
        List[float]
    ] = {}

    for robot in robots:

        type_utilization_values.setdefault(
            robot.robot_type,
            [],
        ).append(
            robot_utilization[
                robot.robot_id
            ]
        )

    robot_type_utilization = {
        robot_type: mean(values)
        for robot_type, values
        in type_utilization_values.items()
    }

    # ========================================================
    # Busy pre-assignment
    # ========================================================

    busy_preassignments = sum(
        1
        for record in assignments
        if record.robot_was_busy
    )

    if assignments:
        busy_preassignment_rate = (
            busy_preassignments
            / len(assignments)
        )
    else:
        busy_preassignment_rate = 0.0

    return SimulationMetrics(
        fleet_configuration=(
            result.fleet_configuration
        ),

        seed=result.seed,

        generated_tasks=generated_tasks,
        assigned_tasks=assigned_tasks,

        completed_within_horizon=(
            completed_within_horizon
        ),

        completed_after_horizon=(
            completed_after_horizon
        ),

        unserved_tasks=unserved_tasks,

        completion_rate=completion_rate,

        average_waiting_time_s=(
            average_waiting_time_s
        ),

        p95_waiting_time_s=(
            p95_waiting_time_s
        ),

        average_source_arrival_time_s=(
            average_source_arrival_time_s
        ),

        p95_source_arrival_time_s=(
            p95_source_arrival_time_s
        ),

        average_total_time_s=(
            average_total_time_s
        ),

        p95_total_time_s=(
            p95_total_time_s
        ),

        average_robot_utilization=(
            average_robot_utilization
        ),

        max_robot_utilization=(
            max_robot_utilization
        ),

        robot_utilization=(
            robot_utilization
        ),

        robot_type_utilization=(
            robot_type_utilization
        ),

        busy_preassignments=(
            busy_preassignments
        ),

        busy_preassignment_rate=(
            busy_preassignment_rate
        ),
    )


# ============================================================
# Pretty Print
# ============================================================

def print_metrics(
    metrics: SimulationMetrics,
) -> None:

    print(
        "Fleet:",
        metrics.fleet_configuration,
    )

    print(
        "Seed:",
        metrics.seed,
    )

    print()

    print(
        "Generated tasks:",
        metrics.generated_tasks,
    )

    print(
        "Assigned tasks:",
        metrics.assigned_tasks,
    )

    print(
        "Completed within horizon:",
        metrics.completed_within_horizon,
    )

    print(
        "Completed after horizon:",
        metrics.completed_after_horizon,
    )

    print(
        "Unserved tasks:",
        metrics.unserved_tasks,
    )

    print(
        "Completion rate:",
        f"{metrics.completion_rate * 100:.2f}%",
    )

    print()

    print(
        "Average waiting time:",
        f"{metrics.average_waiting_time_s:.2f} s",
    )

    print(
        "P95 waiting time:",
        f"{metrics.p95_waiting_time_s:.2f} s",
    )

    print()

    print(
        "Average source-arrival time:",
        f"{metrics.average_source_arrival_time_s:.2f} s",
    )

    print(
        "P95 source-arrival time:",
        f"{metrics.p95_source_arrival_time_s:.2f} s",
    )

    print()

    print(
        "Average total task time:",
        f"{metrics.average_total_time_s:.2f} s",
    )

    print(
        "P95 total task time:",
        f"{metrics.p95_total_time_s:.2f} s",
    )

    print()

    print(
        "Average robot utilization:",
        f"{metrics.average_robot_utilization * 100:.2f}%",
    )

    print(
        "Max robot utilization:",
        f"{metrics.max_robot_utilization * 100:.2f}%",
    )

    print()

    print(
        "Per-robot utilization:"
    )

    for robot_id, utilization in (
        metrics.robot_utilization.items()
    ):
        print(
            f"  {robot_id}: "
            f"{utilization * 100:.2f}%"
        )

    print()

    print(
        "Per-type utilization:"
    )

    for robot_type, utilization in (
        metrics.robot_type_utilization.items()
    ):
        print(
            f"  {robot_type}: "
            f"{utilization * 100:.2f}%"
        )

    print()

    print(
        "Busy pre-assignments:",
        metrics.busy_preassignments,
    )

    print(
        "Busy pre-assignment rate:",
        f"{metrics.busy_preassignment_rate * 100:.2f}%",
    )


# ============================================================
# Manual Run
# ============================================================

if __name__ == "__main__":

    from simulator import (
        FleetSizingSimulator,
    )

    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    result = simulator.run()

    metrics = calculate_metrics(
        result
    )

    print_metrics(
        metrics
    )