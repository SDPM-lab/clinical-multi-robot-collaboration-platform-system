#!/usr/bin/env python3

import math

from collections.abc import (
    Iterable,
    Mapping,
)

from scheduler_v2.battery import (
    calculate_battery_consumption,
    calculate_remaining_battery,
)

from scheduler_v2.candidate_filter import (
    is_feasible_robot,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    BATTERY_DRAIN_PER_METER,
    MIN_BATTERY_LEVEL,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projection import (
    calculate_task_travel_distance,
    get_place,
)

from scheduler_v2.task_selector import (
    sort_tasks,
)


# ==========================================================
# Queue Battery Projection
# ==========================================================

def calculate_projected_battery_after_queue(
    task: Task,
    runtime: RobotRuntimeState,
    places: Mapping[str, Place],
    current_time: float,
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> float:
    """
    假設 NEW Task 被加入此 Robot Waiting Queue，
    計算整條 Queue 全部完成後預計剩餘 Battery。

    重要語意：

    runtime.robot.battery
    已視為扣除目前 Running Task 預留耗電後，
    可供 Waiting Queue 使用的 Battery Budget。

    因此若目前有 Running Task：
    - Position 投影到 Running Task destination
    - 不再重複扣 Running Task Battery
    """

    battery_drain_per_meter = float(
        battery_drain_per_meter
    )

    if battery_drain_per_meter < 0.0:

        raise ValueError(
            "battery_drain_per_meter "
            "cannot be negative"
        )

    existing_ids = {
        queued_task.task_id
        for queued_task
        in runtime.waiting_tasks
    }

    if task.task_id in existing_ids:

        raise ValueError(
            "Duplicate task_id "
            "in waiting queue projection"
        )

    projected_battery = (
        runtime.robot.battery
    )

    projected_place = Place(
        place_id=(
            f"{runtime.robot.robot_id}:current"
        ),
        x=runtime.robot.x,
        y=runtime.robot.y,
        map_name=runtime.robot.map_name,
    )

    # ------------------------------------------------------
    # Running Task
    #
    # Running 已經 reserve battery，
    # 所以只更新未來位置。
    # ------------------------------------------------------

    if runtime.running_task is not None:

        projected_place = (
            get_place(
                places=places,
                place_id=(
                    runtime
                    .running_task
                    .destination
                ),
            )
        )

    # ------------------------------------------------------
    # Hypothetical Queue
    # ------------------------------------------------------

    hypothetical_queue = [
        *runtime.waiting_tasks,
        task,
    ]

    ordered_queue = (
        sort_tasks(
            tasks=(
                hypothetical_queue
            ),
            current_time=(
                current_time
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
        )
    )

    # ------------------------------------------------------
    # Simulate Entire Queue
    # ------------------------------------------------------

    for queued_task in ordered_queue:

        travel_distance = (
            calculate_task_travel_distance(
                task=queued_task,
                start_place=(
                    projected_place
                ),
                places=places,
            )
        )

        consumption = (
            calculate_battery_consumption(
                travel_distance=(
                    travel_distance
                ),
                drain_per_meter=(
                    battery_drain_per_meter
                ),
            )
        )

        projected_battery = (
            calculate_remaining_battery(
                battery=(
                    projected_battery
                ),
                consumption=(
                    consumption
                ),
            )
        )

        projected_place = (
            get_place(
                places=places,
                place_id=(
                    queued_task.destination
                ),
            )
        )

    return projected_battery


# ==========================================================
# Runtime Feasibility
# ==========================================================

def is_projected_feasible_runtime(
    task: Task,
    runtime: RobotRuntimeState,
    places: Mapping[str, Place],
    current_time: float,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> bool:
    """
    完整 Feasibility：

    1. Available
    2. Operational Status
    3. Capability
    4. Current Battery
    5. 加入 NEW Task 後，
       整條 Waiting Queue 仍可在
       Battery Safety Threshold 以上完成
    """

    if not is_feasible_robot(
        task=task,
        robot=runtime.robot,
        battery_threshold=(
            battery_threshold
        ),
    ):

        return False

    remaining = (
        calculate_projected_battery_after_queue(
            task=task,
            runtime=runtime,
            places=places,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    return (
        remaining
        >
        battery_threshold
        or
        math.isclose(
            remaining,
            battery_threshold,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    )


# ==========================================================
# Filter
# ==========================================================

def filter_projected_feasible_runtimes(
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
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> list[RobotRuntimeState]:

    return [
        runtime
        for runtime
        in runtimes
        if is_projected_feasible_runtime(
            task=task,
            runtime=runtime,
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
    ]