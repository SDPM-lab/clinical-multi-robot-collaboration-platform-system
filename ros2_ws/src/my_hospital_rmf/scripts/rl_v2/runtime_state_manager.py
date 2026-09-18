#!/usr/bin/env python3

from dataclasses import dataclass

from scheduler_v2.models import (
    RobotState,
    Task,
)

from scheduler_v2.runtime import (
    RobotRuntimeState,
)

from scheduler_v2.task_selector import (
    sort_tasks,
)


# ==========================================================
# Runtime Snapshot
# ==========================================================

@dataclass(frozen=True)
class RobotRuntimeSnapshot:

    robot_id: str

    status: str

    battery: float

    running_task_id: str | None

    running_remaining_time: float

    waiting_task_ids: tuple[str, ...]


# ==========================================================
# Runtime State Manager
# ==========================================================

class RuntimeStateManager:
    """
    正式 Scheduler 與外部系統之間的 Runtime State Layer。

    它不負責：
        - PPO inference
        - Robot selection
        - RMF execution

    它只負責維護：

        RobotState
        +
        Running Task
        +
        Running Remaining Time
        +
        Waiting Queue

    讓 Frozen PPO 每次做決策時，
    可以取得和 Training Environment
    相同語意的 RobotRuntimeState。
    """

    def __init__(
        self,
        robots: list[RobotState],
        robot_speed_mps: float = 1.0,
    ):

        if not robots:

            raise ValueError(
                "robots cannot be empty"
            )

        robot_speed_mps = float(
            robot_speed_mps
        )

        if robot_speed_mps <= 0.0:

            raise ValueError(
                "robot_speed_mps "
                "must be greater than 0"
            )

        self.runtimes: dict[
            str,
            RobotRuntimeState,
        ] = {}

        self.tasks: dict[
            str,
            Task,
        ] = {}

        for robot in robots:

            if (
                robot.robot_id
                in self.runtimes
            ):

                raise ValueError(
                    "Duplicate robot_id: "
                    f"{robot.robot_id}"
                )

            self.runtimes[
                robot.robot_id
            ] = (
                RobotRuntimeState(
                    robot=robot,
                    robot_speed_mps=(
                        robot_speed_mps
                    ),
                )
            )


    # ======================================================
    # Read
    # ======================================================

    def get_runtimes(
        self,
    ) -> dict[
        str,
        RobotRuntimeState,
    ]:

        return self.runtimes


    def get_runtime(
        self,
        robot_id: str,
    ) -> RobotRuntimeState:

        try:

            return self.runtimes[
                robot_id
            ]

        except KeyError as exc:

            raise KeyError(
                f"Unknown robot: {robot_id}"
            ) from exc


    def get_task(
        self,
        task_id: str,
    ) -> Task:

        try:

            return self.tasks[
                task_id
            ]

        except KeyError as exc:

            raise KeyError(
                f"Unknown task: {task_id}"
            ) from exc


    # ======================================================
    # Robot Telemetry Update
    # ======================================================

    def update_robot_state(
        self,
        *,
        robot_id: str,
        status: str | None = None,
        battery: float | None = None,
        x: float | None = None,
        y: float | None = None,
        map_name: str | None = None,
        available: bool | None = None,
    ) -> None:
        """
        更新外部系統提供的 Robot Telemetry。

        注意：
        不會清除 Running / Waiting Queue。
        """

        runtime = self.get_runtime(
            robot_id
        )

        robot = runtime.robot

        if status is not None:

            status = (
                status
                .strip()
                .lower()
            )

            if status not in {
                "idle",
                "busy",
                "charging",
                "error",
                "offline",
            }:

                raise ValueError(
                    "Invalid robot status: "
                    f"{status}"
                )

            robot.status = status

        if battery is not None:

            battery = float(
                battery
            )

            if not (
                0.0
                <=
                battery
                <=
                1.0
            ):

                raise ValueError(
                    "battery must be "
                    "between 0.0 and 1.0"
                )

            robot.battery = battery

        if x is not None:

            robot.x = float(
                x
            )

        if y is not None:

            robot.y = float(
                y
            )

        if map_name is not None:

            robot.map_name = (
                str(
                    map_name
                )
            )

        if available is not None:

            robot.available = bool(
                available
            )


    # ======================================================
    # Assignment -> Waiting Queue
    # ======================================================

    def enqueue_task(
        self,
        *,
        task: Task,
        robot_id: str,
        current_time: float,
    ) -> None:
        """
        將 Scheduler 已經 Assigned 的 Task
        加入指定 Robot 的 Waiting Queue。
        """

        runtime = self.get_runtime(
            robot_id
        )

        if (
            task.task_id
            in self.tasks
        ):

            raise ValueError(
                "Task already exists in "
                "RuntimeStateManager: "
                f"{task.task_id}"
            )

        task.assigned_robot = (
            robot_id
        )

        task.status = "assigned"

        self.tasks[
            task.task_id
        ] = task

        runtime.waiting_tasks.append(
            task
        )

        # 保持和 Scheduler v2 相同的
        # Priority + Aging Queue 語意。
        runtime.waiting_tasks = (
            sort_tasks(
                tasks=(
                    runtime.waiting_tasks
                ),
                current_time=float(
                    current_time
                ),
            )
        )


    # ======================================================
    # Start Task
    # ======================================================

    def start_task(
        self,
        *,
        robot_id: str,
        task_id: str,
        remaining_time: float,
    ) -> None:
        """
        將 Waiting Task 標記為 Running。

        remaining_time：
            應由外部系統 / 執行層提供或估計。

        Runtime Manager 本身不重新推導
        真實 Robot 任務剩餘時間。
        """

        runtime = self.get_runtime(
            robot_id
        )

        remaining_time = float(
            remaining_time
        )

        if remaining_time < 0.0:

            raise ValueError(
                "remaining_time cannot "
                "be negative"
            )

        if (
            runtime.running_task
            is not None
        ):

            raise RuntimeError(
                "Robot already has "
                "a running task: "
                f"{robot_id} -> "
                f"{runtime.running_task.task_id}"
            )

        target_task = None

        for task in (
            runtime.waiting_tasks
        ):

            if (
                task.task_id
                ==
                task_id
            ):

                target_task = task

                break

        if target_task is None:

            raise ValueError(
                "Task is not in "
                "robot waiting queue: "
                f"task={task_id}, "
                f"robot={robot_id}"
            )

        runtime.waiting_tasks.remove(
            target_task
        )

        target_task.status = (
            "running"
        )

        target_task.assigned_robot = (
            robot_id
        )

        runtime.running_task = (
            target_task
        )

        runtime.running_remaining_time = (
            remaining_time
        )

        runtime.robot.current_task = (
            task_id
        )

        runtime.robot.status = (
            "busy"
        )


    # ======================================================
    # Running Remaining Time
    # ======================================================

    def update_running_remaining_time(
        self,
        *,
        robot_id: str,
        remaining_time: float,
    ) -> None:

        runtime = self.get_runtime(
            robot_id
        )

        if (
            runtime.running_task
            is None
        ):

            raise RuntimeError(
                "Robot has no running task: "
                f"{robot_id}"
            )

        remaining_time = float(
            remaining_time
        )

        if remaining_time < 0.0:

            raise ValueError(
                "remaining_time cannot "
                "be negative"
            )

        runtime.running_remaining_time = (
            remaining_time
        )


    # ======================================================
    # Complete Running Task
    # ======================================================

    def complete_running_task(
        self,
        *,
        robot_id: str,
    ) -> Task:

        runtime = self.get_runtime(
            robot_id
        )

        task = (
            runtime.running_task
        )

        if task is None:

            raise RuntimeError(
                "Robot has no running task: "
                f"{robot_id}"
            )

        task.status = (
            "completed"
        )

        runtime.running_task = None

        runtime.running_remaining_time = (
            0.0
        )

        runtime.robot.current_task = None

        # 真正系統之後仍可被
        # /fleet_states telemetry 覆寫。
        runtime.robot.status = (
            "idle"
        )

        return task


    # ======================================================
    # Waiting Task Reassignment
    #
    # 後面 Dedicated Reassignment PPO 會用到。
    # ======================================================

    def move_waiting_task(
        self,
        *,
        task_id: str,
        from_robot_id: str,
        to_robot_id: str,
        current_time: float,
    ) -> None:

        if (
            from_robot_id
            ==
            to_robot_id
        ):

            return

        old_runtime = self.get_runtime(
            from_robot_id
        )

        new_runtime = self.get_runtime(
            to_robot_id
        )

        target_task = None

        for task in (
            old_runtime.waiting_tasks
        ):

            if (
                task.task_id
                ==
                task_id
            ):

                target_task = task

                break

        if target_task is None:

            raise ValueError(
                "Waiting task not found: "
                f"task={task_id}, "
                f"robot={from_robot_id}"
            )

        old_runtime.waiting_tasks.remove(
            target_task
        )

        target_task.status = (
            "assigned"
        )

        target_task.assigned_robot = (
            to_robot_id
        )

        new_runtime.waiting_tasks.append(
            target_task
        )

        new_runtime.waiting_tasks = (
            sort_tasks(
                tasks=(
                    new_runtime
                    .waiting_tasks
                ),
                current_time=float(
                    current_time
                ),
            )
        )


    # ======================================================
    # Snapshot / Debug
    # ======================================================

    def snapshot(
        self,
    ) -> list[
        RobotRuntimeSnapshot
    ]:

        snapshots = []

        for robot_id in sorted(
            self.runtimes
        ):

            runtime = (
                self.runtimes[
                    robot_id
                ]
            )

            snapshots.append(
                RobotRuntimeSnapshot(
                    robot_id=robot_id,
                    status=(
                        runtime
                        .robot
                        .status
                    ),
                    battery=(
                        runtime
                        .robot
                        .battery
                    ),
                    running_task_id=(
                        None
                        if runtime.running_task
                        is None
                        else
                        runtime
                        .running_task
                        .task_id
                    ),
                    running_remaining_time=(
                        runtime
                        .running_remaining_time
                    ),
                    waiting_task_ids=tuple(
                        task.task_id
                        for task
                        in runtime
                        .waiting_tasks
                    ),
                )
            )

        return snapshots


    def print_state(
        self,
    ) -> None:

        print(
            "=" * 90
        )

        print(
            "RUNTIME STATE"
        )

        print(
            "=" * 90
        )

        for snapshot in (
            self.snapshot()
        ):

            print(
                f"{snapshot.robot_id:<20} "
                f"status={snapshot.status:<5} "
                f"battery={snapshot.battery:.3f} "
                f"running={str(snapshot.running_task_id):<8} "
                f"remaining="
                f"{snapshot.running_remaining_time:>7.2f}s "
                f"waiting="
                f"{list(snapshot.waiting_task_ids)}"
            )

        print(
            "=" * 90
        )
