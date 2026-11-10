from __future__ import annotations

import random

from dataclasses import dataclass

from typing import (
    Dict,
    Iterable,
    Optional,
)

from experiments.fleet_sizing.baseline.common import (
    PlacementCandidateEvaluation,
    apply_placement_queue_order,
    evaluate_placement_candidate_robot,
    get_feasible_robots,
    evaluate_battery_feasible_placement_candidates,
    apply_battery_queue_repair,
    repair_projected_queue_for_battery,
)

from experiments.fleet_sizing.models import (
    RobotState,
    TaskState,
)


# ============================================================
# Random Feasible Decision
# ============================================================

@dataclass(frozen=True)
class RandomFeasibleDecision:
    """
    Random Feasible scheduler 的單次派工結果。

    task_id:
        此次要派工的任務 ID。

    selected_robot_id:
        最後選中的 Robot。
        若沒有任何 feasible robot，則為 None。

    candidate_count:
        此次符合條件的候選 Robot 數量。

    candidate_robot_ids:
        所有 feasible robot 的 ID。

    candidate_evaluation:
        選中 Robot 的 duration-free placement evaluation。

        只包含：
            - projected origin
            - queue position
            - tasks ahead
            - projected approach time
            - future queue order

        不包含：
            - actual service time
            - actual completion time
            - projected completion time
            - projected waiting time
            - projected response time

    decision_status:
        "assigned"
        或
        "no_feasible_robot"
    """

    task_id: str

    selected_robot_id: Optional[str]

    candidate_count: int

    candidate_robot_ids: tuple[
        str,
        ...
    ]

    candidate_evaluation: Optional[
        PlacementCandidateEvaluation
    ]

    decision_status: str

    released_task_ids: tuple[
        str,
        ...
    ]


# ============================================================
# Random Feasible Scheduler
# ============================================================

class RandomFeasibleScheduler:
    """
    Baseline 0: Random Feasible

    流程：

        Task Arrival
            ↓
        Capability / Status Filtering
            ↓
        Feasible Robot Set
            ↓
        Random Selection
            ↓
        Priority + Aging Queue Placement
            ↓
        Optional Queue Commit

    Random Feasible 在選擇 Robot 時不考慮：

        - Travel Distance
        - Travel Time
        - Queue Length
        - Robot Workload
        - Waiting Time
        - Response Time
        - Utilization
        - Service Time
        - Completion Time

    Random 只發生於：

        "從 feasible robot 中選哪一台"

    Robot 選定後，仍共用所有 baseline 的：

        - Capability constraints
        - Robot availability rules
        - Priority + Aging
        - Emergency protection
        - Active task non-preemptive
        - Future queue reordering

    IMPORTANT
    ---------
    此版本使用 duration-free placement projection。

    Scheduler 不會讀取：

        TaskState.service_time_s

    也不會利用：

        RobotState.current_task_completion_time_s

    來決定 future queue placement。

    因此不會取得實際部署時無法事先知道的
    future execution information。
    """

    NAME = "random_feasible"

    # ========================================================
    # Constructor
    # ========================================================

    def __init__(
        self,
        seed: Optional[int] = None,
    ) -> None:

        self.seed = seed

        self._rng = random.Random(
            seed
        )

    # ========================================================
    # Candidate Filtering
    # ========================================================

    def get_candidates(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
        tasks_by_id: Optional[
            Dict[
                str,
                TaskState,
            ]
        ] = None,
        current_time_s: float = 0.0,
        travel_time_fn=None,
        enable_battery_model: bool = False,
    ) -> list[
        RobotState
    ]:

        robots_list = list(
            robots
        )

        # --------------------------------------------------------
        # V1 / Battery disabled
        # --------------------------------------------------------

        if not enable_battery_model:

            candidates = list(
                get_feasible_robots(
                    robots=robots_list,
                    task=task,
                )
            )

            candidates.sort(
                key=lambda robot: (
                    robot.robot_id
                )
            )

            return candidates

        # --------------------------------------------------------
        # Battery-aware candidate filtering
        # --------------------------------------------------------

        if tasks_by_id is None:

            raise ValueError(
                "tasks_by_id is required "
                "when battery model is enabled."
            )

        if travel_time_fn is None:

            raise ValueError(
                "travel_time_fn is required "
                "when battery model is enabled."
            )

        evaluations = (
            evaluate_battery_feasible_placement_candidates(
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
                enable_battery_model=True,
            )
        )

        feasible_robot_ids = {
            evaluation.robot_id
            for evaluation
            in evaluations
        }

        candidates = [
            robot
            for robot
            in robots_list
            if robot.robot_id
            in feasible_robot_ids
        ]

        candidates.sort(
            key=lambda robot: (
                robot.robot_id
            )
        )

        return candidates

    # ========================================================
    # Robot Selection
    # ========================================================

    def select_robot(
        self,
        robots: Iterable[
            RobotState
        ],
        task: TaskState,
    ) -> Optional[
        RobotState
    ]:
        """
        從 feasible robots 中隨機選擇一台。

        若沒有 feasible robot，
        回傳 None。
        """

        candidates = (
            self.get_candidates(
                robots=robots,
                task=task,
            )
        )

        if not candidates:
            return None

        return self._rng.choice(
            candidates
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
    ) -> RandomFeasibleDecision:
        """
        執行一次 Random Feasible 派工。

        Parameters
        ----------
        robots:
            系統目前所有 RobotState。

        task:
            此次要進行派工的新任務。

        tasks_by_id:
            系統中所有已知 TaskState。
            key 為 task_id。

        current_time_s:
            Scheduler 做出決策時的模擬時間。

            此時間只用於 Priority + Aging，
            不用來預測 future completion time。

        travel_time_fn:
            Travel-time function：

                travel_time_fn(
                    source,
                    destination,
                ) -> float

            Random Feasible 不使用 travel time
            來選擇 Robot。

            但選完 Robot 後仍需要計算
            duration-free placement，
            以取得：

                projected origin
                projected approach time

            這些資訊可供 logging 與後續分析使用。

        commit_queue:
            False：
                僅做 placement projection，
                不修改 RobotState。

            True：
                將 Priority + Aging 後的
                future queue 寫回 selected robot。

        Returns
        -------
        RandomFeasibleDecision
        """

        # ----------------------------------------------------
        # Convert to list once.
        #
        # 避免傳入 generator 時，
        # 後續需要再次存取 robots 卻已被消耗。
        # ----------------------------------------------------

        robots_list = list(
            robots
        )

        # ----------------------------------------------------
        # 1. Feasible Candidate Set
        # ----------------------------------------------------

        candidates = (
            self.get_candidates(
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
            robot.robot_id
            for robot
            in candidates
        )

        # ----------------------------------------------------
        # 2. No Feasible Robot
        # ----------------------------------------------------

        if not candidates:

            return RandomFeasibleDecision(
                task_id=(
                    task.task_id
                ),

                selected_robot_id=None,

                candidate_count=0,

                candidate_robot_ids=(),

                candidate_evaluation=None,

                decision_status=(
                    "no_feasible_robot"
                ),

                released_task_ids=(),
            )

        # ----------------------------------------------------
        # 3. Random Robot Selection
        # ----------------------------------------------------

        selected_robot = (
            self._rng.choice(
                candidates
            )
        )

        # ----------------------------------------------------
        # 4. Duration-Free Placement Evaluation
        #
        # IMPORTANT:
        #
        # 這裡不再使用：
        #
        #   evaluate_candidate_robot()
        #
        # 因為舊 evaluation 會推算：
        #
        #   start time
        #   completion time
        #   waiting time
        #   response time
        #
        # 新版本只建立 queue placement。
        # ----------------------------------------------------

        evaluation = (
            evaluate_placement_candidate_robot(
                robot=selected_robot,

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
            )
        )

        # ----------------------------------------------------
        # 5. Optional Queue Commit
        # ----------------------------------------------------

        released_task_ids: tuple[
            str,
            ...
        ] = ()

        if commit_queue:

            if enable_battery_model:

                battery_repair = (
                    repair_projected_queue_for_battery(
                        robot=selected_robot,
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
                        evaluation
                        .queue_projection
                    ),
                )

        # ----------------------------------------------------
        # 6. Decision Result
        # ----------------------------------------------------

        return RandomFeasibleDecision(
            task_id=(
                task.task_id
            ),

            selected_robot_id=(
                selected_robot.robot_id
            ),

            candidate_count=len(
                candidates
            ),

            candidate_robot_ids=(
                candidate_robot_ids
            ),

            candidate_evaluation=(
                evaluation
            ),

            decision_status=(
                "assigned"
            ),

            released_task_ids=(
                released_task_ids
            ),
        )

    # ========================================================
    # RNG Reset
    # ========================================================

    def reset(
        self,
        seed: Optional[int] = None,
    ) -> None:
        """
        重設 Random Feasible 的 RNG。

        用於 paired experiment，
        讓相同 scheduler seed
        可以重新產生相同 random sequence。

        若沒有傳入新 seed，
        則使用目前保存的 self.seed。
        """

        if seed is None:
            seed = self.seed

        self.seed = seed

        self._rng = random.Random(
            seed
        )