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
# Projected Nearest Decision
# ============================================================


@dataclass(frozen=True)
class ProjectedNearestDecision:
    """
    Result of one Projected Nearest scheduling decision.

    selected_evaluation uses duration-free placement
    information only.

    The scheduler does NOT predict:

        - future task completion time
        - future waiting time
        - source arrival time
        - realized service duration

    It only uses:

        - projected queue position
        - projected origin
        - projected approach travel time
    """

    task_id: str

    selected_robot_id: Optional[str]

    candidate_count: int

    candidate_robot_ids: tuple[
        str,
        ...
    ]

    selected_evaluation: Optional[
        PlacementCandidateEvaluation
    ]

    released_task_ids: tuple[
        str,
        ...
    ]

    decision_status: str


# ============================================================
# Projected Nearest Scheduler
# ============================================================


class ProjectedNearestScheduler:
    """
    Baseline 1: Projected Nearest Robot

    Unlike a simple current-position nearest-robot rule,
    this scheduler considers where each robot is expected
    to be immediately before the incoming task.

    Example:

        Robot M01 current location:
            pharmacy

        Active task destination:
            ward_a_2

        Incoming task source:
            lab

    Because the active task is non-preemptive, the incoming
    task cannot start from pharmacy.

    Its projected origin is:

        ward_a_2

    Therefore the relevant travel cost is:

        ward_a_2 -> lab

    rather than:

        pharmacy -> lab


    IMPORTANT
    ---------
    This scheduler uses duration-free placement projection.

    It does NOT need to know:

        - how long the active task will take
        - how long queued tasks will take
        - their actual service_time_s
        - their actual completion times

    It only needs to know the sequence of future tasks and
    their destinations.
    """

    NAME = "projected_nearest"

    # ========================================================
    # Candidate Evaluation
    # ========================================================

    def evaluate_candidates(
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
        """
        Evaluate every feasible robot using duration-free
        placement projection.

        Returned candidates are sorted by robot_id by the
        shared common implementation.
        """

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
    # Selection Key
    # ========================================================

    @staticmethod
    def get_selection_key(
        evaluation: PlacementCandidateEvaluation,
    ) -> tuple:
        """
        Projected Nearest objective.

        Primary objective:
            minimum projected approach time

        Tie breakers:
            1. fewer tasks ahead
            2. shorter projected queue
            3. robot_id

        The tie breakers intentionally avoid future timing
        information.

        In particular, this scheduler does NOT use:

            projected source-arrival time
            projected waiting time
            projected completion time
        """

        return (
            evaluation
            .projected_approach_time_s,

            evaluation
            .tasks_ahead_count,

            evaluation
            .projected_queue_length,

            evaluation.robot_id,
        )

    # ========================================================
    # Select Evaluation
    # ========================================================

    def select_evaluation(
        self,
        evaluations: Iterable[
            PlacementCandidateEvaluation
        ],
    ) -> Optional[
        PlacementCandidateEvaluation
    ]:
        """
        Return the candidate with minimum Projected Nearest
        selection key.
        """

        evaluations_list = list(
            evaluations
        )

        if not evaluations_list:
            return None

        return min(
            evaluations_list,
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
    ) -> ProjectedNearestDecision:
        """
        Execute one Projected Nearest scheduling decision.

        Parameters
        ----------
        robots:
            Current robot states.

        task:
            Newly arrived task.

        tasks_by_id:
            Known tasks used to reconstruct existing queues.

        current_time_s:
            Current scheduler time.

            Used only for Priority + Aging queue ordering.
            It is NOT used to infer actual future completion.

        travel_time_fn:
            Estimated navigation travel-time function.

        commit_queue:
            If True, commit the selected duration-free
            future queue order to the chosen robot.

        Returns
        -------
        ProjectedNearestDecision
        """

        # ----------------------------------------------------
        # Convert Iterable once.
        #
        # This also fixes the generator-consumption issue:
        # evaluate first, then later access robots again.
        # ----------------------------------------------------

        robots_list = list(
            robots
        )

        # ----------------------------------------------------
        # 1. Evaluate Feasible Robots
        # ----------------------------------------------------

        evaluations = (
            self.evaluate_candidates(
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
            evaluation.robot_id
            for evaluation
            in evaluations
        )

        # ----------------------------------------------------
        # 2. No Feasible Robot
        # ----------------------------------------------------

        if not evaluations:

            return ProjectedNearestDecision(
                task_id=task.task_id,
                selected_robot_id=None,
                candidate_count=0,
                candidate_robot_ids=(),
                selected_evaluation=None,
                released_task_ids=(),
                decision_status="no_feasible_robot",
            )

        # ----------------------------------------------------
        # 3. Select Minimum Projected Approach
        # ----------------------------------------------------

        selected = (
            self.select_evaluation(
                evaluations
            )
        )

        if selected is None:

            raise RuntimeError(
                "Projected Nearest had feasible "
                "evaluations but failed to "
                "select a candidate."
            )

        # ----------------------------------------------------
        # 4. Optional Queue Commit
        # ----------------------------------------------------

        released_task_ids: tuple[
            str,
            ...
        ] = ()

        if commit_queue:

            robots_by_id = {
                robot.robot_id: robot
                for robot
                in robots_list
            }

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
                        .queue_projection
                    ),
                )

        # ----------------------------------------------------
        # 5. Return Decision
        # ----------------------------------------------------

        return ProjectedNearestDecision(
            task_id=(
                task.task_id
            ),

            selected_robot_id=(
                selected.robot_id
            ),

            candidate_count=len(
                evaluations
            ),

            candidate_robot_ids=(
                candidate_robot_ids
            ),

            selected_evaluation=(
                selected
            ),

            released_task_ids=(
                released_task_ids
            ),

            decision_status="assigned",
        )