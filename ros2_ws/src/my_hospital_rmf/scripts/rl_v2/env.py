#!/usr/bin/env python3

from copy import deepcopy

import gymnasium as gym
import numpy as np

from gymnasium import spaces

from experiment_v2.models import (
    BaselineMethod,
    SchedulerDecisionRecord,
    SimulationResult,
    SimulationScenario,
)
from experiment_v2.simulator import (
    StaticSimulator,
)

from scheduler_v2.models import Task
from scheduler_v2.projection import (
    project_task_on_robot,
)
from scheduler_v2.task_selector import (
    sort_tasks,
)

from rl_v2.action_mask import (
    build_action_mask,
)
from rl_v2.observation import (
    build_observation,
    get_observation_size,
)
from rl_v2.reward import (
    calculate_assignment_reward,
    get_priority_weight,
)


RL_METHOD_NAME = "masked_ppo"


class RLDecisionKernel(
    StaticSimulator
):
    """
    重用 experiment_v2 StaticSimulator 的
    event-driven execution engine。

    唯一差別：

        Static Baseline:
            arrival -> heuristic -> robot

        RL:
            arrival -> pause
                    -> external action
                    -> robot

    Task execution / queue / battery /
    Priority+Aging 全部沿用 v2。
    """

    def __init__(
        self,
        scenario: SimulationScenario,
        seed: int = 0,
    ):

        # Weighted 只是為了初始化 StaticSimulator。
        # RL 不會呼叫它的 _select_robot()。
        super().__init__(
            scenario=scenario,
            method=(
                BaselineMethod
                .WEIGHTED_HEURISTIC
            ),
            seed=seed,
        )

        self.pending_arrivals: list[
            Task
        ] = []

        self.current_task: Task | None = (
            None
        )

        self.finished = False

        # ==================================================
        # Long-Horizon Reward Accounting
        #
        # 累積所有 Waiting Tasks 真正等待的
        # priority-weighted time。
        #
        # Low       = 1
        # Normal    = 2
        # High      = 4
        # Emergency = 8
        # ==================================================

        self.accumulated_priority_waiting_cost = 0.0


    # ======================================================
    # Advance Time With Waiting-Cost Accounting
    # ======================================================

    def _advance_time(
        self,
        next_time: float,
    ) -> None:
        """
        Simulation time 每往前走 delta 秒，
        所有仍在 Robot Waiting Queue 的 Task
        都真正多等待 delta 秒。

        因此累積：

            priority_weight * delta

        Running Task 不算 Waiting。
        Future Task 尚未 Arrival，也不算 Waiting。
        """

        next_time = float(
            next_time
        )

        delta = (
            next_time
            -
            self.current_time
        )

        if delta < -1e-9:

            raise RuntimeError(
                "Simulation time cannot "
                "move backwards"
            )

        delta = max(
            0.0,
            delta,
        )

        if delta > 0.0:

            for runtime in (
                self.runtimes.values()
            ):

                for task in (
                    runtime.waiting_tasks
                ):

                    self.accumulated_priority_waiting_cost += (
                        get_priority_weight(
                            task.priority
                        )
                        *
                        delta
                    )

        # 真正的 simulator clock / running remaining time
        # 還是交給原本 StaticSimulator。
        super()._advance_time(
            next_time=next_time
        )


    # ======================================================
    # Action Mask
    # ======================================================

    def action_mask(
        self,
        robot_ids: list[str],
    ) -> np.ndarray:

        if self.current_task is None:

            return np.ones(
                len(robot_ids),
                dtype=bool,
            )

        return build_action_mask(
            task=self.current_task,
            robot_ids=robot_ids,
            runtimes=self.runtimes,
            places=self.scenario.places,
            current_time=self.current_time,
        )


    # ======================================================
    # Automatic Failure
    # ======================================================

    def _fail_unassignable_task(
        self,
        task: Task,
    ) -> None:

        task.status = "failed"

        record = (
            self.task_records[
                task.task_id
            ]
        )

        record.status = "failed"

        record.failure_reason = (
            "no_feasible_robot"
        )

        self.decision_records.append(
            SchedulerDecisionRecord(
                task_id=task.task_id,
                simulation_time=(
                    self.current_time
                ),
                method=RL_METHOD_NAME,
                selected_robot=None,
                decision_duration_seconds=0.0,
                decision_type="assignment",
            )
        )


    # ======================================================
    # Prepare Next RL Decision
    # ======================================================

    def prepare_next_decision(
        self,
        robot_ids: list[str],
    ) -> None:
        """
        自動執行 Simulator，
        直到：

        1. 遇到下一筆需要 RL Assignment 的 Task
        或
        2. Episode 完成

        同時間事件順序維持：

        Complete
        -> Collect Arrivals
        -> RL Assignment(s)
        -> Start Idle Robots
        """

        self.current_task = None

        while True:

            # ----------------------------------------------
            # 尚有同時間 Arrival 尚未做 Assignment
            # ----------------------------------------------

            while self.pending_arrivals:

                task = (
                    self.pending_arrivals
                    .pop(0)
                )

                mask = build_action_mask(
                    task=task,
                    robot_ids=robot_ids,
                    runtimes=self.runtimes,
                    places=(
                        self.scenario.places
                    ),
                    current_time=(
                        self.current_time
                    ),
                )

                if not mask.any():

                    self._fail_unassignable_task(
                        task
                    )

                    continue

                self.current_task = task

                return

            # ----------------------------------------------
            # Complete
            # ----------------------------------------------

            self._complete_finished_tasks()

            # ----------------------------------------------
            # Arrivals
            # ----------------------------------------------

            arrivals = (
                self._collect_current_arrivals()
            )

            if arrivals:

                self.pending_arrivals = (
                    sort_tasks(
                        tasks=arrivals,
                        current_time=(
                            self.current_time
                        ),
                    )
                )

                # 不 Start Robot。
                #
                # 必須先把此 simulation time
                # 所有 arrivals 完成 assignment，
                # 才符合 Baseline 的 event ordering。
                continue

            # ----------------------------------------------
            # 所有本時刻 Assignment 完成後
            # 才讓 idle robots 開始工作
            # ----------------------------------------------

            self._start_idle_robots()

            # ----------------------------------------------
            # Finished?
            # ----------------------------------------------

            if not self._has_unfinished_work():

                self.finished = True

                self.current_task = None

                return

            # ----------------------------------------------
            # Advance to next event
            # ----------------------------------------------

            next_time = (
                self._next_event_time()
            )

            if next_time is None:

                raise RuntimeError(
                    "RL simulation has "
                    "unfinished work but "
                    "no future event"
                )

            self._advance_time(
                next_time=next_time
            )


    # ======================================================
    # Assignment From RL Action
    # ======================================================

    def assign_current_task(
        self,
        robot_id: str,
        robot_ids: list[str],
    ):
        """
        將 current_task 指派給 RL 選出的 Robot。

        回傳 assignment 前的 projection，
        後面 Reward 會使用。
        """

        if self.current_task is None:

            raise RuntimeError(
                "No current RL task"
            )

        if robot_id not in self.runtimes:

            raise ValueError(
                f"Unknown robot: {robot_id}"
            )

        mask = self.action_mask(
            robot_ids
        )

        action_index = (
            robot_ids.index(
                robot_id
            )
        )

        if not bool(
            mask[action_index]
        ):

            raise ValueError(
                "RL selected infeasible robot: "
                f"task={self.current_task.task_id}, "
                f"robot={robot_id}"
            )

        task = self.current_task

        runtime = (
            self.runtimes[
                robot_id
            ]
        )

        # Reward / debug 後續需要。
        projection = (
            project_task_on_robot(
                task=task,
                runtime=runtime,
                places=(
                    self.scenario.places
                ),
                current_time=(
                    self.current_time
                ),
                service_time_seconds=(
                    self.scenario
                    .service_time_seconds
                ),
            )
        )

        # ----------------------------------------------
        # Assignment
        # ----------------------------------------------

        task.assigned_robot = robot_id
        task.status = "assigned"

        record = (
            self.task_records[
                task.task_id
            ]
        )

        record.assigned_robot = robot_id
        record.assigned_at = (
            self.current_time
        )
        record.status = "assigned"

        runtime.waiting_tasks.append(
            task
        )

        self.decision_records.append(
            SchedulerDecisionRecord(
                task_id=task.task_id,
                simulation_time=(
                    self.current_time
                ),
                method=RL_METHOD_NAME,
                selected_robot=robot_id,
                decision_duration_seconds=0.0,
                decision_type="assignment",
            )
        )

        self.current_task = None

        return projection


    # ======================================================
    # Result
    # ======================================================

    def get_result(
        self,
    ) -> SimulationResult:

        if not self.finished:

            raise RuntimeError(
                "Episode is not finished"
            )

        return SimulationResult(
            scenario_name=(
                self.scenario.name
            ),
            method=RL_METHOD_NAME,
            episode_start_time=0.0,
            episode_end_time=(
                self.current_time
            ),
            task_records=(
                self.task_records
            ),
            decision_records=(
                self.decision_records
            ),
            robot_records=(
                self.robot_records
            ),
        )


class HospitalRLEnv(
    gym.Env
):
    """
    Gymnasium environment。

    一個 step =
        一次 Task -> Robot Assignment。

    Simulator time 並不是固定步進；
    每次 Assignment 後，
    系統自動前進到下一個需要 RL 決策的事件。
    """

    metadata = {
        "render_modes": [],
    }


    def __init__(
        self,
        scenario: SimulationScenario,
        seed: int = 0,
    ):

        super().__init__()

        self.original_scenario = (
            deepcopy(
                scenario
            )
        )

        self.default_seed = int(
            seed
        )

        self.robot_ids = sorted(
            robot.robot_id
            for robot
            in scenario.robots
        )

        self.action_space = (
            spaces.Discrete(
                len(self.robot_ids)
            )
        )

        observation_size = (
            get_observation_size(
                len(self.robot_ids)
            )
        )

        self.observation_space = (
            spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(
                    observation_size,
                ),
                dtype=np.float32,
            )
        )

        self.kernel: (
            RLDecisionKernel
            |
            None
        ) = None


    # ======================================================
    # Observation
    # ======================================================

    def _get_observation(
        self,
    ) -> np.ndarray:

        if (
            self.kernel is None
            or
            self.kernel.finished
            or
            self.kernel.current_task
            is None
        ):

            return np.zeros(
                self.observation_space.shape,
                dtype=np.float32,
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
    # Action Mask
    # ======================================================

    def action_masks(
        self,
    ) -> np.ndarray:
        """
        sb3-contrib MaskablePPO
        會讀取這個 method。
        """

        if (
            self.kernel is None
            or
            self.kernel.finished
        ):

            return np.ones(
                len(self.robot_ids),
                dtype=bool,
            )

        return (
            self.kernel
            .action_mask(
                self.robot_ids
            )
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

        super().reset(
            seed=seed
        )

        kernel_seed = (
            self.default_seed
            if seed is None
            else int(seed)
        )

        self.kernel = (
            RLDecisionKernel(
                scenario=(
                    self.original_scenario
                ),
                seed=kernel_seed,
            )
        )

        self.kernel.prepare_next_decision(
            self.robot_ids
        )

        observation = (
            self._get_observation()
        )

        info = {
            "simulation_time":
                self.kernel.current_time,

            "task_id":
                (
                    None
                    if self.kernel.current_task
                    is None
                    else
                    self.kernel
                    .current_task
                    .task_id
                ),

            "action_mask":
                self.action_masks().copy(),
        }

        return (
            observation,
            info,
        )


    # ======================================================
    # Step
    # ======================================================

    def step(
        self,
        action,
    ):

        if self.kernel is None:

            raise RuntimeError(
                "Call reset() first"
            )

        if self.kernel.finished:

            raise RuntimeError(
                "Episode already finished"
            )

        action = int(
            action
        )

        if not (
            0
            <=
            action
            <
            len(self.robot_ids)
        ):

            raise ValueError(
                f"Invalid action: {action}"
            )

        mask = self.action_masks()

        if not bool(
            mask[action]
        ):

            raise ValueError(
                "Masked action selected: "
                f"{action}"
            )

        selected_robot_id = (
            self.robot_ids[
                action
            ]
        )

        assigned_task = (
            self.kernel.current_task
        )

        previous_task_id = (
            assigned_task.task_id
        )

        projection = (
            self.kernel
            .assign_current_task(
                robot_id=(
                    selected_robot_id
                ),
                robot_ids=(
                    self.robot_ids
                ),
            )
        )

        # ==================================================
        # Assignment Reward
        # ==================================================

        reward_breakdown = (
            calculate_assignment_reward(
                task=assigned_task,
                projection=projection,
            )
        )

        reward = (
            reward_breakdown.reward
        )

        self.kernel.prepare_next_decision(
            self.robot_ids
        )

        terminated = bool(
            self.kernel.finished
        )

        truncated = False

        observation = (
            self._get_observation()
        )

        info = {
            "assigned_task":
                previous_task_id,

            "selected_robot":
                selected_robot_id,

            "projected_workload_before_task":
                projection
                .workload_before_task,

            "projected_distance_to_source":
                projection
                .distance_to_source,

            "projected_battery_after_task":
                projection
                .projected_battery_after_task,

            "simulation_time":
                self.kernel.current_time,

            "next_task":
                (
                    None
                    if self.kernel.current_task
                    is None
                    else
                    self.kernel
                    .current_task
                    .task_id
                ),

            "action_mask":
                self.action_masks().copy(),

            "reward_waiting_cost":
                reward_breakdown.waiting_cost,

            "reward_distance_cost":
                reward_breakdown.distance_cost,

            "reward_priority_weight":
                reward_breakdown.priority_weight,
        }

        return (
            observation,
            float(reward),
            terminated,
            truncated,
            info,
        )


    def get_simulation_result(
        self,
    ) -> SimulationResult:

        if self.kernel is None:

            raise RuntimeError(
                "Call reset() first"
            )

        return (
            self.kernel
            .get_result()
        )
