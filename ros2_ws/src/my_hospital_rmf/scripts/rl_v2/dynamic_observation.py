#!/usr/bin/env python3

import numpy as np

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projection import (
    get_place,
    project_task_on_robot,
)

from rl_v2.observation import (
    TASK_TYPES,
    _bounded_ratio,
    _coordinate_normalizer,
)

from rl_v2.dynamic_action_mask import (
    DECISION_REASSIGNMENT,
    build_dynamic_action_mask,
    build_reassignment_runtimes,
)


DYNAMIC_TASK_FEATURE_COUNT = 10
DYNAMIC_ROBOT_FEATURE_COUNT = 11


def get_dynamic_observation_size(
    robot_count: int,
) -> int:

    return (
        DYNAMIC_TASK_FEATURE_COUNT
        +
        DYNAMIC_ROBOT_FEATURE_COUNT
        *
        robot_count
    )


def build_dynamic_observation(
    task: Task,
    decision_type: str,
    robot_ids: list[str],
    runtimes: dict[
        str,
        RobotRuntimeState,
    ],
    places: dict[
        str,
        Place,
    ],
    current_time: float,
    service_time_seconds: float,
    current_robot_id: str | None = None,
    last_departed_robot: (
        dict[str, str]
        |
        None
    ) = None,
) -> np.ndarray:

    is_reassignment = (
        decision_type
        ==
        DECISION_REASSIGNMENT
    )

    # Reassignment 時 projection 必須先把
    # Task 從目前 queue 暫時拿掉。
    if is_reassignment:

        projection_runtimes = (
            build_reassignment_runtimes(
                task=task,
                runtimes=runtimes,
            )
        )

    else:

        projection_runtimes = (
            runtimes
        )

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
        if (
            task.task_type
            ==
            task_type
        )
        else
        0.0
        for task_type
        in TASK_TYPES
    ]

    # ======================================================
    # Task / Decision Features = 10
    #
    # 原本 9 維
    # +
    # decision_is_reassignment
    # ======================================================

    observation = [
        float(
            task.priority
        )
        /
        3.0,

        *task_type_one_hot,

        source_x,
        source_y,

        destination_x,
        destination_y,

        float(
            is_reassignment
        ),
    ]

    mask = (
        build_dynamic_action_mask(
            task=task,
            decision_type=(
                decision_type
            ),
            robot_ids=robot_ids,
            runtimes=runtimes,
            places=places,
            current_time=(
                current_time
            ),
            service_time_seconds=(
                service_time_seconds
            ),
            current_robot_id=(
                current_robot_id
            ),
            last_departed_robot=(
                last_departed_robot
            ),
        )
    )

    # ======================================================
    # Robot Features = 11 each
    #
    # 原本 10 維
    # +
    # is_current_robot
    # ======================================================

    for index, robot_id in enumerate(
        robot_ids
    ):

        runtime = (
            projection_runtimes[
                robot_id
            ]
        )

        robot = runtime.robot

        projection = (
            project_task_on_robot(
                task=task,
                runtime=runtime,
                places=places,
                current_time=(
                    current_time
                ),
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

                float(
                    is_reassignment
                    and
                    robot_id
                    ==
                    current_robot_id
                ),
            ]
        )

    result = np.asarray(
        observation,
        dtype=np.float32,
    )

    expected_size = (
        get_dynamic_observation_size(
            len(robot_ids)
        )
    )

    if result.shape != (
        expected_size,
    ):

        raise RuntimeError(
            "Unexpected dynamic observation "
            f"shape: {result.shape}, "
            f"expected ({expected_size},)"
        )

    return result
