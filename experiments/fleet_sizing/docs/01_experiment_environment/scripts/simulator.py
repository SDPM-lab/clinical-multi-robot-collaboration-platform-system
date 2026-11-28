from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from config import (
    CHARGING_WAYPOINT,
    ROBOT_CAPABILITIES,
    ROBOT_TYPE_CLEAN,
    ROBOT_TYPE_MEDICAL,
    ROBOT_TYPE_WARD,
)

from models import (
    RobotState,
    TaskState,
)

from task_generator import (
    GeneratedTask,
    NormalTaskGenerator,
)

from travel_time import TravelTimeModel


# ============================================================
# Assignment Record
# ============================================================

@dataclass(frozen=True)
class AssignmentRecord:
    task_id: str
    robot_id: str

    task_arrival_time_s: float
    robot_previous_available_time_s: float

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
class SimulationResult:
    seed: int
    fleet_configuration: Tuple[int, int, int]

    tasks: List[TaskState]
    robots: List[RobotState]
    assignments: List[AssignmentRecord]


# ============================================================
# Fleet Sizing Simulator
# ============================================================

class FleetSizingSimulator:

    def __init__(
        self,
        fleet_configuration: Tuple[int, int, int],
        seed: int,
        workload_multiplier: float = 1.0,
    ):
        self.fleet_configuration = fleet_configuration
        self.seed = seed
        self.workload_multiplier = workload_multiplier

        self.travel_model = TravelTimeModel()

        self.robots = self._build_fleet(
            fleet_configuration
        )

        self.tasks = []
        self.assignments = []

    # ========================================================
    # Fleet Initialization
    # ========================================================

    def _build_fleet(
        self,
        configuration: Tuple[int, int, int],
    ) -> List[RobotState]:

        clean_count, medical_count, ward_count = (
            configuration
        )

        robots: List[RobotState] = []

        robots.extend(
            self._create_robots(
                prefix="C",
                robot_type=ROBOT_TYPE_CLEAN,
                count=clean_count,
            )
        )

        robots.extend(
            self._create_robots(
                prefix="M",
                robot_type=ROBOT_TYPE_MEDICAL,
                count=medical_count,
            )
        )

        robots.extend(
            self._create_robots(
                prefix="W",
                robot_type=ROBOT_TYPE_WARD,
                count=ward_count,
            )
        )

        return robots

    def _create_robots(
        self,
        prefix: str,
        robot_type: str,
        count: int,
    ) -> List[RobotState]:

        capabilities = ROBOT_CAPABILITIES[
            robot_type
        ]

        robots = []

        for index in range(1, count + 1):

            robot = RobotState(
                robot_id=f"{prefix}{index:02d}",
                robot_type=robot_type,
                capabilities=sorted(
                    capabilities
                ),

                # Fleet Sizing v1:
                # 所有 robot 初始位於 charging point。
                current_location=CHARGING_WAYPOINT,

                status="idle",

                available_time_s=0.0,

                future_location=CHARGING_WAYPOINT,
            )

            robots.append(robot)

        return robots

    # ========================================================
    # Main Simulation
    # ========================================================

    def run(self) -> SimulationResult:

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
            for task in generated_tasks
        ]

        # task_generator 已經排序，
        # 這裡再排序一次以保證 simulator 安全。
        self.tasks.sort(
            key=lambda task: task.arrival_time_s
        )

        for task in self.tasks:

            self._process_task_arrival(
                task
            )

        self._finalize_robot_states()

        return SimulationResult(
            seed=self.seed,
            fleet_configuration=(
                self.fleet_configuration
            ),
            tasks=self.tasks,
            robots=self.robots,
            assignments=self.assignments,
        )

    # ========================================================
    # Task Conversion
    # ========================================================

    @staticmethod
    def _convert_task(
        task: GeneratedTask,
    ) -> TaskState:

        return TaskState(
            task_id=task.task_id,
            task_type=task.task_type,
            source=task.source,
            destination=task.destination,
            priority=task.priority,

            arrival_time_s=(
                task.arrival_time_s
            ),

            service_time_s=(
                task.service_time_s
            ),
        )

    # ========================================================
    # Task Arrival
    # ========================================================

    def _process_task_arrival(
        self,
        task: TaskState,
    ) -> None:

        current_time_s = task.arrival_time_s

        # 先把所有 robot 狀態更新到這個 arrival time
        for robot in self.robots:
            self._refresh_robot_state(
                robot,
                current_time_s,
            )

        feasible_robots = (
            self._get_feasible_robots(task)
        )

        if not feasible_robots:
            task.status = "unserved"
            return

        best_robot = min(
            feasible_robots,
            key=lambda robot:
                self._calculate_candidate_eta(
                    robot,
                    task,
                    current_time_s,
                ),
        )

        self._assign_task(
            robot=best_robot,
            task=task,
            current_time_s=current_time_s,
        )

    # ========================================================
    # Capability Filtering
    # ========================================================

    def _get_feasible_robots(
        self,
        task: TaskState,
    ) -> List[RobotState]:

        return [
            robot
            for robot in self.robots
            if task.task_type
            in robot.capabilities
        ]


    def _refresh_robot_state(
        self,
        robot: RobotState,
        current_time_s: float,
    ) -> None:
        """
        將 robot 狀態推進到 current_time_s。

        若目前時間已經超過 robot 所有已排程工作的
        completion time，代表 robot 已完成 queue，
        此時 current_location 應更新為 future_location。
        """

        if (
            robot.available_time_s <= current_time_s
            and robot.future_location is not None
        ):
            robot.current_location = robot.future_location
            robot.current_task_id = None
            robot.status = "idle"


    # ========================================================
    # Candidate ETA
    # ========================================================

    def _calculate_candidate_eta(
        self,
        robot: RobotState,
        task: TaskState,
        current_time_s: float,
    ) -> float:
        """
        ETA = Robot 最早能抵達新 task source 的時間差。

        Idle:
            travel(current_location -> source)

        Busy / already queued:
            remaining scheduled workload
            +
            travel(future_location -> source)

        注意：
        Busy robot 仍然是合法候選。
        """

        remaining_busy_s = (
            robot.remaining_busy_time(
                current_time_s
            )
        )

        origin = (
            robot.get_assignment_origin(
                current_time_s
            )
        )

        approach_time_s = (
            self.travel_model
            .get_travel_time_mean(
                origin,
                task.source,
            )
        )

        return (
            remaining_busy_s
            + approach_time_s
        )

    # ========================================================
    # Assignment
    # ========================================================

    def _assign_task(
        self,
        robot: RobotState,
        task: TaskState,
        current_time_s: float,
    ) -> None:

        robot_was_available = (
            robot.is_available_at(
                current_time_s
            )
        )

        robot_was_busy = not robot_was_available

        queue_delay_s = max(
            0.0,
            robot.available_time_s - current_time_s,
        )

        # ----------------------------------------------------
        # Robot 在接這筆 task 前，
        # 原有 queue 最後的完成時間與位置。
        # ----------------------------------------------------

        previous_available_time_s = (
            max(
                current_time_s,
                robot.available_time_s,
            )
        )

        if robot_was_available:
            origin = (
                robot.current_location
            )

        else:
            if robot.future_location is None:
                raise RuntimeError(
                    f"{robot.robot_id} has queued work "
                    "but future_location is None."
                )

            origin = (
                robot.future_location
            )

        # ----------------------------------------------------
        # Robot → new task source
        # ----------------------------------------------------

        approach_time_s = (
            self.travel_model
            .get_travel_time_mean(
                origin,
                task.source,
            )
        )

        # ----------------------------------------------------
        # Task source → destination
        # ----------------------------------------------------

        task_travel_time_s = (
            self.travel_model
            .get_travel_time_mean(
                task.source,
                task.destination,
            )
        )

        # ----------------------------------------------------
        # Timing
        # ----------------------------------------------------

        dispatch_start_time_s = (
            previous_available_time_s
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
        # Update Task
        # ----------------------------------------------------

        task.assigned_robot = (
            robot.robot_id
        )

        # 新任務一進來就完成 assignment。
        task.assignment_time_s = (
            current_time_s
        )

        # 這裡 start_time 定義成：
        # Robot 開始執行這筆 task，
        # 也就是開始前往 task source 的時間。
        task.start_time_s = (
            dispatch_start_time_s
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

        task.status = "scheduled"

        # ----------------------------------------------------
        # Update Robot Queue State
        # ----------------------------------------------------

        added_busy_time_s = (
            approach_time_s
            + task_travel_time_s
            + task.service_time_s
        )

        robot.busy_time_s += (
            added_busy_time_s
        )

        robot.available_time_s = (
            completion_time_s
        )

        # Queue 最後一定完成在
        # 新任務 destination。
        robot.future_location = (
            task.destination
        )

        robot.current_task_id = (
            task.task_id
        )

        robot.assigned_task_ids.append(
            task.task_id
        )

        robot.status = "busy"

        # ----------------------------------------------------
        # Assignment Log
        # ----------------------------------------------------

        self.assignments.append(
            AssignmentRecord(
                task_id=task.task_id,
                robot_id=robot.robot_id,

                task_arrival_time_s=(
                    current_time_s
                ),

                robot_previous_available_time_s=(
                    previous_available_time_s
                ),

                assignment_origin=origin,

                task_source=task.source,
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

                robot_was_busy=robot_was_busy,
                queue_delay_s=queue_delay_s,
            )
        )

    # ========================================================
    # Finalization
    # ========================================================

    def _finalize_robot_states(
        self,
    ) -> None:

        for robot in self.robots:

            if robot.future_location is not None:
                robot.current_location = (
                    robot.future_location
                )

            robot.current_task_id = None

            robot.completed_tasks = len(
                robot.assigned_task_ids
            )

            robot.status = "idle"

    # ========================================================
    # Debug Summary
    # ========================================================

    def print_summary(self) -> None:

        print(
            "Fleet:",
            self.fleet_configuration,
        )

        print(
            "Seed:",
            self.seed,
        )

        print(
            "Tasks:",
            len(self.tasks),
        )

        print(
            "\nRobot summary:"
        )

        for robot in self.robots:

            print(
                robot.robot_id,
                robot.robot_type,
                "tasks=",
                len(
                    robot.assigned_task_ids
                ),
                "busy_s=",
                round(
                    robot.busy_time_s,
                    1,
                ),
                "available_until=",
                round(
                    robot.available_time_s,
                    1,
                ),
                "future_location=",
                robot.future_location,
            )

        print(
            "\nFirst 10 assignments:"
        )

        for record in (
            self.assignments[:10]
        ):

            print(
                record.task_id,
                "->",
                record.robot_id,
                "| origin:",
                record.assignment_origin,
                "| approach:",
                f"{record.approach_time_s:.1f}s",
                "| start:",
                f"{record.dispatch_start_time_s:.1f}",
                "| complete:",
                f"{record.completion_time_s:.1f}",
            )

        busy_preassignments = [
            record
            for record in self.assignments
            if record.robot_was_busy
        ]

        print(
            "\nBusy robot pre-assignments:",
            len(busy_preassignments),
        )

        print(
            "Pre-assignment rate:",
            f"{len(busy_preassignments) / len(self.assignments) * 100:.2f}%"
        )

        print("\nFirst 10 busy pre-assignments:")

        for record in busy_preassignments[:10]:
            print(
                record.task_id,
                "->",
                record.robot_id,
                "| queue_delay:",
                f"{record.queue_delay_s:.1f}s",
                "| origin after queue:",
                record.assignment_origin,
                "| source:",
                record.task_source,
            )


if __name__ == "__main__":

    simulator = FleetSizingSimulator(
        fleet_configuration=(1, 1, 1),
        seed=42,
    )

    simulator.run()

    simulator.print_summary()
