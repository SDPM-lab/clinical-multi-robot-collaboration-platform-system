from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from experiments.fleet_sizing.baseline.common import (
    PlacementCandidateEvaluation,
    apply_placement_queue_order,
    evaluate_battery_feasible_placement_candidates,
    apply_battery_queue_repair,
    repair_projected_queue_for_battery,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Candidate
# ============================================================


@dataclass(frozen=True)
class DynamicWeightedCandidate:
    robot_id: str
    task_id: str

    placement_evaluation: PlacementCandidateEvaluation

    observable_load: int

    normalized_approach: float
    normalized_load: float

    weighted_cost: float


# ============================================================
# Decision
# ============================================================


@dataclass(frozen=True)
class DynamicWeightedDecision:
    task_id: str

    selected_robot_id: Optional[str]

    candidate_count: int

    candidate_robot_ids: tuple[str, ...]

    selected_candidate: Optional[
        DynamicWeightedCandidate
    ]

    all_candidates: tuple[
        DynamicWeightedCandidate,
        ...
    ]

    load_imbalance: float

    dynamic_alpha: float

    alpha_min: float
    alpha_max: float

    decision_status: str

    released_task_ids: tuple[
        str,
        ...
    ]


# ============================================================
# Scheduler
# ============================================================


class DynamicWeightedScheduler:
    """
    Adaptive Travel-Load Weighted Scheduler.

    Cost:

        cost_i
        =
        alpha_t * normalized_approach_i
        +
        (1 - alpha_t) * normalized_load_i

    Dynamic alpha:

        imbalance_t
        =
        max(normalized_load)
        -
        min(normalized_load)

        alpha_t
        =
        alpha_max
        -
        (alpha_max - alpha_min)
        * imbalance_t

    Interpretation:

        balanced robot loads
            -> imbalance near 0
            -> alpha near alpha_max
            -> emphasize travel efficiency

        highly imbalanced robot loads
            -> imbalance near 1
            -> alpha near alpha_min
            -> emphasize load balancing

    Important:
        This scheduler is duration-free.

        It does NOT use:
            - realized task.service_time_s
            - actual future completion time
            - ground-truth remaining busy time
    """

    NAME = "dynamic_weighted"

    DEFAULT_ALPHA_MIN = 0.4
    DEFAULT_ALPHA_MAX = 0.8

    def __init__(
        self,
        alpha_min: float = DEFAULT_ALPHA_MIN,
        alpha_max: float = DEFAULT_ALPHA_MAX,
    ) -> None:

        self._validate_alpha_range(
            alpha_min=alpha_min,
            alpha_max=alpha_max,
        )

        self.alpha_min = float(
            alpha_min
        )

        self.alpha_max = float(
            alpha_max
        )

    # ========================================================
    # Validation
    # ========================================================

    @staticmethod
    def _validate_alpha_range(
        alpha_min: float,
        alpha_max: float,
    ) -> None:

        alpha_min = float(
            alpha_min
        )

        alpha_max = float(
            alpha_max
        )

        if not 0.0 <= alpha_min <= 1.0:
            raise ValueError(
                "alpha_min must be in [0, 1]."
            )

        if not 0.0 <= alpha_max <= 1.0:
            raise ValueError(
                "alpha_max must be in [0, 1]."
            )

        if alpha_min > alpha_max:
            raise ValueError(
                "alpha_min cannot be greater "
                "than alpha_max."
            )

    # ========================================================
    # Observable Load
    # ========================================================

    @staticmethod
    def get_observable_load(
        robot: RobotState,
    ) -> int:

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

        value = float(
            value
        )

        maximum = float(
            maximum
        )

        if value < 0.0:
            raise ValueError(
                "Normalization value "
                "cannot be negative."
            )

        if maximum < 0.0:
            raise ValueError(
                "Normalization maximum "
                "cannot be negative."
            )

        if maximum == 0.0:
            return 0.0

        return (
            value
            / maximum
        )

    # ========================================================
    # Load Imbalance
    # ========================================================

    @staticmethod
    def calculate_load_imbalance(
        normalized_loads: Iterable[
            float
        ],
    ) -> float:

        values = [
            float(value)
            for value
            in normalized_loads
        ]

        if not values:
            return 0.0

        for value in values:

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    "Normalized load must be "
                    "in [0, 1]."
                )

        return (
            max(values)
            -
            min(values)
        )

    # ========================================================
    # Dynamic Alpha
    # ========================================================

    def calculate_dynamic_alpha(
        self,
        load_imbalance: float,
    ) -> float:

        load_imbalance = float(
            load_imbalance
        )

        if not 0.0 <= load_imbalance <= 1.0:
            raise ValueError(
                "Load imbalance must be "
                "in [0, 1]."
            )

        return (
            self.alpha_max
            -
            (
                self.alpha_max
                - self.alpha_min
            )
            * load_imbalance
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
        tasks_by_id: dict[
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
                current_time_s=current_time_s,
                travel_time_fn=travel_time_fn,
                enable_battery_model=(
                    enable_battery_model
                ),
            )
        )

    # ========================================================
    # Candidate Construction
    # ========================================================

    def build_candidates(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
        tasks_by_id: dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn,
        enable_battery_model: bool = False,
    ) -> tuple[
        list[
            DynamicWeightedCandidate
        ],
        float,
        float,
    ]:

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

            return (
                [],
                0.0,
                self.alpha_max,
            )

        # ----------------------------------------------------
        # Observable loads
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Candidate-set max normalization
        # ----------------------------------------------------

        max_approach = max(
            evaluation
            .projected_approach_time_s

            for evaluation
            in placement_evaluations
        )

        max_load = max(
            observable_loads.values()
        )

        normalized_loads = {
            robot_id:
            self.normalize_by_max(
                load,
                max_load,
            )
            for robot_id, load
            in observable_loads.items()
        }

        # ----------------------------------------------------
        # Dynamic imbalance + alpha
        # ----------------------------------------------------

        load_imbalance = (
            self.calculate_load_imbalance(
                normalized_loads.values()
            )
        )

        dynamic_alpha = (
            self.calculate_dynamic_alpha(
                load_imbalance
            )
        )

        # ----------------------------------------------------
        # Candidate weighted cost
        # ----------------------------------------------------

        candidates: list[
            DynamicWeightedCandidate
        ] = []

        for evaluation in (
            placement_evaluations
        ):

            observable_load = (
                observable_loads[
                    evaluation.robot_id
                ]
            )

            normalized_approach = (
                self.normalize_by_max(
                    evaluation
                    .projected_approach_time_s,

                    max_approach,
                )
            )

            normalized_load = (
                normalized_loads[
                    evaluation.robot_id
                ]
            )

            weighted_cost = (
                dynamic_alpha
                * normalized_approach

                +
                (
                    1.0
                    - dynamic_alpha
                )
                * normalized_load
            )

            candidates.append(
                DynamicWeightedCandidate(
                    robot_id=(
                        evaluation.robot_id
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
            key=lambda candidate:
                candidate.robot_id
        )

        return (
            candidates,
            load_imbalance,
            dynamic_alpha,
        )

    # ========================================================
    # Selection
    # ========================================================

    @staticmethod
    def get_selection_key(
        candidate: DynamicWeightedCandidate,
    ) -> tuple[
        float,
        float,
        int,
        str,
    ]:

        return (
            candidate.weighted_cost,

            candidate
            .placement_evaluation
            .projected_approach_time_s,

            candidate.observable_load,

            candidate.robot_id,
        )

    def select_candidate(
        self,
        candidates: Iterable[
            DynamicWeightedCandidate
        ],
    ) -> Optional[
        DynamicWeightedCandidate
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
        tasks_by_id: dict[
            str,
            TaskState,
        ],
        current_time_s: float,
        travel_time_fn,
        commit_queue: bool = False,
        enable_battery_model: bool = False,
    ) -> DynamicWeightedDecision:

        robots_list = list(
            robots
        )

        robots_by_id = {
            robot.robot_id: robot
            for robot
            in robots_list
        }

        (
            candidates,
            load_imbalance,
            dynamic_alpha,
        ) = self.build_candidates(
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

        candidate_robot_ids = tuple(
            candidate.robot_id
            for candidate
            in candidates
        )

        if not candidates:

            return (
                DynamicWeightedDecision(
                    task_id=(
                        task.task_id
                    ),

                    selected_robot_id=None,

                    candidate_count=0,

                    candidate_robot_ids=(),

                    selected_candidate=None,

                    all_candidates=(),

                    load_imbalance=0.0,

                    dynamic_alpha=(
                        self.alpha_max
                    ),

                    alpha_min=(
                        self.alpha_min
                    ),

                    alpha_max=(
                        self.alpha_max
                    ),

                    decision_status=(
                        "no_feasible_robot"
                    ),

                    released_task_ids=(),
                )
            )

        selected = (
            self.select_candidate(
                candidates
            )
        )

        if selected is None:

            raise RuntimeError(
                "Candidate list is non-empty "
                "but no candidate was selected."
            )

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

        return (
            DynamicWeightedDecision(
                task_id=(
                    task.task_id
                ),

                selected_robot_id=(
                    selected.robot_id
                ),

                candidate_count=(
                    len(candidates)
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

                load_imbalance=(
                    load_imbalance
                ),

                dynamic_alpha=(
                    dynamic_alpha
                ),

                alpha_min=(
                    self.alpha_min
                ),

                alpha_max=(
                    self.alpha_max
                ),

                decision_status=(
                    "assigned"
                ),

                released_task_ids=(
                    released_task_ids
                ),
            )
        )