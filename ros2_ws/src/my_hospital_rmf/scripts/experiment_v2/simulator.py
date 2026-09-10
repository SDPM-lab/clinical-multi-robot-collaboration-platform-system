#!/usr/bin/env python3

import random
import time

from copy import (
    deepcopy,
)

from typing import (
    Optional,
)

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.projection import (
    calculate_distance,
    get_place,
)

from scheduler_v2.task_selector import (
    select_next_task,
    sort_tasks,
)

from scheduler_v2.robot_selection.random_feasible import (
    select_random_projected_feasible_robot
)

from scheduler_v2.robot_selection.nearest import (
    select_nearest_feasible_robot,
)

from scheduler_v2.robot_selection.weighted import (
    select_weighted_feasible_robot,
)

from scheduler_v2.robot_selection.dynamic_weighted import (
    evaluate_dynamic_weighted_reassignment,
)

from experiment_v2.models import (
    BaselineMethod,
    RobotEpisodeRecord,
    SchedulerDecisionRecord,
    SimulationResult,
    SimulationScenario,
    TaskExecutionRecord,
)

from scheduler_v2.battery import (
    calculate_battery_consumption,
    calculate_remaining_battery,
    has_enough_battery_for_task,
)

from scheduler_v2.config import (
    BATTERY_DRAIN_PER_METER,
    MIN_BATTERY_LEVEL,
)


# ==========================================================
# Constants
# ==========================================================

TIME_EPSILON = 1e-9


# ==========================================================
# Static Simulator
# ==========================================================

class StaticSimulator:
    """
    Static Baseline 共用的 Event-Driven Simulator。

    支援：

    - Random Feasible
    - Projected Nearest
    - Weighted Heuristic

    Static 的意思：

    Task 一旦 Assigned 到某台 Robot，
    後續即使新的高優先級 Task 插隊，
    原 Task 也不會改 Assigned Robot。

    Dynamic Reassignment
    會在之後的 Dynamic Simulator 加入。
    """

    def __init__(
        self,
        scenario: SimulationScenario,
        method: BaselineMethod | str,
        seed: int = 0,
    ):

        # --------------------------------------------------
        # Deep Copy
        #
        # 不允許 Simulator 修改原始 Scenario。
        #
        # 同一個 Scenario 才能公平地重跑：
        #
        # Random
        # Nearest
        # Weighted
        # --------------------------------------------------

        self.scenario = deepcopy(
            scenario
        )

        self.method = BaselineMethod(
            method
        )

        self.rng = random.Random(
            seed
        )

        self.current_time = 0.0

        # --------------------------------------------------
        # Reset Tasks
        # --------------------------------------------------

        for task in self.scenario.tasks:

            task.status = "pending"

            task.assigned_robot = None

        # --------------------------------------------------
        # Runtime States
        # --------------------------------------------------

        self.runtimes: dict[
            str,
            RobotRuntimeState,
        ] = {}

        for robot in self.scenario.robots:

            # 目前 Scenario 尚未提供：
            #
            # initial running task
            # initial remaining time
            #
            # 因此無法合理表示
            # Episode 一開始已 Busy 的 Robot。
            if robot.status == "busy":

                raise ValueError(
                    "Initial busy robot is not "
                    "supported without an "
                    "initial running task"
                )

            self.runtimes[
                robot.robot_id
            ] = RobotRuntimeState(
                robot=robot,
                robot_speed_mps=(
                    self.scenario
                    .robot_speed_mps
                ),
            )

        # --------------------------------------------------
        # Future Arrivals
        # --------------------------------------------------

        self.future_tasks = sorted(
            self.scenario.tasks,
            key=lambda task: (
                task.created_at,
                task.task_id,
            ),
        )

        self.arrival_index = 0

        # --------------------------------------------------
        # Experiment Records
        # --------------------------------------------------

        self.task_records = {
            task.task_id: (
                TaskExecutionRecord(
                    task_id=task.task_id,
                    priority=task.priority,
                    arrival_time=(
                        task.created_at
                    ),
                )
            )
            for task
            in self.scenario.tasks
        }

        self.decision_records: list[
            SchedulerDecisionRecord
        ] = []

        self.robot_records = {
            robot.robot_id: (
                RobotEpisodeRecord(
                    robot_id=(
                        robot.robot_id
                    ),
                )
            )
            for robot
            in self.scenario.robots
        }


    # ======================================================
    # Robot Selection
    # ======================================================

    def _select_robot(
        self,
        task: Task,
    ):
        """
        根據目前 Baseline Method
        呼叫對應 Robot Selector。
        """

        runtimes = list(
            self.runtimes.values()
        )

        if (
            self.method
            ==
            BaselineMethod
            .RANDOM_FEASIBLE
        ):

            return (
                select_random_projected_feasible_robot(
                    task=task,
                    runtimes=runtimes,
                    places=(
                        self.scenario.places
                    ),
                    current_time=(
                        self.current_time
                    ),
                    rng=self.rng,
                )
            )

        if (
            self.method
            ==
            BaselineMethod
            .PROJECTED_NEAREST
        ):

            return (
                select_nearest_feasible_robot(
                    task=task,
                    runtimes=runtimes,
                    places=(
                        self.scenario
                        .places
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

        if (
            self.method
            ==
            BaselineMethod
            .WEIGHTED_HEURISTIC
        ):

            return (
                select_weighted_feasible_robot(
                    task=task,
                    runtimes=runtimes,
                    places=(
                        self.scenario
                        .places
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

        raise ValueError(
            "Unsupported baseline method: "
            f"{self.method}"
        )


    # ======================================================
    # Assignment
    # ======================================================

    def _assign_task(
        self,
        task: Task,
    ) -> None:
        """
        對新到達 Task 執行一次 Static Assignment。
        """

        decision_start = (
            time.perf_counter()
        )

        selected_robot = (
            self._select_robot(
                task=task,
            )
        )

        decision_duration = (
            time.perf_counter()
            -
            decision_start
        )

        self.decision_records.append(
            SchedulerDecisionRecord(
                task_id=task.task_id,
                simulation_time=(
                    self.current_time
                ),
                method=(
                    self.method.value
                ),
                selected_robot=(
                    None
                    if selected_robot is None
                    else selected_robot.robot_id
                ),
                decision_duration_seconds=(
                    decision_duration
                ),
                decision_type="assignment",
            )
        )

        record = (
            self.task_records[
                task.task_id
            ]
        )

        # --------------------------------------------------
        # No Feasible Robot
        #
        # Static Simulator 目前沒有 Robot recovery、
        # Charging completion 等狀態事件。
        #
        # 因此如果現在沒有任何 Feasible Robot，
        # 後面也不會突然變成 Feasible。
        # --------------------------------------------------

        if selected_robot is None:

            task.status = "failed"

            record.status = "failed"

            record.failure_reason = (
                "no_feasible_robot"
            )

            return

        runtime = (
            self.runtimes[
                selected_robot.robot_id
            ]
        )

        task.assigned_robot = (
            selected_robot.robot_id
        )

        task.status = "assigned"

        record.assigned_robot = (
            selected_robot.robot_id
        )

        record.assigned_at = (
            self.current_time
        )

        record.status = "assigned"

        runtime.waiting_tasks.append(
            task
        )


    # ======================================================
    # Start Task
    # ======================================================

    def _start_task(
        self,
        runtime: RobotRuntimeState,
        task: Task,
    ) -> None:
        """
        Robot 開始真正執行 Task。

        Start Time 定義：

            Robot 開始前往 Task Source 的時間

        所以 Waiting Time：

            Start Time - Arrival Time
        """

        runtime.waiting_tasks.remove(
            task
        )

        robot = runtime.robot

        record = (
            self.task_records[
                task.task_id
            ]
        )

        current_place = Place(
            place_id=(
                f"{robot.robot_id}:current"
            ),
            x=robot.x,
            y=robot.y,
            map_name=robot.map_name,
        )

        source = get_place(
            places=(
                self.scenario.places
            ),
            place_id=task.source,
        )

        destination = get_place(
            places=(
                self.scenario.places
            ),
            place_id=task.destination,
        )

        distance_to_source = (
            calculate_distance(
                start=current_place,
                end=source,
            )
        )

        task_distance = (
            calculate_distance(
                start=source,
                end=destination,
            )
        )

        travel_distance = (
            distance_to_source
            +
            task_distance
        )

        # ----------------------------------------------------------
        # Battery Reservation
        #
        # Battery 在 Task Start 時立即扣除預期耗電。
        #
        # Running Task 之後不可 Preempt，
        # 因此這份 Energy Budget
        # 視為已經承諾給此 Running Task。
        # ----------------------------------------------------------

        battery_consumption = (
            calculate_battery_consumption(
                travel_distance=(
                    travel_distance
                ),
                drain_per_meter=(
                    BATTERY_DRAIN_PER_METER
                ),
            )
        )

        if not has_enough_battery_for_task(
            battery=robot.battery,
            expected_consumption=(
                battery_consumption
            ),
            safety_threshold=(
                MIN_BATTERY_LEVEL
            ),
        ):

            raise RuntimeError(
                "Battery safety invariant "
                "violated when starting "
                f"task {task.task_id} "
                f"on robot {robot.robot_id}"
            )

        robot.battery = (
            calculate_remaining_battery(
                battery=robot.battery,
                consumption=(
                    battery_consumption
                ),
            )
        )

        travel_time = (
            travel_distance
            /
            runtime.robot_speed_mps
        )

        execution_duration = (
            travel_time
            +
            self.scenario
            .service_time_seconds
        )

        task.status = "running"

        record.status = "running"

        record.start_time = (
            self.current_time
        )

        record.travel_distance = (
            travel_distance
        )

        runtime.running_task = task

        runtime.running_remaining_time = (
            execution_duration
        )

        robot.status = "busy"

        robot_record = (
            self.robot_records[
                robot.robot_id
            ]
        )

        robot_record.total_travel_distance += (
            travel_distance
        )

        robot_record.busy_time += (
            execution_duration
        )


    # ======================================================
    # Start Waiting Tasks
    # ======================================================

    def _start_idle_robots(
        self,
    ) -> bool:
        """
        所有 Idle Robot
        從自己的 Waiting Queue 中選下一個 Task。

        Queue Selection 共用：

        Priority + Aging
        +
        Emergency Protection
        """

        started_any = False

        for robot_id in sorted(
            self.runtimes
        ):

            runtime = (
                self.runtimes[
                    robot_id
                ]
            )

            if (
                runtime.running_task
                is not None
            ):

                continue

            if (
                runtime.robot.status
                !=
                "idle"
            ):

                continue

            if not runtime.waiting_tasks:

                continue

            next_task = (
                select_next_task(
                    tasks=(
                        runtime
                        .waiting_tasks
                    ),
                    current_time=(
                        self.current_time
                    ),
                )
            )

            if next_task is None:

                continue

            self._start_task(
                runtime=runtime,
                task=next_task,
            )

            started_any = True

        return started_any


    # ======================================================
    # Complete Tasks
    # ======================================================

    def _complete_finished_tasks(
        self,
    ) -> bool:
        """
        完成 remaining_time 已經到 0 的 Running Tasks。
        """

        completed_any = False

        for robot_id in sorted(
            self.runtimes
        ):

            runtime = (
                self.runtimes[
                    robot_id
                ]
            )

            task = (
                runtime.running_task
            )

            if task is None:

                continue

            if (
                runtime
                .running_remaining_time
                >
                TIME_EPSILON
            ):

                continue

            destination = (
                get_place(
                    places=(
                        self.scenario
                        .places
                    ),
                    place_id=(
                        task.destination
                    ),
                )
            )

            robot = runtime.robot

            # Robot 完成任務後，
            # 位置更新到 Task Destination。
            robot.x = destination.x

            robot.y = destination.y

            robot.map_name = (
                destination.map_name
            )

            robot.status = "idle"

            task.status = "completed"

            record = (
                self.task_records[
                    task.task_id
                ]
            )

            record.status = "completed"

            record.completion_time = (
                self.current_time
            )

            robot_record = (
                self.robot_records[
                    robot.robot_id
                ]
            )

            robot_record.completed_tasks += 1

            runtime.running_task = None

            runtime.running_remaining_time = 0.0

            completed_any = True

        return completed_any


    # ======================================================
    # Task Arrivals
    # ======================================================

    def _collect_current_arrivals(
        self,
    ) -> list[Task]:
        """
        取得目前 simulation time
        所有剛到達的 Task。
        """

        arrivals = []

        while (
            self.arrival_index
            <
            len(self.future_tasks)
        ):

            task = (
                self.future_tasks[
                    self.arrival_index
                ]
            )

            if (
                task.created_at
                >
                self.current_time
                +
                TIME_EPSILON
            ):

                break

            arrivals.append(
                task
            )

            self.arrival_index += 1

        return arrivals


    # ======================================================
    # Process Current Time
    # ======================================================

    def _settle_current_time(
        self,
    ) -> None:
        """
        將目前 simulation time
        所有可以立即完成的事件處理完。

        同一時間的事件順序：

        1. Complete Running Tasks
        2. Receive New Arrivals
        3. Assign New Tasks
        4. Start Idle Robots

        這樣可以確保：

        - Running Task 不會被搶占
        - 同時間的新 Emergency
          可以先於舊 Waiting Task
        """

        while True:

            changed = False

            # ----------------------------------------------
            # 1. Complete
            # ----------------------------------------------

            if self._complete_finished_tasks():

                changed = True

            # ----------------------------------------------
            # 2. Arrivals
            # ----------------------------------------------

            arrivals = (
                self._collect_current_arrivals()
            )

            if arrivals:

                changed = True

                # 同時間到達時，
                # 先按照共用 Priority + Aging 排序。
                ordered_arrivals = (
                    sort_tasks(
                        tasks=arrivals,
                        current_time=(
                            self.current_time
                        ),
                    )
                )

                # ------------------------------------------
                # 3. Assignment
                # ------------------------------------------

                for task in ordered_arrivals:

                    self._assign_task(
                        task=task
                    )

            # ----------------------------------------------
            # 4. Start
            # ----------------------------------------------

            if self._start_idle_robots():

                changed = True

            if not changed:

                break


    # ======================================================
    # Advance Time
    # ======================================================

    def _next_event_time(
        self,
    ) -> Optional[float]:
        """
        下一個事件可能是：

        - 下一個 Task Arrival
        - 某台 Robot 完成 Running Task
        """

        event_times = []

        # --------------------------------------------------
        # Next Arrival
        # --------------------------------------------------

        if (
            self.arrival_index
            <
            len(self.future_tasks)
        ):

            next_task = (
                self.future_tasks[
                    self.arrival_index
                ]
            )

            event_times.append(
                next_task.created_at
            )

        # --------------------------------------------------
        # Next Completion
        # --------------------------------------------------

        for runtime in (
            self.runtimes.values()
        ):

            if (
                runtime.running_task
                is None
            ):

                continue

            remaining = (
                runtime
                .running_remaining_time
            )

            if (
                remaining
                <=
                TIME_EPSILON
            ):

                continue

            event_times.append(
                self.current_time
                +
                remaining
            )

        if not event_times:

            return None

        return min(
            event_times
        )


    def _advance_time(
        self,
        next_time: float,
    ) -> None:
        """
        Simulation Clock 往下一個 Event 前進，
        並同步扣除 Running Task remaining time。
        """

        next_time = float(
            next_time
        )

        delta = (
            next_time
            -
            self.current_time
        )

        if (
            delta
            <
            -TIME_EPSILON
        ):

            raise RuntimeError(
                "Simulation time "
                "cannot move backwards"
            )

        delta = max(
            0.0,
            delta,
        )

        for runtime in (
            self.runtimes.values()
        ):

            if (
                runtime.running_task
                is None
            ):

                continue

            runtime.running_remaining_time = (
                max(
                    0.0,
                    runtime
                    .running_remaining_time
                    -
                    delta,
                )
            )

        self.current_time = (
            next_time
        )


    # ======================================================
    # Termination
    # ======================================================

    def _has_unfinished_work(
        self,
    ) -> bool:

        if (
            self.arrival_index
            <
            len(self.future_tasks)
        ):

            return True

        for runtime in (
            self.runtimes.values()
        ):

            if (
                runtime.running_task
                is not None
            ):

                return True

            if runtime.waiting_tasks:

                return True

        return False


    # ======================================================
    # Run Episode
    # ======================================================

    def run(
        self,
    ) -> SimulationResult:
        """
        執行完整 Static Episode。
        """

        while True:

            # ------------------------------------------------
            # 把目前時間所有事件處理完。
            # ------------------------------------------------

            self._settle_current_time()

            # ------------------------------------------------
            # 若沒有未完成工作：
            # Episode 結束。
            # ------------------------------------------------

            if not self._has_unfinished_work():

                break

            # ------------------------------------------------
            # 找下一個事件時間。
            # ------------------------------------------------

            next_time = (
                self._next_event_time()
            )

            if next_time is None:

                raise RuntimeError(
                    "Simulation has unfinished "
                    "work but no future event"
                )

            self._advance_time(
                next_time=next_time
            )

        return SimulationResult(
            scenario_name=(
                self.scenario.name
            ),
            method=(
                self.method.value
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
# Dynamic Weighted Simulator
# ==========================================================

class DynamicWeightedSimulator(
    StaticSimulator
):
    """
    Dynamic Weighted Heuristic Simulator。

    Initial Assignment：
        使用與 Static Weighted 完全相同的
        Weighted Heuristic。

    Dynamic Reassignment：
        在 Completion / Arrival Event 發生後，
        重新評估目前所有 Waiting Tasks。

    第一版採用 bounded single-pass：

        每個 root event batch 中，
        每個 Waiting Task 最多評估一次。

    因此目前：
        cascade_depth = 1

    Running Task：
        永遠不可 reassignment。
    """

    def __init__(
        self,
        scenario: SimulationScenario,
        seed: int = 0,
    ):

        super().__init__(
            scenario=scenario,
            method=(
                BaselineMethod
                .DYNAMIC_WEIGHTED_HEURISTIC
            ),
            seed=seed,
        )

        # ======================================================
        # Immediate Reversal Guard
        #
        # Task ID -> 最近一次 Reassignment 時
        # 該 Task 離開的 Robot。
        #
        # 例如：
        #
        # T1:
        # R1 -> R2
        #
        # 則：
        # last_departed_robot["T1"] = "R1"
        #
        # 下一次不允許直接：
        # R2 -> R1
        #
        # 除非 Current Robot 已 infeasible。
        # ======================================================

        self.last_departed_robot: dict[
            str,
            str,
        ] = {}


    # ======================================================
    # Initial Assignment
    # ======================================================

    def _select_robot(
        self,
        task: Task,
    ):
        """
        Dynamic Weighted 的 Initial Assignment
        與 Static Weighted 完全一致。

        差別只在：
        Task 尚未開始執行前，
        後續事件允許重新評估 Assigned Robot。
        """

        return (
            select_weighted_feasible_robot(
                task=task,
                runtimes=list(
                    self.runtimes.values()
                ),
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


    # ======================================================
    # Root Event
    # ======================================================

    @staticmethod
    def _build_root_event_id(
        completed_task_ids: list[str],
        arrivals: list[Task],
    ) -> Optional[str]:
        """
        同一 simulation time
        可能同時有：

        - 多個 Completion
        - 多個 Arrival

        我們把同一時間的事件視為
        一個 atomic event batch。

        好處：

        不會因為同一時間有 3 個 Arrival，
        就把全部 Waiting Tasks
        重複 Reevaluation 3 次。
        """

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
        """
        取得此次 Dynamic Pass
        開始時的所有 Waiting Tasks。

        使用 Priority + Aging
        做 deterministic ordering。

        Snapshot 的目的：

        即使某個 Task 被搬到另一台 Robot，
        同一次 pass 中它也不會再次被處理。
        """

        waiting_tasks = []

        for runtime in (
            self.runtimes.values()
        ):

            for task in (
                runtime.waiting_tasks
            ):

                waiting_tasks.append(
                    task
                )

        if not waiting_tasks:

            return []

        return (
            sort_tasks(
                tasks=waiting_tasks,
                current_time=(
                    self.current_time
                ),
            )
        )


    # ======================================================
    # Queue Migration
    # ======================================================

    def _move_waiting_task(
        self,
        task: Task,
        new_robot_id: str,
    ) -> None:
        """
        真正執行 Waiting Task Reassignment。

        只允許：

            Assigned + Waiting

        不允許：

            Running Task
        """

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

        if (
            old_robot_id
            not in self.runtimes
        ):

            raise RuntimeError(
                "Unknown current robot: "
                f"{old_robot_id}"
            )

        if (
            new_robot_id
            not in self.runtimes
        ):

            raise RuntimeError(
                "Unknown new robot: "
                f"{new_robot_id}"
            )

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

        # --------------------------------------------------
        # Running Task Protection
        # --------------------------------------------------

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
                "is not in waiting queue "
                f"of {old_robot_id}"
            )

        if any(
            queued.task_id
            ==
            task.task_id
            for queued
            in new_runtime.waiting_tasks
        ):

            raise RuntimeError(
                f"Task {task.task_id} "
                "already exists in "
                f"waiting queue of "
                f"{new_robot_id}"
            )

        # --------------------------------------------------
        # Move Queue
        # --------------------------------------------------

        old_runtime.waiting_tasks.remove(
            task
        )

        new_runtime.waiting_tasks.append(
            task
        )

        task.assigned_robot = (
            new_robot_id
        )

        # TaskExecutionRecord
        # 保留原 assigned_at，
        # 因為那是 Initial Assignment Time。
        #
        # assigned_robot 則更新成
        # 最新 Assigned Robot。
        record = (
            self.task_records[
                task.task_id
            ]
        )

        record.assigned_robot = (
            new_robot_id
        )


    # ======================================================
    # Immediate Reversal Guard
    # ======================================================

    def _is_immediate_reversal(
        self,
        task: Task,
        selected_robot_id: str,
    ) -> bool:
        """
        判斷新的 Reassignment 是否會
        立即回到 Task 剛離開的 Robot。

        例如：

            R1 -> R2

        last_departed_robot = R1

        下一次：

            R2 -> R1

        會回傳 True。

        但：

            R2 -> R3

        回傳 False。
        """

        last_robot = (
            self.last_departed_robot.get(
                task.task_id
            )
        )

        if last_robot is None:

            return False

        return (
            selected_robot_id
            ==
            last_robot
        )


    # ======================================================
    # Dynamic Reassignment Pass
    # ======================================================

    def _run_dynamic_reassignment_pass(
        self,
        root_event_id: str,
    ) -> bool:
        """
        對此次 Event 後的
        所有 Waiting Tasks
        做一次 Dynamic Weighted Reevaluation。

        第一版規則：

            每個 Task 最多一次。

        所以：
            cascade_depth = 1
        """

        waiting_tasks = (
            self._snapshot_waiting_tasks()
        )

        if not waiting_tasks:

            return False

        changed_any = False

        for task in waiting_tasks:

            # 理論上 snapshot 裡全部都是 assigned waiting。
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
                    "Waiting task "
                    "has no assigned_robot: "
                    f"{task.task_id}"
                )

            decision_start = (
                time.perf_counter()
            )

            evaluation = (
                evaluate_dynamic_weighted_reassignment(
                    task=task,
                    runtimes=list(
                        self.runtimes.values()
                    ),
                    places=(
                        self.scenario
                        .places
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

            decision_duration = (
                time.perf_counter()
                -
                decision_start
            )

            # --------------------------------------------------
            # Immediate Reversal Guard
            #
            # 一般情況下：
            #
            #     R1 -> R2
            #     R2 -> R1
            #
            # 這種立即反向改派會被阻止。
            #
            # 但如果 Current Robot 已經 infeasible，
            # Safety 優先，不得阻止。
            # --------------------------------------------------

            reversal_blocked = (
                evaluation.changed
                and
                evaluation.reason
                !=
                "current_infeasible"
                and
                self._is_immediate_reversal(
                    task=task,
                    selected_robot_id=(
                        evaluation.selected_robot
                    ),
                )
            )

            selected_robot_id = (
                previous_robot
                if reversal_blocked
                else evaluation.selected_robot
            )

            # --------------------------------------------------
            # Record Reevaluation
            #
            # Stay 也必須記。
            # --------------------------------------------------

            self.decision_records.append(
                SchedulerDecisionRecord(
                    task_id=(
                        task.task_id
                    ),
                    simulation_time=(
                        self.current_time
                    ),
                    method=(
                        self.method.value
                    ),
                    selected_robot=(
                        selected_robot_id
                    ),
                    previous_robot=(
                        previous_robot
                    ),
                    decision_duration_seconds=(
                        decision_duration
                    ),
                    decision_type=(
                        "reassignment"
                    ),
                    root_event_id=(
                        root_event_id
                    ),
                    cascade_depth=1,
                )
            )

            # --------------------------------------------------
            # Stay
            # --------------------------------------------------

            if (
                selected_robot_id
                ==
                previous_robot
            ):

                continue

            # --------------------------------------------------
            # Actual Reassignment
            # --------------------------------------------------

            self._move_waiting_task(
                task=task,
                new_robot_id=(
                    selected_robot_id
                ),
            )

            # 記錄這次 Task 剛離開哪台 Robot。
            #
            # 例如：
            #
            # previous_robot = R1
            # selected_robot = R2
            #
            # 下一次會阻止 R2 -> R1。
            self.last_departed_robot[
                task.task_id
            ] = previous_robot

            changed_any = True

        return changed_any


    # ======================================================
    # Process Current Time
    # ======================================================

    def _settle_current_time(
        self,
    ) -> None:
        """
        Dynamic Weighted 的事件順序：

        1. Complete Running Tasks
        2. Receive Arrivals
        3. Initial Assignment
        4. Dynamic Reassignment Pass
        5. Start Idle Robots

        關鍵：

        Reassignment 必須發生在 Start 前。

        因為 Task 一旦 Start，
        就成為 non-preemptive Running Task。
        """

        while True:

            changed = False

            # ==================================================
            # 1. 找出本次即將完成的 Tasks
            #
            # 要在 _complete_finished_tasks()
            # 前先記 ID，
            # 因為完成後 runtime.running_task
            # 會被清成 None。
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

            # ==================================================
            # 2. Complete
            # ==================================================

            if self._complete_finished_tasks():

                changed = True

            # ==================================================
            # 3. Arrivals
            # ==================================================

            arrivals = (
                self._collect_current_arrivals()
            )

            ordered_arrivals = []

            if arrivals:

                changed = True

                ordered_arrivals = (
                    sort_tasks(
                        tasks=arrivals,
                        current_time=(
                            self.current_time
                        ),
                    )
                )

                # ==============================================
                # Initial Assignment
                # ==============================================

                for task in ordered_arrivals:

                    self._assign_task(
                        task=task
                    )

            # ==================================================
            # 4. Dynamic Reassignment
            # ==================================================

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

                if (
                    self
                    ._run_dynamic_reassignment_pass(
                        root_event_id=(
                            root_event_id
                        ),
                    )
                ):

                    changed = True

            # ==================================================
            # 5. Start
            # ==================================================

            if self._start_idle_robots():

                changed = True

            if not changed:

                break


# ==========================================================
# Public Helper
# ==========================================================

def run_static_simulation(
    scenario: SimulationScenario,
    method: BaselineMethod | str,
    seed: int = 0,
) -> SimulationResult:
    """
    執行一個 Static Baseline Episode。
    """

    simulator = StaticSimulator(
        scenario=scenario,
        method=method,
        seed=seed,
    )

    return simulator.run()


def run_dynamic_weighted_simulation(
    scenario: SimulationScenario,
    seed: int = 0,
) -> SimulationResult:
    """
    執行 Dynamic Weighted Heuristic Episode。
    """

    simulator = (
        DynamicWeightedSimulator(
            scenario=scenario,
            seed=seed,
        )
    )

    return simulator.run()