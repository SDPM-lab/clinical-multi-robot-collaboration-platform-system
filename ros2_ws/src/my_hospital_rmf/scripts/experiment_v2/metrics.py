#!/usr/bin/env python3

from dataclasses import (
    dataclass,
)

from typing import (
    Optional,
)

from experiment_v2.models import (
    SimulationResult,
)

from collections import (
    Counter,
)


# ==========================================================
# Priority
# ==========================================================

PRIORITIES = (
    0,
    1,
    2,
    3,
)


# ==========================================================
# Experiment Metrics
# ==========================================================

@dataclass(frozen=True)
class ExperimentMetrics:
    """
    一個完整 Episode 的評估指標。

    注意：

    task_success_rate 使用 0.0 ~ 1.0。

    Decision Time 單位：
        second
    """

    # ------------------------------------------------------
    # Task Time
    # ------------------------------------------------------

    average_task_waiting_time: Optional[float]

    waiting_time_by_priority: dict[
        int,
        Optional[float],
    ]

    average_task_completion_time: Optional[float]

    makespan: Optional[float]

    # ------------------------------------------------------
    # Distance / Success
    # ------------------------------------------------------

    total_travel_distance: float

    task_success_rate: float

    # ------------------------------------------------------
    # Workload
    # ------------------------------------------------------

    robot_utilization: dict[
        str,
        float,
    ]

    jain_fairness_index: float

    # ------------------------------------------------------
    # Decision Performance
    # ------------------------------------------------------

    average_decision_time_seconds: float

    max_decision_time_seconds: float

    # ------------------------------------------------------
    # Supporting Counts
    # ------------------------------------------------------

    total_tasks: int

    completed_tasks: int

    failed_tasks: int

    total_decisions: int

    # ======================================================
    # Dynamic Scheduling
    # ======================================================

    # 所有 reassignment evaluation 次數，
    # 包含最後選擇 Stay 的情況。
    reassignment_decision_count: int = 0

    # 真正 previous_robot != selected_robot
    # 的次數。
    reassignment_count: int = 0

    # actual changes / reassignment decisions
    reassignment_rate: float = 0.0

    # Actual Robot Changes / Total Tasks
    average_reassignments_per_task: float = 0.0

    # 單一 Task 最多真正換過幾次 Robot。
    max_reassignments_per_task: int = 0

    # Episode 中最高 cascade depth。
    max_cascade_depth: int = 0


# ==========================================================
# Mean
# ==========================================================

def calculate_mean(
    values: list[float],
) -> Optional[float]:
    """
    計算平均值。

    若沒有資料：
        return None

    使用 None 而不是 0，
    避免把：

        沒有資料

    誤解成：

        平均值真的等於 0
    """

    if not values:

        return None

    return (
        sum(values)
        /
        len(values)
    )


# ==========================================================
# Waiting Time
# ==========================================================

def calculate_average_waiting_time(
    result: SimulationResult,
) -> Optional[float]:
    """
    Average Task Waiting Time

        Start Time - Arrival Time

    只有真正開始執行的 Task
    才具有 Waiting Time。

    Failed 且從未開始的 Task
    不會被填成 0。
    """

    waiting_times = [
        record.waiting_time
        for record
        in result.task_records.values()
        if record.waiting_time
        is not None
    ]

    return calculate_mean(
        waiting_times
    )


# ==========================================================
# Waiting Time By Priority
# ==========================================================

def calculate_waiting_time_by_priority(
    result: SimulationResult,
) -> dict[
    int,
    Optional[float],
]:
    """
    分別計算：

        0 = Low
        1 = Normal
        2 = High
        3 = Emergency

    的 Average Waiting Time。

    若某 Priority 沒有可計算的 Task，
    該值為 None。
    """

    result_by_priority = {}

    for priority in PRIORITIES:

        waiting_times = [
            record.waiting_time
            for record
            in result.task_records.values()
            if (
                record.priority
                ==
                priority
                and
                record.waiting_time
                is not None
            )
        ]

        result_by_priority[
            priority
        ] = calculate_mean(
            waiting_times
        )

    return result_by_priority


# ==========================================================
# Completion Time
# ==========================================================

def calculate_average_completion_time(
    result: SimulationResult,
) -> Optional[float]:
    """
    Average Task Completion Time

        Completion Time
        -
        Arrival Time

    僅對有完成時間的 Task 計算。
    """

    completion_times = [
        record.completion_duration
        for record
        in result.task_records.values()
        if record.completion_duration
        is not None
    ]

    return calculate_mean(
        completion_times
    )


# ==========================================================
# Makespan
# ==========================================================

def calculate_makespan(
    result: SimulationResult,
) -> Optional[float]:
    """
    Makespan

        max(Task Completion Time)
        -
        Episode Start Time

    若 Episode 沒有任何完成 Task：
        return None
    """

    completion_times = [
        record.completion_time
        for record
        in result.task_records.values()
        if record.completion_time
        is not None
    ]

    if not completion_times:

        return None

    return (
        max(completion_times)
        -
        result.episode_start_time
    )


# ==========================================================
# Travel Distance
# ==========================================================

def calculate_total_travel_distance(
    result: SimulationResult,
) -> float:
    """
    所有 Robot 在 Episode 中
    產生的總移動距離。
    """

    return sum(
        record.total_travel_distance
        for record
        in result.robot_records.values()
    )


# ==========================================================
# Task Success Rate
# ==========================================================

def calculate_task_success_rate(
    result: SimulationResult,
) -> float:
    """
    Task Success Rate

        Completed Tasks
        /
        Total Tasks

    內部使用 0.0 ~ 1.0。

    若 Episode 沒有 Task，
    回傳 0.0。
    """

    total_tasks = len(
        result.task_records
    )

    if total_tasks == 0:

        return 0.0

    completed_tasks = sum(
        1
        for record
        in result.task_records.values()
        if record.status
        ==
        "completed"
    )

    return (
        completed_tasks
        /
        total_tasks
    )


# ==========================================================
# Robot Utilization
# ==========================================================

def calculate_robot_utilization(
    result: SimulationResult,
) -> dict[str, float]:
    """
    每台 Robot 的 Utilization：

        Busy Time
        /
        Episode Duration

    若 Episode Duration = 0：
        utilization = 0
    """

    episode_duration = (
        result.episode_duration
    )

    utilizations = {}

    for robot_id, record in (
        result.robot_records.items()
    ):

        if episode_duration <= 0.0:

            utilization = 0.0

        else:

            utilization = (
                record.busy_time
                /
                episode_duration
            )

        utilizations[
            robot_id
        ] = utilization

    return utilizations


# ==========================================================
# Jain's Fairness Index
# ==========================================================

def calculate_jain_fairness_index(
    values: list[float],
) -> float:
    """
    Jain's Fairness Index：

            (sum(x_i))^2
        ---------------------
        n * sum(x_i^2)

    範圍通常為：

        1 / N ~ 1

    越接近 1：
        工作量越平均。

    若所有 values 都是 0，
    表示所有 Robot 工作量完全相同，
    此處定義 fairness = 1.0。
    """

    if not values:

        return 1.0

    if any(
        value < 0.0
        for value in values
    ):

        raise ValueError(
            "Jain fairness values "
            "cannot be negative"
        )

    total = sum(
        values
    )

    squared_total = sum(
        value * value
        for value in values
    )

    if squared_total == 0.0:

        return 1.0

    return (
        total * total
        /
        (
            len(values)
            *
            squared_total
        )
    )


# ==========================================================
# Decision Time
# ==========================================================

def calculate_average_decision_time(
    result: SimulationResult,
) -> float:
    """
    Scheduler 平均 Decision Time。

    單位：
        second
    """

    decision_times = [
        record.decision_duration_seconds
        for record
        in result.decision_records
    ]

    if not decision_times:

        return 0.0

    return (
        sum(decision_times)
        /
        len(decision_times)
    )


def calculate_max_decision_time(
    result: SimulationResult,
) -> float:
    """
    Episode 中最大的單次 Decision Time。
    """

    decision_times = [
        record.decision_duration_seconds
        for record
        in result.decision_records
    ]

    if not decision_times:

        return 0.0

    return max(
        decision_times
    )


# ==========================================================
# Dynamic Reassignment Metrics
# ==========================================================

def calculate_reassignment_decision_count(
    result: SimulationResult,
) -> int:
    """
    有多少次 Waiting Task
    被 Dynamic Scheduler 重新評估。

    Stay 也算一次 Decision。
    """

    return sum(
        1
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "reassignment"
        )
    )


def calculate_reassignment_count(
    result: SimulationResult,
) -> int:
    """
    真正 Assigned Robot 發生變化的次數。
    """

    return sum(
        1
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "reassignment"
            and
            decision.changed
        )
    )


def calculate_reassignment_rate(
    result: SimulationResult,
) -> float:
    """
    Changed Robot Decisions
    -----------------------
    Total Reassignment Decisions
    """

    decision_count = (
        calculate_reassignment_decision_count(
            result
        )
    )

    if decision_count == 0:

        return 0.0

    changed_count = (
        calculate_reassignment_count(
            result
        )
    )

    return (
        changed_count
        /
        decision_count
    )


def calculate_average_reassignments_per_task(
    result: SimulationResult,
) -> float:
    """
    Actual Reassignments
    --------------------
    Total Tasks

    沒有被 Reassign 的 Task
    也包含在分母。
    """

    task_count = len(
        result.task_records
    )

    if task_count == 0:

        return 0.0

    return (
        calculate_reassignment_count(
            result
        )
        /
        task_count
    )


def calculate_max_reassignments_per_task(
    result: SimulationResult,
) -> int:
    """
    找出 Episode 中
    單一 Task 真正換 Robot 的最大次數。
    """

    counts = Counter(
        decision.task_id
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "reassignment"
            and
            decision.changed
        )
    )

    if not counts:

        return 0

    return max(
        counts.values()
    )


def calculate_max_cascade_depth(
    result: SimulationResult,
) -> int:
    """
    Dynamic Reassignment
    最大 Cascade Depth。

    Static Episode 沒有 reassignment：
        0
    """

    depths = [
        decision.cascade_depth
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "reassignment"
        )
    ]

    if not depths:

        return 0

    return max(
        depths
    )


# ==========================================================
# Full Metrics
# ==========================================================

def calculate_metrics(
    result: SimulationResult,
) -> ExperimentMetrics:
    """
    從 SimulationResult
    一次產生完整 Static Baseline Metrics。
    """

    robot_utilization = (
        calculate_robot_utilization(
            result=result
        )
    )

    total_tasks = len(
        result.task_records
    )

    completed_tasks = sum(
        1
        for record
        in result.task_records.values()
        if record.status
        ==
        "completed"
    )

    failed_tasks = sum(
        1
        for record
        in result.task_records.values()
        if record.status
        ==
        "failed"
    )

    return ExperimentMetrics(
        average_task_waiting_time=(
            calculate_average_waiting_time(
                result=result
            )
        ),

        waiting_time_by_priority=(
            calculate_waiting_time_by_priority(
                result=result
            )
        ),

        average_task_completion_time=(
            calculate_average_completion_time(
                result=result
            )
        ),

        makespan=(
            calculate_makespan(
                result=result
            )
        ),

        total_travel_distance=(
            calculate_total_travel_distance(
                result=result
            )
        ),

        task_success_rate=(
            calculate_task_success_rate(
                result=result
            )
        ),

        robot_utilization=(
            robot_utilization
        ),

        jain_fairness_index=(
            calculate_jain_fairness_index(
                list(
                    robot_utilization.values()
                )
            )
        ),

        average_decision_time_seconds=(
            calculate_average_decision_time(
                result=result
            )
        ),

        max_decision_time_seconds=(
            calculate_max_decision_time(
                result=result
            )
        ),

        total_tasks=(
            total_tasks
        ),

        completed_tasks=(
            completed_tasks
        ),

        failed_tasks=(
            failed_tasks
        ),

        total_decisions=len(
            result.decision_records
        ),

        reassignment_decision_count=(
            calculate_reassignment_decision_count(
                result
            )
        ),

        reassignment_count=(
            calculate_reassignment_count(
                result
            )
        ),

        reassignment_rate=(
            calculate_reassignment_rate(
                result
            )
        ),

        average_reassignments_per_task=(
            calculate_average_reassignments_per_task(
                result
            )
        ),

        max_reassignments_per_task=(
            calculate_max_reassignments_per_task(
                result
            )
        ),

        max_cascade_depth=(
            calculate_max_cascade_depth(
                result
            )
        ),
    )