from __future__ import annotations

from dataclasses import dataclass

from typing import (
    Dict,
    Iterable,
    Optional,
)

from experiments.fleet_sizing.baseline.common import (
    PlacementCandidateEvaluation,
    apply_battery_queue_repair,
    apply_placement_queue_order,
    evaluate_battery_feasible_placement_candidates,
    repair_projected_queue_for_battery,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Static Weighted Candidate
# ============================================================


@dataclass(frozen=True)
class StaticWeightedCandidate:
    """
    One candidate robot evaluated by Static Weighted.

    observable_load:
        Scheduler-visible robot load before assigning
        the incoming task.

        load =
            active-task indicator
            +
            number of queued tasks

    normalized_approach:
        Candidate projected approach time normalized by
        the maximum projected approach time among all
        feasible candidates.

    normalized_load:
        Candidate observable load normalized by the
        maximum observable load among all feasible
        candidates.

    weighted_cost:
        alpha * normalized_approach
        +
        (1 - alpha) * normalized_load
    """

    robot_id: str

    task_id: str

    placement_evaluation: (
        PlacementCandidateEvaluation
    )

    observable_load: int

    normalized_approach: float

    normalized_load: float

    weighted_cost: float


# ============================================================
# Static Weighted Decision
# ============================================================


@dataclass(frozen=True)
class StaticWeightedDecision:
    """
    Result of one Static Weighted scheduling decision.
    """

    task_id: str

    selected_robot_id: Optional[str]

    candidate_count: int

    candidate_robot_ids: tuple[
        str,
        ...
    ]

    selected_candidate: Optional[
        StaticWeightedCandidate
    ]

    all_candidates: tuple[
        StaticWeightedCandidate,
        ...
    ]

    alpha: float

    decision_status: str

    released_task_ids: tuple[
        str,
        ...
    ]


# ============================================================
# Static Weighted Scheduler
# ============================================================


class StaticWeightedScheduler:
    """
    Baseline 2: Static Weighted Heuristic

    The scheduler balances two observable factors:

        1. Projected Approach Travel
        2. Current Observable Robot Load

    Cost:

        cost =
            alpha * normalized_approach
            +
            (1 - alpha) * normalized_load

    where:

        projected approach
            =
        travel time from the robot's projected origin
        immediately before the incoming task
        to the incoming task source

    and:

        observable load
            =
        active-task indicator
        +
        existing queued task count


    IMPORTANT
    ---------
    This scheduler is duration-free.

    It does NOT use:

        - TaskState.service_time_s
        - actual future completion time
        - projected waiting time
        - projected completion time
        - estimated remaining service duration

    Therefore it does not rely on future information that
    would be unavailable in a real online environment.
    """

    NAME = "static_weighted"

    DEFAULT_ALPHA = 0.5

    # ========================================================
    # Constructor
    # ========================================================

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
    ) -> None:

        self._validate_alpha(
            alpha
        )

        self.alpha = float(
            alpha
        )

    # ========================================================
    # Alpha Validation
    # ========================================================

    @staticmethod
    def _validate_alpha(
        alpha: float,
    ) -> None:

        if not (
            0.0
            <= float(alpha)
            <= 1.0
        ):

            raise ValueError(
                "alpha must be between "
                "0.0 and 1.0."
            )

    # ========================================================
    # Observable Load
    # ========================================================

    @staticmethod
    def get_observable_load(
        robot: RobotState,
    ) -> int:
        """
        Scheduler-visible robot load.

        load =
            1 if robot currently has an active task
            +
            number of future queued tasks

        The incoming task is NOT included.

        Examples
        --------
        idle, queue=[]
            -> load = 0

        busy, queue=[]
            -> load = 1

        idle, queue=[A, B]
            -> load = 2

        busy, queue=[A, B]
            -> load = 3
        """

        active_load = int(
            robot.current_task_id
            is not None
        )

        queue_load = len(
            robot.queued_task_ids
        )

        return (
            active_load
            + queue_load
        )

    # ========================================================
    # Normalization
    # ========================================================

    @staticmethod
    def normalize_by_max(
        value: float,
        maximum: float,
    ) -> float:
        """
        Normalize using candidate-set maximum.

        value_norm =
            value / maximum

        If maximum == 0:

            value_norm = 0

        This avoids division by zero when all candidates
        have zero cost for one dimension.
        """

        value = float(
            value
        )

        maximum = float(
            maximum
        )

        if value < 0.0:
            raise ValueError(
                "Normalization value "
                "must be non-negative."
            )

        if maximum < 0.0:
            raise ValueError(
                "Normalization maximum "
                "must be non-negative."
            )

        if maximum == 0.0:
            return 0.0

        return (
            value
            / maximum
        )

    # ========================================================
    # Placement Evaluation
    # ========================================================

    def evaluate_placements(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
        tasks_by_id: Dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn,
        enable_battery_model: bool = False,
    ) -> list[
        PlacementCandidateEvaluation
    ]:

        return (
            evaluate_battery_feasible_placement_candidates(
                robots=robots,
                task=task,
                tasks_by_id=tasks_by_id,
                current_time_s=(
                    current_time_s
                ),
                travel_time_fn=(
                    travel_time_fn
                ),
                enable_battery_model=(
                    enable_battery_model
                ),
            )
        )

    # ========================================================
    # Static Weighted Candidate Construction
    # ========================================================

    def build_candidates(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
        tasks_by_id: Dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn,
        enable_battery_model: bool = False,
    ) -> list[
        StaticWeightedCandidate
    ]:
        """
        Build normalized Static Weighted candidates.

        Steps
        -----
        1. Evaluate duration-free projected placement.
        2. Calculate current observable load.
        3. Find candidate-set maxima.
        4. Normalize travel and load.
        5. Calculate weighted cost.
        """

        robots_list = list(
            robots
        )

        robots_by_id = {
            robot.robot_id: robot
            for robot
            in robots_list
        }

        placement_evaluations = (
            self.evaluate_placements(
                robots=robots_list,
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
                enable_battery_model=(
                    enable_battery_model
                ),
            )
        )

        if not placement_evaluations:
            return []

        observable_loads = {
            evaluation.robot_id:
                self.get_observable_load(
                    robots_by_id[
                        evaluation.robot_id
                    ]
                )

            for evaluation
            in placement_evaluations
        }

        max_approach = max(
            evaluation
            .projected_approach_time_s

            for evaluation
            in placement_evaluations
        )

        max_load = max(
            observable_loads.values()
        )

        candidates: list[
            StaticWeightedCandidate
        ] = []

        for evaluation in (
            placement_evaluations
        ):

            robot_id = (
                evaluation.robot_id
            )

            observable_load = (
                observable_loads[
                    robot_id
                ]
            )

            normalized_approach = (
                self.normalize_by_max(
                    value=(
                        evaluation
                        .projected_approach_time_s
                    ),
                    maximum=(
                        max_approach
                    ),
                )
            )

            normalized_load = (
                self.normalize_by_max(
                    value=(
                        observable_load
                    ),
                    maximum=(
                        max_load
                    ),
                )
            )

            weighted_cost = (
                self.alpha
                * normalized_approach

                + (
                    1.0
                    - self.alpha
                )
                * normalized_load
            )

            candidates.append(
                StaticWeightedCandidate(
                    robot_id=(
                        robot_id
                    ),

                    task_id=(
                        task.task_id
                    ),

                    placement_evaluation=(
                        evaluation
                    ),

                    observable_load=(
                        observable_load
                    ),

                    normalized_approach=(
                        normalized_approach
                    ),

                    normalized_load=(
                        normalized_load
                    ),

                    weighted_cost=(
                        weighted_cost
                    ),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                candidate.robot_id
            )
        )

        return candidates

    # ========================================================
    # Selection Key
    # ========================================================

    @staticmethod
    def get_selection_key(
        candidate: StaticWeightedCandidate,
    ) -> tuple:
        """
        Deterministic Static Weighted selection order.

        Primary objective:
            minimum weighted cost

        Tie breakers:
            1. shorter projected approach
            2. lower current observable load
            3. robot_id
        """

        return (
            candidate.weighted_cost,

            candidate
            .placement_evaluation
            .projected_approach_time_s,

            candidate.observable_load,

            candidate.robot_id,
        )

    # ========================================================
    # Candidate Selection
    # ========================================================

    def select_candidate(
        self,
        candidates: Iterable[
            StaticWeightedCandidate
        ],
    ) -> Optional[
        StaticWeightedCandidate
    ]:

        candidates_list = list(
            candidates
        )

        if not candidates_list:
            return None

        return min(
            candidates_list,
            key=self.get_selection_key,
        )

    # ========================================================
    # Decision
    # ========================================================

    def decide(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
        tasks_by_id: Dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn,
        commit_queue: bool = False,
        enable_battery_model: bool = False,
    ) -> StaticWeightedDecision:
        """
        Execute one Static Weighted scheduling decision.
        """

        # ----------------------------------------------------
        # Materialize Iterable once.
        # ----------------------------------------------------

        robots_list = list(
            robots
        )

        robots_by_id = {
            robot.robot_id: robot
            for robot
            in robots_list
        }

        # ----------------------------------------------------
        # 1. Build Weighted Candidates
        # ----------------------------------------------------

        candidates = (
            self.build_candidates(
                robots=robots_list,
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
                enable_battery_model=(
                    enable_battery_model
                ),
            )
        )

        candidate_robot_ids = tuple(
            candidate.robot_id
            for candidate
            in candidates
        )

        # ----------------------------------------------------
        # 2. No Feasible Robot
        # ----------------------------------------------------

        if not candidates:

            return StaticWeightedDecision(
                task_id=(
                    task.task_id
                ),

                selected_robot_id=None,

                candidate_count=0,

                candidate_robot_ids=(),

                selected_candidate=None,

                all_candidates=(),

                alpha=(
                    self.alpha
                ),

                decision_status=(
                    "no_feasible_robot"
                ),

                released_task_ids=(),
            )

        # ----------------------------------------------------
        # 3. Select Minimum Weighted Cost
        # ----------------------------------------------------

        selected = (
            self.select_candidate(
                candidates
            )
        )

        if selected is None:

            raise RuntimeError(
                "Static Weighted had feasible "
                "candidates but failed to "
                "select one."
            )

        # ----------------------------------------------------
        # 4. Optional Queue Commit
        # ----------------------------------------------------

        released_task_ids: tuple[
            str,
            ...
        ] = ()

        if commit_queue:

            selected_robot = (
                robots_by_id[
                    selected.robot_id
                ]
            )

            if enable_battery_model:

                battery_repair = (
                    repair_projected_queue_for_battery(
                        robot=selected_robot,
                        queue_projection=(
                            selected
                            .placement_evaluation
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

                released_task_ids = (
                    apply_battery_queue_repair(
                        robot=selected_robot,
                        repair=(
                            battery_repair
                        ),
                        tasks_by_id=(
                            tasks_by_id
                        ),
                    )
                )

            else:

                apply_placement_queue_order(
                    robot=selected_robot,
                    projection=(
                        selected
                        .placement_evaluation
                        .queue_projection
                    ),
                )

        # ----------------------------------------------------
        # 5. Decision
        # ----------------------------------------------------

        return StaticWeightedDecision(
            task_id=(
                task.task_id
            ),

            selected_robot_id=(
                selected.robot_id
            ),

            candidate_count=len(
                candidates
            ),

            candidate_robot_ids=(
                candidate_robot_ids
            ),

            selected_candidate=(
                selected
            ),

            all_candidates=tuple(
                candidates
            ),

            alpha=(
                self.alpha
            ),

            decision_status=(
                "assigned"
            ),

            released_task_ids=(
                released_task_ids
            ),
        )