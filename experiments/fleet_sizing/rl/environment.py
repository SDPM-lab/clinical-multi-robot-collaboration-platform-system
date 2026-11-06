from __future__ import annotations

import heapq
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from experiments.fleet_sizing.baseline.common import (
    apply_battery_queue_repair,
    evaluate_feasible_placement_candidates,
    get_queue_sort_key,
    release_robot_future_queue_for_reassignment,
    repair_projected_queue_for_battery,
)

from experiments.fleet_sizing.rl.action_mask import (
    ActionMaskBuilder,
)

from experiments.fleet_sizing.rl.observation import (
    BATTERY_LAYOUT,
    DEFAULT_LAYOUT,
    ObservationEncoder,
    calculate_load_imbalance,
)

from experiments.fleet_sizing.rl.reward import (
    DEFAULT_REWARD_CONFIG,
    RewardConfig,
    calculate_assignment_reward,
    calculate_waiting_reward,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
    _AssignmentContext,
)

from experiments.fleet_sizing.task_generator import (
    NormalTaskGenerator,
)


DEFAULT_FLEET_CONFIGURATION = (
    2,  # Clean
    2,  # Medical
    3,  # Ward
)

DEFAULT_WORKLOAD_MULTIPLIER = 4.0


class _UnusedScheduler:
    """
    Placeholder required by SchedulingSimulator.__init__.

    The RL environment intercepts arrival events before
    SchedulingSimulator._handle_arrival() is called, so this
    scheduler must never make an assignment decision.
    """

    NAME = "rl_environment_placeholder"

    def decide(
        self,
        *args,
        **kwargs,
    ):
        raise RuntimeError(
            "_UnusedScheduler.decide() must never be called "
            "inside HospitalSchedulingEnv."
        )


class HospitalSchedulingEnv(
    gym.Env
):
    """
    Gymnasium environment for centralized heterogeneous
    hospital robot task assignment.

    One RL step corresponds to one incoming task.

    Decision flow
    -------------
    reset()
        -> advance simulator to first arrival
        -> expose scheduler-visible observation

    step(action)
        -> assign current incoming task to selected robot
        -> advance completion events
        -> stop at next arrival
        -> return next observation and reward

    Important
    ---------
    Realized service time and actual completion times remain
    simulator-only ground truth. They are never included in
    the observation or action mask.
    """

    metadata = {
        "render_modes": [],
    }

    def __init__(
        self,
        *,
        seed: int = 3001,
        fleet_configuration: tuple[
            int,
            int,
            int,
        ] = DEFAULT_FLEET_CONFIGURATION,
        workload_multiplier: float = (
            DEFAULT_WORKLOAD_MULTIPLIER
        ),
        reward_config: RewardConfig = (
            DEFAULT_REWARD_CONFIG
        ),
        episode_seeds: tuple[int, ...] | None = None,
        enable_battery_model: bool = False,
    ) -> None:

        super().__init__()

        if len(
            fleet_configuration
        ) != 3:
            raise ValueError(
                "fleet_configuration must be "
                "(clean, medical, ward)"
            )

        if any(
            count < 0
            for count
            in fleet_configuration
        ):
            raise ValueError(
                "fleet robot counts must be non-negative"
            )

        robot_count = sum(
            fleet_configuration
        )

        # Current ObservationEncoder is intentionally frozen
        # for the reference seven-robot fleet.
        if robot_count != 7:
            raise ValueError(
                "HospitalSchedulingEnv currently requires "
                "the reference 7-robot fleet."
            )

        if (
            workload_multiplier
            <= 0.0
        ):
            raise ValueError(
                "workload_multiplier must be > 0"
            )

        self.base_seed = int(
            seed
        )

        self.fleet_configuration = tuple(
            int(value)
            for value
            in fleet_configuration
        )

        self.workload_multiplier = float(
            workload_multiplier
        )

        self.reward_config = (
            reward_config
        )

        self.enable_battery_model = bool(
            enable_battery_model
        )

        if (
            episode_seeds
            is not None
        ):

            if not episode_seeds:

                raise ValueError(
                    "episode_seeds cannot be empty"
                )

            self.episode_seeds = tuple(
                int(value)
                for value
                in episode_seeds
            )

        else:

            self.episode_seeds = None

        self.action_space = (
            spaces.Discrete(
                robot_count
            )
        )

        self.observation_layout = (
            BATTERY_LAYOUT
            if self.enable_battery_model
            else DEFAULT_LAYOUT
        )

        self.observation_space = (
            spaces.Box(
                low=0.0,
                high=1.0,
                shape=(
                    self.observation_layout
                    .total_size,
                ),
                dtype=np.float32,
            )
        )

        self.simulator: (
            SchedulingSimulator
            | None
        ) = None

        self.observation_encoder: (
            ObservationEncoder
            | None
        ) = None

        self.mask_builder: (
            ActionMaskBuilder
            | None
        ) = None

        self.current_task_id: (
            str
            | None
        ) = None

        # Tasks released from an existing robot queue because
        # battery feasibility changed.
        #
        # These are NOT new arrivals.
        #
        # Their original arrival_time_s is preserved.
        self.reassignment_task_ids: list[
            str
        ] = []

        self.current_time_s = 0.0

        self.episode_seed = (
            self.base_seed
        )

        self.episode_index = -1

        self.decision_count = 0

        self._terminated = True

    # ========================================================
    # Reset
    # ========================================================

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[
            str,
            Any,
        ] | None = None,
    ) -> tuple[
        np.ndarray,
        dict[
            str,
            Any,
        ],
    ]:

        super().reset(
            seed=seed
        )

        self.episode_index += 1

        if seed is not None:

            self.episode_seed = int(
                seed
            )

        elif (
            self.episode_seeds
            is not None
        ):

            seed_index = (
                self.episode_index
                % len(
                    self.episode_seeds
                )
            )

            self.episode_seed = (
                self.episode_seeds[
                    seed_index
                ]
            )

        else:

            self.episode_seed = (
                self.base_seed
                + self.episode_index
            )

        self.simulator = (
            SchedulingSimulator(
                fleet_configuration=(
                    self.fleet_configuration
                ),
                seed=(
                    self.episode_seed
                ),
                scheduler=(
                    _UnusedScheduler()
                ),
                workload_multiplier=(
                    self.workload_multiplier
                ),
                enable_battery_model=(
                    self.enable_battery_model
                ),
            )
        )

        robot_ids = tuple(
            robot.robot_id
            for robot
            in self.simulator.robots
        )

        self.observation_encoder = (
            ObservationEncoder(
                robot_ids=(
                    robot_ids
                ),
                layout=(
                    self.observation_layout
                ),
            )
        )

        self.mask_builder = (
            ActionMaskBuilder(
                robot_ids=robot_ids
            )
        )

        self.current_task_id = None

        self.reassignment_task_ids = []

        self.current_time_s = 0.0

        self.decision_count = 0

        self._terminated = False

        self._initialize_tasks()

        self._advance_until_next_arrival()

        observation = (
            self._get_observation()
        )

        info = (
            self._build_info()
        )

        return (
            observation,
            info,
        )

    # ========================================================
    # Step
    # ========================================================

    def step(
        self,
        action: int,
    ) -> tuple[
        np.ndarray,
        float,
        bool,
        bool,
        dict[
            str,
            Any,
        ],
    ]:

        self._require_initialized()

        if self._terminated:

            raise RuntimeError(
                "step() called after episode termination. "
                "Call reset() first."
            )

        task = (
            self._current_task()
        )

        action = int(
            action
        )

        assert (
            self.mask_builder
            is not None
        )

        assert (
            self.simulator
            is not None
        )

        if not (
            self.mask_builder.validate_action(
                action=action,
                task=task,
                robots=(
                    self.simulator
                    .robots
                ),
                enable_battery_model=(
                    self.enable_battery_model
                ),
                tasks_by_id=(
                    self.simulator
                    .tasks_by_id
                ),
                current_time_s=(
                    self.current_time_s
                ),
                travel_time_fn=(
                    self.simulator
                    ._travel_time
                ),
            )
        ):

            raise ValueError(
                f"Action {action} is infeasible "
                f"for task {task.task_id}"
            )

        robot_id = (
            self.mask_builder
            .robot_id_from_action(
                action
            )
        )

        robot = (
            self.simulator
            ._get_robot(
                robot_id
            )
        )

        # ----------------------------------------------------
        # Duration-free candidate evaluation.
        #
        # Same information boundary as the baseline schedulers.
        # ----------------------------------------------------

        evaluations = (
            evaluate_feasible_placement_candidates(
                robots=(
                    self.simulator
                    .robots
                ),
                task=task,
                tasks_by_id=(
                    self.simulator
                    .tasks_by_id
                ),
                current_time_s=(
                    self.current_time_s
                ),
                travel_time_fn=(
                    self.simulator
                    ._travel_time
                ),
            )
        )

        selected_evaluation = next(
            (
                evaluation
                for evaluation
                in evaluations
                if (
                    evaluation.robot_id
                    == robot_id
                )
            ),
            None,
        )

        if (
            selected_evaluation
            is None
        ):

            raise RuntimeError(
                "Feasible action has no placement "
                f"evaluation: {robot_id}"
            )

        # Remember how many assignment records already existed.
        # Any new record created during this transition
        # corresponds to a task that actually started execution.
        assignment_record_start = len(
            self.simulator.assignments
        )

        robot_was_busy = (
            robot.current_task_id
            is not None
        )

        # ----------------------------------------------------
        # Battery-aware future queue repair.
        #
        # 1. Priority + Aging has already produced the
        #    projected future queue.
        #
        # 2. Battery feasibility is propagated through that
        #    queue using navigation energy only.
        #
        # 3. Tasks that no longer fit within the battery
        #    reserve are released for reassignment.
        #
        # Active task is never preempted.
        # ----------------------------------------------------

        if self.enable_battery_model:

            battery_repair = (
                repair_projected_queue_for_battery(
                    robot=robot,

                    queue_projection=(
                        selected_evaluation
                        .queue_projection
                    ),

                    tasks_by_id=(
                        self.simulator
                        .tasks_by_id
                    ),

                    travel_time_fn=(
                        self.simulator
                        ._travel_time
                    ),
                )
            )


            released_task_ids = (
                apply_battery_queue_repair(
                    robot=robot,

                    repair=(
                        battery_repair
                    ),

                    tasks_by_id=(
                        self.simulator
                        .tasks_by_id
                    ),
                )
            )


            for released_task_id in (
                released_task_ids
            ):

                self._enqueue_reassignment(
                    released_task_id
                )


            # ----------------------------------------------------
            # The selected incoming task itself must remain
            # feasible on the chosen robot.
            #
            # Until battery-aware action masking is implemented,
            # reject an action whose selected task cannot survive
            # battery queue repair.
            # ----------------------------------------------------

            if (
                task.task_id
                in released_task_ids
            ):

                raise RuntimeError(
                    "Selected action is battery-infeasible: "
                    f"task {task.task_id} cannot remain on "
                    f"robot {robot.robot_id}."
                )

        else:

            # Original Battery-disabled v1 behavior.
            robot.queued_task_ids = [
                projected.task_id
                for projected
                in (
                    selected_evaluation
                    .queue_projection
                    .projected_tasks
                )
            ]

            battery_repair = None
            released_task_ids = ()


        # ----------------------------------------------------
        # Assignment state
        # ----------------------------------------------------

        task.assigned_robot = (
            robot.robot_id
        )

        task.assignment_time_s = (
            self.current_time_s
        )

        task.status = "queued"

        if (
            task.task_id
            not in robot.assigned_task_ids
        ):

            robot.assigned_task_ids.append(
                task.task_id
            )

        self.simulator._assignment_context[
            task.task_id
        ] = _AssignmentContext(
            assignment_time_s=(
                self.current_time_s
            ),
            robot_was_busy=(
                robot_was_busy
            ),
        )

        # ----------------------------------------------------
        # If idle, begin execution immediately using the
        # simulator's ORIGINAL execution logic.
        # ----------------------------------------------------

        if (
            robot.current_task_id
            is None
        ):

            self.simulator._start_next_task(
                robot=robot,
                current_time_s=(
                    self.current_time_s
                ),
            )

        # ----------------------------------------------------
        # Assignment-time shaping reward
        # ----------------------------------------------------

        post_assignment_imbalance = (
            calculate_load_imbalance(
                self.simulator.robots
            )
        )

        assignment_reward = (
            calculate_assignment_reward(
                projected_approach_time_s=(
                    selected_evaluation
                    .projected_approach_time_s
                ),
                tasks_ahead_count=(
                    selected_evaluation
                    .tasks_ahead_count
                ),
                post_assignment_load_imbalance=(
                    post_assignment_imbalance
                ),
                config=(
                    self.reward_config
                ),
            )
        )

        selected_task_id = (
            task.task_id
        )

        selected_priority = (
            task.priority
        )

        self.decision_count += 1

        # Current decision has been consumed.
        self.current_task_id = None

        # ----------------------------------------------------
        # Advance environment until next task arrival.
        #
        # Completion events may cause queued tasks to actually
        # start. Those realized waits are rewarded only AFTER
        # they have happened.
        # ----------------------------------------------------

        self._advance_until_next_arrival()

        # ----------------------------------------------------
        # Realized waiting rewards
        # ----------------------------------------------------

        new_records = (
            self.simulator
            .assignments[
                assignment_record_start:
            ]
        )

        waiting_reward_total = 0.0

        waiting_details: list[
            dict[
                str,
                Any,
            ]
        ] = []

        for record in new_records:

            started_task = (
                self.simulator
                .tasks_by_id[
                    record.task_id
                ]
            )

            waiting_reward = (
                calculate_waiting_reward(
                    waiting_time_s=(
                        record.queue_delay_s
                    ),
                    priority=(
                        started_task.priority
                    ),
                    config=(
                        self.reward_config
                    ),
                )
            )

            waiting_reward_total += (
                waiting_reward
                .total_reward
            )

            waiting_details.append(
                {
                    "task_id":
                    record.task_id,

                    "waiting_time_s":
                    record.queue_delay_s,

                    "priority":
                    started_task.priority,

                    "reward":
                    waiting_reward
                    .total_reward,
                }
            )

        total_reward = (
            assignment_reward
            .total_reward
            + waiting_reward_total
        )

        observation = (
            self._get_observation()
        )

        info = (
            self._build_info()
        )

        info.update(
            {
                "selected_task_id":
                selected_task_id,

                "selected_task_priority":
                selected_priority,

                "selected_robot_id":
                robot_id,

                "assignment_reward":
                assignment_reward
                .total_reward,

                "waiting_reward":
                waiting_reward_total,

                "reward":
                total_reward,

                "projected_approach_time_s":
                selected_evaluation
                .projected_approach_time_s,

                "tasks_ahead_count":
                selected_evaluation
                .tasks_ahead_count,

                "post_assignment_load_imbalance":
                post_assignment_imbalance,

                "realized_waiting_events":
                waiting_details,

                "battery_initial_soc":
                (
                    battery_repair.initial_soc
                    if battery_repair is not None
                    else None
                ),

                "battery_final_projected_soc":
                (
                    battery_repair.final_soc
                    if battery_repair is not None
                    else None
                ),

                "battery_kept_task_ids":
                (
                    list(
                        battery_repair.kept_task_ids
                    )
                    if battery_repair is not None
                    else []
                ),

                "battery_released_task_ids":
                (
                    list(
                        battery_repair.released_task_ids
                    )
                    if battery_repair is not None
                    else []
                ),

                "reassignment_queue":
                list(
                    self.reassignment_task_ids
                ),
            }
        )

        return (
            observation,
            float(
                total_reward
            ),
            bool(
                self._terminated
            ),
            False,
            info,
        )

    # ========================================================
    # MaskablePPO API
    # ========================================================

    def action_masks(
        self,
    ) -> np.ndarray:

        self._require_initialized()

        assert (
            self.mask_builder
            is not None
        )

        assert (
            self.simulator
            is not None
        )

        if (
            self._terminated
            or self.current_task_id
            is None
        ):

            # MaskablePPO should never request another action
            # after termination, but return a valid shape
            # defensively.
            return np.ones(
                self.action_space.n,
                dtype=np.bool_,
            )

        return (
            self.mask_builder
            .build(
                task=(
                    self._current_task()
                ),
                robots=(
                    self.simulator
                    .robots
                ),
                enable_battery_model=(
                    self.enable_battery_model
                ),
                tasks_by_id=(
                    self.simulator
                    .tasks_by_id
                ),
                current_time_s=(
                    self.current_time_s
                ),
                travel_time_fn=(
                    self.simulator
                    ._travel_time
                ),
            )
        )

    # ========================================================
    # Initialization
    # ========================================================

    def _initialize_tasks(
        self,
    ) -> None:

        assert (
            self.simulator
            is not None
        )

        generated_tasks = (
            NormalTaskGenerator(
                seed=(
                    self.episode_seed
                ),
                workload_multiplier=(
                    self.workload_multiplier
                ),
            ).generate()
        )

        self.simulator.tasks = [
            self.simulator._convert_task(
                task
            )
            for task
            in generated_tasks
        ]

        self.simulator.tasks.sort(
            key=lambda task:
                (
                    task.arrival_time_s,
                    task.task_id,
                )
        )

        self.simulator.tasks_by_id = {
            task.task_id:
            task
            for task
            in self.simulator.tasks
        }

        for task in (
            self.simulator.tasks
        ):

            self.simulator._push_event(
                time_s=(
                    task.arrival_time_s
                ),
                event_priority=(
                    self.simulator
                    .EVENT_ARRIVAL
                ),
                event_type="arrival",
                payload=(
                    task.task_id
                ),
            )

    # ========================================================
    # Event Advancement
    # ========================================================

    def _advance_until_next_arrival(
        self,
    ) -> None:

        assert (
            self.simulator
            is not None
        )

        # ----------------------------------------------------
        # Battery-triggered reassignment has priority over
        # future external arrivals.
        #
        # These tasks have already arrived previously, so they
        # must be reconsidered before advancing simulation time
        # to a later external arrival.
        # ----------------------------------------------------

        if (
            self._activate_next_reassignment()
        ):

            return

        # ----------------------------------------------------
        # Otherwise advance the simulator event queue.
        # ----------------------------------------------------

        while (
            self.simulator
            ._event_queue
        ):

            (
                current_time_s,
                _,
                _,
                event_type,
                payload,
            ) = heapq.heappop(
                self.simulator
                ._event_queue
            )

            self.current_time_s = float(
                current_time_s
            )

            if (
                event_type
                == "arrival"
            ):

                task_id = str(
                    payload
                )

                task = (
                    self.simulator
                    .tasks_by_id[
                        task_id
                    ]
                )

                # --------------------------------------------
                # Expose the arrival to PPO only when at least
                # one legal action currently exists.
                # --------------------------------------------

                if (
                    self._task_has_feasible_action(
                        task
                    )
                ):

                    self.current_task_id = (
                        task_id
                    )

                    self._terminated = False

                    # PPO must choose the assignment.
                    return

                # --------------------------------------------
                # Temporarily unassignable arrival.
                #
                # The task has already arrived, so preserve its
                # original arrival_time_s and wait for a later
                # robot-state-changing event.
                # --------------------------------------------

                self._enqueue_reassignment(
                    task_id
                )

                self.current_task_id = None

                # Do NOT return.
                #
                # Continue advancing time until e.g.
                # charging_complete makes a robot feasible.
                continue

            if (
                event_type
                == "completion"
            ):

                (
                    robot_id,
                    task_id,
                ) = payload

                self.simulator._handle_completion(
                    robot_id=robot_id,
                    task_id=task_id,
                    current_time_s=(
                        self.current_time_s
                    ),
                )

                # --------------------------------------------
                # Low-battery queue release
                #
                # If completion triggered a return-to-charge
                # or charging state, every future queued task
                # must be released for a new RL decision.
                #
                # Active task has already completed and is
                # therefore never affected here.
                # --------------------------------------------

                robot = (
                    self.simulator._get_robot(
                        robot_id
                    )
                )

                if (
                    self.enable_battery_model
                    and robot.status
                    in {
                        "returning_to_charge",
                        "charging",
                    }
                    and robot.queued_task_ids
                ):

                    released_task_ids = (
                        release_robot_future_queue_for_reassignment(
                            robot=robot,
                            tasks_by_id=(
                                self.simulator
                                .tasks_by_id
                            ),
                        )
                    )

                    for released_task_id in (
                        released_task_ids
                    ):

                        self._enqueue_reassignment(
                            released_task_id
                        )

                # Released tasks have already arrived before,
                # so expose them before advancing simulation
                # time to the next external arrival.
                if (
                    self._activate_next_reassignment()
                ):

                    return

                continue

            if (
                event_type
                == "charging_complete"
            ):

                self.simulator._handle_charging_complete(
                    robot_id=str(
                        payload
                    ),
                    current_time_s=(
                        self.current_time_s
                    ),
                )

                if (
                    self._activate_next_reassignment()
                ):
                    return

                continue

            if (
                event_type
                == "return_to_charge_complete"
            ):

                self.simulator._handle_return_to_charge_complete(
                    robot_id=str(
                        payload
                    ),
                    current_time_s=(
                        self.current_time_s
                    ),
                )

                if (
                    self._activate_next_reassignment()
                ):
                    return

                continue

            raise RuntimeError(
                "Unknown event type: "
                f"{event_type}"
            )

        # ----------------------------------------------------
        # No simulator events remain.
        #
        # Check reassignment one final time defensively.
        # ----------------------------------------------------

        if (
            self._activate_next_reassignment()
        ):

            return

        self.current_task_id = None

        self._terminated = True

    # ========================================================
    # Observation
    # ========================================================

    def _get_observation(
        self,
    ) -> np.ndarray:

        self._require_initialized()

        assert (
            self.observation_encoder
            is not None
        )

        assert (
            self.simulator
            is not None
        )

        if (
            self._terminated
            or self.current_task_id
            is None
        ):

            return np.zeros(
                self.observation_space.shape,
                dtype=np.float32,
            )

        return (
            self.observation_encoder
            .encode(
                task=(
                    self._current_task()
                ),
                robots=(
                    self.simulator
                    .robots
                ),
                tasks_by_id=(
                    self.simulator
                    .tasks_by_id
                ),
                current_time_s=(
                    self.current_time_s
                ),
                travel_time_fn=(
                    self.simulator
                    ._travel_time
                ),
            )
        )

    # ========================================================
    # Helpers
    # ========================================================

    def _task_has_feasible_action(
        self,
        task,
    ) -> bool:
        """
        Return True only when the task currently has at least
        one legal robot action.

        This is used before exposing a task as an RL decision,
        preventing MaskablePPO from receiving an all-False mask.
        """

        self._require_initialized()

        assert (
            self.simulator
            is not None
        )

        assert (
            self.mask_builder
            is not None
        )

        mask = (
            self.mask_builder.build(
                task=task,
                robots=(
                    self.simulator
                    .robots
                ),
                enable_battery_model=(
                    self.enable_battery_model
                ),
                tasks_by_id=(
                    self.simulator
                    .tasks_by_id
                ),
                current_time_s=(
                    self.current_time_s
                ),
                travel_time_fn=(
                    self.simulator
                    ._travel_time
                ),
            )
        )

        return bool(
            np.any(
                mask
            )
        )

    def _enqueue_reassignment(
        self,
        task_id: str,
    ) -> None:
        """
        Queue one already-arrived task for a new scheduling
        decision.

        The task keeps its original arrival_time_s.
        """

        self._require_initialized()

        assert (
            self.simulator
            is not None
        )

        task_id = str(
            task_id
        )

        if (
            task_id
            not in self.simulator.tasks_by_id
        ):

            raise KeyError(
                f"Unknown reassignment task: "
                f"{task_id}"
            )

        task = (
            self.simulator
            .tasks_by_id[
                task_id
            ]
        )

        if task.status != "waiting":

            raise ValueError(
                f"Reassignment task "
                f"{task_id} must be waiting, "
                f"got status={task.status!r}"
            )

        if (
            task.assigned_robot
            is not None
        ):

            raise ValueError(
                f"Reassignment task "
                f"{task_id} is still assigned "
                f"to {task.assigned_robot}"
            )

        if (
            task_id
            == self.current_task_id
        ):

            return

        if (
            task_id
            in self.reassignment_task_ids
        ):

            return

        self.reassignment_task_ids.append(
            task_id
        )


    def _activate_next_reassignment(
        self,
    ) -> bool:
        """
        Make the next released task the current RL decision.

        Returns True if a reassignment task was activated.
        """

        if not self.reassignment_task_ids:

            return False

        assert (
            self.simulator
            is not None
        )

        # ----------------------------------------------------
        # Use the same Priority + Aging ordering principle.
        #
        # Important:
        # original arrival_time_s is retained.
        # ----------------------------------------------------

        candidate_tasks = [
            self.simulator.tasks_by_id[
                task_id
            ]
            for task_id
            in self.reassignment_task_ids
        ]

        candidate_tasks.sort(
            key=lambda task: (
                get_queue_sort_key(
                    task=task,
                    current_time_s=(
                        self.current_time_s
                    ),
                )
            )
        )

        selected_task = None

        for candidate_task in (
            candidate_tasks
        ):

            if (
                self._task_has_feasible_action(
                    candidate_task
                )
            ):

                selected_task = (
                    candidate_task
                )

                break

        # No released / waiting task is currently assignable.
        #
        # Keep all of them in reassignment_task_ids and allow
        # simulation time to advance until a robot state changes,
        # e.g. charging_complete.
        if selected_task is None:

            return False

        self.reassignment_task_ids.remove(
            selected_task.task_id
        )

        self.current_task_id = (
            selected_task.task_id
        )

        self._terminated = False

        return True


    def _current_task(
        self,
    ):

        self._require_initialized()

        assert (
            self.simulator
            is not None
        )

        if (
            self.current_task_id
            is None
        ):

            raise RuntimeError(
                "There is no pending arrival task."
            )

        return (
            self.simulator
            .tasks_by_id[
                self.current_task_id
            ]
        )

    def _build_info(
        self,
    ) -> dict[
        str,
        Any,
    ]:

        mask = (
            self.action_masks()
        )

        return {
            "episode_seed":
            self.episode_seed,

            "decision_count":
            self.decision_count,

            "current_time_s":
            self.current_time_s,

            "current_task_id":
            self.current_task_id,

            "terminated":
            self._terminated,

            "action_mask":
            mask.copy(),
        }

    def _require_initialized(
        self,
    ) -> None:

        if (
            self.simulator
            is None
        ):

            raise RuntimeError(
                "Environment has not been reset."
            )
