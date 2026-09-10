#!/usr/bin/env python3

import math

from collections.abc import (
    Mapping,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    BATTERY_DRAIN_PER_METER,
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
    TaskProjection,
)

from scheduler_v2.task_selector import (
    sort_tasks,
)

from scheduler_v2.battery import (
    calculate_battery_consumption,
    calculate_remaining_battery,
)


# ==========================================================
# Place Lookup
# ==========================================================

def get_place(
    places: Mapping[str, Place],
    place_id: str,
) -> Place:
    """
    根據 Task 的 source / destination ID
    找到真正地點資料。
    """

    try:

        return places[
            place_id
        ]

    except KeyError as exc:

        raise KeyError(
            "Unknown place: "
            f"{place_id}"
        ) from exc


# ==========================================================
# Distance
# ==========================================================

def calculate_distance(
    start: Place,
    end: Place,
) -> float:
    """
    第一版 Algorithm-level Simulator
    使用同樓層 Euclidean Distance。

    未來與 RMF 整合時，
    可替換成 Nav Graph / Navigation Path Distance。
    """

    if (
        start.map_name
        !=
        end.map_name
    ):

        raise ValueError(
            "Cannot calculate Euclidean distance "
            "between different maps: "
            f"{start.map_name} -> {end.map_name}"
        )

    return math.hypot(
        end.x - start.x,
        end.y - start.y,
    )


# ==========================================================
# Task Travel Distance
# ==========================================================

def calculate_task_travel_distance(
    task: Task,
    start_place: Place,
    places: Mapping[str, Place],
) -> float:
    """
    計算 Robot 執行某 Task 所需要的移動距離：

        current/projected position
        -> Task Source
        -> Task Destination

    此距離同時會供：

    - Travel Distance
    - Task Duration
    - Battery Consumption

    使用。
    """

    source = get_place(
        places=places,
        place_id=task.source,
    )

    destination = get_place(
        places=places,
        place_id=task.destination,
    )

    distance_to_source = (
        calculate_distance(
            start=start_place,
            end=source,
        )
    )

    task_distance = (
        calculate_distance(
            start=source,
            end=destination,
        )
    )

    return (
        distance_to_source
        +
        task_distance
    )


# ==========================================================
# Task Execution Duration
# ==========================================================

def calculate_task_duration(
    task: Task,
    start_place: Place,
    places: Mapping[str, Place],
    robot_speed_mps: float,
    service_time_seconds: float = (
        DEFAULT_TASK_SERVICE_TIME_SECONDS
    ),
) -> float:
    """
    從 Robot 開始執行某 Task 時計算：

        current/projected position
        -> Task Source
        -> Task Destination
        + Service Time

    回傳此 Task 佔用 Robot 的預估時間。
    """

    robot_speed_mps = float(
        robot_speed_mps
    )

    service_time_seconds = float(
        service_time_seconds
    )

    if robot_speed_mps <= 0.0:

        raise ValueError(
            "robot_speed_mps "
            "must be greater than 0"
        )

    if service_time_seconds < 0.0:

        raise ValueError(
            "service_time_seconds "
            "cannot be negative"
        )

    travel_distance = (
        calculate_task_travel_distance(
            task=task,
            start_place=start_place,
            places=places,
        )
    )

    travel_time = (
        travel_distance
        /
        robot_speed_mps
    )

    return (
        travel_time
        +
        service_time_seconds
    )


# ==========================================================
# Task Projection
# ==========================================================

def project_task_on_robot(
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
) -> TaskProjection:
    """
    假設 task 現在被分配給指定 Robot，
    計算它按照 Priority + Aging 插入 Waiting Queue 後：

    - 前面有哪些 Waiting Tasks
    - 真正輪到它時 Robot 預計在哪裡
    - 前面還有多少 workload
    - 從 projected position 到 task source 的距離

    注意：

    workload_before_task 不包含 task 自己前往 Source 的時間。

    因為 Waiting Time 的定義是：

        Task 開始被 Robot 執行
        -
        Task Arrival

    Robot 開始前往此 Task Source 時，
    就視為此 Task 已開始執行。
    """

    hypothetical_tasks = [
        *runtime.waiting_tasks,
        task,
    ]

    # ------------------------------------------------------
    # Prevent Duplicate Task IDs
    # ------------------------------------------------------

    task_ids = [
        queued_task.task_id
        for queued_task
        in hypothetical_tasks
    ]

    if (
        len(task_ids)
        !=
        len(set(task_ids))
    ):

        raise ValueError(
            "Duplicate task_id in "
            "projected waiting queue"
        )

    # ------------------------------------------------------
    # Apply Shared Priority + Aging Rule
    # ------------------------------------------------------

    ordered_tasks = (
        sort_tasks(
            tasks=hypothetical_tasks,
            current_time=current_time,
            aging_interval_seconds=(
                aging_interval_seconds
            ),
        )
    )

    target_index = next(
        index
        for index, queued_task
        in enumerate(ordered_tasks)
        if queued_task.task_id
        ==
        task.task_id
    )

    tasks_before = (
        ordered_tasks[
            :target_index
        ]
    )

    # ------------------------------------------------------
    # Start From Current Robot Position
    # ------------------------------------------------------

    projected_place = Place(
        place_id=(
            f"{runtime.robot.robot_id}"
            ":current"
        ),
        x=runtime.robot.x,
        y=runtime.robot.y,
        map_name=(
            runtime.robot.map_name
        ),
    )

    workload_before_task = 0.0

    projected_battery = (
        runtime.robot.battery
    )

    # ------------------------------------------------------
    # Running Task
    #
    # Running Task is non-preemptive.
    #
    # 所以新的 Task 必須至少等 Running Task 完成。
    # ------------------------------------------------------

    if (
        runtime.running_task
        is not None
    ):

        workload_before_task += (
            runtime.running_remaining_time
        )

        projected_place = get_place(
            places=places,
            place_id=(
                runtime
                .running_task
                .destination
            ),
        )

    # ------------------------------------------------------
    # Waiting Tasks Ahead
    # ------------------------------------------------------

    for queued_task in tasks_before:

        # ------------------------------------------------------
        # Travel Distance
        # ------------------------------------------------------

        queued_task_distance = (
            calculate_task_travel_distance(
                task=queued_task,
                start_place=(
                    projected_place
                ),
                places=places,
            )
        )

        # ------------------------------------------------------
        # Workload
        # ------------------------------------------------------

        task_duration = (
            calculate_task_duration(
                task=queued_task,
                start_place=(
                    projected_place
                ),
                places=places,
                robot_speed_mps=(
                    runtime
                    .robot_speed_mps
                ),
                service_time_seconds=(
                    service_time_seconds
                ),
            )
        )

        workload_before_task += (
            task_duration
        )

        # ------------------------------------------------------
        # Battery
        # ------------------------------------------------------

        battery_consumption = (
            calculate_battery_consumption(
                travel_distance=(
                    queued_task_distance
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
                    battery_consumption
                ),
            )
        )

        # ------------------------------------------------------
        # Projected Position
        # ------------------------------------------------------

        projected_place = (
            get_place(
                places=places,
                place_id=(
                    queued_task
                    .destination
                ),
            )
        )

    # ------------------------------------------------------
    # Distance From Projected Position To New Task Source
    # ------------------------------------------------------

    target_source = (
        get_place(
            places=places,
            place_id=task.source,
        )
    )

    distance_to_source = (
        calculate_distance(
            start=projected_place,
            end=target_source,
        )
    )

    # ------------------------------------------------------
    # Target Task Battery
    # ------------------------------------------------------

    target_task_distance = (
        calculate_task_travel_distance(
            task=task,
            start_place=(
                projected_place
            ),
            places=places,
        )
    )

    expected_task_battery_consumption = (
        calculate_battery_consumption(
            travel_distance=(
                target_task_distance
            ),
            drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    projected_battery_after_task = (
        calculate_remaining_battery(
            battery=(
                projected_battery
            ),
            consumption=(
                expected_task_battery_consumption
            ),
        )
    )

    return TaskProjection(
        robot_id=(
            runtime.robot.robot_id
        ),
        projected_x=(
            projected_place.x
        ),
        projected_y=(
            projected_place.y
        ),
        projected_map_name=(
            projected_place.map_name
        ),
        workload_before_task=(
            workload_before_task
        ),
        distance_to_source=(
            distance_to_source
        ),
        queue_length_before_task=(
            len(tasks_before)
        ),
        task_ids_before=tuple(
            queued_task.task_id
            for queued_task
            in tasks_before
        ),
        projected_battery_before_task=(
            projected_battery
        ),
        expected_task_battery_consumption=(
            expected_task_battery_consumption
        ),
        projected_battery_after_task=(
            projected_battery_after_task
        ),
    )