from __future__ import annotations

from typing import Callable, Dict, Iterable, Sequence

import numpy as np

from experiments.fleet_sizing.baseline.common import (
    project_robot_queue_placement,
    repair_projected_queue_for_battery,
    robot_is_feasible,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Action Mask
# ============================================================


class ActionMaskBuilder:

    def __init__(
        self,
        robot_ids: Sequence[str],
    ) -> None:

        self.robot_ids = tuple(
            robot_ids
        )

        if not self.robot_ids:
            raise ValueError(
                "robot_ids cannot be empty"
            )

        if (
            len(set(self.robot_ids))
            != len(self.robot_ids)
        ):
            raise ValueError(
                "robot_ids must be unique"
            )

    @property
    def action_count(
        self,
    ) -> int:

        return len(
            self.robot_ids
        )

    @staticmethod
    def _battery_allows_task(
        *,
        robot: RobotState,
        task: TaskState,
        tasks_by_id: Dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn: Callable[
            [str, str],
            float,
        ],
    ) -> bool:
        """
        Return True if the incoming task itself can remain on
        this robot after battery-aware queue repair.

        Downstream existing tasks are allowed to be released
        and reassigned.

        Therefore this does NOT require the entire projected
        queue to remain battery-feasible.
        """

        projection = (
            project_robot_queue_placement(
                robot=robot,
                tasks_by_id=tasks_by_id,
                current_time_s=(
                    current_time_s
                ),
                travel_time_fn=(
                    travel_time_fn
                ),
                extra_task=task,
            )
        )

        repair = (
            repair_projected_queue_for_battery(
                robot=robot,
                queue_projection=(
                    projection
                ),
                tasks_by_id=tasks_by_id,
                travel_time_fn=(
                    travel_time_fn
                ),
            )
        )

        return repair.task_is_kept(
            task.task_id
        )

    def build(
        self,
        *,
        task: TaskState,
        robots: Iterable[
            RobotState
        ],
        enable_battery_model: bool = False,
        tasks_by_id: Dict[
            str,
            TaskState,
        ] | None = None,
        current_time_s: float | None = None,
        travel_time_fn: Callable[
            [str, str],
            float,
        ] | None = None,
    ) -> np.ndarray:

        robot_list = list(
            robots
        )

        robot_by_id = {
            robot.robot_id: robot
            for robot in robot_list
        }

        if (
            set(robot_by_id)
            != set(self.robot_ids)
        ):
            raise ValueError(
                "Robot set does not match "
                "ActionMaskBuilder robot_ids"
            )

        if enable_battery_model:

            if tasks_by_id is None:

                raise ValueError(
                    "tasks_by_id is required when "
                    "enable_battery_model=True"
                )

            if current_time_s is None:

                raise ValueError(
                    "current_time_s is required when "
                    "enable_battery_model=True"
                )

            if travel_time_fn is None:

                raise ValueError(
                    "travel_time_fn is required when "
                    "enable_battery_model=True"
                )

        mask = np.zeros(
            self.action_count,
            dtype=np.bool_,
        )

        for index, robot_id in enumerate(
            self.robot_ids
        ):

            robot = (
                robot_by_id[
                    robot_id
                ]
            )

            basic_feasible = (
                robot_is_feasible(
                    robot=robot,
                    task=task,
                )
            )

            if not basic_feasible:

                mask[index] = False

                continue

            if not enable_battery_model:

                mask[index] = True

                continue

            assert (
                tasks_by_id
                is not None
            )

            assert (
                current_time_s
                is not None
            )

            assert (
                travel_time_fn
                is not None
            )

            mask[index] = (
                self._battery_allows_task(
                    robot=robot,
                    task=task,
                    tasks_by_id=(
                        tasks_by_id
                    ),
                    current_time_s=(
                        current_time_s
                    ),
                    travel_time_fn=(
                        travel_time_fn
                    ),
                )
            )

        return mask

    def feasible_action_indices(
        self,
        *,
        task: TaskState,
        robots: Iterable[
            RobotState
        ],
    ) -> tuple[int, ...]:

        mask = self.build(
            task=task,
            robots=robots,
        )

        return tuple(
            int(index)
            for index
            in np.flatnonzero(
                mask
            )
        )

    def robot_id_from_action(
        self,
        action: int,
    ) -> str:

        action = int(
            action
        )

        if (
            action < 0
            or action >= self.action_count
        ):
            raise IndexError(
                f"Invalid action {action}; "
                f"expected 0 <= action "
                f"< {self.action_count}"
            )

        return (
            self.robot_ids[
                action
            ]
        )

    def action_from_robot_id(
        self,
        robot_id: str,
    ) -> int:

        try:
            return (
                self.robot_ids.index(
                    robot_id
                )
            )

        except ValueError as exc:

            raise KeyError(
                f"Unknown robot_id "
                f"{robot_id!r}"
            ) from exc

    def validate_action(
        self,
        *,
        action: int,
        task: TaskState,
        robots: Iterable[
            RobotState
        ],
        enable_battery_model: bool = False,
        tasks_by_id: Dict[
            str,
            TaskState,
        ] | None = None,
        current_time_s: float | None = None,
        travel_time_fn: Callable[
            [str, str],
            float,
        ] | None = None,
    ) -> bool:

        mask = self.build(
            task=task,
            robots=robots,
            enable_battery_model=(
                enable_battery_model
            ),
            tasks_by_id=(
                tasks_by_id
            ),
            current_time_s=(
                current_time_s
            ),
            travel_time_fn=(
                travel_time_fn
            ),
        )

        action = int(
            action
        )

        if (
            action < 0
            or action >= len(mask)
        ):
            return False

        return bool(
            mask[
                action
            ]
        )