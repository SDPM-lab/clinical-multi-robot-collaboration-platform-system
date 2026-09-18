#!/usr/bin/env python3

from copy import deepcopy

from rmf_fleet_msgs.msg import (
    FleetState,
    RobotMode,
)

from scheduler_v2.models import (
    RobotState,
)

from rl_v2.runtime_state_manager import (
    RuntimeStateManager,
)

from scheduler_v2.capabilities import (
    ROBOT_CAPABILITIES,
)


# ==========================================================
# Expected Robots
# ==========================================================

EXPECTED_ROBOT_IDS = (
    "hospital_robot_1",
    "hospital_robot_2",
    "hospital_robot_3",
    "hospital_robot_4",
)


# ==========================================================
# RMF Mode -> Scheduler Status
# ==========================================================

def convert_rmf_mode(
    mode: int,
) -> tuple[str, bool]:
    """
    回傳：

        scheduler_status,
        available

    Scheduler 支援：
        idle
        busy
        charging
        error
        offline

    available != idle

    MOVING / WAITING 等 busy robot
    仍可接受未來 Waiting Task。
    """

    mode = int(
        mode
    )

    if mode == RobotMode.MODE_IDLE:

        return (
            "idle",
            True,
        )

    if mode == RobotMode.MODE_CHARGING:

        return (
            "charging",
            False,
        )

    if mode == RobotMode.MODE_MOVING:

        return (
            "busy",
            True,
        )

    if mode == RobotMode.MODE_PAUSED:

        # 暫停中的 Robot
        # 暫時不接受新 Task。
        return (
            "busy",
            False,
        )

    if mode == RobotMode.MODE_WAITING:

        return (
            "busy",
            True,
        )

    if mode == RobotMode.MODE_EMERGENCY:

        return (
            "error",
            False,
        )

    if mode == RobotMode.MODE_GOING_HOME:

        return (
            "busy",
            True,
        )

    if mode == RobotMode.MODE_DOCKING:

        return (
            "busy",
            True,
        )

    if mode == RobotMode.MODE_ADAPTER_ERROR:

        return (
            "error",
            False,
        )

    if mode == RobotMode.MODE_CLEANING:

        return (
            "busy",
            True,
        )

    # 未知 Mode 採保守策略。
    return (
        "error",
        False,
    )


# ==========================================================
# Battery
# ==========================================================

def normalize_rmf_battery(
    battery_percent: float,
) -> float:
    """
    RMF 欄位雖然叫 battery_percent，
    目前實際 FleetState 收到的是約：

        0.99

    Scheduler 要求：

        0.0 ~ 1.0

    為了兼容：
        0~1   -> 直接使用
        0~100 -> 除以 100
    """

    value = float(
        battery_percent
    )

    if (
        0.0
        <=
        value
        <=
        1.0
    ):

        return value

    if (
        1.0
        <
        value
        <=
        100.0
    ):

        return (
            value
            /
            100.0
        )

    raise ValueError(
        "Unexpected RMF battery value: "
        f"{value}"
    )


# ==========================================================
# One RMF Robot -> Scheduler RobotState
# ==========================================================

def convert_rmf_robot_state(
    rmf_robot,
    *,
    fleet_name: str = "hospital_fleet",
) -> RobotState:

    robot_id = str(
        rmf_robot.name
    )

    if (
        robot_id
        not in ROBOT_CAPABILITIES
    ):

        raise ValueError(
            "No Scheduler Capability "
            "configuration for Robot: "
            f"{robot_id}"
        )

    (
        status,
        available,
    ) = convert_rmf_mode(
        rmf_robot.mode.mode
    )

    task_id = (
        str(
            rmf_robot.task_id
        ).strip()
    )

    return RobotState(
        robot_id=robot_id,

        fleet_name=(
            fleet_name
        ),

        status=status,

        battery=(
            normalize_rmf_battery(
                rmf_robot
                .battery_percent
            )
        ),

        x=float(
            rmf_robot
            .location
            .x
        ),

        y=float(
            rmf_robot
            .location
            .y
        ),

        map_name=(
            str(
                rmf_robot
                .location
                .level_name
            )
        ),

        capabilities=set(
            ROBOT_CAPABILITIES[
                robot_id
            ]
        ),

        # 注意：
        #
        # RMF RobotState.task_id 是最近 Request
        # 的 task_id。
        #
        # 這裡先只存成 telemetry information，
        # 不直接將它轉成 Runtime running_task。
        current_task=(
            task_id
            if task_id
            else None
        ),

        available=available,
    )


# ==========================================================
# Fleet State Aggregator
# ==========================================================

class RMFFleetStateAggregator:
    """
    /fleet_states 有多個 Publisher。

    因此不能假設一筆 FleetState
    就包含所有 Robot。

    此 class 依 robot.name 保存
    每台 Robot 最新狀態。
    """

    def __init__(
        self,
        expected_robot_ids=(
            EXPECTED_ROBOT_IDS
        ),
    ):

        self.expected_robot_ids = tuple(
            expected_robot_ids
        )

        self.latest_states: dict[
            str,
            RobotState,
        ] = {}

        self.latest_source_fleet: dict[
            str,
            str,
        ] = {}


    # ======================================================
    # Ingest
    # ======================================================

    def ingest(
        self,
        message: FleetState,
    ) -> None:

        for rmf_robot in (
            message.robots
        ):

            robot_id = str(
                rmf_robot.name
            )

            if (
                robot_id
                not in self.expected_robot_ids
            ):

                continue

            state = (
                convert_rmf_robot_state(
                    rmf_robot,
                    fleet_name=(
                        "hospital_fleet"
                    ),
                )
            )

            self.latest_states[
                robot_id
            ] = state

            self.latest_source_fleet[
                robot_id
            ] = str(
                message.name
            )


    # ======================================================
    # State
    # ======================================================

    def missing_robot_ids(
        self,
    ) -> tuple[str, ...]:

        return tuple(
            robot_id
            for robot_id
            in self.expected_robot_ids
            if (
                robot_id
                not in
                self.latest_states
            )
        )


    def ready(
        self,
    ) -> bool:

        return (
            len(
                self.missing_robot_ids()
            )
            ==
            0
        )


    def get_robot_states(
        self,
    ) -> list[
        RobotState
    ]:

        if not self.ready():

            raise RuntimeError(
                "RMF Robot States incomplete. "
                f"Missing: "
                f"{self.missing_robot_ids()}"
            )

        return [
            deepcopy(
                self.latest_states[
                    robot_id
                ]
            )
            for robot_id
            in sorted(
                self.expected_robot_ids
            )
        ]


    # ======================================================
    # Runtime Manager
    # ======================================================

    def create_runtime_manager(
        self,
        *,
        robot_speed_mps: float = 1.0,
    ) -> RuntimeStateManager:

        return (
            RuntimeStateManager(
                robots=(
                    self
                    .get_robot_states()
                ),
                robot_speed_mps=(
                    robot_speed_mps
                ),
            )
        )


    def update_runtime_manager(
        self,
        manager: RuntimeStateManager,
    ) -> None:
        """
        只同步 RMF Telemetry：

            status
            battery
            x
            y
            map
            available

        不碰：
            running_task
            waiting_tasks
            running_remaining_time

        這些由 Scheduler / Task Lifecycle
        自己維護。
        """

        for robot_id in sorted(
            self.latest_states
        ):

            state = (
                self.latest_states[
                    robot_id
                ]
            )

            manager.update_robot_state(
                robot_id=robot_id,
                status=state.status,
                battery=state.battery,
                x=state.x,
                y=state.y,
                map_name=state.map_name,
                available=(
                    state.available
                ),
            )

            # task_id 目前先當 Telemetry。
            manager.get_runtime(
                robot_id
            ).robot.current_task = (
                state.current_task
            )
