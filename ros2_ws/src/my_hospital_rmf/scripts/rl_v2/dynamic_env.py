#!/usr/bin/env python3

from copy import deepcopy

import gymnasium as gym
import numpy as np

from gymnasium import spaces

from experiment_v2.models import (
    SchedulerDecisionRecord,
    SimulationResult,
    SimulationScenario,
)

from experiment_v2.simulator import (
    TIME_EPSILON,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.task_selector import (
    sort_tasks,
)

from rl_v2.env import (
    RLDecisionKernel,
)

from rl_v2.dynamic_action_mask import (
    DECISION_ASSIGNMENT,
    DECISION_REASSIGNMENT,
    build_dynamic_action_mask,
)

from rl_v2.dynamic_observation import (
    build_dynamic_observation,
    get_dynamic_observation_size,
)

from rl_v2.system_reward import (
    SystemRewardConfig,
    calculate_system_reward,
)


DYNAMIC_RL_METHOD_NAME = (
    "dynamic_masked_ppo"
)


# ==========================================================
# Dynamic RL Kernel
# ==========================================================

class DynamicRLDecisionKernel(
    RLDecisionKernel
):

    def __init__(
        self,
        scenario: SimulationScenario,
        seed: int = 0,
        reward_config: SystemRewardConfig | None = None,
    ):

        super().__init__(
            scenario=scenario,
            seed=seed,
        )

        self.current_decision_type: (
            str
            |
            None
        ) = None

        self.current_previous_robot: (
            str
            |
            None
        ) = None

        self.current_root_event_id: (
            str
            |
            None
        ) = None

        self.active_root_event_id: (
            str
            |
            None
        ) = None

        self.pending_reassignments: list[
            Task
        ] = []

        self.reassignment_snapshot_ready = (
            False
        )

        self.last_departed_robot: dict[
            str,
            str,
        ] = {}

        self.reward_config = (
            SystemRewardConfig()
            if reward_config is None
            else reward_config
        )


    # ======================================================
    # Root Event
    # ======================================================

    @staticmethod
    def _build_root_event_id(
        completed_task_ids: list[str],
        arrivals: list[Task],
    ) -> str | None:

        event_ids = []

        for task_id in (
            completed_task_ids
        ):

            event_ids.append(
                "completion:"
                f"{task_id}"
            )

        for task in arrivals:

            event_ids.append(
                "arrival:"
                f"{task.task_id}"
            )

        if not event_ids:
            return None

        if len(event_ids) == 1:
            return event_ids[0]

        return (
            "batch:"
            +
            "|".join(
                event_ids
            )
        )


    # ======================================================
    # Waiting Snapshot
    # ======================================================

    def _snapshot_waiting_tasks(
        self,
    ) -> list[Task]:

        waiting_tasks = []

        for runtime in (
            self.runtimes.values()
        ):

            waiting_tasks.extend(
                runtime.waiting_tasks
            )

        if not waiting_tasks:
            return []

        return sort_tasks(
            tasks=waiting_tasks,
            current_time=(
                self.current_time
            ),
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

        if (
            self.current_decision_type
            is None
        ):

            raise RuntimeError(
                "Current task has no "
                "decision type"
            )

        return (
            build_dynamic_action_mask(
                task=(
                    self.current_task
                ),
                decision_type=(
                    self.current_decision_type
                ),
                robot_ids=robot_ids,
                runtimes=self.runtimes,
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
                current_robot_id=(
                    self
                    .current_previous_robot
                ),
                last_departed_robot=(
                    self
                    .last_departed_robot
                ),
            )
        )


    # ======================================================
    # Assignment
    # ======================================================

    def _apply_assignment(
        self,
        robot_id: str,
    ) -> dict:

        task = self.current_task

        if task is None:

            raise RuntimeError(
                "No current task"
            )

        runtime = (
            self.runtimes[
                robot_id
            ]
        )

        task.assigned_robot = (
            robot_id
        )

        task.status = "assigned"

        record = (
            self.task_records[
                task.task_id
            ]
        )

        record.assigned_robot = (
            robot_id
        )

        record.assigned_at = (
            self.current_time
        )

        record.status = (
            "assigned"
        )

        runtime.waiting_tasks.append(
            task
        )

        self.decision_records.append(
            SchedulerDecisionRecord(
                task_id=task.task_id,
                simulation_time=(
                    self.current_time
                ),
                method=(
                    DYNAMIC_RL_METHOD_NAME
                ),
                selected_robot=(
                    robot_id
                ),
                decision_duration_seconds=0.0,
                decision_type=(
                    "assignment"
                ),
            )
        )

        return {
            "decision_type":
                DECISION_ASSIGNMENT,

            "task_id":
                task.task_id,

            "previous_robot":
                None,

            "selected_robot":
                robot_id,

            "changed":
                True,

            "root_event_id":
                self.active_root_event_id,
        }


    # ======================================================
    # Queue Migration
    # ======================================================

    def _move_waiting_task(
        self,
        task: Task,
        new_robot_id: str,
    ) -> None:

        old_robot_id = (
            task.assigned_robot
        )

        if old_robot_id is None:

            raise RuntimeError(
                "Cannot reassign task "
                "without assigned_robot"
            )

        if (
            old_robot_id
            ==
            new_robot_id
        ):

            return

        old_runtime = (
            self.runtimes[
                old_robot_id
            ]
        )

        new_runtime = (
            self.runtimes[
                new_robot_id
            ]
        )

        if (
            old_runtime.running_task
            is not None
            and
            old_runtime
            .running_task
            .task_id
            ==
            task.task_id
        ):

            raise RuntimeError(
                "Running task cannot "
                "be reassigned"
            )

        if task not in (
            old_runtime.waiting_tasks
        ):

            raise RuntimeError(
                f"Task {task.task_id} "
                "is not waiting on "
                f"{old_robot_id}"
            )

        old_runtime.waiting_tasks.remove(
            task
        )

        new_runtime.waiting_tasks.append(
            task
        )

        task.assigned_robot = (
            new_robot_id
        )

        record = (
            self.task_records[
                task.task_id
            ]
        )

        record.assigned_robot = (
            new_robot_id
        )


    # ======================================================
    # Reassignment
    # ======================================================

    def _apply_reassignment(
        self,
        robot_id: str,
    ) -> dict:

        task = self.current_task

        if task is None:

            raise RuntimeError(
                "No current task"
            )

        previous_robot = (
            self.current_previous_robot
        )

        if previous_robot is None:

            raise RuntimeError(
                "Reassignment has no "
                "previous robot"
            )

        if (
            task.assigned_robot
            !=
            previous_robot
        ):

            raise RuntimeError(
                "Reassignment state changed "
                "unexpectedly"
            )

        changed = (
            robot_id
            !=
            previous_robot
        )

        self.decision_records.append(
            SchedulerDecisionRecord(
                task_id=(
                    task.task_id
                ),
                simulation_time=(
                    self.current_time
                ),
                method=(
                    DYNAMIC_RL_METHOD_NAME
                ),
                selected_robot=(
                    robot_id
                ),
                previous_robot=(
                    previous_robot
                ),
                decision_duration_seconds=0.0,
                decision_type=(
                    "reassignment"
                ),
                root_event_id=(
                    self
                    .current_root_event_id
                ),
                cascade_depth=1,
            )
        )

        if changed:

            self._move_waiting_task(
                task=task,
                new_robot_id=(
                    robot_id
                ),
            )

            self.last_departed_robot[
                task.task_id
            ] = previous_robot

        return {
            "decision_type":
                DECISION_REASSIGNMENT,

            "task_id":
                task.task_id,

            "previous_robot":
                previous_robot,

            "selected_robot":
                robot_id,

            "changed":
                changed,

            "root_event_id":
                self.current_root_event_id,
        }


    # ======================================================
    # Apply RL Action
    # ======================================================

    def apply_current_action(
        self,
        robot_id: str,
        robot_ids: list[str],
    ) -> dict:

        if self.current_task is None:

            raise RuntimeError(
                "No current RL decision"
            )

        if robot_id not in robot_ids:

            raise ValueError(
                "Unknown robot: "
                f"{robot_id}"
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
                "Dynamic RL selected "
                "masked action: "
                f"task={self.current_task.task_id}, "
                f"robot={robot_id}"
            )

        if (
            self.current_decision_type
            ==
            DECISION_ASSIGNMENT
        ):

            result = (
                self._apply_assignment(
                    robot_id
                )
            )

        elif (
            self.current_decision_type
            ==
            DECISION_REASSIGNMENT
        ):

            result = (
                self._apply_reassignment(
                    robot_id
                )
            )

        else:

            raise RuntimeError(
                "Unknown current "
                "decision type"
            )

        self.current_task = None
        self.current_decision_type = (
            None
        )
        self.current_previous_robot = (
            None
        )
        self.current_root_event_id = (
            None
        )

        return result


    # ======================================================
    # Prepare Next Decision
    # ======================================================

    def prepare_next_decision(
        self,
        robot_ids: list[str],
    ) -> None:

        self.current_task = None
        self.current_decision_type = (
            None
        )
        self.current_previous_robot = (
            None
        )
        self.current_root_event_id = (
            None
        )

        while True:

            # ==================================================
            # A. Finish all Initial Assignments
            # ==================================================

            while self.pending_arrivals:

                task = (
                    self.pending_arrivals
                    .pop(0)
                )

                mask = (
                    build_dynamic_action_mask(
                        task=task,
                        decision_type=(
                            DECISION_ASSIGNMENT
                        ),
                        robot_ids=(
                            robot_ids
                        ),
                        runtimes=(
                            self.runtimes
                        ),
                        places=(
                            self
                            .scenario
                            .places
                        ),
                        current_time=(
                            self.current_time
                        ),
                        service_time_seconds=(
                            self
                            .scenario
                            .service_time_seconds
                        ),
                    )
                )

                if not mask.any():

                    self._fail_unassignable_task(
                        task
                    )

                    continue

                self.current_task = (
                    task
                )

                self.current_decision_type = (
                    DECISION_ASSIGNMENT
                )

                self.current_root_event_id = (
                    self.active_root_event_id
                )

                return

            # ==================================================
            # B. Snapshot Dynamic Pass
            # ==================================================

            if (
                self.active_root_event_id
                is not None
                and
                not
                self.reassignment_snapshot_ready
            ):

                self.pending_reassignments = (
                    self
                    ._snapshot_waiting_tasks()
                )

                self.reassignment_snapshot_ready = (
                    True
                )

            # ==================================================
            # C. Reassignment Decisions
            # ==================================================

            while self.pending_reassignments:

                task = (
                    self.pending_reassignments
                    .pop(0)
                )

                if (
                    task.status
                    !=
                    "assigned"
                ):

                    continue

                previous_robot = (
                    task.assigned_robot
                )

                if previous_robot is None:

                    raise RuntimeError(
                        "Waiting task has "
                        "no assigned robot"
                    )

                # 必須仍然真的在 waiting queue，
                # Running task 不允許進 RL reassignment。
                previous_runtime = (
                    self.runtimes[
                        previous_robot
                    ]
                )

                if task not in (
                    previous_runtime
                    .waiting_tasks
                ):

                    continue

                mask = (
                    build_dynamic_action_mask(
                        task=task,
                        decision_type=(
                            DECISION_REASSIGNMENT
                        ),
                        robot_ids=(
                            robot_ids
                        ),
                        runtimes=(
                            self.runtimes
                        ),
                        places=(
                            self
                            .scenario
                            .places
                        ),
                        current_time=(
                            self.current_time
                        ),
                        service_time_seconds=(
                            self
                            .scenario
                            .service_time_seconds
                        ),
                        current_robot_id=(
                            previous_robot
                        ),
                        last_departed_robot=(
                            self
                            .last_departed_robot
                        ),
                    )
                )

                # 正常情況至少 current robot
                # 應該仍然能 Stay。
                if not mask.any():

                    raise RuntimeError(
                        "Reassignment has "
                        "no feasible action: "
                        f"task={task.task_id}"
                    )

                self.current_task = (
                    task
                )

                self.current_decision_type = (
                    DECISION_REASSIGNMENT
                )

                self.current_previous_robot = (
                    previous_robot
                )

                self.current_root_event_id = (
                    self.active_root_event_id
                )

                return

            # ==================================================
            # D. Current Root Event Finished
            # ==================================================

            if (
                self.active_root_event_id
                is not None
            ):

                # Reassignment 全部完成後，
                # 才允許 Idle Robot Start。
                self._start_idle_robots()

                self.active_root_event_id = (
                    None
                )

                self.reassignment_snapshot_ready = (
                    False
                )

                continue

            # ==================================================
            # E. Build Current Root Event
            # ==================================================

            completed_task_ids = sorted(
                runtime
                .running_task
                .task_id
                for runtime
                in self.runtimes.values()
                if (
                    runtime.running_task
                    is not None
                    and
                    runtime
                    .running_remaining_time
                    <=
                    TIME_EPSILON
                )
            )

            self._complete_finished_tasks()

            arrivals = (
                self._collect_current_arrivals()
            )

            ordered_arrivals = (
                sort_tasks(
                    tasks=arrivals,
                    current_time=(
                        self.current_time
                    ),
                )
                if arrivals
                else []
            )

            root_event_id = (
                self._build_root_event_id(
                    completed_task_ids=(
                        completed_task_ids
                    ),
                    arrivals=(
                        ordered_arrivals
                    ),
                )
            )

            if (
                root_event_id
                is not None
            ):

                self.active_root_event_id = (
                    root_event_id
                )

                self.pending_arrivals = (
                    ordered_arrivals
                )

                self.pending_reassignments = []

                self.reassignment_snapshot_ready = (
                    False
                )

                continue

            # ==================================================
            # F. No event at current time
            # ==================================================

            self._start_idle_robots()

            if not self._has_unfinished_work():

                self.finished = True

                return

            next_time = (
                self._next_event_time()
            )

            if next_time is None:

                raise RuntimeError(
                    "Dynamic RL simulation "
                    "has unfinished work "
                    "but no future event"
                )

            self._advance_time(
                next_time=(
                    next_time
                )
            )


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
            method=(
                DYNAMIC_RL_METHOD_NAME
            ),
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


# ==========================================================
# Gym Environment
# ==========================================================

class DynamicHospitalRLEnv(
    gym.Env
):

    metadata = {
        "render_modes": [],
    }

    def __init__(
        self,
        scenario: SimulationScenario,
        seed: int = 0,
        reward_config: SystemRewardConfig | None = None,
    ):

        super().__init__()

        self.original_scenario = deepcopy(
            scenario
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

        self.observation_space = (
            spaces.Box(
                low=-1.0,
                high=1.0,
                shape=(
                    get_dynamic_observation_size(
                        len(
                            self.robot_ids
                        )
                    ),
                ),
                dtype=np.float32,
            )
        )

        self.kernel: (
            DynamicRLDecisionKernel
            |
            None
        ) = None

        self.reward_config = (
            SystemRewardConfig()
            if reward_config is None
            else reward_config
        )


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

        return (
            build_dynamic_observation(
                task=(
                    self.kernel
                    .current_task
                ),
                decision_type=(
                    self.kernel
                    .current_decision_type
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
                    self.kernel
                    .current_time
                ),
                service_time_seconds=(
                    self.kernel
                    .scenario
                    .service_time_seconds
                ),
                current_robot_id=(
                    self.kernel
                    .current_previous_robot
                ),
                last_departed_robot=(
                    self.kernel
                    .last_departed_robot
                ),
            )
        )


    # ======================================================
    # Action Mask
    # ======================================================

    def action_masks(
        self,
    ) -> np.ndarray:

        if (
            self.kernel is None
            or
            self.kernel.finished
        ):

            return np.ones(
                len(self.robot_ids),
                dtype=bool,
            )

        return self.kernel.action_mask(
            self.robot_ids
        )


    # ======================================================
    # Reward Helpers
    # ======================================================

    def _total_travel_distance(
        self,
    ) -> float:

        if self.kernel is None:
            return 0.0

        return sum(
            record.total_travel_distance
            for record
            in self.kernel
            .robot_records
            .values()
        )


    def _failed_task_count(
        self,
    ) -> int:

        if self.kernel is None:
            return 0

        return sum(
            1
            for record
            in self.kernel
            .task_records
            .values()
            if (
                record.status
                ==
                "failed"
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
            DynamicRLDecisionKernel(
                scenario=(
                    self.original_scenario
                ),
                seed=kernel_seed,
            )
        )

        self.kernel.prepare_next_decision(
            self.robot_ids
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

            "decision_type":
                self.kernel
                .current_decision_type,

            "current_robot":
                self.kernel
                .current_previous_robot,

            "root_event_id":
                self.kernel
                .current_root_event_id,

            "action_mask":
                self.action_masks().copy(),
        }

        return (
            self._get_observation(),
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

        mask = (
            self.action_masks()
        )

        if not bool(
            mask[action]
        ):

            raise ValueError(
                "Masked action selected: "
                f"{action}"
            )

        waiting_before = (
            self.kernel
            .accumulated_priority_waiting_cost
        )

        distance_before = (
            self._total_travel_distance()
        )

        failed_before = (
            self._failed_task_count()
        )

        selected_robot = (
            self.robot_ids[
                action
            ]
        )

        decision_info = (
            self.kernel
            .apply_current_action(
                robot_id=(
                    selected_robot
                ),
                robot_ids=(
                    self.robot_ids
                ),
            )
        )

        reassignment_delta = int(
            decision_info[
                "decision_type"
            ]
            ==
            DECISION_REASSIGNMENT
            and
            decision_info[
                "changed"
            ]
        )

        self.kernel.prepare_next_decision(
            self.robot_ids
        )

        waiting_after = (
            self.kernel
            .accumulated_priority_waiting_cost
        )

        distance_after = (
            self._total_travel_distance()
        )

        failed_after = (
            self._failed_task_count()
        )

        reward_breakdown = (
            calculate_system_reward(
                weighted_waiting_delta=(
                    waiting_after
                    -
                    waiting_before
                ),
                travel_distance_delta=(
                    distance_after
                    -
                    distance_before
                ),
                failed_task_delta=(
                    failed_after
                    -
                    failed_before
                ),
                reassignment_delta=(
                    reassignment_delta
                ),
                config=(
                    self.reward_config
                ),
            )
        )

        terminated = bool(
            self.kernel.finished
        )

        truncated = False

        info = {
            **decision_info,

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

            "next_decision_type":
                self.kernel
                .current_decision_type,

            "next_current_robot":
                self.kernel
                .current_previous_robot,

            "action_mask":
                self.action_masks().copy(),

            "system_weighted_waiting_delta":
                reward_breakdown
                .weighted_waiting_delta,

            "system_distance_delta":
                reward_breakdown
                .travel_distance_delta,

            "system_failed_delta":
                reward_breakdown
                .failed_task_delta,

            "system_waiting_cost":
                reward_breakdown
                .waiting_cost,

            "system_distance_cost":
                reward_breakdown
                .distance_cost,

            "system_failure_cost":
                reward_breakdown
                .failure_cost,

            "system_reassignment_delta":
                reward_breakdown
                .reassignment_delta,

            "system_reassignment_cost":
                reward_breakdown
                .reassignment_cost,
        }

        return (
            self._get_observation(),
            float(
                reward_breakdown.reward
            ),
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
