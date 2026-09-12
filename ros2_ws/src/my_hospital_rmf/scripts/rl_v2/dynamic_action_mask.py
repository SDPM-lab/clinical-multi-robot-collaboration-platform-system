#!/usr/bin/env python3

from copy import deepcopy

import numpy as np

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)

from rl_v2.action_mask import (
    build_action_mask,
)


DECISION_ASSIGNMENT = "assignment"
DECISION_REASSIGNMENT = "reassignment"


# ==========================================================
# Reassignment Projection State
# ==========================================================

def build_reassignment_runtimes(
    task: Task,
    runtimes: dict[
        str,
        RobotRuntimeState,
    ],
) -> dict[
    str,
    RobotRuntimeState,
]:
    """
    Reassignment projection 前，
    先把目前 Task 從原本 waiting queue 暫時移除。

    原因：

        Task 已經存在於某台 Robot queue。

    若直接再 project_task_on_robot(task)，
    會形成 duplicate task。

    這裡只修改 deepcopy，
    不影響真正 Simulator state。
    """

    projected_runtimes = deepcopy(
        runtimes
    )

    found_count = 0

    for runtime in (
        projected_runtimes.values()
    ):

        original_count = len(
            runtime.waiting_tasks
        )

        runtime.waiting_tasks = [
            queued_task
            for queued_task
            in runtime.waiting_tasks
            if (
                queued_task.task_id
                !=
                task.task_id
            )
        ]

        found_count += (
            original_count
            -
            len(runtime.waiting_tasks)
        )

    if found_count != 1:

        raise RuntimeError(
            "Reassignment task must appear "
            "in exactly one waiting queue: "
            f"task={task.task_id}, "
            f"found={found_count}"
        )

    return projected_runtimes


# ==========================================================
# Dynamic Mask
# ==========================================================

def build_dynamic_action_mask(
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
    """
    Initial Assignment：
        與 Static PPO 完全相同。

    Reassignment：
        先把 Task 從目前 queue 暫時拿掉，
        再計算放到每一台 Robot 的可行性。

    Action：
        選 current_robot = Stay
        選其他 robot = Reassign
    """

    if (
        decision_type
        ==
        DECISION_ASSIGNMENT
    ):

        return build_action_mask(
            task=task,
            robot_ids=robot_ids,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
        )

    if (
        decision_type
        !=
        DECISION_REASSIGNMENT
    ):

        raise ValueError(
            "Unknown decision_type: "
            f"{decision_type}"
        )

    if current_robot_id is None:

        raise ValueError(
            "current_robot_id is required "
            "for reassignment"
        )

    if current_robot_id not in robot_ids:

        raise ValueError(
            "Unknown current robot: "
            f"{current_robot_id}"
        )

    projected_runtimes = (
        build_reassignment_runtimes(
            task=task,
            runtimes=runtimes,
        )
    )

    mask = build_action_mask(
        task=task,
        robot_ids=robot_ids,
        runtimes=projected_runtimes,
        places=places,
        current_time=current_time,
    )

    current_index = (
        robot_ids.index(
            current_robot_id
        )
    )

    current_feasible = bool(
        mask[current_index]
    )

    # ======================================================
    # Immediate Reversal Guard
    #
    # R1 -> R2 之後，
    # 下一個 event 不允許直接 R2 -> R1。
    #
    # 但若 current robot 已 infeasible，
    # Safety 優先，允許回去。
    # ======================================================

    if (
        current_feasible
        and
        last_departed_robot
        is not None
    ):

        blocked_robot = (
            last_departed_robot.get(
                task.task_id
            )
        )

        if (
            blocked_robot is not None
            and
            blocked_robot in robot_ids
            and
            blocked_robot
            !=
            current_robot_id
        ):

            blocked_index = (
                robot_ids.index(
                    blocked_robot
                )
            )

            mask[
                blocked_index
            ] = False

    # ======================================================
    # Emergency Projected Start Guard
    #
    # Emergency 若目前 Robot 仍 feasible，
    # 不允許搬到 projected start 更晚的 Robot。
    #
    # 與 Dynamic Weighted 的醫療安全語意一致。
    # ======================================================

    if (
        task.priority == 3
        and
        current_feasible
    ):

        current_projection = (
            project_task_on_robot(
                task=task,
                runtime=(
                    projected_runtimes[
                        current_robot_id
                    ]
                ),
                places=places,
                current_time=current_time,
                service_time_seconds=(
                    service_time_seconds
                ),
            )
        )

        current_delay = (
            current_projection
            .workload_before_task
        )

        for index, robot_id in enumerate(
            robot_ids
        ):

            if not mask[index]:
                continue

            if (
                robot_id
                ==
                current_robot_id
            ):
                continue

            projection = (
                project_task_on_robot(
                    task=task,
                    runtime=(
                        projected_runtimes[
                            robot_id
                        ]
                    ),
                    places=places,
                    current_time=(
                        current_time
                    ),
                    service_time_seconds=(
                        service_time_seconds
                    ),
                )
            )

            if (
                projection
                .workload_before_task
                >
                current_delay
                +
                1e-9
            ):

                mask[index] = False

    return np.asarray(
        mask,
        dtype=bool,
    )
