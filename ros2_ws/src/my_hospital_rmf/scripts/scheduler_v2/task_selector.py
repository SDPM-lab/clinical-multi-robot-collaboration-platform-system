#!/usr/bin/env python3

from collections.abc import (
    Iterable,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
)

from scheduler_v2.models import (
    Task,
)


# ==========================================================
# Waiting Time
# ==========================================================

def calculate_waiting_time(
    task: Task,
    current_time: float,
) -> float:
    """
    計算 Task 從建立到目前為止的等待時間。

    若 current_time 小於 created_at，
    為避免產生負等待時間，
    統一回傳 0。
    """

    waiting_time = (
        float(current_time)
        -
        task.created_at
    )

    return max(
        0.0,
        waiting_time,
    )


# ==========================================================
# Effective Priority
# ==========================================================

def calculate_effective_priority(
    task: Task,
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
) -> float:
    """
    使用 Priority + Aging 計算目前實際排序分數。

    Formula:

        effective_priority
        =
        base_priority
        +
        waiting_time / aging_interval

    注意：
    這不會修改 task.priority。
    """

    if aging_interval_seconds <= 0.0:

        raise ValueError(
            "aging_interval_seconds "
            "must be greater than 0"
        )

    waiting_time = (
        calculate_waiting_time(
            task=task,
            current_time=current_time,
        )
    )

    return (
        float(task.priority)
        +
        waiting_time
        /
        aging_interval_seconds
    )


# ==========================================================
# Sort Key
# ==========================================================

def task_priority_key(
    task: Task,
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
) -> tuple[int, float, float, str]:
    """
    產生 Task 排序 key。

    排序規則：

    1. Emergency Protection
       Emergency (priority=3) 永遠優先於
       Low / Normal / High。

    2. Effective Priority
       同一層級內，
       Effective Priority 越高越前面。

       Non-Emergency Task 可透過 Aging
       提高順位，避免 starvation。

    3. created_at
       Effective Priority 相同時，
       越早建立的 Task 越前面。

    4. task_id
       created_at 也相同時，
       使用 task_id 作為 deterministic tie-break。
    """

    effective_priority = (
        calculate_effective_priority(
            task=task,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
        )
    )

    # ------------------------------------------------------
    # Emergency Protection
    #
    # Python sorted() 預設由小到大。
    #
    # Emergency:
    #   emergency_rank = 0
    #
    # Non-Emergency:
    #   emergency_rank = 1
    #
    # 因此 Emergency 永遠排在前面，
    # 不會被其他 Task 的 Aging 超越。
    # ------------------------------------------------------

    if task.priority == 3:

        emergency_rank = 0

    else:

        emergency_rank = 1

    return (
        emergency_rank,
        -effective_priority,
        task.created_at,
        task.task_id,
    )


# ==========================================================
# Sort Tasks
# ==========================================================

def sort_tasks(
    tasks: Iterable[Task],
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
) -> list[Task]:
    """
    根據 Priority + Aging 對 Task 排序。

    此函式不判斷：
    - Capability
    - Robot
    - Battery
    - Task Status

    呼叫端應先決定哪些 Task 要參與排序。
    """

    return sorted(
        tasks,
        key=lambda task: task_priority_key(
            task=task,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
        ),
    )


# ==========================================================
# Select Next Task
# ==========================================================

def select_next_task(
    tasks: Iterable[Task],
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
) -> Task | None:
    """
    從傳入的 Task 中，
    選出目前 Priority + Aging 排名最高者。

    如果沒有 Task：
        return None
    """

    ordered_tasks = (
        sort_tasks(
            tasks=tasks,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
        )
    )

    if not ordered_tasks:

        return None

    return ordered_tasks[0]