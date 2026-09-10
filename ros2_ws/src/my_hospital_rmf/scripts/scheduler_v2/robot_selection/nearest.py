#!/usr/bin/env python3

from collections.abc import (
    Iterable,
    Mapping,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
    MIN_BATTERY_LEVEL,
    BATTERY_DRAIN_PER_METER,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projected_candidate_filter import (
    filter_projected_feasible_runtimes,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)


# ==========================================================
# Projected Distance
# ==========================================================

def calculate_projected_distance_to_source(
    task: Task,
    runtime: RobotRuntimeState,
    places: Mapping[str, Place],
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
) -> float:
    """
    假設 Task 被分配給此 Robot，
    依照 Priority + Aging 插入 Waiting Queue 後，
    計算 Task 真正開始前：

        Robot projected position
        ->
        Task source

    的距離。

    此距離才是 Nearest Baseline
    用來比較 Robot 的唯一成本。
    """

    projection = (
        project_task_on_robot(
            task=task,
            runtime=runtime,
            places=places,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            service_time_seconds=(
                service_time_seconds
            ),
        )
    )

    return (
        projection.distance_to_source
    )


# ==========================================================
# Priority + Projected Nearest Robot
# ==========================================================

def select_nearest_feasible_robot(
    task: Task,
    runtimes: Iterable[RobotRuntimeState],
    places: Mapping[str, Place],
    current_time: float,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> RobotState | None:
    """
    Baseline 1：
    Priority + Projected Nearest Robot

    流程：

    1. 使用所有方法共用的 Candidate Filter
    2. 對每台 Feasible Robot：
       假設新 Task 依 Priority + Aging
       插入該 Robot 的 Waiting Queue
    3. 計算 Task 真正開始時的 projected position
    4. 計算 projected position -> Task source
    5. 選擇距離最短的 Robot

    此 Baseline 不使用：

    - Battery 高低作為 cost
    - Workload cost
    - Queue length cost
    - Reassignment cost

    Battery 只作為安全門檻。

    若距離完全相同：
        robot_id 較小者優先

    讓實驗結果 deterministic。
    """

    candidate_runtimes = (
        filter_projected_feasible_runtimes(
            task=task,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            battery_threshold=(
                battery_threshold
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    if not candidate_runtimes:

        return None

    selected_runtime = min(
        candidate_runtimes,
        key=lambda runtime: (
            calculate_projected_distance_to_source(
                task=task,
                runtime=runtime,
                places=places,
                current_time=current_time,
                aging_interval_seconds=(
                    aging_interval_seconds
                ),
                service_time_seconds=(
                    service_time_seconds
                ),
            ),
            runtime.robot.robot_id,
        ),
    )

    return selected_runtime.robot