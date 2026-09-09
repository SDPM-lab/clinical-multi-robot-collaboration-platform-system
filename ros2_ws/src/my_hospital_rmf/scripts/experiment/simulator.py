#!/usr/bin/env python3

import copy
import math

from dataclasses import (
    dataclass,
    field,
)

from scheduler.capability_matcher import (
    capability_matching,
)


# ==========================================================
# Task Execution Record
# ==========================================================

@dataclass
class TaskExecutionRecord:

    task_id: str
    priority: int

    robot_id: str | None

    arrival_time: float
    start_time: float | None
    completion_time: float | None

    waiting_time: float | None
    service_time: float | None

    travel_distance: float | None

    success: bool


# ==========================================================
# Running Task State
#
# 已經真正開始執行的任務。
# Running Task 採 non-preemptive：開始後不被後到高優先任務中斷。
# ==========================================================

@dataclass
class RunningTaskState:

    task: object

    arrival_time: float
    start_time: float
    completion_time: float

    service_time: float
    travel_distance: float

    destination_x: float
    destination_y: float


# ==========================================================
# Robot Simulation State
#
# 每台 Robot 擁有：
# 1. running_task：正在執行的任務
# 2. waiting_tasks：已指派但尚未開始的本地 Queue
# ==========================================================

@dataclass
class RobotSimulationState:

    robot: object

    x: float
    y: float

    running_task: RunningTaskState | None = None

    waiting_tasks: list = field(
        default_factory=list
    )

    total_distance: float = 0.0
    total_busy_time: float = 0.0
    completed_tasks: int = 0


# ==========================================================
# Distance Helper
# ==========================================================

def euclidean_distance(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:

    dx = x2 - x1
    dy = y2 - y1

    return math.sqrt(
        dx * dx
        + dy * dy
    )


# ==========================================================
# Baseline Simulator
#
# 架構：
#
# Task arrival
#   -> Capability Matching
#   -> Robot Selection
#   -> 加入該 Robot waiting queue
#
# Robot idle
#   -> FCFS / Priority 從自己的 waiting queue 選下一筆
#   -> running_task
#
# Priority 只重排尚未開始的 waiting tasks，
# 不搶占已經開始的 running task。
# ==========================================================

class BaselineSimulator:

    def __init__(
        self,
        scenario,
        task_scheduler,
        robot_scheduler,
        robot_speed: float = 1.0,
        service_time: float = 5.0,
        enable_dynamic_reassignment: bool = False,
    ):

        self.scenario = scenario

        self.waypoints = copy.deepcopy(
            scenario.waypoints
        )

        self.task_scheduler = (
            task_scheduler
        )

        self.robot_scheduler = (
            robot_scheduler
        )

        self.robot_speed = (
            robot_speed
        )

        self.fixed_service_time = (
            service_time
        )

        # Dynamic Reassignment 預設關閉，
        # 以保留 RL v1 / 舊 Baseline 的實驗語意。
        self.enable_dynamic_reassignment = (
            enable_dynamic_reassignment
        )

        self.task_arrival_times = (
            copy.deepcopy(
                scenario.task_arrival_times
            )
        )

        # 每筆 Task 原始 FCFS 次序。
        # Dynamic Reassignment 後仍保留原始到達順序，
        # 不把 reassignment 時間當成新的 arrival time。
        self.task_fcfs_order = {
            task.task_id: index
            for index, task
            in enumerate(
                scenario.tasks
            )
        }

        # 紀錄 Dynamic Reassignment，
        # 方便之後做測試與統計。
        self.reassignment_events = []

        self.future_tasks = sorted(
            copy.deepcopy(
                scenario.tasks
            ),
            key=lambda task:
                self.task_arrival_times[
                    task.task_id
                ],
        )

        self.robot_states = {}

        for robot in copy.deepcopy(
            scenario.robots
        ):

            self.robot_states[
                robot.robot_id
            ] = RobotSimulationState(
                robot=robot,
                x=robot.x,
                y=robot.y,
            )

        self.records = []
        self.current_time = 0.0


    # ======================================================
    # Queue Selection
    #
    # FCFSScheduler：queue 中最早者
    # PriorityScheduler：priority 高者；同 priority 保持 FCFS
    # ======================================================

    def select_next_robot_task(
        self,
        sim_state,
    ):

        if not sim_state.waiting_tasks:
            return None

        return self.task_scheduler.select(
            sim_state.waiting_tasks
        )


    # ======================================================
    # Remaining Running Time
    # ======================================================

    def get_remaining_running_time(
        self,
        sim_state,
    ) -> float:

        running = (
            sim_state.running_task
        )

        if running is None:
            return 0.0

        return max(
            0.0,
            running.completion_time
            - self.current_time,
        )


    # ======================================================
    # Estimate Service From Position
    #
    # 回傳：
    # total_distance, service_time, destination_x, destination_y
    # ======================================================

    def estimate_task_service(
        self,
        task,
        start_x: float,
        start_y: float,
    ):

        if task.source not in self.waypoints:
            raise RuntimeError(
                f"Unknown task source: {task.source}"
            )

        if task.destination not in self.waypoints:
            raise RuntimeError(
                "Unknown task destination: "
                f"{task.destination}"
            )

        source_x, source_y = (
            self.waypoints[
                task.source
            ]
        )

        destination_x, destination_y = (
            self.waypoints[
                task.destination
            ]
        )

        robot_to_source = (
            euclidean_distance(
                start_x,
                start_y,
                source_x,
                source_y,
            )
        )

        source_to_destination = (
            euclidean_distance(
                source_x,
                source_y,
                destination_x,
                destination_y,
            )
        )

        total_distance = (
            robot_to_source
            + source_to_destination
        )

        travel_time = (
            total_distance
            / self.robot_speed
        )

        service_time = (
            travel_time
            + self.fixed_service_time
        )

        return (
            total_distance,
            service_time,
            destination_x,
            destination_y,
        )


    # ======================================================
    # Project Waiting Queue Order
    #
    # 不修改真正的 waiting_tasks。
    # 依目前 Task Scheduler 規則，
    # 模擬這批 waiting tasks 真正會以什麼順序執行。
    # ======================================================

    def get_projected_queue_order(
        self,
        tasks,
    ):

        projected_queue = list(
            tasks
        )

        ordered_tasks = []

        while projected_queue:

            selected_task = (
                self.task_scheduler.select(
                    projected_queue
                )
            )

            if selected_task is None:
                break

            ordered_tasks.append(
                selected_task
            )

            projected_queue.remove(
                selected_task
            )

        return ordered_tasks


    # ======================================================
    # Detect Displaced Waiting Tasks
    #
    # 判斷 new_task 加入 selected Robot 的 waiting queue 後，
    # 是否因 Priority 關係插到既有 Task 前面。
    #
    # 只回傳「因 new_task 插入而被往後推」的既有 Task。
    #
    # 若 new_task 只是排在原 queue 尾端：
    #   -> 回傳空 list
    #   -> 不觸發 Dynamic Reassignment
    # ======================================================

    def get_displaced_tasks(
        self,
        sim_state,
        new_task,
    ):

        existing_tasks = list(
            sim_state.waiting_tasks
        )

        if not existing_tasks:
            return []

        before_order = (
            self.get_projected_queue_order(
                existing_tasks
            )
        )

        after_tasks = list(
            existing_tasks
        )

        after_tasks.append(
            new_task
        )

        after_order = (
            self.get_projected_queue_order(
                after_tasks
            )
        )

        new_task_index = next(
            (
                index
                for index, task
                in enumerate(after_order)
                if (
                    task.task_id
                    ==
                    new_task.task_id
                )
            ),
            None,
        )

        if new_task_index is None:
            raise RuntimeError(
                "New task not found in "
                "projected queue order: "
                f"{new_task.task_id}"
            )

        displaced_tasks = []

        for task in before_order:

            before_index = next(
                index
                for index, item
                in enumerate(before_order)
                if item.task_id == task.task_id
            )

            after_index = next(
                index
                for index, item
                in enumerate(after_order)
                if item.task_id == task.task_id
            )

            # new_task 加入後，
            # 原 Task 的 index 變大，
            # 表示它真的被往後推。
            if after_index > before_index:
                displaced_tasks.append(
                    task
                )

        return displaced_tasks


    # ======================================================
    # Insert Waiting Task With Original FCFS Order
    #
    # waiting_tasks 本身維持原始 arrival order。
    #
    # PriorityScheduler 仍會：
    #   Priority 高者先選
    #   同 Priority 時依 list order -> FCFS
    #
    # FCFSScheduler 也能直接使用。
    # ======================================================

    def insert_waiting_task(
        self,
        sim_state,
        task,
    ):

        task_key = (
            self.task_arrival_times[
                task.task_id
            ],
            self.task_fcfs_order.get(
                task.task_id,
                len(
                    self.task_fcfs_order
                ),
            ),
        )

        insert_index = len(
            sim_state.waiting_tasks
        )

        for index, existing_task in enumerate(
            sim_state.waiting_tasks
        ):

            existing_key = (
                self.task_arrival_times[
                    existing_task.task_id
                ],
                self.task_fcfs_order.get(
                    existing_task.task_id,
                    len(
                        self.task_fcfs_order
                    ),
                ),
            )

            if task_key < existing_key:

                insert_index = index
                break

        sim_state.waiting_tasks.insert(
            insert_index,
            task,
        )


    # ======================================================
    # Find Waiting Task Robot
    # ======================================================

    def find_waiting_task_robot(
        self,
        task_id,
    ):

        for robot_id, sim_state in (
            self.robot_states.items()
        ):

            for task in (
                sim_state.waiting_tasks
            ):

                if (
                    task.task_id
                    ==
                    task_id
                ):
                    return robot_id

        return None


    # ======================================================
    # Cascade Reassignment For Displaced Waiting Tasks
    #
    # 規則：
    #
    # 1. 只有真的被插隊延後的 Waiting Task 才重新評估。
    #
    # 2. Running Task 永遠不重新派工。
    #
    # 3. 如果 Task 搬到新 Robot 後，
    #    又插隊影響該 Robot 原本的 Waiting Tasks，
    #    只有那些被影響的 Tasks 繼續 Cascade Reassignment。
    #
    # 4. 如果搬過去沒有影響既有 Queue，
    #    Cascade 到此停止。
    #
    # 5. 使用 processed_states + max_steps
    #    防止同一 Cascade 發生無限震盪。
    # ======================================================

    def reassign_displaced_tasks(
        self,
        displaced_tasks,
        trigger_task_id,
    ):

        # ------------------------------------------
        # Pending Reassignment Queue
        #
        # 每筆：
        #
        # (
        #     task,
        #     direct_trigger_task_id,
        #     cascade_depth,
        # )
        #
        # root trigger 例如：
        #
        # D -> B -> E
        #
        # trigger_task_id = D
        #
        # B 的 direct trigger = D
        # E 的 direct trigger = B
        # ------------------------------------------

        pending_reassignments = [
            (
                task,
                trigger_task_id,
                1,
            )
            for task in displaced_tasks
        ]

        # ------------------------------------------
        # 防止：
        #
        # B@robot1
        # -> robot2
        # -> 又回 robot1
        # -> 又重新處理
        #
        # 同一 Cascade 中，
        # 同一 Task 在同一 Robot 最多重新評估一次。
        # ------------------------------------------

        processed_states = set()

        # 任務數 * Robot 數 * 2
        # 作為 Cascade 安全上限。
        max_steps = max(
            10,
            len(
                self.task_fcfs_order
            )
            *
            max(
                1,
                len(
                    self.robot_states
                ),
            )
            *
            2,
        )

        steps = 0

        while pending_reassignments:

            steps += 1

            if steps > max_steps:

                raise RuntimeError(
                    "Dynamic reassignment "
                    "exceeded maximum cascade steps. "
                    f"root_trigger={trigger_task_id}, "
                    f"max_steps={max_steps}"
                )

            (
                task,
                direct_trigger_task_id,
                cascade_depth,
            ) = pending_reassignments.pop(
                0
            )

            # --------------------------------------
            # 找這筆 Waiting Task 目前在哪台 Robot。
            # --------------------------------------

            current_robot_id = (
                self.find_waiting_task_robot(
                    task.task_id
                )
            )

            if current_robot_id is None:
                continue

            state_signature = (
                task.task_id,
                current_robot_id,
            )

            if (
                state_signature
                in processed_states
            ):
                continue

            processed_states.add(
                state_signature
            )

            current_sim_state = (
                self.robot_states[
                    current_robot_id
                ]
            )

            # --------------------------------------
            # 暫時從原 Robot 移除。
            #
            # 否則 projection 會把 task
            # 同時算成 existing + candidate。
            # --------------------------------------

            remove_index = next(
                (
                    index
                    for index, item
                    in enumerate(
                        current_sim_state
                        .waiting_tasks
                    )
                    if (
                        item.task_id
                        ==
                        task.task_id
                    )
                ),
                None,
            )

            if remove_index is None:
                continue

            current_sim_state.waiting_tasks.pop(
                remove_index
            )

            # --------------------------------------
            # 重新計算所有 Robot。
            # --------------------------------------

            all_robots = (
                self.prepare_robots_for_scheduling(
                    task
                )
            )

            candidates = (
                capability_matching(
                    task.required_capabilities,
                    all_robots,
                )
            )

            # 防呆：
            # 如果沒有 Candidate，
            # 放回原 Robot。
            if not candidates:

                self.insert_waiting_task(
                    current_sim_state,
                    task,
                )

                continue

            assignment = (
                self.robot_scheduler.schedule(
                    task,
                    candidates,
                )
            )

            if (
                assignment.decision_status
                != "assigned"
                or assignment.robot_id
                is None
            ):

                self.insert_waiting_task(
                    current_sim_state,
                    task,
                )

                continue

            new_robot_id = (
                assignment.robot_id
            )

            new_sim_state = (
                self.robot_states[
                    new_robot_id
                ]
            )

            changed_robot = (
                new_robot_id
                !=
                current_robot_id
            )

            # --------------------------------------
            # Cascade Trigger
            #
            # 只有真的搬到「另一台 Robot」時，
            # 才檢查這筆 Task 是否插隊影響
            # 新 Robot 原本的 Waiting Tasks。
            #
            # 如果最後仍留在原 Robot，
            # 只是把剛剛暫時移除的 Task 放回去，
            # 不視為新的插隊事件。
            # --------------------------------------

            if changed_robot:

                newly_displaced_tasks = (
                    self.get_displaced_tasks(
                        new_sim_state,
                        task,
                    )
                )

            else:

                newly_displaced_tasks = []

            # --------------------------------------
            # 正式放入新的 Queue。
            # --------------------------------------

            self.insert_waiting_task(
                new_sim_state,
                task,
            )

            # --------------------------------------
            # Reassignment Log
            # --------------------------------------

            self.reassignment_events.append(
                {
                    # 最初觸發整個 Cascade 的 Task。
                    #
                    # 例如：
                    # D -> B -> E
                    #
                    # D
                    "trigger_task_id":
                        trigger_task_id,

                    # 直接造成此 Task 被重新評估的 Task。
                    #
                    # B：
                    # direct = D
                    #
                    # E：
                    # direct = B
                    "direct_trigger_task_id":
                        direct_trigger_task_id,

                    "task_id":
                        task.task_id,

                    "from_robot_id":
                        current_robot_id,

                    "to_robot_id":
                        new_robot_id,

                    "changed_robot":
                        changed_robot,

                    "cascade_depth":
                        cascade_depth,
                }
            )

            # --------------------------------------
            # 只有新 Robot 上真的有人被插隊，
            # 才繼續 Cascade。
            #
            # B -> Robot2
            #
            # 若：
            #
            # B E F
            #
            # newly_displaced = [E, F]
            #
            # 若：
            #
            # E F B
            #
            # newly_displaced = []
            # -> Cascade 停止。
            # --------------------------------------

            for displaced_task in (
                newly_displaced_tasks
            ):

                pending_reassignments.append(
                    (
                        displaced_task,

                        # E/F 是被 B 直接影響。
                        task.task_id,

                        cascade_depth + 1,
                    )
                )


    # ======================================================
    # Task-Specific Queue Projection
    #
    # 核心用途：
    # 「如果現在把 new_task 指派給這台 Robot，
    #  它依目前 Queue Policy 實際會插在哪裡？」
    #
    # 回傳的是 new_task 真正開始前的 projected state，
    # 而不是整條既有 Queue 的尾端狀態。
    #
    # workload_before_task：
    #   running task 剩餘時間
    #   + 所有會排在 new_task 前面的 waiting task service time
    #
    # projected_x/y：
    #   new_task 真正輪到執行時 Robot 預計所在位置
    # ======================================================

    def project_task_on_robot(
        self,
        sim_state,
        new_task,
    ):

        workload_before_task = (
            self.get_remaining_running_time(
                sim_state
            )
        )

        # Running task 不可被搶占。
        # 若目前正在執行，下一筆工作的起點會是 running destination。
        if (
            sim_state.running_task
            is not None
        ):

            current_x = (
                sim_state
                .running_task
                .destination_x
            )

            current_y = (
                sim_state
                .running_task
                .destination_y
            )

        else:

            current_x = (
                sim_state.x
            )

            current_y = (
                sim_state.y
            )

        # 把「正在評估的新 Task」暫時加入 queue。
        # 不修改真正的 sim_state.waiting_tasks。
        projected_queue = list(
            sim_state.waiting_tasks
        )

        projected_queue.append(
            new_task
        )

        queue_length_before_task = 0

        while projected_queue:

            selected_task = (
                self.task_scheduler.select(
                    projected_queue
                )
            )

            if selected_task is None:
                break

            # task_id 在一個 scenario 中應唯一。
            # 這樣不依賴 Python object identity。
            if (
                selected_task.task_id
                == new_task.task_id
            ):

                source_x, source_y = (
                    self.waypoints[
                        new_task.source
                    ]
                )

                distance_to_source = (
                    euclidean_distance(
                        current_x,
                        current_y,
                        source_x,
                        source_y,
                    )
                )

                return {
                    "projected_x": current_x,
                    "projected_y": current_y,
                    "workload_before_task": (
                        workload_before_task
                    ),
                    "queue_length_before_task": (
                        queue_length_before_task
                    ),
                    "distance_to_source": (
                        distance_to_source
                    ),
                    "existing_queue_length": (
                        len(
                            sim_state.waiting_tasks
                        )
                    ),
                }

            (
                _,
                service_time,
                destination_x,
                destination_y,
            ) = self.estimate_task_service(
                selected_task,
                current_x,
                current_y,
            )

            workload_before_task += (
                service_time
            )

            current_x = (
                destination_x
            )

            current_y = (
                destination_y
            )

            queue_length_before_task += 1

            projected_queue.remove(
                selected_task
            )

        raise RuntimeError(
            "Failed to project task "
            f"{new_task.task_id} on robot "
            f"{sim_state.robot.robot_id}"
        )


    # ======================================================
    # Prepare Candidate Robot States For One Task
    #
    # 為避免 projection 汙染真正 RobotState，
    # 這裡傳給 Robot Scheduler 的是 robot copy。
    #
    # robot.x / y：
    #   改成「這筆 task 真正輪到時」的 projected position
    #
    # robot.remaining_busy_time：
    #   暫時保留舊欄位名稱，語意改為 workload_before_task
    #   讓目前 RuleBasedScheduler 可以直接使用。
    # ======================================================

    def prepare_robots_for_scheduling(
        self,
        task,
    ):

        robots = []

        for sim_state in (
            self.robot_states.values()
        ):

            projection = (
                self.project_task_on_robot(
                    sim_state,
                    task,
                )
            )

            robot = copy.deepcopy(
                sim_state.robot
            )

            robot.x = (
                projection[
                    "projected_x"
                ]
            )

            robot.y = (
                projection[
                    "projected_y"
                ]
            )

            robot.available = (
                sim_state.running_task
                is None
                and not sim_state.waiting_tasks
            )

            robot.status = (
                "idle"
                if robot.available
                else "busy"
            )

            # RuleBasedScheduler 目前使用此欄位。
            # 新語意：這筆 Task 開始前預估要等待的既有 workload。
            robot.remaining_busy_time = (
                projection[
                    "workload_before_task"
                ]
            )

            robot.queue_workload_before_task = (
                projection[
                    "workload_before_task"
                ]
            )

            robot.queue_length_before_task = (
                projection[
                    "queue_length_before_task"
                ]
            )

            robot.queue_length = (
                len(
                    sim_state.waiting_tasks
                )
            )

            robot.projected_distance_to_source = (
                projection[
                    "distance_to_source"
                ]
            )

            robots.append(
                robot
            )

        return robots


    # ======================================================
    # Assign Arrived Task
    #
    # Assignment 只代表「這筆 task 屬於哪台 Robot」。
    # 尚未開始執行，會先加入 robot.waiting_tasks。
    # ======================================================

    def assign_task_to_robot(
        self,
        task,
    ):

        all_robots = (
            self.prepare_robots_for_scheduling(
                task
            )
        )

        candidates = (
            capability_matching(
                task.required_capabilities,
                all_robots,
            )
        )

        if not candidates:

            self.records.append(
                TaskExecutionRecord(
                    task_id=task.task_id,
                    priority=task.priority,
                    robot_id=None,
                    arrival_time=(
                        self.task_arrival_times[
                            task.task_id
                        ]
                    ),
                    start_time=None,
                    completion_time=None,
                    waiting_time=None,
                    service_time=None,
                    travel_distance=None,
                    success=False,
                )
            )

            return

        assignment = (
            self.robot_scheduler.schedule(
                task,
                candidates,
            )
        )

        if (
            assignment.decision_status
            != "assigned"
            or assignment.robot_id
            is None
        ):

            self.records.append(
                TaskExecutionRecord(
                    task_id=task.task_id,
                    priority=task.priority,
                    robot_id=None,
                    arrival_time=(
                        self.task_arrival_times[
                            task.task_id
                        ]
                    ),
                    start_time=None,
                    completion_time=None,
                    waiting_time=None,
                    service_time=None,
                    travel_distance=None,
                    success=False,
                )
            )

            return

        sim_state = (
            self.robot_states[
                assignment.robot_id
            ]
        )

        # ------------------------------------------
        # Dynamic Reassignment
        #
        # 關閉：
        #   完全維持 RL v1 舊語意，
        #   Task 直接 append 到原 Robot queue。
        #
        # 開啟：
        #   只有 new task 真的插隊，
        #   才重新評估被延後的 waiting tasks。
        # ------------------------------------------

        if self.enable_dynamic_reassignment:

            displaced_tasks = (
                self.get_displaced_tasks(
                    sim_state,
                    task,
                )
            )

            self.insert_waiting_task(
                sim_state,
                task,
            )

            if displaced_tasks:

                self.reassign_displaced_tasks(
                    displaced_tasks,
                    trigger_task_id=(
                        task.task_id
                    ),
                )

        else:

            # RL v1 / 舊 Baseline 行為。
            sim_state.waiting_tasks.append(
                task
            )


    # ======================================================
    # Process Arrived Tasks
    # ======================================================

    def process_arrived_tasks(
        self,
    ):

        while self.future_tasks:

            task = (
                self.future_tasks[0]
            )

            arrival_time = (
                self.task_arrival_times[
                    task.task_id
                ]
            )

            if (
                arrival_time
                > self.current_time
            ):
                break

            self.future_tasks.pop(
                0
            )

            self.assign_task_to_robot(
                task
            )


    # ======================================================
    # Start Idle Robots
    # ======================================================

    def start_idle_robots(
        self,
    ):

        for sim_state in (
            self.robot_states.values()
        ):

            if (
                sim_state.running_task
                is not None
            ):
                continue

            if not sim_state.waiting_tasks:
                continue

            task = (
                self.select_next_robot_task(
                    sim_state
                )
            )

            if task is None:
                continue

            sim_state.waiting_tasks.remove(
                task
            )

            (
                total_distance,
                service_time,
                destination_x,
                destination_y,
            ) = self.estimate_task_service(
                task,
                sim_state.x,
                sim_state.y,
            )

            arrival_time = (
                self.task_arrival_times[
                    task.task_id
                ]
            )

            start_time = (
                self.current_time
            )

            waiting_time = (
                start_time
                - arrival_time
            )

            completion_time = (
                start_time
                + service_time
            )

            sim_state.running_task = (
                RunningTaskState(
                    task=task,
                    arrival_time=arrival_time,
                    start_time=start_time,
                    completion_time=(
                        completion_time
                    ),
                    service_time=service_time,
                    travel_distance=(
                        total_distance
                    ),
                    destination_x=(
                        destination_x
                    ),
                    destination_y=(
                        destination_y
                    ),
                )
            )

            # Record 在真正開始時建立。
            # 因為只有到這一刻，Task 的最終 start/completion 才確定。
            self.records.append(
                TaskExecutionRecord(
                    task_id=task.task_id,
                    priority=task.priority,
                    robot_id=(
                        sim_state.robot.robot_id
                    ),
                    arrival_time=arrival_time,
                    start_time=start_time,
                    completion_time=(
                        completion_time
                    ),
                    waiting_time=waiting_time,
                    service_time=service_time,
                    travel_distance=(
                        total_distance
                    ),
                    success=True,
                )
            )


    # ======================================================
    # Complete Running Tasks
    # ======================================================

    def complete_running_tasks(
        self,
    ):

        for sim_state in (
            self.robot_states.values()
        ):

            running = (
                sim_state.running_task
            )

            if running is None:
                continue

            if (
                running.completion_time
                > self.current_time
            ):
                continue

            sim_state.x = (
                running.destination_x
            )

            sim_state.y = (
                running.destination_y
            )

            sim_state.total_distance += (
                running.travel_distance
            )

            sim_state.total_busy_time += (
                running.service_time
            )

            sim_state.completed_tasks += 1

            sim_state.running_task = None


    # ======================================================
    # Next Event Time
    #
    # Event：
    # 1. 新 Task Arrival
    # 2. Running Task Completion
    # ======================================================

    def get_next_event_time(
        self,
    ):

        event_times = []

        if self.future_tasks:

            next_task = (
                self.future_tasks[0]
            )

            arrival_time = (
                self.task_arrival_times[
                    next_task.task_id
                ]
            )

            if (
                arrival_time
                > self.current_time
            ):

                event_times.append(
                    arrival_time
                )

        for sim_state in (
            self.robot_states.values()
        ):

            running = (
                sim_state.running_task
            )

            if (
                running is not None
                and running.completion_time
                > self.current_time
            ):

                event_times.append(
                    running.completion_time
                )

        if not event_times:
            return None

        return min(
            event_times
        )


    # ======================================================
    # Run Simulation
    # ======================================================

    def run(
        self,
    ):

        while True:

            # 1. 先完成此時間點已完成的 Running Tasks。
            self.complete_running_tasks()

            # 2. 再處理此時間點到達的新 Tasks。
            #    它們會先完成 Robot Assignment，加入 local queue。
            self.process_arrived_tasks()

            # 3. Idle Robot 依自己的 FCFS/Priority queue 開始下一筆。
            self.start_idle_robots()

            has_running = any(
                sim_state.running_task
                is not None
                for sim_state
                in self.robot_states.values()
            )

            has_waiting = any(
                bool(
                    sim_state.waiting_tasks
                )
                for sim_state
                in self.robot_states.values()
            )

            if (
                not self.future_tasks
                and not has_running
                and not has_waiting
            ):
                break

            next_event = (
                self.get_next_event_time()
            )

            if next_event is None:
                raise RuntimeError(
                    "Simulation has unfinished work "
                    "but no future event exists."
                )

            self.current_time = (
                next_event
            )

        successful_completion_times = [
            record.completion_time
            for record
            in self.records
            if (
                record.success
                and record.completion_time
                is not None
            )
        ]

        if successful_completion_times:
            simulation_end_time = max(
                successful_completion_times
            )
        else:
            simulation_end_time = (
                self.current_time
            )

        return {
            "records": self.records,
            "robots": self.robot_states,
            "simulation_end_time": (
                simulation_end_time
            ),
        }
