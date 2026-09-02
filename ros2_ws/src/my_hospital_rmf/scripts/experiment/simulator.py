#!/usr/bin/env python3

import copy
import math

from dataclasses import dataclass

from scheduler.capability_matcher import (
    capability_matching,
)


# ==========================================================
# Task Execution Record
#
# 用來記錄每一筆 Task 的實驗結果。
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
# Robot Simulation State
#
# 不直接修改原本的 RobotState，
# 額外記錄模擬期間需要的資訊。
# ==========================================================

@dataclass
class RobotSimulationState:

    robot: object

    available_time: float

    x: float
    y: float

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
# ==========================================================

class BaselineSimulator:

    def __init__(
        self,
        scenario,
        task_scheduler,
        robot_scheduler,
        robot_speed: float = 1.0,
        service_time: float = 5.0,
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

        # ==================================================
        # Task Arrival
        #
        # future_tasks:
        # 尚未進入系統
        #
        # pending_tasks:
        # 已經 arrival、等待排程
        # ==================================================

        self.task_arrival_times = (
            copy.deepcopy(
                scenario.task_arrival_times
            )
        )

        self.future_tasks = sorted(

            copy.deepcopy(
                scenario.tasks
            ),

            key=lambda task:
                self.task_arrival_times[
                    task.task_id
                ],
        )

        self.pending_tasks = []

        # ==================================================
        # Robot Simulation State
        # ==================================================

        self.robot_states = {}

        for robot in copy.deepcopy(
            scenario.robots
        ):

            self.robot_states[
                robot.robot_id
            ] = RobotSimulationState(

                robot=robot,

                available_time=0.0,

                x=robot.x,
                y=robot.y,
            )

        self.records = []

        self.current_time = 0.0

    # ======================================================
    # 把已到達的 Task 移入 Pending Queue
    # ======================================================

    def move_arrived_tasks_to_pending(
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

            self.pending_tasks.append(
                task
            )

    # ======================================================
    # 下一筆 Task 到達時間
    # ======================================================

    def get_next_task_arrival_time(
        self,
    ):

        if not self.future_tasks:
            return None

        task = (
            self.future_tasks[0]
        )

        return (
            self.task_arrival_times[
                task.task_id
            ]
        )

    # ======================================================
    # 取得目前 Available Robots
    # ======================================================

    def get_available_robots(
        self,
        current_time: float,
    ):

        robots = []

        for sim_state in (
            self.robot_states.values()
        ):

            robot = (
                sim_state.robot
            )

            robot.x = (
                sim_state.x
            )

            robot.y = (
                sim_state.y
            )

            robot.available = (
                sim_state.available_time
                <= current_time
            )

            robot.status = (
                "idle"
                if robot.available
                else "busy"
            )

            if robot.available:

                robots.append(
                    robot
                )

        return robots

    # ======================================================
    # 下一個 Robot Available Time
    # ======================================================

    def get_next_robot_available_time(
        self,
    ):

        future_times = [

            sim_state.available_time

            for sim_state
            in self.robot_states.values()

            if (
                sim_state.available_time
                > self.current_time
            )
        ]

        if not future_times:
            return None

        return min(
            future_times
        )

    # ======================================================
    # 下一個 Event Time
    #
    # Event 可以是：
    #
    # 1. 新 Task Arrival
    # 2. Robot 完成任務
    # ======================================================

    def advance_to_next_event(
        self,
    ):

        event_times = []

        next_task_time = (
            self.get_next_task_arrival_time()
        )

        if (
            next_task_time
            is not None
            and next_task_time
            > self.current_time
        ):

            event_times.append(
                next_task_time
            )

        next_robot_time = (
            self.get_next_robot_available_time()
        )

        if (
            next_robot_time
            is not None
            and next_robot_time
            > self.current_time
        ):

            event_times.append(
                next_robot_time
            )

        if not event_times:
            return False

        self.current_time = min(
            event_times
        )

        return True

    # ======================================================
    # Run Simulation
    # ======================================================

    def run(self):

        while (
            self.future_tasks
            or self.pending_tasks
        ):

            # ----------------------------------------------
            # 將目前時間已經 arrival 的 Task
            # 放入 Pending Queue
            # ----------------------------------------------

            self.move_arrived_tasks_to_pending()

            # ----------------------------------------------
            # Pending Queue 為空
            #
            # 直接跳到下一個 Task Arrival。
            # ----------------------------------------------

            if not self.pending_tasks:

                next_arrival = (
                    self.get_next_task_arrival_time()
                )

                if next_arrival is None:
                    break

                self.current_time = (
                    next_arrival
                )

                continue

            # ----------------------------------------------
            # Task Selection
            # ----------------------------------------------

            task = (
                self.task_scheduler.select(
                    self.pending_tasks
                )
            )

            if task is None:

                if not self.advance_to_next_event():
                    break

                continue

            # ----------------------------------------------
            # Current Available Robots
            # ----------------------------------------------

            available_robots = (
                self.get_available_robots(
                    self.current_time
                )
            )

            # ----------------------------------------------
            # Capability Matching
            # ----------------------------------------------

            capability_candidates = (
                capability_matching(
                    task.required_capabilities,
                    available_robots,
                )
            )

            # ----------------------------------------------
            # 沒有目前可用的 Candidate
            # ----------------------------------------------

            if not capability_candidates:

                all_robots = [

                    sim_state.robot

                    for sim_state
                    in self.robot_states.values()
                ]

                all_capability_candidates = (
                    capability_matching(
                        task.required_capabilities,
                        all_robots,
                    )
                )

                # ------------------------------------------
                # 系統中完全沒有符合 Capability 的 Robot
                # ------------------------------------------

                if not all_capability_candidates:

                    self.records.append(
                        TaskExecutionRecord(

                            task_id=(
                                task.task_id
                            ),

                            priority=(
                                task.priority
                            ),

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

                    self.pending_tasks.remove(
                        task
                    )

                    continue

                # ------------------------------------------
                # 有符合能力 Robot，
                # 但現在正在 Busy。
                #
                # 跳到下一個事件。
                #
                # 注意：
                # 下一個事件可能是新的 Emergency Task。
                # ------------------------------------------

                if not self.advance_to_next_event():
                    break

                continue

            # ----------------------------------------------
            # Robot Selection
            # ----------------------------------------------

            assignment = (
                self.robot_scheduler.schedule(
                    task,
                    capability_candidates,
                )
            )

            if (
                assignment.decision_status
                != "assigned"
                or assignment.robot_id
                is None
            ):

                if not self.advance_to_next_event():
                    break

                continue

            sim_robot = (
                self.robot_states[
                    assignment.robot_id
                ]
            )

            # ----------------------------------------------
            # Waypoints
            # ----------------------------------------------

            if (
                task.source
                not in self.waypoints
            ):

                raise RuntimeError(
                    "Unknown task source: "
                    f"{task.source}"
                )

            if (
                task.destination
                not in self.waypoints
            ):

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

            # ----------------------------------------------
            # Robot → Source
            # ----------------------------------------------

            distance_to_source = (
                euclidean_distance(

                    sim_robot.x,
                    sim_robot.y,

                    source_x,
                    source_y,
                )
            )

            # ----------------------------------------------
            # Source → Destination
            # ----------------------------------------------

            delivery_distance = (
                euclidean_distance(

                    source_x,
                    source_y,

                    destination_x,
                    destination_y,
                )
            )

            total_distance = (
                distance_to_source
                + delivery_distance
            )

            # ----------------------------------------------
            # Travel Time
            # ----------------------------------------------

            travel_time = (
                total_distance
                / self.robot_speed
            )

            # ----------------------------------------------
            # Timing
            # ----------------------------------------------

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

            total_service_time = (
                travel_time
                + self.fixed_service_time
            )

            completion_time = (
                start_time
                + total_service_time
            )

            # ----------------------------------------------
            # Update Robot
            # ----------------------------------------------

            sim_robot.available_time = (
                completion_time
            )

            sim_robot.x = (
                destination_x
            )

            sim_robot.y = (
                destination_y
            )

            sim_robot.total_distance += (
                total_distance
            )

            sim_robot.total_busy_time += (
                total_service_time
            )

            sim_robot.completed_tasks += 1

            # ----------------------------------------------
            # Record
            # ----------------------------------------------

            self.records.append(
                TaskExecutionRecord(

                    task_id=(
                        task.task_id
                    ),

                    priority=(
                        task.priority
                    ),

                    robot_id=(
                        assignment.robot_id
                    ),

                    arrival_time=(
                        arrival_time
                    ),

                    start_time=(
                        start_time
                    ),

                    completion_time=(
                        completion_time
                    ),

                    waiting_time=(
                        waiting_time
                    ),

                    service_time=(
                        total_service_time
                    ),

                    travel_distance=(
                        total_distance
                    ),

                    success=True,
                )
            )

            # ----------------------------------------------
            # 成功派工後離開 Pending Queue
            # ----------------------------------------------

            self.pending_tasks.remove(
                task
            )

            # 不主動增加 current_time。
            #
            # 因為同一個時間點可能還有其他
            # Available Robot 可以接受其他 Task。

        # ==================================================
        # Simulation End Time
        # ==================================================

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

            "records":
                self.records,

            "robots":
                self.robot_states,

            "simulation_end_time":
                simulation_end_time,
        }