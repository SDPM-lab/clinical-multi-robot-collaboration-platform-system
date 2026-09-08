#!/usr/bin/env python3

import copy
import math
from dataclasses import dataclass, field

import numpy as np

from scheduler.capability_matcher import capability_matching


@dataclass
class RLTaskExecutionRecord:
    task_id: str
    priority: int
    robot_id: str
    arrival_time: float
    start_time: float
    completion_time: float
    waiting_time: float
    service_time: float
    travel_distance: float


@dataclass
class RLRunningTaskState:
    task: object
    arrival_time: float
    start_time: float
    completion_time: float
    service_time: float
    travel_distance: float
    destination_x: float
    destination_y: float


@dataclass
class RLRobotSimulationState:
    robot: object
    x: float
    y: float
    running_task: RLRunningTaskState | None = None
    waiting_tasks: list = field(default_factory=list)
    total_distance: float = 0.0
    total_busy_time: float = 0.0
    completed_tasks: int = 0


def euclidean_distance(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


class HospitalRLEnv:
    """
    Priority + RL environment.

    RL 負責：
        決定新 Task 要加入哪一台 Robot 的 local queue。

    Robot local queue 負責：
        Priority 高者先執行；
        同 Priority 時使用 FCFS；
        已經開始執行的 running task 不可被搶占。

    一個 RL step = 一筆 Task 的 Robot Assignment。
    Assignment 不等於 Task 立刻開始執行。
    """

    def __init__(
        self,
        scenario,
        robot_speed: float = 1.0,
        service_time: float = 5.0,
    ):
        self.original_scenario = copy.deepcopy(scenario)

        self.robot_speed = robot_speed
        self.fixed_service_time = service_time

        self.robot_ids = sorted(
            robot.robot_id
            for robot in scenario.robots
        )
        self.robot_count = len(self.robot_ids)
        self.task_count = len(scenario.tasks)

        self.scenario = None
        self.waypoints = None
        self.task_arrival_times = None
        self.future_tasks = None
        self.pending_tasks = None
        self.robot_states = None

        self.current_time = 0.0
        self.current_task = None

        self.assigned_task_count = 0
        self.completed_task_count = 0

        self.execution_records = None

        self.total_reward = 0.0
        self.done = False

    # ======================================================
    # Reset
    # ======================================================

    def reset(self):
        self.scenario = copy.deepcopy(
            self.original_scenario
        )

        self.waypoints = copy.deepcopy(
            self.scenario.waypoints
        )

        self.task_arrival_times = copy.deepcopy(
            self.scenario.task_arrival_times
        )

        self.future_tasks = sorted(
            copy.deepcopy(self.scenario.tasks),
            key=lambda task:
                self.task_arrival_times[
                    task.task_id
                ],
        )

        self.pending_tasks = []

        self.robot_states = {}

        for robot in copy.deepcopy(
            self.scenario.robots
        ):
            self.robot_states[
                robot.robot_id
            ] = RLRobotSimulationState(
                robot=robot,
                x=robot.x,
                y=robot.y,
            )

        self.current_time = 0.0
        self.current_task = None

        self.assigned_task_count = 0
        self.completed_task_count = 0

        self.execution_records = []

        self.total_reward = 0.0
        self.done = False

        self._prepare_next_decision()

        return self.get_observation()

    # ======================================================
    # Priority Local Queue
    # ======================================================

    def _select_priority_task(
        self,
        tasks,
    ):
        if not tasks:
            return None

        best_index = max(
            range(len(tasks)),
            key=lambda index:
                tasks[index].priority,
        )

        return tasks[best_index]

    # ======================================================
    # Task Arrival
    # ======================================================

    def _move_arrived_tasks_to_pending(
        self,
    ):
        while self.future_tasks:
            task = self.future_tasks[0]

            arrival_time = (
                self.task_arrival_times[
                    task.task_id
                ]
            )

            if arrival_time > self.current_time:
                break

            self.future_tasks.pop(0)
            self.pending_tasks.append(task)

    # ======================================================
    # Running Time
    # ======================================================

    def _get_remaining_running_time(
        self,
        sim_state,
    ):
        running = sim_state.running_task

        if running is None:
            return 0.0

        return max(
            0.0,
            running.completion_time
            - self.current_time,
        )

    # ======================================================
    # Task-specific Projection
    # ======================================================

    def project_task_on_robot(
        self,
        sim_state,
        new_task,
    ):
        """
        模擬 new_task 加入此 Robot 的 Priority Queue 後，
        new_task 真正輪到時的預估狀態。

        回傳：
            projected_x
            projected_y
            workload_before_task
            queue_length_before_task
            distance_to_source
        """

        workload_before_task = (
            self._get_remaining_running_time(
                sim_state
            )
        )

        queue_length_before_task = 0

        if sim_state.running_task is not None:
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
            current_x = sim_state.x
            current_y = sim_state.y

        projected_queue = list(
            sim_state.waiting_tasks
        )
        projected_queue.append(new_task)

        while projected_queue:
            task = self._select_priority_task(
                projected_queue
            )

            if task is None:
                break

            if task is new_task:
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
                    "projected_x":
                        float(current_x),

                    "projected_y":
                        float(current_y),

                    "workload_before_task":
                        float(
                            workload_before_task
                        ),

                    "queue_length_before_task":
                        int(
                            queue_length_before_task
                        ),

                    "distance_to_source":
                        float(
                            distance_to_source
                        ),
                }

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
                    current_x,
                    current_y,
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

            travel_distance = (
                robot_to_source
                + source_to_destination
            )

            service_time = (
                travel_distance
                / self.robot_speed
                + self.fixed_service_time
            )

            workload_before_task += (
                service_time
            )

            queue_length_before_task += 1

            current_x = destination_x
            current_y = destination_y

            projected_queue.remove(task)

        raise RuntimeError(
            "Failed to project task "
            f"{new_task.task_id}"
        )

    # ======================================================
    # Capability Matching
    # ======================================================

    def _get_candidate_robot_ids(
        self,
        task,
    ):
        all_robots = [
            sim_state.robot
            for sim_state
            in self.robot_states.values()
        ]

        candidates = capability_matching(
            task.required_capabilities,
            all_robots,
        )

        return {
            robot.robot_id
            for robot in candidates
        }

    def _task_has_compatible_robot(
        self,
        task,
    ):
        return bool(
            self._get_candidate_robot_ids(
                task
            )
        )

    # ======================================================
    # Start Idle Robots
    # ======================================================

    def _start_idle_robots(
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

            task = self._select_priority_task(
                sim_state.waiting_tasks
            )

            if task is None:
                continue

            sim_state.waiting_tasks.remove(
                task
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
                    sim_state.x,
                    sim_state.y,
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

            travel_distance = (
                robot_to_source
                + source_to_destination
            )

            service_time = (
                travel_distance
                / self.robot_speed
                + self.fixed_service_time
            )

            arrival_time = (
                self.task_arrival_times[
                    task.task_id
                ]
            )

            start_time = self.current_time

            completion_time = (
                start_time
                + service_time
            )

            waiting_time = (
                start_time
                - arrival_time
            )

            sim_state.running_task = (
                RLRunningTaskState(
                    task=task,
                    arrival_time=arrival_time,
                    start_time=start_time,
                    completion_time=(
                        completion_time
                    ),
                    service_time=service_time,
                    travel_distance=(
                        travel_distance
                    ),
                    destination_x=(
                        destination_x
                    ),
                    destination_y=(
                        destination_y
                    ),
                )
            )

            self.execution_records.append(
                RLTaskExecutionRecord(
                    task_id=task.task_id,
                    priority=task.priority,
                    robot_id=(
                        sim_state
                        .robot
                        .robot_id
                    ),
                    arrival_time=(
                        arrival_time
                    ),
                    start_time=start_time,
                    completion_time=(
                        completion_time
                    ),
                    waiting_time=(
                        waiting_time
                    ),
                    service_time=(
                        service_time
                    ),
                    travel_distance=(
                        travel_distance
                    ),
                )
            )

    # ======================================================
    # Complete Running Tasks
    # ======================================================

    def _complete_running_tasks(
        self,
    ):
        for sim_state in (
            self.robot_states.values()
        ):
            running = sim_state.running_task

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
            self.completed_task_count += 1

            sim_state.running_task = None

    # ======================================================
    # Next Event
    # ======================================================

    def _get_next_event_time(
        self,
    ):
        event_times = []

        if self.future_tasks:
            next_task = self.future_tasks[0]

            next_arrival = (
                self.task_arrival_times[
                    next_task.task_id
                ]
            )

            if next_arrival > self.current_time:
                event_times.append(
                    next_arrival
                )

        for sim_state in (
            self.robot_states.values()
        ):
            running = sim_state.running_task

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

        return min(event_times)

    # ======================================================
    # Prepare Next Decision
    # ======================================================

    def _prepare_next_decision(
        self,
    ):
        """
        同一 current_time 到達的 Tasks：
        先全部完成 Robot Assignment，
        再讓 Idle Robot 從自己的 Priority Queue 開始工作。

        這樣和 BaselineSimulator 的事件語意一致。
        """

        self.current_task = None

        while True:
            self._complete_running_tasks()

            self._move_arrived_tasks_to_pending()

            # 還有尚未完成 Assignment 的 Task：
            # 交給 RL 決定 Robot。
            if self.pending_tasks:
                task = self.pending_tasks[0]

                if not (
                    self._task_has_compatible_robot(
                        task
                    )
                ):
                    raise RuntimeError(
                        "No compatible robot exists "
                        f"for task {task.task_id}"
                    )

                self.current_task = task
                return

            # 此時間點 Assignment 全部完成，
            # 現在才讓 Idle Robot 開始工作。
            self._start_idle_robots()

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
                and not self.pending_tasks
                and not has_running
                and not has_waiting
            ):
                self.done = True
                return

            next_event = (
                self._get_next_event_time()
            )

            if next_event is None:
                raise RuntimeError(
                    "RL simulation has "
                    "unfinished work but "
                    "no future event exists."
                )

            self.current_time = next_event

    # ======================================================
    # Action Mask
    # ======================================================

    def action_masks(
        self,
    ):
        if (
            self.done
            or self.current_task is None
        ):
            return np.zeros(
                self.robot_count,
                dtype=bool,
            )

        candidate_ids = (
            self._get_candidate_robot_ids(
                self.current_task
            )
        )

        return np.array(
            [
                robot_id
                in candidate_ids
                for robot_id
                in self.robot_ids
            ],
            dtype=bool,
        )

    # ======================================================
    # Normalization
    # ======================================================

    def _normalize_coordinate(
        self,
        value,
    ):
        return float(
            np.clip(
                value / 50.0,
                0.0,
                1.0,
            )
        )

    def _normalize_distance(
        self,
        value,
    ):
        value = max(
            0.0,
            value,
        )

        return float(
            value
            /
            (
                value
                + 100.0
            )
        )

    def _normalize_waiting_time(
        self,
        value,
    ):
        value = max(
            0.0,
            value,
        )

        return float(
            value
            /
            (
                value
                + 300.0
            )
        )

    def _normalize_workload(
        self,
        value,
    ):
        value = max(
            0.0,
            value,
        )

        return float(
            value
            /
            (
                value
                + 300.0
            )
        )

    def _normalize_queue_length(
        self,
        value,
    ):
        value = max(
            0,
            int(value),
        )

        return float(
            value
            /
            max(
                1,
                self.task_count,
            )
        )

    # ======================================================
    # Observation
    #
    # Task = 6
    #
    # 每台 Robot = 9
    #
    # 1. projected_x
    # 2. projected_y
    # 3. battery
    # 4. workload_before_task
    # 5. distance_to_source
    # 6. capability_match
    # 7. queue_length_before_task
    # 8. total_queue_length
    # 9. completed_tasks ratio
    #
    # 3 Robots：
    #
    # 6 + 3 * 9 = 33 dimensions
    # ======================================================

    def get_observation(
        self,
    ):
        observation_size = (
            6
            +
            self.robot_count
            * 9
        )

        if (
            self.done
            or self.current_task is None
        ):
            return np.zeros(
                observation_size,
                dtype=np.float32,
            )

        task = self.current_task

        source = (
            self.waypoints[
                task.source
            ]
        )

        destination = (
            self.waypoints[
                task.destination
            ]
        )

        arrival_time = (
            self.task_arrival_times[
                task.task_id
            ]
        )

        waiting_time = max(
            0.0,
            self.current_time
            - arrival_time,
        )

        observation = [
            float(
                np.clip(
                    task.priority / 3.0,
                    0.0,
                    1.0,
                )
            ),

            self._normalize_coordinate(
                source[0]
            ),

            self._normalize_coordinate(
                source[1]
            ),

            self._normalize_coordinate(
                destination[0]
            ),

            self._normalize_coordinate(
                destination[1]
            ),

            self._normalize_waiting_time(
                waiting_time
            ),
        ]

        required_capabilities = set(
            task.required_capabilities
        )

        for robot_id in self.robot_ids:
            sim_state = (
                self.robot_states[
                    robot_id
                ]
            )

            robot = sim_state.robot

            projection = (
                self.project_task_on_robot(
                    sim_state,
                    task,
                )
            )

            capability_match = (
                required_capabilities
                .issubset(
                    set(
                        robot.capabilities
                    )
                )
            )

            observation.extend(
                [
                    self._normalize_coordinate(
                        projection[
                            "projected_x"
                        ]
                    ),

                    self._normalize_coordinate(
                        projection[
                            "projected_y"
                        ]
                    ),

                    float(
                        np.clip(
                            robot.battery,
                            0.0,
                            1.0,
                        )
                    ),

                    self._normalize_workload(
                        projection[
                            "workload_before_task"
                        ]
                    ),

                    self._normalize_distance(
                        projection[
                            "distance_to_source"
                        ]
                    ),

                    float(
                        capability_match
                    ),

                    # 這筆 Task 插入後，
                    # 在它前面的 waiting task 數量。
                    self._normalize_queue_length(
                        projection[
                            "queue_length_before_task"
                        ]
                    ),

                    # 這台 Robot 目前所有尚未開始的 Task 數量。
                    #
                    # 注意：
                    # 不包含 running_task。
                    self._normalize_queue_length(
                        len(
                            sim_state.waiting_tasks
                        )
                    ),

                    float(
                        sim_state.completed_tasks
                        /
                        max(
                            1,
                            self.task_count,
                        )
                    ),
                ]
            )

        return np.array(
            observation,
            dtype=np.float32,
        )

    # ======================================================
    # Simulation End Time
    # ======================================================

    def get_simulation_end_time(
        self,
    ):
        if not self.execution_records:
            return self.current_time

        return max(
            record.completion_time
            for record
            in self.execution_records
        )

    # ======================================================
    # Reward v3
    #
    # Assignment 當下使用 task-specific projection：
    #
    # distance_cost
    # + workload_cost
    # + low_battery_cost
    #
    # total_queue_length 仍保留在 33D Observation，
    # 但不直接加入 Reward。
    #
    # Battery penalty 固定為 0.3。
    # ======================================================

    def _calculate_reward(
        self,
        travel_distance,
        workload_before_task,
        battery,
    ):

        distance_cost = (
            travel_distance
            /
            100.0
        )

        workload_cost = (
            workload_before_task
            /
            (
                workload_before_task
                +
                300.0
            )
        )

        low_battery_cost = (
            0.3
            if battery < 0.20
            else 0.0
        )

        reward = -(
            distance_cost
            +
            workload_cost
            +
            low_battery_cost
        )

        return reward
    # ======================================================
    # Step
    #
    # 一個 Step 只做 Assignment。
    # 不在這裡把 Task 的 final start/completion time 算死。
    # ======================================================

    def step(
        self,
        action: int,
    ):
        if self.done:
            raise RuntimeError(
                "Episode already finished. "
                "Call reset()."
            )

        if self.current_task is None:
            raise RuntimeError(
                "No current task available."
            )

        if (
            action < 0
            or action >= self.robot_count
        ):
            raise ValueError(
                f"Invalid action: {action}"
            )

        mask = self.action_masks()

        if not mask[action]:
            invalid_reward = -2.0

            self.total_reward += (
                invalid_reward
            )

            info = {
                "invalid_action": True,
                "action": action,
                "current_time": (
                    self.current_time
                ),
                "task_id": (
                    self.current_task
                    .task_id
                ),
            }

            return (
                self.get_observation(),
                invalid_reward,
                False,
                info,
            )

        task = self.current_task

        robot_id = (
            self.robot_ids[action]
        )

        sim_state = (
            self.robot_states[
                robot_id
            ]
        )

        robot = sim_state.robot

        projection = (
            self.project_task_on_robot(
                sim_state,
                task,
            )
        )

        source = (
            self.waypoints[
                task.source
            ]
        )

        destination = (
            self.waypoints[
                task.destination
            ]
        )

        source_to_destination = (
            euclidean_distance(
                source[0],
                source[1],
                destination[0],
                destination[1],
            )
        )

        projected_travel_distance = (
            projection[
                "distance_to_source"
            ]
            +
            source_to_destination
        )

        reward = self._calculate_reward(

            travel_distance=(
                projected_travel_distance
            ),

            workload_before_task=(
                projection[
                    "workload_before_task"
                ]
            ),

            battery=(
                sim_state.robot.battery
            ),
        )

        self.total_reward += reward

        # Assignment：
        # 只加入 selected Robot 的 local queue。
        sim_state.waiting_tasks.append(
            task
        )

        self.pending_tasks.remove(
            task
        )

        self.assigned_task_count += 1

        arrival_time = (
            self.task_arrival_times[
                task.task_id
            ]
        )

        info = {
            "invalid_action":
                False,

            "task_id":
                task.task_id,

            "priority":
                task.priority,

            "robot_id":
                robot_id,

            "decision_time":
                self.current_time,

            "arrival_time":
                arrival_time,

            # 下面都是 Assignment 當下 projection，
            # 不是 final execution result。
            "projected_x":
                projection[
                    "projected_x"
                ],

            "projected_y":
                projection[
                    "projected_y"
                ],

            "projected_workload_before_task":
                projection[
                    "workload_before_task"
                ],

            "projected_queue_length_before_task":
                projection[
                    "queue_length_before_task"
                ],

            "projected_distance_to_source":
                projection[
                    "distance_to_source"
                ],

            "projected_travel_distance":
                projected_travel_distance,

            "battery":
                robot.battery,

            "reward":
                reward,
        }

        self._prepare_next_decision()

        if self.done:
            info[
                "simulation_end_time"
            ] = (
                self.get_simulation_end_time()
            )

            info[
                "completed_tasks"
            ] = (
                self.completed_task_count
            )

            info[
                "assigned_tasks"
            ] = (
                self.assigned_task_count
            )

        return (
            self.get_observation(),
            reward,
            self.done,
            info,
        )
