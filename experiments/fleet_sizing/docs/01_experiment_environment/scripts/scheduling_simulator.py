from __future__ import annotations

import heapq

from dataclasses import dataclass
from itertools import count
from typing import Any, Dict, List, Optional, Tuple

from experiments.fleet_sizing.baseline.common import (
    build_pending_queue,
    order_waiting_tasks,
)

from experiments.fleet_sizing.config import (
    BATTERY_INITIAL_SOC,
    BATTERY_TRAVEL_DRAIN_PER_SECOND,
    BATTERY_CHARGE_RATE_PER_SECOND,
    BATTERY_CHARGE_TRIGGER_SOC,
    BATTERY_RESUME_SOC,
    CHARGING_WAYPOINT,
    ENABLE_BATTERY_MODEL,
    ROBOT_CAPABILITIES,
    ROBOT_TYPE_CLEAN,
    ROBOT_TYPE_MEDICAL,
    ROBOT_TYPE_WARD,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)

from experiments.fleet_sizing.task_generator import (
    GeneratedTask,
    NormalTaskGenerator,
)

from experiments.fleet_sizing.travel_time import (
    TravelTimeModel,
)


# ============================================================
# Assignment Record
# ============================================================


@dataclass(frozen=True)
class SchedulingAssignmentRecord:
    task_id: str
    robot_id: str

    task_arrival_time_s: float
    assignment_time_s: float

    robot_was_busy: bool
    queue_delay_s: float

    assignment_origin: str
    task_source: str
    task_destination: str

    approach_time_s: float
    task_travel_time_s: float
    service_time_s: float

    dispatch_start_time_s: float
    source_arrival_time_s: float
    completion_time_s: float


# ============================================================
# Simulation Result
# ============================================================


@dataclass
class SchedulingSimulationResult:
    seed: int

    fleet_configuration: Tuple[
        int,
        int,
        int,
    ]

    workload_multiplier: float

    scheduler_name: str

    tasks: List[
        TaskState
    ]

    robots: List[
        RobotState
    ]

    assignments: List[
        SchedulingAssignmentRecord
    ]


# ============================================================
# Internal Assignment Context
# ============================================================


@dataclass(frozen=True)
class _AssignmentContext:
    assignment_time_s: float
    robot_was_busy: bool


# ============================================================
# Scheduling Simulator
# ============================================================


class SchedulingSimulator:
    """
    Event-driven simulator for scheduler comparison.

    Important separation
    --------------------
    Scheduler-visible information:
        - current robot location
        - active task / active destination
        - queued task IDs
        - robot capability / status
        - task type / source / destination / priority
        - route travel-time estimate

    Simulator-only ground truth:
        - realized TaskState.service_time_s
        - actual active-task completion time
        - future execution timing

    Therefore scheduler decisions do not receive future
    realized task duration information.
    """

    EVENT_COMPLETION = 0
    EVENT_RETURN_TO_CHARGE_COMPLETE = 1
    EVENT_CHARGING_COMPLETE = 2
    EVENT_ARRIVAL = 3

    def __init__(
        self,
        fleet_configuration,
        seed,
        scheduler,
        workload_multiplier: float = 1.0,
        enable_battery_model: bool = ENABLE_BATTERY_MODEL,
    ) -> None:

        self.fleet_configuration = (
            fleet_configuration
        )

        self.seed = seed

        self.scheduler = scheduler

        self.workload_multiplier = float(
            workload_multiplier
        )

        self.enable_battery_model = bool(
            enable_battery_model
        )

        self.travel_model = (
            TravelTimeModel()
        )

        self.robots = self._build_fleet(
            fleet_configuration
        )

        self.tasks: List[
            TaskState
        ] = []

        self.reassignment_task_ids: List[
            str
        ] = []

        self.tasks_by_id: Dict[
            str,
            TaskState
        ] = {}

        self.assignments: List[
            SchedulingAssignmentRecord
        ] = []

        self._assignment_context: Dict[
            str,
            _AssignmentContext
        ] = {}

        self._event_queue: list[
            tuple[
                float,
                int,
                int,
                str,
                Any,
            ]
        ] = []

        self._event_counter = count()

    # ========================================================
    # Fleet Initialization
    # ========================================================

    def _build_fleet(
        self,
        configuration: Tuple[
            int,
            int,
            int,
        ],
    ) -> List[
        RobotState
    ]:

        (
            clean_count,
            medical_count,
            ward_count,
        ) = configuration

        robots: List[
            RobotState
        ] = []

        robots.extend(
            self._create_robots(
                prefix="C",
                robot_type=(
                    ROBOT_TYPE_CLEAN
                ),
                count=clean_count,
            )
        )

        robots.extend(
            self._create_robots(
                prefix="M",
                robot_type=(
                    ROBOT_TYPE_MEDICAL
                ),
                count=medical_count,
            )
        )

        robots.extend(
            self._create_robots(
                prefix="W",
                robot_type=(
                    ROBOT_TYPE_WARD
                ),
                count=ward_count,
            )
        )

        return robots

    def _create_robots(
        self,
        prefix: str,
        robot_type: str,
        count: int,
    ) -> List[
        RobotState
    ]:

        capabilities = (
            ROBOT_CAPABILITIES[
                robot_type
            ]
        )

        robots: List[
            RobotState
        ] = []

        for index in range(
            1,
            count + 1,
        ):

            robot = RobotState(
                robot_id=(
                    f"{prefix}{index:02d}"
                ),

                robot_type=(
                    robot_type
                ),

                capabilities=sorted(
                    capabilities
                ),

                current_location=(
                    CHARGING_WAYPOINT
                ),

                status="idle",

                available_time_s=0.0,

                future_location=(
                    CHARGING_WAYPOINT
                ),

                battery_soc=(
                    BATTERY_INITIAL_SOC
                ),
            )

            robots.append(
                robot
            )

        return robots

    # ========================================================
    # Public Run
    # ========================================================

    def run(
        self,
    ) -> SchedulingSimulationResult:

        generated_tasks = (
            NormalTaskGenerator(
                seed=self.seed,
                workload_multiplier=(
                    self.workload_multiplier
                ),
            ).generate()
        )

        self.tasks = [
            self._convert_task(task)
            for task
            in generated_tasks
        ]

        self.tasks.sort(
            key=lambda task:
                (
                    task.arrival_time_s,
                    task.task_id,
                )
        )

        self.tasks_by_id = {
            task.task_id: task
            for task
            in self.tasks
        }

        # ----------------------------------------------------
        # Add all arrivals to event queue.
        # ----------------------------------------------------

        for task in self.tasks:

            self._push_event(
                time_s=(
                    task.arrival_time_s
                ),

                event_priority=(
                    self.EVENT_ARRIVAL
                ),

                event_type="arrival",

                payload=(
                    task.task_id
                ),
            )

        # ----------------------------------------------------
        # Event loop
        # ----------------------------------------------------

        while self._event_queue:

            (
                current_time_s,
                _,
                _,
                event_type,
                payload,
            ) = heapq.heappop(
                self._event_queue
            )

            if event_type == "arrival":

                self._handle_arrival(
                    task_id=payload,
                    current_time_s=(
                        current_time_s
                    ),
                )

            elif event_type == "completion":

                (
                    robot_id,
                    task_id,
                ) = payload

                self._handle_completion(
                    robot_id=robot_id,
                    task_id=task_id,
                    current_time_s=(
                        current_time_s
                    ),
                )

                while self._activate_next_reassignment(
                    current_time_s=current_time_s
                ):
                    pass

            elif (
                event_type
                == "charging_complete"
            ):

                self._handle_charging_complete(
                    robot_id=payload,
                    current_time_s=(
                        current_time_s
                    ),
                )

                while self._activate_next_reassignment(
                    current_time_s=current_time_s
                ):
                    pass

            elif (
                event_type
                == "return_to_charge_complete"
            ):

                self._handle_return_to_charge_complete(
                    robot_id=payload,
                    current_time_s=(
                        current_time_s
                    ),
                )

                while self._activate_next_reassignment(
                    current_time_s=current_time_s
                ):
                    pass

            else:

                raise RuntimeError(
                    "Unknown event type: "
                    f"{event_type}"
                )

        self._finalize_robot_states()

        return (
            SchedulingSimulationResult(
                seed=self.seed,

                fleet_configuration=(
                    self.fleet_configuration
                ),

                workload_multiplier=(
                    self.workload_multiplier
                ),

                scheduler_name=(
                    getattr(
                        self.scheduler,
                        "NAME",
                        type(
                            self.scheduler
                        ).__name__,
                    )
                ),

                tasks=self.tasks,

                robots=self.robots,

                assignments=(
                    self.assignments
                ),
            )
        )

    # ========================================================
    # Event Queue
    # ========================================================

    def _push_event(
        self,
        time_s: float,
        event_priority: int,
        event_type: str,
        payload: Any,
    ) -> None:

        heapq.heappush(
            self._event_queue,
            (
                float(
                    time_s
                ),

                event_priority,

                next(
                    self._event_counter
                ),

                event_type,

                payload,
            ),
        )

    # ========================================================
    # Task Conversion
    # ========================================================

    @staticmethod
    def _convert_task(
        task: GeneratedTask,
    ) -> TaskState:

        return TaskState(
            task_id=(
                task.task_id
            ),

            task_type=(
                task.task_type
            ),

            source=(
                task.source
            ),

            destination=(
                task.destination
            ),

            priority=(
                task.priority
            ),

            arrival_time_s=(
                task.arrival_time_s
            ),

            service_time_s=(
                task.service_time_s
            ),
        )

    # ========================================================
    # Travel-Time Adapter
    # ========================================================

    def _travel_time(
        self,
        source: str,
        destination: str,
    ) -> float:

        return float(
            self.travel_model
            .get_travel_time_mean(
                source,
                destination,
            )
        )


    def _navigation_energy_soc(
        self,
        travel_time_s: float,
    ) -> float:
        """
        Convert observable navigation travel time into
        normalized battery consumption.

        This does NOT include service-time energy.
        """

        travel_time_s = float(
            travel_time_s
        )

        if travel_time_s < 0.0:

            raise ValueError(
                "travel_time_s must be non-negative"
            )

        return (
            travel_time_s
            * BATTERY_TRAVEL_DRAIN_PER_SECOND
        )


    # ========================================================
    # Arrival Event
    # ========================================================

    def _handle_arrival(
        self,
        task_id: str,
        current_time_s: float,
    ) -> None:

        task = (
            self.tasks_by_id[
                task_id
            ]
        )

        # ----------------------------------------------------
        # Scheduler sees current state and decides assignment.
        #
        # It is allowed to reorder future queued tasks.
        # It is NOT allowed to use realized service time.
        # ----------------------------------------------------

        decision = (
            self.scheduler.decide(
                robots=self.robots,
                task=task,
                tasks_by_id=(
                    self.tasks_by_id
                ),
                current_time_s=(
                    current_time_s
                ),
                travel_time_fn=(
                    self._travel_time
                ),
                commit_queue=True,
                enable_battery_model=(
                    self.enable_battery_model
                ),
            )
        )

        released_task_ids = getattr(
            decision,
            "released_task_ids",
            (),
        )

        for released_task_id in released_task_ids:

            if (
                released_task_id
                == task.task_id
            ):
                continue

            self._enqueue_reassignment(
                released_task_id
            )

        selected_robot_id = (
            decision.selected_robot_id
        )

        if selected_robot_id is None:

            if self.enable_battery_model:

                task.status = "waiting"

                self._enqueue_reassignment(
                    task.task_id
                )

                return

            task.status = "unserved"

            return

        robot = self._get_robot(
            selected_robot_id
        )

        robot_was_busy = (
            robot.current_task_id
            is not None
        )

        task.assigned_robot = (
            robot.robot_id
        )

        task.assignment_time_s = (
            current_time_s
        )

        task.status = "queued"

        if (
            task.task_id
            not in robot.assigned_task_ids
        ):

            robot.assigned_task_ids.append(
                task.task_id
            )

        self._assignment_context[
            task.task_id
        ] = _AssignmentContext(
            assignment_time_s=(
                current_time_s
            ),

            robot_was_busy=(
                robot_was_busy
            ),
        )

        # ----------------------------------------------------
        # If robot was idle, start first queued task now.
        # ----------------------------------------------------

        if robot.current_task_id is None:

            self._start_next_task(
                robot=robot,
                current_time_s=(
                    current_time_s
                ),
            )

        while self._activate_next_reassignment(
            current_time_s=current_time_s
        ):
            pass

    # ========================================================
    # Completion Event
    # ========================================================

    def _handle_completion(
        self,
        robot_id: str,
        task_id: str,
        current_time_s: float,
    ) -> None:

        robot = self._get_robot(
            robot_id
        )

        # Ignore stale completion events defensively.
        if (
            robot.current_task_id
            != task_id
        ):
            return

        task = (
            self.tasks_by_id[
                task_id
            ]
        )

        task.status = "completed"

        robot.current_location = (
            task.destination
        )

        robot.future_location = (
            task.destination
        )

        robot.current_task_id = None
        robot.current_task_start_time_s = None
        robot.current_task_completion_time_s = None
        robot.current_task_destination = None

        robot.completed_tasks += 1

        robot.status = "idle"

        # ----------------------------------------------------
        # Battery-aware post-task behavior
        # ----------------------------------------------------

        if (
            self.enable_battery_model
            and robot.battery_soc
            < BATTERY_CHARGE_TRIGGER_SOC
        ):

            self._start_return_to_charge(
                robot=robot,
                current_time_s=(
                    current_time_s
                ),
            )

            return

        # Battery is still sufficient.
        self._start_next_task(
            robot=robot,
            current_time_s=(
                current_time_s
            ),
        )

    # ========================================================
    # Start Next Task
    # ========================================================

    def _start_next_task(
        self,
        robot: RobotState,
        current_time_s: float,
    ) -> None:

        if robot.current_task_id is not None:
            return

        if not robot.queued_task_ids:

            robot.status = "idle"

            robot.available_time_s = (
                current_time_s
            )

            robot.future_location = (
                robot.current_location
            )

            return

        # ----------------------------------------------------
        # Re-evaluate Priority + Aging among future tasks.
        # ----------------------------------------------------

        ordered_tasks = (
            build_pending_queue(
                robot=robot,
                tasks_by_id=(
                    self.tasks_by_id
                ),
                current_time_s=(
                    current_time_s
                ),
            )
        )

        robot.queued_task_ids = [
            queued_task.task_id
            for queued_task
            in ordered_tasks
        ]

        task_id = (
            robot.queued_task_ids.pop(
                0
            )
        )

        task = (
            self.tasks_by_id[
                task_id
            ]
        )

        self._start_task(
            robot=robot,
            task=task,
            current_time_s=(
                current_time_s
            ),
        )

    # ========================================================
    # Actual Task Execution
    # ========================================================

    def _start_task(
        self,
        robot: RobotState,
        task: TaskState,
        current_time_s: float,
    ) -> None:
        """
        Actual simulator execution.

        This function MAY use realized service_time_s because
        it belongs to environment ground truth, not scheduler
        decision logic.
        """

        origin = (
            robot.current_location
        )

        approach_time_s = (
            self._travel_time(
                origin,
                task.source,
            )
        )

        task_travel_time_s = (
            self._travel_time(
                task.source,
                task.destination,
            )
        )

        # ----------------------------------------------------
        # Battery reservation
        #
        # Once this task starts, its navigation is
        # non-preemptive and therefore its navigation energy
        # is already committed.
        #
        # Reserve that energy immediately so future
        # scheduling decisions cannot reuse the same battery.
        #
        # IMPORTANT:
        # service_time_s is intentionally excluded.
        # ----------------------------------------------------

        if self.enable_battery_model:

            approach_energy_soc = (
                self._navigation_energy_soc(
                    approach_time_s
                )
            )

            task_travel_energy_soc = (
                self._navigation_energy_soc(
                    task_travel_time_s
                )
            )

            navigation_energy_soc = (
                approach_energy_soc
                + task_travel_energy_soc
            )

            projected_soc_after_task = (
                robot.battery_soc
                - navigation_energy_soc
            )

            if projected_soc_after_task < -1e-9:

                raise RuntimeError(
                    f"Robot {robot.robot_id} "
                    f"does not have enough battery "
                    f"to execute active task "
                    f"{task.task_id}: "
                    f"soc={robot.battery_soc:.6f}, "
                    f"required={navigation_energy_soc:.6f}"
                )

            robot.battery_soc = max(
                0.0,
                projected_soc_after_task,
            )

            robot.minimum_battery_soc = min(
                robot.minimum_battery_soc,
                robot.battery_soc,
            )

            robot.total_energy_consumed_soc += (
                navigation_energy_soc
            )

        dispatch_start_time_s = (
            current_time_s
        )

        source_arrival_time_s = (
            dispatch_start_time_s
            + approach_time_s
        )

        completion_time_s = (
            source_arrival_time_s
            + task_travel_time_s
            + task.service_time_s
        )

        # ----------------------------------------------------
        # Task state
        # ----------------------------------------------------

        task.start_time_s = (
            dispatch_start_time_s
        )

        task.source_arrival_time_s = (
            source_arrival_time_s
        )

        task.completion_time_s = (
            completion_time_s
        )

        task.approach_time_s = (
            approach_time_s
        )

        task.task_travel_time_s = (
            task_travel_time_s
        )

        task.status = "active"

        # ----------------------------------------------------
        # Robot state
        # ----------------------------------------------------

        robot.current_task_id = (
            task.task_id
        )

        robot.current_task_start_time_s = (
            dispatch_start_time_s
        )

        robot.current_task_completion_time_s = (
            completion_time_s
        )

        robot.current_task_destination = (
            task.destination
        )

        robot.available_time_s = (
            completion_time_s
        )

        robot.future_location = (
            task.destination
        )

        robot.status = "busy"

        added_busy_time_s = (
            approach_time_s
            + task_travel_time_s
            + task.service_time_s
        )

        robot.busy_time_s += (
            added_busy_time_s
        )

        # ----------------------------------------------------
        # Assignment record
        # ----------------------------------------------------

        context = (
            self._assignment_context[
                task.task_id
            ]
        )

        queue_delay_s = max(
            0.0,
            dispatch_start_time_s
            - context.assignment_time_s,
        )

        self.assignments.append(
            SchedulingAssignmentRecord(
                task_id=(
                    task.task_id
                ),

                robot_id=(
                    robot.robot_id
                ),

                task_arrival_time_s=(
                    task.arrival_time_s
                ),

                assignment_time_s=(
                    context.assignment_time_s
                ),

                robot_was_busy=(
                    context.robot_was_busy
                ),

                queue_delay_s=(
                    queue_delay_s
                ),

                assignment_origin=(
                    origin
                ),

                task_source=(
                    task.source
                ),

                task_destination=(
                    task.destination
                ),

                approach_time_s=(
                    approach_time_s
                ),

                task_travel_time_s=(
                    task_travel_time_s
                ),

                service_time_s=(
                    task.service_time_s
                ),

                dispatch_start_time_s=(
                    dispatch_start_time_s
                ),

                source_arrival_time_s=(
                    source_arrival_time_s
                ),

                completion_time_s=(
                    completion_time_s
                ),
            )
        )

        # ----------------------------------------------------
        # Completion event
        # ----------------------------------------------------

        self._push_event(
            time_s=(
                completion_time_s
            ),

            event_priority=(
                self.EVENT_COMPLETION
            ),

            event_type="completion",

            payload=(
                robot.robot_id,
                task.task_id,
            ),
        )

    # ========================================================
    # Helpers
    # ========================================================

    def _get_robot(
        self,
        robot_id: str,
    ) -> RobotState:

        for robot in self.robots:

            if (
                robot.robot_id
                == robot_id
            ):
                return robot

        raise KeyError(
            f"Unknown robot: {robot_id}"
        )

    def _enqueue_reassignment(
        self,
        task_id: str,
    ) -> None:
        """
        Add one waiting task to the same-time reassignment queue.

        Original arrival_time_s is preserved.
        """

        if task_id not in self.tasks_by_id:

            raise KeyError(
                f"Unknown task_id: {task_id}"
            )

        task = self.tasks_by_id[
            task_id
        ]

        if task.status == "completed":

            raise RuntimeError(
                "Completed task cannot be reassigned: "
                f"{task_id}"
            )

        if (
            task_id
            not in self.reassignment_task_ids
        ):

            self.reassignment_task_ids.append(
                task_id
            )

    def _activate_next_reassignment(
        self,
        current_time_s: float,
    ) -> bool:
        """
        Try to re-dispatch one waiting task at the current
        simulation time.

        Returns True if one task is successfully assigned.
        """

        if not self.reassignment_task_ids:
            return False

        candidate_tasks = [
            self.tasks_by_id[
                task_id
            ]
            for task_id
            in self.reassignment_task_ids
        ]

        ordered_tasks = order_waiting_tasks(
            tasks=candidate_tasks,
            current_time_s=current_time_s,
        )
        candidate_tasks = [
            self.tasks_by_id[
                task_id
            ]
            for task_id
            in self.reassignment_task_ids
        ]

        ordered_tasks = order_waiting_tasks(
            tasks=candidate_tasks,
            current_time_s=current_time_s,
        )

        for task in ordered_tasks:

            decision = (
                self.scheduler.decide(
                    robots=self.robots,
                    task=task,
                    tasks_by_id=(
                        self.tasks_by_id
                    ),
                    current_time_s=(
                        current_time_s
                    ),
                    travel_time_fn=(
                        self._travel_time
                    ),
                    commit_queue=True,
                    enable_battery_model=(
                        self.enable_battery_model
                    ),
                )
            )

            released_task_ids = getattr(
                decision,
                "released_task_ids",
                (),
            )

            for released_task_id in released_task_ids:

                if (
                    released_task_id
                    == task.task_id
                ):
                    continue

                self._enqueue_reassignment(
                    released_task_id
                )

            if (
                decision.selected_robot_id
                is None
            ):
                continue

            self.reassignment_task_ids.remove(
                task.task_id
            )

            robot = self._get_robot(
                decision.selected_robot_id
            )

            robot_was_busy = (
                robot.current_task_id
                is not None
            )

            task.assigned_robot = (
                robot.robot_id
            )

            task.assignment_time_s = (
                current_time_s
            )

            task.status = "queued"

            if (
                task.task_id
                not in robot.assigned_task_ids
            ):
                robot.assigned_task_ids.append(
                    task.task_id
                )

            self._assignment_context[
                task.task_id
            ] = _AssignmentContext(
                assignment_time_s=(
                    current_time_s
                ),
                robot_was_busy=(
                    robot_was_busy
                ),
            )

            if (
                robot.current_task_id
                is None
            ):
                self._start_next_task(
                    robot=robot,
                    current_time_s=(
                        current_time_s
                    ),
                )

            return True

        return False

    # ========================================================
    # Finalization
    # ========================================================

    def _finalize_robot_states(
        self,
    ) -> None:

        for robot in self.robots:

            robot.current_task_id = None
            robot.current_task_start_time_s = None
            robot.current_task_completion_time_s = None
            robot.current_task_destination = None

            robot.queued_task_ids = []

            robot.status = "idle"

            robot.available_time_s = max(
                robot.available_time_s,
                0.0,
            )

            robot.future_location = (
                robot.current_location
            )

    # ========================================================
    # Debug Summary
    # ========================================================

    def print_summary(
        self,
    ) -> None:

        scheduler_name = getattr(
            self.scheduler,
            "NAME",
            type(
                self.scheduler
            ).__name__,
        )

        print(
            "Scheduler:",
            scheduler_name,
        )

        print(
            "Fleet:",
            self.fleet_configuration,
        )

        print(
            "Seed:",
            self.seed,
        )

        print(
            "Workload multiplier:",
            self.workload_multiplier,
        )

        print(
            "Tasks:",
            len(
                self.tasks
            ),
        )

        print(
            "Assignments:",
            len(
                self.assignments
            ),
        )

        print(
            "\nRobot summary:"
        )

        for robot in self.robots:

            print(
                robot.robot_id,
                robot.robot_type,
                "assigned=",
                len(
                    robot.assigned_task_ids
                ),
                "completed=",
                robot.completed_tasks,
                "busy_s=",
                round(
                    robot.busy_time_s,
                    1,
                ),
                "location=",
                robot.current_location,
            )

    def _start_return_to_charge(
        self,
        robot: RobotState,
        current_time_s: float,
    ) -> None:
        """
        Send an idle low-battery robot back to the charger.

        Navigation energy is reserved immediately, using the
        same duration-free travel-energy model as task travel.
        """

        if not self.enable_battery_model:
            return

        if robot.current_task_id is not None:
            raise ValueError(
                f"Robot {robot.robot_id} cannot return "
                "to charge while executing an active task."
            )

        if robot.status in {
            "returning_to_charge",
            "charging",
        }:
            return

        if (
            robot.current_location
            == CHARGING_WAYPOINT
        ):
            self._start_charging(
                robot=robot,
                current_time_s=current_time_s,
            )

            return

        return_travel_time_s = (
            self._travel_time(
                robot.current_location,
                CHARGING_WAYPOINT,
            )
        )

        return_energy_soc = (
            self._navigation_energy_soc(
                return_travel_time_s
            )
        )

        projected_soc = (
            robot.battery_soc
            - return_energy_soc
        )

        if projected_soc < -1e-9:
            raise RuntimeError(
                f"Robot {robot.robot_id} cannot reach "
                f"{CHARGING_WAYPOINT}: "
                f"soc={robot.battery_soc:.6f}, "
                f"required={return_energy_soc:.6f}"
            )

        # Reserve return-to-charger navigation energy
        # immediately.
        robot.battery_soc = max(
            0.0,
            projected_soc,
        )

        robot.minimum_battery_soc = min(
            robot.minimum_battery_soc,
            robot.battery_soc,
        )

        robot.total_energy_consumed_soc += (
            return_energy_soc
        )

        return_complete_time_s = (
            float(current_time_s)
            + return_travel_time_s
        )

        robot.status = "returning_to_charge"

        robot.return_to_charge_count += 1

        robot.available_time_s = (
            return_complete_time_s
        )

        robot.future_location = (
            CHARGING_WAYPOINT
        )

        self._push_event(
            time_s=(
                return_complete_time_s
            ),
            event_priority=(
                self.EVENT_RETURN_TO_CHARGE_COMPLETE
            ),
            event_type=(
                "return_to_charge_complete"
            ),
            payload=(
                robot.robot_id
            ),
        )

    def _handle_return_to_charge_complete(
        self,
        robot_id: str,
        current_time_s: float,
    ) -> None:

        robot = self._get_robot(
            robot_id
        )

        if (
            robot.status
            != "returning_to_charge"
        ):
            # Ignore stale event defensively.
            return

        robot.current_location = (
            CHARGING_WAYPOINT
        )

        robot.future_location = (
            CHARGING_WAYPOINT
        )

        robot.available_time_s = (
            float(current_time_s)
        )

        robot.status = "idle"

        self._start_charging(
            robot=robot,
            current_time_s=(
                current_time_s
            ),
        )

    def _start_charging(
        self,
        robot: RobotState,
        current_time_s: float,
    ) -> None:

        if not self.enable_battery_model:
            return

        if (
            robot.current_location
            != CHARGING_WAYPOINT
        ):
            raise ValueError(
                f"Robot {robot.robot_id} cannot start "
                "charging away from charging station: "
                f"{robot.current_location}"
            )

        if robot.current_task_id is not None:
            raise ValueError(
                f"Robot {robot.robot_id} cannot charge "
                "while executing an active task."
            )

        if robot.status == "charging":
            return

        start_soc = float(
            robot.battery_soc
        )

        if start_soc >= BATTERY_RESUME_SOC:
            robot.status = "idle"
            return

        required_soc = (
            BATTERY_RESUME_SOC
            - start_soc
        )

        charging_duration_s = (
            required_soc
            / BATTERY_CHARGE_RATE_PER_SECOND
        )

        charging_end_time_s = (
            float(current_time_s)
            + charging_duration_s
        )

        robot.status = "charging"

        robot.charging_count += 1

        robot.charging_start_time_s = (
            float(current_time_s)
        )

        robot.charging_end_time_s = (
            charging_end_time_s
        )

        robot.charging_start_soc = (
            start_soc
        )

        self._push_event(
            time_s=charging_end_time_s,
            event_priority=(
                self.EVENT_CHARGING_COMPLETE
            ),
            event_type="charging_complete",
            payload=robot.robot_id,
        )

    def _handle_charging_complete(
        self,
        robot_id: str,
        current_time_s: float,
    ) -> None:

        robot = self._get_robot(
            robot_id
        )

        if robot.status != "charging":
            return

        if (
            robot.charging_start_time_s
            is None
        ):
            raise RuntimeError(
                f"Robot {robot.robot_id} "
                "has no charging_start_time_s."
            )

        charging_time_s = max(
            0.0,
            float(current_time_s)
            - float(
                robot.charging_start_time_s
            ),
        )

        robot.battery_soc = (
            BATTERY_RESUME_SOC
        )

        robot.total_charging_time_s += (
            charging_time_s
        )

        robot.charging_cycles += 1

        robot.charging_start_time_s = None
        robot.charging_end_time_s = None
        robot.charging_start_soc = None

        robot.status = "idle"

        robot.available_time_s = (
            float(current_time_s)
        )

        robot.future_location = (
            robot.current_location
        )

        self._start_next_task(
            robot=robot,
            current_time_s=current_time_s,
        )