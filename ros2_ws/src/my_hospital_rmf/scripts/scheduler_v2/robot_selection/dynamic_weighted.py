#!/usr/bin/env python3

import math

from collections.abc import (
    Iterable,
    Mapping,
)

from dataclasses import (
    dataclass,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    BATTERY_DRAIN_PER_METER,
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
    DISTANCE_NORMALIZATION_REFERENCE,
    DYNAMIC_REASSIGNMENT_MIN_IMPROVEMENT,
    MIN_BATTERY_LEVEL,
    WEIGHTED_BATTERY_WEIGHT,
    WEIGHTED_DISTANCE_WEIGHT,
    WEIGHTED_WORKLOAD_WEIGHT,
    WORKLOAD_NORMALIZATION_REFERENCE_SECONDS,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.robot_selection.weighted import (
    score_weighted_candidates,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)


# ==========================================================
# Result
# ==========================================================

@dataclass(frozen=True)
class DynamicWeightedEvaluation:
    """
    一次 Waiting Task 的 Dynamic Reassignment 評估結果。
    """

    task_id: str

    previous_robot: str

    selected_robot: str

    # Current Robot 如果仍然 feasible，
    # 這裡會有目前方案的 Weighted Cost。
    #
    # 若 Current Robot 已失效 / 不可行，
    # 則為 None。
    current_cost: float | None

    selected_cost: float

    best_alternative_robot: str | None

    best_alternative_cost: float | None

    # current_cost - alternative_cost
    #
    # 若沒有可比較的 Current / Alternative，
    # 則為 None。
    improvement: float | None

    # 方便 Debug / Experiment 分析：
    #
    # current_best
    # no_alternative
    # below_hysteresis
    # improved
    # current_infeasible
    # emergency_start_guard
    reason: str

    @property
    def changed(self) -> bool:

        return (
            self.previous_robot
            !=
            self.selected_robot
        )


# ==========================================================
# Hysteresis
# ==========================================================

def should_reassign(
    current_cost: float,
    alternative_cost: float,
    minimum_improvement: float = (
        DYNAMIC_REASSIGNMENT_MIN_IMPROVEMENT
    ),
) -> bool:
    """
    判斷 Alternative 是否值得 Reassign。

    Improvement：

        current_cost
        -
        alternative_cost

    必須「明顯大於」 minimum_improvement
    才允許換 Robot。

    剛好等於 threshold 時：
        Stay
    """

    current_cost = float(
        current_cost
    )

    alternative_cost = float(
        alternative_cost
    )

    minimum_improvement = float(
        minimum_improvement
    )

    if minimum_improvement < 0.0:

        raise ValueError(
            "minimum_improvement "
            "cannot be negative"
        )

    improvement = (
        current_cost
        -
        alternative_cost
    )

    if math.isclose(
        improvement,
        minimum_improvement,
        rel_tol=1e-9,
        abs_tol=1e-12,
    ):

        return False

    return (
        improvement
        >
        minimum_improvement
    )


# ==========================================================
# Priority-Aware Reassignment Safety
# ==========================================================

def calculate_projected_start_delay(
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
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> float:
    """
    計算 Task 在指定 Robot 上
    預計還要多久才能 Start。

    projected_start_time
        =
        current_time
        +
        workload_before_task

    因為同一次 Reassignment Decision
    的 current_time 相同，
    所以只需要比較 workload_before_task。
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
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    return float(
        projection.workload_before_task
    )


def emergency_reassignment_preserves_start_time(
    current_start_delay: float,
    alternative_start_delay: float,
) -> bool:
    """
    Emergency Task 不允許因 Reassignment
    而讓 projected start time 變晚。

    Alternative 比 Current 更早：
        True

    完全相同：
        True

    Alternative 更晚：
        False
    """

    current_start_delay = float(
        current_start_delay
    )

    alternative_start_delay = float(
        alternative_start_delay
    )

    return (
        alternative_start_delay
        <
        current_start_delay
        or
        math.isclose(
            alternative_start_delay,
            current_start_delay,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    )


# ==========================================================
# Evaluation Runtime Views
# ==========================================================

def build_reassignment_runtime_views(
    task: Task,
    runtimes: Iterable[
        RobotRuntimeState
    ],
) -> list[RobotRuntimeState]:
    """
    為 Dynamic Reassignment 建立「不修改原資料」的
    hypothetical runtime views。

    關鍵：

    Target Task 原本已經存在 Current Robot Waiting Queue。

    如果直接呼叫 Weighted Score：

        existing queue
        +
        same target task

    會造成 duplicate task_id。

    因此評估前要先把 Target Task
    從原本 Waiting Queue 暫時移除，
    然後對每台 Robot 假設重新插入一次。

    這也讓：

        Stay on Current Robot

    與：

        Move to Alternative Robot

    使用完全相同的評估條件。
    """

    runtime_list = list(
        runtimes
    )

    if task.status != "assigned":

        raise ValueError(
            "Only assigned waiting tasks "
            "can be dynamically reassigned"
        )

    if task.assigned_robot is None:

        raise ValueError(
            "Task requires assigned_robot "
            "for reassignment"
        )

    waiting_locations = []

    views = []

    for runtime in runtime_list:

        # --------------------------------------------------
        # Running Task 永遠不可 Reassign
        # --------------------------------------------------

        if (
            runtime.running_task
            is not None
            and
            runtime.running_task.task_id
            ==
            task.task_id
        ):

            raise ValueError(
                "Running task cannot "
                "be reassigned"
            )

        contains_task = any(
            queued_task.task_id
            ==
            task.task_id
            for queued_task
            in runtime.waiting_tasks
        )

        if contains_task:

            waiting_locations.append(
                runtime.robot.robot_id
            )

        filtered_waiting_tasks = [
            queued_task
            for queued_task
            in runtime.waiting_tasks
            if (
                queued_task.task_id
                !=
                task.task_id
            )
        ]

        # --------------------------------------------------
        # 建立新的 Runtime View
        #
        # RobotState 本身不會被 scoring 修改，
        # 所以可以共用；
        # Waiting list 則建立新 list。
        # --------------------------------------------------

        views.append(
            RobotRuntimeState(
                robot=runtime.robot,
                running_task=(
                    runtime.running_task
                ),
                running_remaining_time=(
                    runtime
                    .running_remaining_time
                ),
                waiting_tasks=(
                    filtered_waiting_tasks
                ),
                robot_speed_mps=(
                    runtime.robot_speed_mps
                ),
            )
        )

    if len(
        waiting_locations
    ) != 1:

        raise ValueError(
            "Task must appear in exactly "
            "one waiting queue"
        )

    if (
        waiting_locations[0]
        !=
        task.assigned_robot
    ):

        raise ValueError(
            "Task assigned_robot does not "
            "match its waiting queue"
        )

    return views


# ==========================================================
# Dynamic Weighted Evaluation
# ==========================================================

def evaluate_dynamic_weighted_reassignment(
    task: Task,
    runtimes: Iterable[
        RobotRuntimeState
    ],
    places: Mapping[str, Place],
    current_time: float,
    minimum_improvement: float = (
        DYNAMIC_REASSIGNMENT_MIN_IMPROVEMENT
    ),
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    distance_weight: float = (
        WEIGHTED_DISTANCE_WEIGHT
    ),
    battery_weight: float = (
        WEIGHTED_BATTERY_WEIGHT
    ),
    workload_weight: float = (
        WEIGHTED_WORKLOAD_WEIGHT
    ),
    distance_reference: float = (
        DISTANCE_NORMALIZATION_REFERENCE
    ),
    workload_reference: float = (
        WORKLOAD_NORMALIZATION_REFERENCE_SECONDS
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
) -> DynamicWeightedEvaluation:
    """
    對一個 Waiting Task 做 Dynamic Weighted 評估。

    流程：

        1. 暫時從 Current Queue 移除 Target Task
        2. 對所有 Robot 假設重新插入 Target Task
        3. 套用共同：
           Capability / Status / Battery Safety
        4. 計算 Weighted Cost
        5. 比較 Current 與 Best Alternative
        6. 套 Hysteresis
        7. 回傳 Stay / Reassign
    """

    minimum_improvement = float(
        minimum_improvement
    )

    if minimum_improvement < 0.0:

        raise ValueError(
            "minimum_improvement "
            "cannot be negative"
        )

    previous_robot = (
        task.assigned_robot
    )

    if previous_robot is None:

        raise ValueError(
            "Task requires assigned_robot"
        )

    evaluation_runtimes = (
        build_reassignment_runtime_views(
            task=task,
            runtimes=runtimes,
        )
    )

    runtime_by_robot = {
        runtime.robot.robot_id: runtime
        for runtime
        in evaluation_runtimes
    }

    scores = (
        score_weighted_candidates(
            task=task,
            runtimes=(
                evaluation_runtimes
            ),
            places=places,
            current_time=current_time,
            battery_threshold=(
                battery_threshold
            ),
            distance_weight=(
                distance_weight
            ),
            battery_weight=(
                battery_weight
            ),
            workload_weight=(
                workload_weight
            ),
            distance_reference=(
                distance_reference
            ),
            workload_reference=(
                workload_reference
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            service_time_seconds=(
                service_time_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    # Explicit sort：
    # 不依賴 Weighted module 回傳順序。
    scores = sorted(
        scores,
        key=lambda score: (
            score.total_cost,
            score.robot.robot_id,
        ),
    )

    score_by_robot = {
        score.robot.robot_id: score
        for score
        in scores
    }

    current_score = (
        score_by_robot.get(
            previous_robot
        )
    )

    alternative_scores = [
        score
        for score
        in scores
        if (
            score.robot.robot_id
            !=
            previous_robot
        )
    ]

    best_alternative = (
        alternative_scores[0]
        if alternative_scores
        else None
    )

    # ======================================================
    # Current Robot 已不可行
    # ======================================================

    if current_score is None:

        if best_alternative is None:

            raise RuntimeError(
                "Current robot is infeasible "
                "and no feasible alternative "
                f"exists for task {task.task_id}"
            )

        return DynamicWeightedEvaluation(
            task_id=task.task_id,
            previous_robot=(
                previous_robot
            ),
            selected_robot=(
                best_alternative
                .robot
                .robot_id
            ),
            current_cost=None,
            selected_cost=(
                best_alternative
                .total_cost
            ),
            best_alternative_robot=(
                best_alternative
                .robot
                .robot_id
            ),
            best_alternative_cost=(
                best_alternative
                .total_cost
            ),
            improvement=None,
            reason=(
                "current_infeasible"
            ),
        )

    # ======================================================
    # 沒有 Alternative
    # ======================================================

    if best_alternative is None:

        return DynamicWeightedEvaluation(
            task_id=task.task_id,
            previous_robot=(
                previous_robot
            ),
            selected_robot=(
                previous_robot
            ),
            current_cost=(
                current_score.total_cost
            ),
            selected_cost=(
                current_score.total_cost
            ),
            best_alternative_robot=None,
            best_alternative_cost=None,
            improvement=None,
            reason="no_alternative",
        )

    improvement = (
        current_score.total_cost
        -
        best_alternative.total_cost
    )

    # ======================================================
    # Current 已經最好
    # ======================================================

    if improvement <= 0.0:

        return DynamicWeightedEvaluation(
            task_id=task.task_id,
            previous_robot=(
                previous_robot
            ),
            selected_robot=(
                previous_robot
            ),
            current_cost=(
                current_score.total_cost
            ),
            selected_cost=(
                current_score.total_cost
            ),
            best_alternative_robot=(
                best_alternative
                .robot
                .robot_id
            ),
            best_alternative_cost=(
                best_alternative
                .total_cost
            ),
            improvement=(
                improvement
            ),
            reason="current_best",
        )

    # ======================================================
    # Alternative 較好，但改善不足
    # ======================================================

    if not should_reassign(
        current_cost=(
            current_score.total_cost
        ),
        alternative_cost=(
            best_alternative
            .total_cost
        ),
        minimum_improvement=(
            minimum_improvement
        ),
    ):

        return DynamicWeightedEvaluation(
            task_id=task.task_id,
            previous_robot=(
                previous_robot
            ),
            selected_robot=(
                previous_robot
            ),
            current_cost=(
                current_score.total_cost
            ),
            selected_cost=(
                current_score.total_cost
            ),
            best_alternative_robot=(
                best_alternative
                .robot
                .robot_id
            ),
            best_alternative_cost=(
                best_alternative
                .total_cost
            ),
            improvement=(
                improvement
            ),
            reason=(
                "below_hysteresis"
            ),
        )

    # ======================================================
    # Emergency Projected Start Guard
    #
    # Emergency = Priority 3
    #
    # Weighted Cost 即使改善，
    # 也不能把 Emergency 搬到
    # 預計更晚才能開始的 Robot。
    #
    # 注意：
    # Current Robot infeasible 的 case
    # 已經在前面直接處理，因此不會走到這裡。
    # ======================================================

    if task.priority == 3:

        current_runtime = (
            runtime_by_robot[
                previous_robot
            ]
        )

        alternative_robot_id = (
            best_alternative
            .robot
            .robot_id
        )

        alternative_runtime = (
            runtime_by_robot[
                alternative_robot_id
            ]
        )

        current_start_delay = (
            calculate_projected_start_delay(
                task=task,
                runtime=current_runtime,
                places=places,
                current_time=current_time,
                aging_interval_seconds=(
                    aging_interval_seconds
                ),
                service_time_seconds=(
                    service_time_seconds
                ),
                battery_drain_per_meter=(
                    battery_drain_per_meter
                ),
            )
        )

        alternative_start_delay = (
            calculate_projected_start_delay(
                task=task,
                runtime=(
                    alternative_runtime
                ),
                places=places,
                current_time=current_time,
                aging_interval_seconds=(
                    aging_interval_seconds
                ),
                service_time_seconds=(
                    service_time_seconds
                ),
                battery_drain_per_meter=(
                    battery_drain_per_meter
                ),
            )
        )

        if not (
            emergency_reassignment_preserves_start_time(
                current_start_delay=(
                    current_start_delay
                ),
                alternative_start_delay=(
                    alternative_start_delay
                ),
            )
        ):

            return DynamicWeightedEvaluation(
                task_id=task.task_id,
                previous_robot=(
                    previous_robot
                ),
                selected_robot=(
                    previous_robot
                ),
                current_cost=(
                    current_score.total_cost
                ),
                selected_cost=(
                    current_score.total_cost
                ),
                best_alternative_robot=(
                    best_alternative
                    .robot
                    .robot_id
                ),
                best_alternative_cost=(
                    best_alternative
                    .total_cost
                ),
                improvement=(
                    improvement
                ),
                reason=(
                    "emergency_start_guard"
                ),
            )

    # ======================================================
    # 真正 Reassign
    # ======================================================

    return DynamicWeightedEvaluation(
        task_id=task.task_id,
        previous_robot=(
            previous_robot
        ),
        selected_robot=(
            best_alternative
            .robot
            .robot_id
        ),
        current_cost=(
            current_score.total_cost
        ),
        selected_cost=(
            best_alternative
            .total_cost
        ),
        best_alternative_robot=(
            best_alternative
            .robot
            .robot_id
        ),
        best_alternative_cost=(
            best_alternative
            .total_cost
        ),
        improvement=(
            improvement
        ),
        reason="improved",
    )