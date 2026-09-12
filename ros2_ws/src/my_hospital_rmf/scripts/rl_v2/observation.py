#!/usr/bin/env python3

import numpy as np

from scheduler_v2.models import Task
from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)
from scheduler_v2.projection import (
    get_place,
    project_task_on_robot,
)

from rl_v2.action_mask import (
    build_action_mask,
)


TASK_TYPES = (
    "medicine_delivery",
    "specimen_delivery",
    "general_delivery",
    "waste_collection",
)

TASK_FEATURE_COUNT = 9
ROBOT_FEATURE_COUNT = 10


def get_observation_size(
    robot_count: int,
) -> int:

    return (
        TASK_FEATURE_COUNT
        +
        ROBOT_FEATURE_COUNT
        *
        robot_count
    )


def _bounded_ratio(
    value: float,
    scale: float,
) -> float:

    value = max(
        0.0,
        float(value),
    )

    scale = float(scale)

    return (
        value
        /
        (value + scale)
    )


def _coordinate_normalizer(
    places: dict[str, Place],
):

    xs = [
        place.x
        for place in places.values()
    ]

    ys = [
        place.y
        for place in places.values()
    ]

    min_x = min(xs)
    max_x = max(xs)

    min_y = min(ys)
    max_y = max(ys)

    def normalize(
        x: float,
        y: float,
    ) -> tuple[float, float]:

        if max_x > min_x:
            nx = (
                2.0
                *
                (x - min_x)
                /
                (max_x - min_x)
                -
                1.0
            )
        else:
            nx = 0.0

        if max_y > min_y:
            ny = (
                2.0
                *
                (y - min_y)
                /
                (max_y - min_y)
                -
                1.0
            )
        else:
            ny = 0.0

        return (
            float(
                np.clip(
                    nx,
                    -1.0,
                    1.0,
                )
            ),
            float(
                np.clip(
                    ny,
                    -1.0,
                    1.0,
                )
            ),
        )

    return normalize


def build_observation(
    task: Task,
    robot_ids: list[str],
    runtimes: dict[str, RobotRuntimeState],
    places: dict[str, Place],
    current_time: float,
    service_time_seconds: float,
) -> np.ndarray:
    """
    建立 RL Robot Assignment Observation。

    這裡不重新推導排程資訊，
    而是直接使用 scheduler_v2 的 projection。
    """

    normalize_position = (
        _coordinate_normalizer(
            places
        )
    )

    source = get_place(
        places=places,
        place_id=task.source,
    )

    destination = get_place(
        places=places,
        place_id=task.destination,
    )

    source_x, source_y = (
        normalize_position(
            source.x,
            source.y,
        )
    )

    destination_x, destination_y = (
        normalize_position(
            destination.x,
            destination.y,
        )
    )

    task_type_one_hot = [
        1.0
        if task.task_type == task_type
        else 0.0
        for task_type in TASK_TYPES
    ]

    observation = [
        float(task.priority) / 3.0,
        *task_type_one_hot,
        source_x,
        source_y,
        destination_x,
        destination_y,
    ]

    mask = build_action_mask(
        task=task,
        robot_ids=robot_ids,
        runtimes=runtimes,
        places=places,
        current_time=current_time,
    )

    for index, robot_id in enumerate(
        robot_ids
    ):

        runtime = (
            runtimes[robot_id]
        )

        robot = runtime.robot

        projection = (
            project_task_on_robot(
                task=task,
                runtime=runtime,
                places=places,
                current_time=current_time,
                service_time_seconds=(
                    service_time_seconds
                ),
            )
        )

        projected_x, projected_y = (
            normalize_position(
                projection.projected_x,
                projection.projected_y,
            )
        )

        observation.extend(
            [
                projected_x,
                projected_y,

                float(
                    np.clip(
                        robot.battery,
                        0.0,
                        1.0,
                    )
                ),

                float(
                    np.clip(
                        projection
                        .projected_battery_after_task,
                        0.0,
                        1.0,
                    )
                ),

                _bounded_ratio(
                    projection
                    .workload_before_task,
                    300.0,
                ),

                _bounded_ratio(
                    projection
                    .distance_to_source,
                    50.0,
                ),

                _bounded_ratio(
                    projection
                    .queue_length_before_task,
                    10.0,
                ),

                _bounded_ratio(
                    len(
                        runtime.waiting_tasks
                    ),
                    10.0,
                ),

                float(
                    runtime.running_task
                    is not None
                ),

                float(
                    mask[index]
                ),
            ]
        )

    result = np.asarray(
        observation,
        dtype=np.float32,
    )

    expected_size = (
        get_observation_size(
            len(robot_ids)
        )
    )

    if result.shape != (
        expected_size,
    ):

        raise RuntimeError(
            "Unexpected observation shape: "
            f"{result.shape}, "
            f"expected ({expected_size},)"
        )

    return result
