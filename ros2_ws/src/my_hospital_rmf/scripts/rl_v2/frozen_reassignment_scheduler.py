#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
import time

import numpy as np

from sb3_contrib import MaskablePPO

from scheduler_v2.config import (
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from rl_v2.dynamic_action_mask import (
    DECISION_REASSIGNMENT,
    build_dynamic_action_mask,
)

from rl_v2.dynamic_observation import (
    build_dynamic_observation,
)


# ==========================================================
# Result
# ==========================================================

@dataclass(frozen=True)
class FrozenReassignmentDecision:

    task_id: str

    previous_robot: str

    selected_robot: str

    action_index: int

    feasible_robot_ids: tuple[str, ...]

    changed: bool

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
# Frozen Reassignment Scheduler
# ==========================================================

class FrozenReassignmentScheduler:
    """
    正式系統用的 Frozen Reassignment Scheduler。

    使用已訓練完成的 Dedicated Reassignment
    Maskable PPO。

    輸入：
        - Waiting Task
        - Task 目前所在 Robot
        - RobotRuntimeState
        - Places
        - Current Time

    輸出：
        - Stay
          selected_robot == previous_robot

        - Reassign
          selected_robot != previous_robot

    注意：
        這個 class 只負責「做決策」。

        不會：
        - 修改 Waiting Queue
        - 啟動 Robot
        - 執行 RMF Task

        Queue migration 交給 RuntimeStateManager。
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
                "Frozen Reassignment PPO "
                "model not found: "
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

        # --------------------------------------------------
        # 必須與 Dynamic Training Environment
        # 的 last_departed_robot 語意一致。
        #
        # task_id -> 上一次離開的 Robot
        # --------------------------------------------------

        self.last_departed_robot: dict[
            str,
            str,
        ] = {}

        # Model 只 Load 一次。
        self.model = MaskablePPO.load(
            str(
                self.model_path
            ),
            device=device,
        )


    # ======================================================
    # Reassignment Decision
    # ======================================================

    def decide(
        self,
        *,
        task: Task,
        current_robot_id: str,
        runtimes: dict[
            str,
            RobotRuntimeState,
        ],
        places: dict[
            str,
            Place,
        ],
        current_time: float,
    ) -> FrozenReassignmentDecision:

        if not runtimes:

            raise ValueError(
                "runtimes cannot be empty"
            )

        if (
            current_robot_id
            not in runtimes
        ):

            raise ValueError(
                "Unknown current robot: "
                f"{current_robot_id}"
            )

        current_time = float(
            current_time
        )

        # ==================================================
        # IMPORTANT
        #
        # Training Env 使用 sorted robot IDs。
        # 正式 inference 必須保持相同 action ordering。
        # ==================================================

        robot_ids = sorted(
            runtimes.keys()
        )

        start_time = (
            time.perf_counter()
        )

        # ==================================================
        # Action Mask
        #
        # 包含：
        # - capability / battery feasibility
        # - Immediate Reversal Guard
        # - Emergency Projected Start Guard
        # ==================================================

        mask = build_dynamic_action_mask(
            task=task,
            decision_type=(
                DECISION_REASSIGNMENT
            ),
            robot_ids=robot_ids,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            service_time_seconds=(
                self.service_time_seconds
            ),
            current_robot_id=(
                current_robot_id
            ),
            last_departed_robot=(
                self.last_departed_robot
            ),
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

        # Reassignment 正常情況至少應該能 Stay。
        if not mask.any():

            raise RuntimeError(
                "Reassignment has no "
                "feasible action: "
                f"task={task.task_id}, "
                f"current_robot="
                f"{current_robot_id}"
            )

        # ==================================================
        # 54-D Dynamic Observation
        #
        # Task features  = 10
        # Robot features = 11 x 4
        # Total          = 54
        # ==================================================

        observation = (
            build_dynamic_observation(
                task=task,
                decision_type=(
                    DECISION_REASSIGNMENT
                ),
                robot_ids=robot_ids,
                runtimes=runtimes,
                places=places,
                current_time=(
                    current_time
                ),
                service_time_seconds=(
                    self
                    .service_time_seconds
                ),
                current_robot_id=(
                    current_robot_id
                ),
                last_departed_robot=(
                    self
                    .last_departed_robot
                ),
            )
        )

        # ==================================================
        # Frozen PPO Inference
        #
        # Final Experiment 使用 deterministic=True。
        # ==================================================

        action, _ = (
            self.model.predict(
                observation,
                action_masks=mask,
                deterministic=True,
            )
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
                "Frozen Reassignment PPO "
                "returned invalid action: "
                f"{action}"
            )

        if not bool(
            mask[action]
        ):

            raise RuntimeError(
                "Frozen Reassignment PPO "
                "selected masked Robot: "
                f"action={action}, "
                f"robot={robot_ids[action]}"
            )

        selected_robot = (
            robot_ids[
                action
            ]
        )

        changed = (
            selected_robot
            !=
            current_robot_id
        )

        elapsed = (
            time.perf_counter()
            -
            start_time
        )

        return (
            FrozenReassignmentDecision(
                task_id=(
                    task.task_id
                ),
                previous_robot=(
                    current_robot_id
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
                changed=(
                    changed
                ),
                decision_time_seconds=(
                    elapsed
                ),
            )
        )


    # ======================================================
    # Commit Successful Migration
    # ======================================================

    def record_reassignment(
        self,
        *,
        task_id: str,
        departed_robot_id: str,
    ) -> None:
        """
        只有 RuntimeStateManager.move_waiting_task()
        真正成功後才呼叫。

        與 DynamicRLDecisionKernel：

            last_departed_robot[task_id]
                = previous_robot

        保持相同語意。
        """

        self.last_departed_robot[
            task_id
        ] = departed_robot_id
