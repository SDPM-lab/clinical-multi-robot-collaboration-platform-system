#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import time

import numpy as np

from sb3_contrib import MaskablePPO

from scheduler_v2.config import (
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
)
from scheduler_v2.models import Task
from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from rl_v2.action_mask import (
    build_action_mask,
)
from rl_v2.observation import (
    build_observation,
)


# ==========================================================
# Result
# ==========================================================

@dataclass(frozen=True)
class FrozenAssignmentDecision:

    task_id: str

    selected_robot: str | None

    action_index: int | None

    feasible_robot_ids: tuple[str, ...]

    decision_time_seconds: float


    @property
    def decision_time_ms(
        self,
    ) -> float:

        return (
            self.decision_time_seconds
            *
            1000.0
        )


# ==========================================================
# Frozen Initial Assignment Scheduler
# ==========================================================

class FrozenInitialAssignmentScheduler:
    """
    正式系統用的 Frozen Initial Assignment Scheduler。

    使用已訓練完成的：

        Long-Horizon Masked PPO

    輸入：
        - Task
        - RobotRuntimeState
        - Places
        - Current Time

    輸出：
        - selected_robot

    注意：
        這個 class 只負責「做決策」。

        不會：
        - 自動修改 Task
        - 自動加入 Robot Queue
        - 自動執行 Robot
        - 自動做 Reassignment

        Queue / Runtime State 更新交給之後的
        Scheduler Runtime / ROS Adapter 處理。
    """

    def __init__(
        self,
        model_path: str | Path,
        service_time_seconds: float = (
            DEFAULT_TASK_SERVICE_TIME_SECONDS
        ),
        device: str = "cpu",
    ):

        self.model_path = Path(
            model_path
        )

        if not self.model_path.exists():

            raise FileNotFoundError(
                "Frozen PPO model not found: "
                f"{self.model_path}"
            )

        self.service_time_seconds = float(
            service_time_seconds
        )

        if (
            self.service_time_seconds
            <
            0.0
        ):

            raise ValueError(
                "service_time_seconds "
                "cannot be negative"
            )

        # ----------------------------------------------
        # Model 只 Load 一次。
        #
        # 正式 Server 執行時不能每個 Task
        # 都重新 Load PPO。
        # ----------------------------------------------

        self.model = MaskablePPO.load(
            str(
                self.model_path
            ),
            device=device,
        )


    # ======================================================
    # Assignment
    # ======================================================

    def assign_task(
        self,
        task: Task,
        runtimes: dict[
            str,
            RobotRuntimeState,
        ],
        places: dict[
            str,
            Place,
        ],
        current_time: float,
    ) -> FrozenAssignmentDecision:

        if not runtimes:

            raise ValueError(
                "runtimes cannot be empty"
            )

        current_time = float(
            current_time
        )

        # ==================================================
        # IMPORTANT
        #
        # Training Env 使用：
        #
        #     sorted(robot.robot_id ...)
        #
        # 正式 inference 必須維持相同 action ordering。
        # ==================================================

        robot_ids = sorted(
            runtimes.keys()
        )

        start_time = (
            time.perf_counter()
        )

        # ==================================================
        # Action Mask
        # ==================================================

        mask = build_action_mask(
            task=task,
            robot_ids=robot_ids,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
        )

        feasible_robot_ids = tuple(
            robot_id
            for index, robot_id
            in enumerate(
                robot_ids
            )
            if bool(
                mask[index]
            )
        )

        # ==================================================
        # No Feasible Robot
        # ==================================================

        if not mask.any():

            elapsed = (
                time.perf_counter()
                -
                start_time
            )

            return (
                FrozenAssignmentDecision(
                    task_id=(
                        task.task_id
                    ),
                    selected_robot=None,
                    action_index=None,
                    feasible_robot_ids=(),
                    decision_time_seconds=(
                        elapsed
                    ),
                )
            )

        # ==================================================
        # Observation
        #
        # 必須與 Training 時的 49-D Observation
        # 完全相同。
        # ==================================================

        observation = build_observation(
            task=task,
            robot_ids=robot_ids,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            service_time_seconds=(
                self.service_time_seconds
            ),
        )

        # ==================================================
        # Frozen PPO Inference
        #
        # Final Experiment 使用 deterministic=True，
        # 正式 Scheduler 必須保持一致。
        # ==================================================

        action, _ = self.model.predict(
            observation,
            action_masks=mask,
            deterministic=True,
        )

        action = int(
            np.asarray(
                action
            )
            .reshape(-1)[0]
        )

        # ==================================================
        # Defensive Checks
        # ==================================================

        if not (
            0
            <=
            action
            <
            len(robot_ids)
        ):

            raise RuntimeError(
                "Frozen PPO returned "
                "invalid action index: "
                f"{action}"
            )

        if not bool(
            mask[action]
        ):

            raise RuntimeError(
                "Frozen PPO selected "
                "a masked Robot: "
                f"action={action}, "
                f"robot={robot_ids[action]}"
            )

        selected_robot = (
            robot_ids[
                action
            ]
        )

        elapsed = (
            time.perf_counter()
            -
            start_time
        )

        return (
            FrozenAssignmentDecision(
                task_id=(
                    task.task_id
                ),
                selected_robot=(
                    selected_robot
                ),
                action_index=(
                    action
                ),
                feasible_robot_ids=(
                    feasible_robot_ids
                ),
                decision_time_seconds=(
                    elapsed
                ),
            )
        )
