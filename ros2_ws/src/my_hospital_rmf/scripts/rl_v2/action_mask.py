#!/usr/bin/env python3

import numpy as np

from scheduler_v2.models import Task
from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)
from scheduler_v2.projected_candidate_filter import (
    filter_projected_feasible_runtimes,
)


def build_action_mask(
    task: Task,
    robot_ids: list[str],
    runtimes: dict[str, RobotRuntimeState],
    places: dict[str, Place],
    current_time: float,
) -> np.ndarray:
    """
    建立 PPO Robot Selection Action Mask。

    Action index 與 robot_ids 一一對應。

    True:
        此 Robot 對目前 Task 為 projected feasible。

    False:
        不允許 PPO 選擇。

    Feasibility 完全沿用 scheduler_v2：
    - available
    - operational status
    - capability
    - battery threshold
    - whole waiting queue battery safety
    """

    feasible = (
        filter_projected_feasible_runtimes(
            task=task,
            runtimes=[
                runtimes[robot_id]
                for robot_id in robot_ids
            ],
            places=places,
            current_time=current_time,
        )
    )

    feasible_ids = {
        runtime.robot.robot_id
        for runtime in feasible
    }

    return np.asarray(
        [
            robot_id in feasible_ids
            for robot_id in robot_ids
        ],
        dtype=bool,
    )
