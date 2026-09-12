#!/usr/bin/env python3

from copy import deepcopy

import numpy as np

from experiment_v2.models import (
    SimulationScenario,
)

from rl_v2.dynamic_env import (
    DynamicHospitalRLEnv,
)

from rl_v2.observation import (
    build_observation,
)

from rl_v2.system_reward import (
    SystemRewardConfig,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)

from rl_v2.dynamic_action_mask import (
    DECISION_ASSIGNMENT,
    DECISION_REASSIGNMENT,
)

from rl_v2.reassignment_shaping import (
    ReassignmentShapingConfig,
    calculate_reassignment_shaping,
)


class ReassignmentHospitalRLEnv(
    DynamicHospitalRLEnv
):
    """
    Two-Policy Dynamic Environment。

    Policy A:
        Frozen Static Long-Horizon PPO
        自動負責 Initial Assignment。

    Policy B:
        Dedicated Reassignment PPO
        Gym Environment 只暴露
        Waiting Task 的 Stay / Reassign 決策。

    因此新的 PPO 不再看到 Initial Assignment samples。
    """

    def __init__(
        self,
        scenario: SimulationScenario,
        assignment_policy,
        seed: int = 0,
        reward_config: SystemRewardConfig | None = None,
        shaping_config: ReassignmentShapingConfig | None = None,
    ):

        self.assignment_policy = (
            assignment_policy
        )

        # Shaping 是 Dedicated Reassignment Env 自己的功能，
        # 不傳給 DynamicHospitalRLEnv。
        self.shaping_config = (
            shaping_config
        )

        super().__init__(
            scenario=scenario,
            seed=seed,
            reward_config=(
                reward_config
            ),
        )


    # ======================================================
    # Frozen Assignment Observation
    # ======================================================

    def _get_assignment_observation(
        self,
    ) -> np.ndarray:
        """
        Frozen Static PPO 使用原本 49-D Observation。

        即使底層 Simulator 是 Dynamic，
        Initial Assignment 的 Observation
        仍與 Static Long-Horizon PPO
        訓練時完全一致。
        """

        if self.kernel is None:

            raise RuntimeError(
                "Kernel is not initialized"
            )

        if (
            self.kernel.current_task
            is None
        ):

            raise RuntimeError(
                "No current assignment task"
            )

        if (
            self.kernel
            .current_decision_type
            !=
            DECISION_ASSIGNMENT
        ):

            raise RuntimeError(
                "Current decision is not "
                "an assignment"
            )

        return build_observation(
            task=(
                self.kernel.current_task
            ),
            robot_ids=(
                self.robot_ids
            ),
            runtimes=(
                self.kernel.runtimes
            ),
            places=(
                self.kernel
                .scenario
                .places
            ),
            current_time=(
                self.kernel.current_time
            ),
            service_time_seconds=(
                self.kernel
                .scenario
                .service_time_seconds
            ),
        )


    # ======================================================
    # Automatic Frozen Assignment
    # ======================================================

    def _predict_assignment_action(
        self,
    ) -> int:

        observation = (
            self._get_assignment_observation()
        )

        mask = (
            self.action_masks()
        )

        action, _ = (
            self.assignment_policy.predict(
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

        if not bool(
            mask[action]
        ):

            raise RuntimeError(
                "Frozen assignment policy "
                "selected masked action"
            )

        return action


    def _resolve_automatic_assignments(
        self,
    ):
        """
        自動執行目前所有 Initial Assignments，
        直到：

        1. 下一個 Reassignment Decision
        2. Episode 結束

        回傳：
            observation
            cumulative reward
            terminated
            truncated
            latest info
            assignment count
        """

        cumulative_reward = 0.0

        assignment_count = 0

        latest_info = {}

        terminated = False
        truncated = False

        observation = (
            self._get_observation()
        )

        while (
            self.kernel is not None
            and
            not self.kernel.finished
            and
            self.kernel.current_decision_type
            ==
            DECISION_ASSIGNMENT
        ):

            action = (
                self._predict_assignment_action()
            )

            (
                observation,
                reward,
                terminated,
                truncated,
                latest_info,
            ) = super().step(
                action
            )

            cumulative_reward += float(
                reward
            )

            assignment_count += 1

            if (
                terminated
                or
                truncated
            ):

                break

        return (
            observation,
            cumulative_reward,
            terminated,
            truncated,
            latest_info,
            assignment_count,
        )


    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self,
        *,
        seed=None,
        options=None,
    ):

        (
            observation,
            info,
        ) = super().reset(
            seed=seed,
            options=options,
        )

        # Episode 起始通常先遇到 Assignment。
        #
        # Assignment 不暴露給 Dedicated PPO。
        (
            observation,
            automatic_reward,
            terminated,
            truncated,
            latest_info,
            assignment_count,
        ) = (
            self
            ._resolve_automatic_assignments()
        )

        if (
            self.kernel is not None
            and
            not self.kernel.finished
            and
            self.kernel
            .current_decision_type
            !=
            DECISION_REASSIGNMENT
        ):

            raise RuntimeError(
                "Reassignment environment "
                "did not stop at a "
                "reassignment decision"
            )

        result_info = dict(
            info
        )

        if latest_info:

            result_info.update(
                {
                    "simulation_time":
                        latest_info.get(
                            "simulation_time",
                            result_info.get(
                                "simulation_time"
                            ),
                        ),

                    "task_id":
                        latest_info.get(
                            "next_task"
                        ),

                    "decision_type":
                        latest_info.get(
                            "next_decision_type"
                        ),

                    "current_robot":
                        latest_info.get(
                            "next_current_robot"
                        ),

                    "action_mask":
                        latest_info.get(
                            "action_mask",
                            self.action_masks().copy(),
                        ),
                }
            )

        result_info[
            "automatic_assignment_count"
        ] = assignment_count

        # Reset 前的 cost 與 Reassignment Agent
        # 尚未做任何 action 無關，
        # 因此不作為第一個 RL step reward。
        result_info[
            "automatic_assignment_reward_before_first_decision"
        ] = float(
            automatic_reward
        )

        return (
            self._get_observation(),
            result_info,
        )


    def _calculate_action_shaping(
        self,
        action: int,
    ):
        """
        在真正執行 Reassignment action 前，
        根據目前 simulator state 計算
        projected-improvement shaping。

        shaping_config=None：
            完全關閉 shaping。
        """

        if self.shaping_config is None:

            return None

        if self.kernel is None:

            raise RuntimeError(
                "Kernel is not initialized"
            )

        if (
            self.kernel.current_decision_type
            !=
            DECISION_REASSIGNMENT
        ):

            return None

        task = (
            self.kernel.current_task
        )

        current_robot = (
            self.kernel.current_previous_robot
        )

        if (
            task is None
            or
            current_robot is None
        ):

            raise RuntimeError(
                "Reassignment shaping requires "
                "current task and current robot"
            )

        selected_robot = (
            self.robot_ids[
                int(action)
            ]
        )

        # ------------------------------------------------------
        # Reassignment projection 必須先從 copied runtime
        # 移除 target task。
        # ------------------------------------------------------

        projection_runtimes = deepcopy(
            self.kernel.runtimes
        )

        current_runtime = (
            projection_runtimes[
                current_robot
            ]
        )

        matching_indices = [
            index
            for index, queued_task
            in enumerate(
                current_runtime
                .waiting_tasks
            )
            if (
                queued_task.task_id
                ==
                task.task_id
            )
        ]

        if len(
            matching_indices
        ) != 1:

            raise RuntimeError(
                "Expected reassignment target "
                "exactly once in current "
                "waiting queue. "
                f"task={task.task_id}, "
                f"robot={current_robot}, "
                f"matches={len(matching_indices)}"
            )

        current_runtime.waiting_tasks.pop(
            matching_indices[0]
        )

        current_projection = (
            project_task_on_robot(
                task=task,
                runtime=(
                    projection_runtimes[
                        current_robot
                    ]
                ),
                places=(
                    self.kernel
                    .scenario
                    .places
                ),
                current_time=(
                    self.kernel.current_time
                ),
                service_time_seconds=(
                    self.kernel
                    .scenario
                    .service_time_seconds
                ),
            )
        )

        selected_projection = (
            project_task_on_robot(
                task=task,
                runtime=(
                    projection_runtimes[
                        selected_robot
                    ]
                ),
                places=(
                    self.kernel
                    .scenario
                    .places
                ),
                current_time=(
                    self.kernel.current_time
                ),
                service_time_seconds=(
                    self.kernel
                    .scenario
                    .service_time_seconds
                ),
            )
        )

        return (
            calculate_reassignment_shaping(
                priority=task.priority,
                current_projection=(
                    current_projection
                ),
                selected_projection=(
                    selected_projection
                ),
                config=(
                    self.shaping_config
                ),
            )
        )


    # ======================================================
    # Step
    # ======================================================

    def step(
        self,
        action,
    ):
        """
        外部 PPO 的一次 step：

            Reassignment action
            ↓
            Simulator continues
            ↓
            Frozen PPO 自動處理途中所有 Assignment
            ↓
            停在下一個 Reassignment decision

        Reward：
            從本次 Reassignment
            到下一次 Reassignment 之間的
            actual system cost 總和。
        """

        if self.kernel is None:

            raise RuntimeError(
                "Call reset() first"
            )

        if (
            self.kernel
            .current_decision_type
            !=
            DECISION_REASSIGNMENT
        ):

            raise RuntimeError(
                "Dedicated policy may only "
                "act on reassignment decisions"
            )

        shaping_breakdown = (
            self._calculate_action_shaping(
                action
            )
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            agent_info,
        ) = super().step(
            action
        )

        system_reward = float(
            reward
        )

        shaping_reward = (
            0.0
            if shaping_breakdown is None
            else float(
                shaping_breakdown
                .shaping_reward
            )
        )

        total_reward = (
            system_reward
            +
            shaping_reward
        )

        automatic_assignment_reward = 0.0

        automatic_assignment_count = 0

        latest_info = agent_info

        if (
            not terminated
            and
            not truncated
        ):

            (
                observation,
                automatic_reward,
                automatic_terminated,
                automatic_truncated,
                automatic_info,
                assignment_count,
            ) = (
                self
                ._resolve_automatic_assignments()
            )

            total_reward += float(
                automatic_reward
            )

            automatic_assignment_reward = (
                float(
                    automatic_reward
                )
            )

            automatic_assignment_count = (
                assignment_count
            )

            terminated = (
                terminated
                or
                automatic_terminated
            )

            truncated = (
                truncated
                or
                automatic_truncated
            )

            if automatic_info:

                latest_info = (
                    automatic_info
                )

        # --------------------------------------------------
        # Agent Info
        #
        # decision_type / changed /
        # previous_robot / selected_robot
        # 必須保留這次真正的 RL Reassignment。
        # --------------------------------------------------

        info = dict(
            agent_info
        )

        info[
            "automatic_assignment_count"
        ] = (
            automatic_assignment_count
        )

        info[
            "automatic_assignment_reward"
        ] = (
            automatic_assignment_reward
        )

        # --------------------------------------------------
        # Reward Diagnostics
        #
        # 將真正的 system reward、shaping reward
        # 與 PPO 最後收到的 total reward 分開記錄。
        # --------------------------------------------------

        info[
            "system_reward_before_automatic_assignment"
        ] = (
            system_reward
        )

        info[
            "system_reward_total"
        ] = (
            system_reward
            +
            automatic_assignment_reward
        )

        info[
            "reassignment_shaping_reward"
        ] = (
            shaping_reward
        )

        info[
            "total_reward"
        ] = (
            total_reward
        )

        if shaping_breakdown is not None:

            info[
                "reassignment_current_projected_cost"
            ] = (
                shaping_breakdown
                .current_projected_cost
            )

            info[
                "reassignment_selected_projected_cost"
            ] = (
                shaping_breakdown
                .selected_projected_cost
            )

            info[
                "reassignment_raw_improvement"
            ] = (
                shaping_breakdown
                .raw_improvement
            )

        else:

            info[
                "reassignment_current_projected_cost"
            ] = None

            info[
                "reassignment_selected_projected_cost"
            ] = None

            info[
                "reassignment_raw_improvement"
            ] = 0.0

        if latest_info:

            info[
                "simulation_time"
            ] = latest_info.get(
                "simulation_time",
                info.get(
                    "simulation_time"
                ),
            )

            info[
                "next_task"
            ] = latest_info.get(
                "next_task"
            )

            info[
                "next_decision_type"
            ] = latest_info.get(
                "next_decision_type"
            )

            info[
                "next_current_robot"
            ] = latest_info.get(
                "next_current_robot"
            )

        info[
            "action_mask"
        ] = self.action_masks().copy()

        if (
            not terminated
            and
            self.kernel is not None
            and
            self.kernel
            .current_decision_type
            !=
            DECISION_REASSIGNMENT
        ):

            raise RuntimeError(
                "Environment returned control "
                "before reaching a "
                "reassignment decision"
            )

        return (
            self._get_observation(),
            float(
                total_reward
            ),
            bool(
                terminated
            ),
            bool(
                truncated
            ),
            info,
        )
