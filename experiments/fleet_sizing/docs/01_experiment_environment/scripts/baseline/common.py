from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
)

from experiments.fleet_sizing.config import (
    BATTERY_MIN_RESERVE_SOC,
    BATTERY_TRAVEL_DRAIN_PER_SECOND,
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Shared Baseline Constants
# ============================================================

AGING_INTERVAL_SECONDS = 120.0


ASSIGNABLE_ROBOT_STATUSES = {
    "idle",
    "busy",
}


UNAVAILABLE_ROBOT_STATUSES = {
    "offline",
    "error",
    "charging",
    "returning_to_charge",
}


TravelTimeFunction = Callable[
    [str, str],
    float,
]


# ============================================================
# Projected Schedule Models
# ============================================================

@dataclass(frozen=True)
class ProjectedTaskTiming:

    task_id: str

    queue_position: int

    origin: str

    start_time_s: float

    approach_time_s: float

    source_arrival_time_s: float

    task_travel_time_s: float

    completion_time_s: float


@dataclass(frozen=True)
class QueueProjection:

    robot_id: str

    projected_tasks: tuple[
        ProjectedTaskTiming,
        ...
    ]

    final_available_time_s: float

    final_location: str

    @property
    def queue_length(
        self,
    ) -> int:

        return len(
            self.projected_tasks
        )

    def get_task(
        self,
        task_id: str,
    ) -> Optional[
        ProjectedTaskTiming
    ]:

        for projected in (
            self.projected_tasks
        ):

            if (
                projected.task_id
                == task_id
            ):
                return projected

        return None


@dataclass(frozen=True)
class CandidateEvaluation:

    robot_id: str

    task_id: str

    current_location: str

    assignment_origin: str

    current_queue_length: int

    projected_queue_length: int

    projected_queue_position: int

    projected_start_time_s: float

    projected_approach_time_s: float

    projected_source_arrival_time_s: float

    projected_task_travel_time_s: float

    projected_completion_time_s: float

    projected_waiting_time_s: float

    projected_response_time_s: float

    queue_projection: QueueProjection


# ============================================================
# Priority / Aging
# ============================================================

def get_waiting_time_s(
    task: TaskState,
    current_time_s: float,
) -> float:

    return max(
        0.0,
        (
            float(current_time_s)
            - float(task.arrival_time_s)
        ),
    )


def get_effective_priority(
    task: TaskState,
    current_time_s: float,
) -> float:

    if (
        task.priority
        == PRIORITY_EMERGENCY
    ):
        return float(
            PRIORITY_EMERGENCY
        )

    waiting_time_s = (
        get_waiting_time_s(
            task=task,
            current_time_s=(
                current_time_s
            ),
        )
    )

    aging_bonus = (
        waiting_time_s
        / AGING_INTERVAL_SECONDS
    )

    return (
        float(task.priority)
        + aging_bonus
    )


def get_queue_sort_key(
    task: TaskState,
    current_time_s: float,
) -> tuple:

    # --------------------------------------------------------
    # Emergency protection
    #
    # Emergency always comes before every non-Emergency task.
    #
    # Emergency tasks are FCFS among themselves.
    # --------------------------------------------------------

    if (
        task.priority
        == PRIORITY_EMERGENCY
    ):

        return (
            0,
            task.arrival_time_s,
            task.task_id,
        )

    effective_priority = (
        get_effective_priority(
            task=task,
            current_time_s=(
                current_time_s
            ),
        )
    )

    return (
        1,
        -effective_priority,
        task.arrival_time_s,
        task.task_id,
    )


def order_waiting_tasks(
    tasks: Iterable[TaskState],
    current_time_s: float,
) -> List[TaskState]:

    return sorted(
        list(tasks),
        key=lambda task: (
            get_queue_sort_key(
                task=task,
                current_time_s=(
                    current_time_s
                ),
            )
        ),
    )


# ============================================================
# Capability / Robot Feasibility
# ============================================================

def robot_can_perform_task(
    robot: RobotState,
    task: TaskState,
) -> bool:

    return (
        task.task_type
        in robot.capabilities
    )


def robot_status_is_assignable(
    robot: RobotState,
) -> bool:

    status = (
        str(robot.status)
        .strip()
        .lower()
    )

    if (
        status
        in UNAVAILABLE_ROBOT_STATUSES
    ):
        return False

    return (
        status
        in ASSIGNABLE_ROBOT_STATUSES
    )


def robot_is_feasible(
    robot: RobotState,
    task: TaskState,
) -> bool:

    if not robot_can_perform_task(
        robot=robot,
        task=task,
    ):
        return False

    if not robot_status_is_assignable(
        robot=robot,
    ):
        return False

    return True


def get_feasible_robots(
    robots: Iterable[RobotState],
    task: TaskState,
) -> List[RobotState]:

    return [
        robot
        for robot in robots
        if robot_is_feasible(
            robot=robot,
            task=task,
        )
    ]


# ============================================================
# Robot Future-State Helpers
# ============================================================

def get_robot_projection_start_time(
    robot: RobotState,
    current_time_s: float,
) -> float:

    # --------------------------------------------------------
    # Active task is non-preemptive.
    # --------------------------------------------------------

    if (
        robot.current_task_id
        is not None
        and
        robot.current_task_completion_time_s
        is not None
    ):

        return max(
            float(current_time_s),
            float(
                robot
                .current_task_completion_time_s
            ),
        )

    return float(
        current_time_s
    )


def get_robot_projection_start_location(
    robot: RobotState,
) -> str:

    if (
        robot.current_task_id
        is not None
        and
        robot.current_task_destination
        is not None
    ):

        return (
            robot.current_task_destination
        )

    return (
        robot.current_location
    )


# ============================================================
# Future Queue
# ============================================================

def get_robot_queued_tasks(
    robot: RobotState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
) -> List[TaskState]:

    queued_tasks: List[
        TaskState
    ] = []

    for task_id in (
        robot.queued_task_ids
    ):

        # Active task must never appear in future queue.
        if (
            robot.current_task_id
            is not None
            and
            task_id
            == robot.current_task_id
        ):

            raise ValueError(
                f"Robot {robot.robot_id} "
                f"contains active task "
                f"{task_id} inside "
                "queued_task_ids."
            )

        if (
            task_id
            not in tasks_by_id
        ):

            raise KeyError(
                f"Queued task {task_id} "
                f"for robot "
                f"{robot.robot_id} "
                "does not exist."
            )

        queued_tasks.append(
            tasks_by_id[task_id]
        )

    return queued_tasks


def build_pending_queue(
    robot: RobotState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    extra_task: Optional[
        TaskState
    ] = None,
) -> List[TaskState]:

    pending_tasks = (
        get_robot_queued_tasks(
            robot=robot,
            tasks_by_id=tasks_by_id,
        )
    )

    if extra_task is not None:

        existing_ids = {
            task.task_id
            for task
            in pending_tasks
        }

        if (
            extra_task.task_id
            not in existing_ids
        ):

            pending_tasks.append(
                extra_task
            )

    return order_waiting_tasks(
        tasks=pending_tasks,
        current_time_s=(
            current_time_s
        ),
    )


# ============================================================
# Duration-Free Queue Placement Projection
# ============================================================

@dataclass(frozen=True)
class ProjectedTaskPlacement:
    """
    Scheduler-visible queue placement for one future task.

    IMPORTANT:
    This model intentionally contains NO:

        - service time
        - start time
        - completion time
        - waiting time
        - response time

    It only describes:

        1. where the robot is expected to be before this task
        2. where this task appears in the future queue
        3. how far / long the robot must travel from that
           projected origin to the task source

    Therefore it does not require future task durations.
    """

    task_id: str

    queue_position: int

    origin: str

    approach_time_s: float

    tasks_ahead_count: int


@dataclass(frozen=True)
class QueuePlacementProjection:
    """
    Duration-free projection of a robot's future queue.

    This projection only follows task destinations to infer
    future robot locations.

    It does NOT predict when any task will start or finish.
    """

    robot_id: str

    projected_tasks: tuple[
        ProjectedTaskPlacement,
        ...
    ]

    final_location: str

    @property
    def queue_length(
        self,
    ) -> int:

        return len(
            self.projected_tasks
        )

    def get_task(
        self,
        task_id: str,
    ) -> Optional[
        ProjectedTaskPlacement
    ]:

        for projected in (
            self.projected_tasks
        ):

            if (
                projected.task_id
                == task_id
            ):

                return projected

        return None


@dataclass(frozen=True)
class PlacementCandidateEvaluation:
    """
    Scheduler-visible candidate evaluation.

    Unlike CandidateEvaluation, this data structure does not
    contain any predicted task duration or completion time.

    It is intended for online schedulers that must not access
    environment ground-truth future information.
    """

    robot_id: str

    task_id: str

    current_location: str

    assignment_origin: str

    current_queue_length: int

    projected_queue_length: int

    projected_queue_position: int

    tasks_ahead_count: int

    projected_approach_time_s: float

    queue_projection: (
        QueuePlacementProjection
    )


def project_robot_queue_placement(
    robot: RobotState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
    extra_task: Optional[
        TaskState
    ] = None,
) -> QueuePlacementProjection:
    """
    Build a duration-free projection of a robot's future queue.

    The scheduler knows:

        - current robot location
        - active task destination
        - queued task destinations
        - task sources
        - task priorities
        - task arrival times
        - route travel estimates

    The scheduler does NOT need to know:

        - actual service duration
        - actual completion time
        - future realized processing time

    Projection logic
    ----------------

    If there is an active task:

        projected location
            =
        active task destination

    Otherwise:

        projected location
            =
        robot current location

    Future tasks are then ordered using Priority + Aging.

    For each queued task:

        origin
            =
        previous projected destination

        approach time
            =
        travel(origin -> task source)

    After that task:

        projected location
            =
        task destination

    No timing propagation is performed.
    """

    pending_tasks = (
        build_pending_queue(
            robot=robot,
            tasks_by_id=tasks_by_id,
            current_time_s=(
                current_time_s
            ),
            extra_task=extra_task,
        )
    )

    # --------------------------------------------------------
    # Active task is non-preemptive.
    #
    # We do NOT need to know when it finishes.
    # We only know that, after completion, the robot should
    # be located at its destination.
    # --------------------------------------------------------

    projected_location = (
        get_robot_projection_start_location(
            robot=robot
        )
    )

    projected_tasks: List[
        ProjectedTaskPlacement
    ] = []

    for queue_index, task in enumerate(
        pending_tasks
    ):

        queue_position = (
            queue_index + 1
        )

        tasks_ahead_count = (
            queue_index
        )

        origin = (
            projected_location
        )

        approach_time_s = float(
            travel_time_fn(
                origin,
                task.source,
            )
        )

        if (
            approach_time_s
            < 0.0
        ):

            raise ValueError(
                "Negative approach time: "
                f"{origin} -> "
                f"{task.source}"
            )

        projected_tasks.append(
            ProjectedTaskPlacement(
                task_id=(
                    task.task_id
                ),
                queue_position=(
                    queue_position
                ),
                origin=origin,
                approach_time_s=(
                    approach_time_s
                ),
                tasks_ahead_count=(
                    tasks_ahead_count
                ),
            )
        )

        # ----------------------------------------------------
        # We know where the robot should be after the task,
        # but NOT when it will arrive there.
        # ----------------------------------------------------

        projected_location = (
            task.destination
        )

    return QueuePlacementProjection(
        robot_id=(
            robot.robot_id
        ),
        projected_tasks=tuple(
            projected_tasks
        ),
        final_location=(
            projected_location
        ),
    )


def evaluate_placement_candidate_robot(
    robot: RobotState,
    task: TaskState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
) -> PlacementCandidateEvaluation:
    """
    Evaluate one feasible robot without using future task
    durations.

    This should become the main candidate-evaluation path for
    scheduling baselines that must avoid future-information
    leakage.
    """

    if not robot_is_feasible(
        robot=robot,
        task=task,
    ):

        raise ValueError(
            f"Robot {robot.robot_id} "
            f"is not feasible for "
            f"task {task.task_id}."
        )

    current_queue_length = len(
        robot.queued_task_ids
    )

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

    projected_task = (
        projection.get_task(
            task.task_id
        )
    )

    if projected_task is None:

        raise RuntimeError(
            f"Task {task.task_id} "
            "was not found in "
            f"robot {robot.robot_id} "
            "placement projection."
        )

    return PlacementCandidateEvaluation(
        robot_id=(
            robot.robot_id
        ),

        task_id=(
            task.task_id
        ),

        current_location=(
            robot.current_location
        ),

        assignment_origin=(
            projected_task.origin
        ),

        current_queue_length=(
            current_queue_length
        ),

        projected_queue_length=(
            projection.queue_length
        ),

        projected_queue_position=(
            projected_task.queue_position
        ),

        tasks_ahead_count=(
            projected_task
            .tasks_ahead_count
        ),

        projected_approach_time_s=(
            projected_task
            .approach_time_s
        ),

        queue_projection=(
            projection
        ),
    )


def evaluate_feasible_placement_candidates(
    robots: Iterable[
        RobotState
    ],
    task: TaskState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
) -> List[
    PlacementCandidateEvaluation
]:
    """
    Evaluate all feasible robots using only duration-free
    scheduler-visible information.
    """

    feasible_robots = (
        get_feasible_robots(
            robots=robots,
            task=task,
        )
    )

    evaluations = [

        evaluate_placement_candidate_robot(
            robot=robot,
            task=task,
            tasks_by_id=tasks_by_id,
            current_time_s=(
                current_time_s
            ),
            travel_time_fn=(
                travel_time_fn
            ),
        )

        for robot
        in feasible_robots
    ]

    evaluations.sort(
        key=lambda candidate: (
            candidate.robot_id
        )
    )

    return evaluations


def evaluate_battery_feasible_placement_candidates(
    *,
    robots: Iterable[RobotState],
    task: TaskState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
    enable_battery_model: bool = False,
) -> list[
    PlacementCandidateEvaluation
]:
    """
    Evaluate duration-free placement candidates and,
    when battery mode is enabled, retain only robots on
    which the incoming task itself survives battery-aware
    queue repair.

    Existing downstream queued tasks may be released.
    Therefore the entire future queue does NOT need to
    remain feasible.

    This matches the feasibility semantics used by the
    RL action mask.
    """

    robots_list = list(
        robots
    )

    evaluations = (
        evaluate_feasible_placement_candidates(
            robots=robots_list,
            task=task,
            tasks_by_id=tasks_by_id,
            current_time_s=(
                current_time_s
            ),
            travel_time_fn=(
                travel_time_fn
            ),
        )
    )

    if not enable_battery_model:

        return list(
            evaluations
        )

    robots_by_id = {
        robot.robot_id: robot
        for robot
        in robots_list
    }

    battery_feasible: list[
        PlacementCandidateEvaluation
    ] = []

    for evaluation in evaluations:

        robot = robots_by_id[
            evaluation.robot_id
        ]

        repair = (
            repair_projected_queue_for_battery(
                robot=robot,
                queue_projection=(
                    evaluation
                    .queue_projection
                ),
                tasks_by_id=(
                    tasks_by_id
                ),
                travel_time_fn=(
                    travel_time_fn
                ),
            )
        )

        # Important:
        # downstream existing tasks may be released.
        # The candidate remains legal as long as the
        # incoming task itself survives.
        if repair.task_is_kept(
            task.task_id
        ):

            battery_feasible.append(
                evaluation
            )

    return battery_feasible


def apply_placement_queue_order(
    robot: RobotState,
    projection: QueuePlacementProjection,
) -> None:
    """
    Commit a duration-free projected future queue to RobotState.

    Active task is not touched.
    Only queued_task_ids are updated.
    """

    if (
        robot.robot_id
        != projection.robot_id
    ):

        raise ValueError(
            "Projection robot ID does "
            "not match RobotState: "
            f"{projection.robot_id} != "
            f"{robot.robot_id}"
        )

    robot.queued_task_ids = [

        projected.task_id

        for projected
        in projection.projected_tasks
    ]


# ============================================================
# Duration-Free Battery Queue Projection
# ============================================================


@dataclass(frozen=True)
class ProjectedTaskBattery:
    """
    Battery projection for one future queued task.

    This model uses only scheduler-visible navigation
    information.

    It does NOT use:
        - TaskState.service_time_s
        - actual future completion time
        - predicted service duration
    """

    task_id: str

    queue_position: int

    origin: str

    approach_time_s: float

    task_travel_time_s: float

    approach_energy_soc: float

    task_travel_energy_soc: float

    total_energy_soc: float

    soc_before_task: float

    soc_after_task: float

    battery_feasible: bool


@dataclass(frozen=True)
class QueueBatteryProjection:
    """
    Duration-free battery feasibility result for a projected
    future queue.

    battery_soc is interpreted as the currently available
    scheduling SoC.

    Once an active task has started, its navigation energy
    will later be reserved by the simulator. Therefore this
    projection evaluates only the future queued tasks.
    """

    robot_id: str

    initial_soc: float

    reserve_soc: float

    projected_tasks: tuple[
        ProjectedTaskBattery,
        ...
    ]

    final_soc: float

    minimum_projected_soc: float

    first_infeasible_task_id: Optional[str]

    @property
    def is_feasible(
        self,
    ) -> bool:

        return (
            self.first_infeasible_task_id
            is None
        )

    @property
    def infeasible_task_ids(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            projected.task_id
            for projected
            in self.projected_tasks
            if not projected.battery_feasible
        )


def travel_time_to_energy_soc(
    travel_time_s: float,
) -> float:
    """
    Convert estimated navigation time to normalized
    battery consumption.

    1.0 SoC = full battery.

    This function intentionally models navigation energy only.
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


def project_queue_battery(
    *,
    robot: RobotState,
    queue_projection: QueuePlacementProjection,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    travel_time_fn: TravelTimeFunction,
    reserve_soc: float = BATTERY_MIN_RESERVE_SOC,
) -> QueueBatteryProjection:
    """
    Propagate battery state through an already constructed
    duration-free future queue.

    Important
    ---------
    queue_projection must already contain the Priority + Aging
    ordering, including the incoming task when applicable.

    Example:

        original:
            T2 -> T3

        incoming Emergency:
            T4

        projected queue:
            T4 -> T2 -> T3

    Battery is then propagated in exactly that order.

    If T4 itself is feasible but T3 becomes infeasible,
    first_infeasible_task_id will be T3.

    No service duration or future completion time is used.
    """

    if (
        queue_projection.robot_id
        != robot.robot_id
    ):

        raise ValueError(
            "Queue projection robot ID does not match "
            f"RobotState: {queue_projection.robot_id} "
            f"!= {robot.robot_id}"
        )

    initial_soc = float(
        robot.battery_soc
    )

    reserve_soc = float(
        reserve_soc
    )

    if not (
        0.0
        <= initial_soc
        <= 1.0
    ):

        raise ValueError(
            f"Robot {robot.robot_id} has invalid "
            f"battery_soc={initial_soc}"
        )

    if not (
        0.0
        <= reserve_soc
        <= 1.0
    ):

        raise ValueError(
            "reserve_soc must be within [0, 1]"
        )

    projected_soc = initial_soc

    minimum_projected_soc = (
        initial_soc
    )

    first_infeasible_task_id: (
        Optional[str]
    ) = None

    projected_battery_tasks: List[
        ProjectedTaskBattery
    ] = []

    for placement in (
        queue_projection.projected_tasks
    ):

        if (
            placement.task_id
            not in tasks_by_id
        ):

            raise KeyError(
                f"Projected task "
                f"{placement.task_id} "
                "does not exist in tasks_by_id."
            )

        task = (
            tasks_by_id[
                placement.task_id
            ]
        )

        # ----------------------------------------------------
        # Projected origin -> task source
        #
        # Already computed by the duration-free queue
        # projection.
        # ----------------------------------------------------

        approach_time_s = float(
            placement.approach_time_s
        )

        # ----------------------------------------------------
        # Task source -> task destination
        #
        # This is route information and does not depend on
        # service duration.
        # ----------------------------------------------------

        task_travel_time_s = float(
            travel_time_fn(
                task.source,
                task.destination,
            )
        )

        if task_travel_time_s < 0.0:

            raise ValueError(
                "Negative task travel time: "
                f"{task.source} -> "
                f"{task.destination}"
            )

        approach_energy_soc = (
            travel_time_to_energy_soc(
                approach_time_s
            )
        )

        task_travel_energy_soc = (
            travel_time_to_energy_soc(
                task_travel_time_s
            )
        )

        total_energy_soc = (
            approach_energy_soc
            + task_travel_energy_soc
        )

        soc_before_task = (
            projected_soc
        )

        soc_after_task = (
            soc_before_task
            - total_energy_soc
        )

        battery_feasible = (
            soc_after_task
            >= reserve_soc
        )

        if (
            not battery_feasible
            and
            first_infeasible_task_id
            is None
        ):

            first_infeasible_task_id = (
                task.task_id
            )

        projected_battery_tasks.append(
            ProjectedTaskBattery(
                task_id=(
                    task.task_id
                ),

                queue_position=(
                    placement.queue_position
                ),

                origin=(
                    placement.origin
                ),

                approach_time_s=(
                    approach_time_s
                ),

                task_travel_time_s=(
                    task_travel_time_s
                ),

                approach_energy_soc=(
                    approach_energy_soc
                ),

                task_travel_energy_soc=(
                    task_travel_energy_soc
                ),

                total_energy_soc=(
                    total_energy_soc
                ),

                soc_before_task=(
                    soc_before_task
                ),

                soc_after_task=(
                    soc_after_task
                ),

                battery_feasible=(
                    battery_feasible
                ),
            )
        )

        projected_soc = (
            soc_after_task
        )

        minimum_projected_soc = min(
            minimum_projected_soc,
            projected_soc,
        )

    return QueueBatteryProjection(
        robot_id=(
            robot.robot_id
        ),

        initial_soc=(
            initial_soc
        ),

        reserve_soc=(
            reserve_soc
        ),

        projected_tasks=tuple(
            projected_battery_tasks
        ),

        final_soc=(
            projected_soc
        ),

        minimum_projected_soc=(
            minimum_projected_soc
        ),

        first_infeasible_task_id=(
            first_infeasible_task_id
        ),
    )


# ============================================================
# Battery-Aware Queue Repair
# ============================================================


@dataclass(frozen=True)
class BatteryQueueRepairTask:
    """
    Result of battery checking for one future task.

    keep_on_robot:
        True:
            task remains on this robot.

        False:
            task must be released for reassignment.
    """

    task_id: str

    original_queue_position: int

    origin: str

    approach_time_s: float

    task_travel_time_s: float

    required_energy_soc: float

    soc_before_task: float

    soc_after_task: float

    keep_on_robot: bool


@dataclass(frozen=True)
class BatteryQueueRepairResult:
    """
    Result after repairing one robot's projected queue
    according to battery feasibility.
    """

    robot_id: str

    initial_soc: float

    reserve_soc: float

    task_results: tuple[
        BatteryQueueRepairTask,
        ...
    ]

    kept_task_ids: tuple[
        str,
        ...
    ]

    released_task_ids: tuple[
        str,
        ...
    ]

    final_soc: float

    final_location: str

    def task_is_kept(
        self,
        task_id: str,
    ) -> bool:

        return (
            task_id
            in self.kept_task_ids
        )


def repair_projected_queue_for_battery(
    *,
    robot: RobotState,
    queue_projection: QueuePlacementProjection,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    travel_time_fn: TravelTimeFunction,
    reserve_soc: float = BATTERY_MIN_RESERVE_SOC,
) -> BatteryQueueRepairResult:
    """
    Repair a Priority + Aging projected queue according to
    battery feasibility.

    The task order comes from queue_projection.

    Tasks are checked sequentially.

    If a task can be completed while retaining reserve SoC:

        keep task
        consume projected energy
        move projected robot location to task destination

    Otherwise:

        release task for reassignment
        do NOT consume its energy
        do NOT move projected robot location

    Therefore later tasks are checked again after an
    infeasible task is removed.

    IMPORTANT:
    This function uses navigation energy only.

    It does NOT use:
        - TaskState.service_time_s
        - current_task_completion_time_s
        - future realized completion times
    """

    if (
        queue_projection.robot_id
        != robot.robot_id
    ):

        raise ValueError(
            "Queue projection robot ID does not match "
            f"RobotState: {queue_projection.robot_id} "
            f"!= {robot.robot_id}"
        )

    projected_soc = float(
        robot.battery_soc
    )

    reserve_soc = float(
        reserve_soc
    )

    if not (
        0.0
        <= projected_soc
        <= 1.0
    ):

        raise ValueError(
            f"Robot {robot.robot_id} has invalid "
            f"battery_soc={projected_soc}"
        )

    if not (
        0.0
        <= reserve_soc
        <= 1.0
    ):

        raise ValueError(
            "reserve_soc must be within [0, 1]"
        )

    initial_soc = (
        projected_soc
    )

    # --------------------------------------------------------
    # Active task is non-preemptive.
    #
    # Future queue begins from the location after the active
    # task. If no active task exists, it begins at the robot's
    # current location.
    # --------------------------------------------------------

    projected_location = (
        get_robot_projection_start_location(
            robot=robot
        )
    )

    task_results: List[
        BatteryQueueRepairTask
    ] = []

    kept_task_ids: List[
        str
    ] = []

    released_task_ids: List[
        str
    ] = []

    for placement in (
        queue_projection.projected_tasks
    ):

        if (
            placement.task_id
            not in tasks_by_id
        ):

            raise KeyError(
                f"Projected task "
                f"{placement.task_id} "
                "does not exist in tasks_by_id."
            )

        task = (
            tasks_by_id[
                placement.task_id
            ]
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Recalculate approach from the last KEPT task.
        #
        # Do not blindly use placement.origin because an
        # earlier task may already have been released.
        # ----------------------------------------------------

        origin = (
            projected_location
        )

        approach_time_s = float(
            travel_time_fn(
                origin,
                task.source,
            )
        )

        task_travel_time_s = float(
            travel_time_fn(
                task.source,
                task.destination,
            )
        )

        if approach_time_s < 0.0:

            raise ValueError(
                "Negative approach time: "
                f"{origin} -> "
                f"{task.source}"
            )

        if task_travel_time_s < 0.0:

            raise ValueError(
                "Negative task travel time: "
                f"{task.source} -> "
                f"{task.destination}"
            )

        required_energy_soc = (
            travel_time_to_energy_soc(
                approach_time_s
            )
            +
            travel_time_to_energy_soc(
                task_travel_time_s
            )
        )

        soc_before_task = (
            projected_soc
        )

        candidate_soc_after = (
            soc_before_task
            - required_energy_soc
        )

        keep_on_robot = (
            candidate_soc_after
            >= reserve_soc
        )

        if keep_on_robot:

            # Commit projected battery consumption.
            projected_soc = (
                candidate_soc_after
            )

            # Robot will finish this task here.
            projected_location = (
                task.destination
            )

            kept_task_ids.append(
                task.task_id
            )

            soc_after_task = (
                projected_soc
            )

        else:

            # ------------------------------------------------
            # Task is removed from this robot.
            #
            # Energy is NOT consumed.
            # Location is NOT changed.
            #
            # The following task will therefore be checked
            # again from the last feasible location.
            # ------------------------------------------------

            released_task_ids.append(
                task.task_id
            )

            soc_after_task = (
                projected_soc
            )

        task_results.append(
            BatteryQueueRepairTask(
                task_id=(
                    task.task_id
                ),

                original_queue_position=(
                    placement.queue_position
                ),

                origin=(
                    origin
                ),

                approach_time_s=(
                    approach_time_s
                ),

                task_travel_time_s=(
                    task_travel_time_s
                ),

                required_energy_soc=(
                    required_energy_soc
                ),

                soc_before_task=(
                    soc_before_task
                ),

                soc_after_task=(
                    soc_after_task
                ),

                keep_on_robot=(
                    keep_on_robot
                ),
            )
        )

    return BatteryQueueRepairResult(
        robot_id=(
            robot.robot_id
        ),

        initial_soc=(
            initial_soc
        ),

        reserve_soc=(
            reserve_soc
        ),

        task_results=tuple(
            task_results
        ),

        kept_task_ids=tuple(
            kept_task_ids
        ),

        released_task_ids=tuple(
            released_task_ids
        ),

        final_soc=(
            projected_soc
        ),

        final_location=(
            projected_location
        ),
    )


def apply_battery_queue_repair(
    *,
    robot: RobotState,
    repair: BatteryQueueRepairResult,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
) -> tuple[str, ...]:
    """
    Commit a BatteryQueueRepairResult.

    Active task is never modified.

    Kept tasks:
        remain assigned to this robot.

    Released tasks:
        are removed from this robot's future queue
        and returned to waiting/unassigned state.

    Returns:
        IDs of tasks that must be reassigned.
    """

    if (
        robot.robot_id
        != repair.robot_id
    ):

        raise ValueError(
            "Repair robot ID does not match "
            f"RobotState: {repair.robot_id} "
            f"!= {robot.robot_id}"
        )

    # --------------------------------------------------------
    # Active task must never appear in the repair result.
    # --------------------------------------------------------

    if (
        robot.current_task_id
        is not None
        and
        robot.current_task_id
        in {
            item.task_id
            for item
            in repair.task_results
        }
    ):

        raise ValueError(
            f"Active task "
            f"{robot.current_task_id} "
            "cannot be modified by battery queue repair."
        )

    # --------------------------------------------------------
    # Commit kept future queue.
    # --------------------------------------------------------

    robot.queued_task_ids = list(
        repair.kept_task_ids
    )

    # --------------------------------------------------------
    # Update kept tasks.
    # --------------------------------------------------------

    for queue_index, task_id in enumerate(
        repair.kept_task_ids,
        start=1,
    ):

        if task_id not in tasks_by_id:

            raise KeyError(
                f"Kept task {task_id} "
                "does not exist in tasks_by_id."
            )

        task = tasks_by_id[
            task_id
        ]

        task.assigned_robot = (
            robot.robot_id
        )

        task.queue_position = (
            queue_index
        )

        # Future tasks remain queued.
        if task.status != "active":
            task.status = "queued"

    # --------------------------------------------------------
    # Release battery-infeasible tasks.
    #
    # IMPORTANT:
    # arrival_time_s is NOT reset.
    #
    # Therefore the task keeps accumulating waiting time
    # while it is being reassigned.
    # --------------------------------------------------------

    for task_id in (
        repair.released_task_ids
    ):

        if task_id not in tasks_by_id:

            raise KeyError(
                f"Released task {task_id} "
                "does not exist in tasks_by_id."
            )

        task = tasks_by_id[
            task_id
        ]

        if (
            task.task_id
            == robot.current_task_id
        ):

            raise ValueError(
                "Cannot release active task "
                f"{task.task_id}."
            )

        task.assigned_robot = None
        task.assignment_time_s = None
        task.queue_position = None

        task.status = "waiting"

        if (
            task_id
            in robot.assigned_task_ids
        ):

            robot.assigned_task_ids.remove(
                task_id
            )

    return (
        repair.released_task_ids
    )


def release_robot_future_queue_for_reassignment(
    *,
    robot: RobotState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
) -> tuple[str, ...]:
    """
    Release every future queued task from one robot.

    The active task is never modified.

    Released tasks preserve their original arrival_time_s
    and become waiting tasks for immediate reassignment.
    """

    released_task_ids = tuple(
        robot.queued_task_ids
    )

    robot.queued_task_ids = []

    for task_id in released_task_ids:

        if task_id not in tasks_by_id:
            raise KeyError(
                f"Unknown queued task: {task_id}"
            )

        task = tasks_by_id[
            task_id
        ]

        if (
            task.task_id
            == robot.current_task_id
        ):
            raise RuntimeError(
                "Active task cannot be released: "
                f"{task.task_id}"
            )

        if (
            task.assigned_robot
            not in {
                None,
                robot.robot_id,
            }
        ):
            raise RuntimeError(
                f"Task {task.task_id} belongs to "
                f"{task.assigned_robot}, not "
                f"{robot.robot_id}"
            )

        task.assigned_robot = None
        task.assignment_time_s = None
        task.queue_position = None
        task.status = "waiting"

        if (
            task_id
            in robot.assigned_task_ids
        ):
            robot.assigned_task_ids.remove(
                task_id
            )

    return released_task_ids


# ============================================================
# Queue Projection
# ============================================================

def project_robot_queue(
    robot: RobotState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
    extra_task: Optional[
        TaskState
    ] = None,
) -> QueueProjection:

    pending_tasks = (
        build_pending_queue(
            robot=robot,
            tasks_by_id=tasks_by_id,
            current_time_s=(
                current_time_s
            ),
            extra_task=extra_task,
        )
    )

    projected_time_s = (
        get_robot_projection_start_time(
            robot=robot,
            current_time_s=(
                current_time_s
            ),
        )
    )

    projected_location = (
        get_robot_projection_start_location(
            robot=robot
        )
    )

    projected_tasks: List[
        ProjectedTaskTiming
    ] = []

    for queue_index, task in enumerate(
        pending_tasks
    ):

        queue_position = (
            queue_index
            + 1
        )

        origin = (
            projected_location
        )

        start_time_s = (
            projected_time_s
        )

        # ----------------------------------------------------
        # Robot's projected position -> task source
        # ----------------------------------------------------

        approach_time_s = float(
            travel_time_fn(
                origin,
                task.source,
            )
        )

        if (
            approach_time_s
            < 0.0
        ):

            raise ValueError(
                "Negative approach time: "
                f"{origin} -> "
                f"{task.source}"
            )

        source_arrival_time_s = (
            start_time_s
            + approach_time_s
        )

        # ----------------------------------------------------
        # Task source -> task destination
        # ----------------------------------------------------

        task_travel_time_s = float(
            travel_time_fn(
                task.source,
                task.destination,
            )
        )

        if (
            task_travel_time_s
            < 0.0
        ):

            raise ValueError(
                "Negative task travel time: "
                f"{task.source} -> "
                f"{task.destination}"
            )

        completion_time_s = (
            source_arrival_time_s
            + task_travel_time_s
            + float(
                task.service_time_s
            )
        )

        projected_tasks.append(
            ProjectedTaskTiming(
                task_id=(
                    task.task_id
                ),
                queue_position=(
                    queue_position
                ),
                origin=origin,
                start_time_s=(
                    start_time_s
                ),
                approach_time_s=(
                    approach_time_s
                ),
                source_arrival_time_s=(
                    source_arrival_time_s
                ),
                task_travel_time_s=(
                    task_travel_time_s
                ),
                completion_time_s=(
                    completion_time_s
                ),
            )
        )

        # Next task starts from this task's destination.
        projected_time_s = (
            completion_time_s
        )

        projected_location = (
            task.destination
        )

    return QueueProjection(
        robot_id=(
            robot.robot_id
        ),
        projected_tasks=tuple(
            projected_tasks
        ),
        final_available_time_s=(
            projected_time_s
        ),
        final_location=(
            projected_location
        ),
    )


# ============================================================
# Candidate Evaluation
# ============================================================

def evaluate_candidate_robot(
    robot: RobotState,
    task: TaskState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
) -> CandidateEvaluation:

    if not robot_is_feasible(
        robot=robot,
        task=task,
    ):

        raise ValueError(
            f"Robot {robot.robot_id} "
            f"is not feasible for "
            f"task {task.task_id}."
        )

    current_queue_length = len(
        robot.queued_task_ids
    )

    projection = (
        project_robot_queue(
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

    projected_task = (
        projection.get_task(
            task.task_id
        )
    )

    if projected_task is None:

        raise RuntimeError(
            f"Task {task.task_id} "
            "was not found in "
            f"robot {robot.robot_id} "
            "projection."
        )

    projected_waiting_time_s = max(
        0.0,
        (
            projected_task.start_time_s
            - task.arrival_time_s
        ),
    )

    projected_response_time_s = max(
        0.0,
        (
            projected_task
            .source_arrival_time_s
            - task.arrival_time_s
        ),
    )

    return CandidateEvaluation(

        robot_id=(
            robot.robot_id
        ),

        task_id=(
            task.task_id
        ),

        current_location=(
            robot.current_location
        ),

        assignment_origin=(
            projected_task.origin
        ),

        current_queue_length=(
            current_queue_length
        ),

        projected_queue_length=(
            projection.queue_length
        ),

        projected_queue_position=(
            projected_task.queue_position
        ),

        projected_start_time_s=(
            projected_task.start_time_s
        ),

        projected_approach_time_s=(
            projected_task.approach_time_s
        ),

        projected_source_arrival_time_s=(
            projected_task
            .source_arrival_time_s
        ),

        projected_task_travel_time_s=(
            projected_task
            .task_travel_time_s
        ),

        projected_completion_time_s=(
            projected_task
            .completion_time_s
        ),

        projected_waiting_time_s=(
            projected_waiting_time_s
        ),

        projected_response_time_s=(
            projected_response_time_s
        ),

        queue_projection=(
            projection
        ),
    )


def evaluate_feasible_candidates(
    robots: Iterable[RobotState],
    task: TaskState,
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
    current_time_s: float,
    travel_time_fn: TravelTimeFunction,
) -> List[
    CandidateEvaluation
]:

    feasible_robots = (
        get_feasible_robots(
            robots=robots,
            task=task,
        )
    )

    evaluations = [

        evaluate_candidate_robot(
            robot=robot,
            task=task,
            tasks_by_id=tasks_by_id,
            current_time_s=(
                current_time_s
            ),
            travel_time_fn=(
                travel_time_fn
            ),
        )

        for robot
        in feasible_robots
    ]

    evaluations.sort(
        key=lambda candidate: (
            candidate.robot_id
        )
    )

    return evaluations


# ============================================================
# Queue Commit
# ============================================================

def apply_projected_queue_order(
    robot: RobotState,
    projection: QueueProjection,
) -> None:

    if (
        robot.robot_id
        != projection.robot_id
    ):

        raise ValueError(
            "Projection robot ID does "
            "not match RobotState: "
            f"{projection.robot_id} != "
            f"{robot.robot_id}"
        )

    robot.queued_task_ids = [

        projected.task_id

        for projected
        in projection.projected_tasks
    ]


# ============================================================
# Validation
# ============================================================

def validate_priority(
    priority: int,
) -> None:

    valid_priorities = {
        PRIORITY_LOW,
        PRIORITY_NORMAL,
        PRIORITY_HIGH,
        PRIORITY_EMERGENCY,
    }

    if (
        priority
        not in valid_priorities
    ):

        raise ValueError(
            f"Unsupported priority: "
            f"{priority}"
        )


def validate_task(
    task: TaskState,
) -> None:

    validate_priority(
        task.priority
    )

    if (
        task.source
        == task.destination
    ):

        raise ValueError(
            f"Task {task.task_id} "
            "has identical source "
            "and destination."
        )

    if (
        task.service_time_s
        < 0.0
    ):

        raise ValueError(
            f"Task {task.task_id} "
            "has negative service time."
        )


def validate_robot(
    robot: RobotState,
) -> None:

    if not robot.robot_id:

        raise ValueError(
            "Robot ID cannot be empty."
        )

    if not robot.current_location:

        raise ValueError(
            f"Robot {robot.robot_id} "
            "has no current location."
        )

    if (
        robot.current_task_id
        is not None
        and
        robot.current_task_id
        in robot.queued_task_ids
    ):

        raise ValueError(
            f"Robot {robot.robot_id}: "
            f"active task "
            f"{robot.current_task_id} "
            "appears in future queue."
        )


def validate_scheduler_state(
    robots: Sequence[RobotState],
    tasks_by_id: Dict[
        str,
        TaskState,
    ],
) -> None:

    robot_ids = set()

    for robot in robots:

        validate_robot(
            robot
        )

        if (
            robot.robot_id
            in robot_ids
        ):

            raise ValueError(
                "Duplicate robot ID: "
                f"{robot.robot_id}"
            )

        robot_ids.add(
            robot.robot_id
        )

    for task in (
        tasks_by_id.values()
    ):

        validate_task(
            task
        )