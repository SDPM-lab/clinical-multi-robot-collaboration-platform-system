from dataclasses import dataclass
from typing import Callable

from scheduler.models import (
    Task,
    RobotState,
)


# ==========================================================
# Experiment Scenario
# ==========================================================

@dataclass
class Scenario:

    name: str
    description: str

    waypoints: dict[
        str,
        tuple[float, float],
    ]

    robots: list[RobotState]

    tasks: list[Task]

    task_arrival_times: dict[
        str,
        float,
    ]


# ==========================================================
# 共用 Waypoints
#
# 第一版先使用簡化座標。
# 之後可以換成 hospital nav_graph 真實座標。
# ==========================================================

BASE_WAYPOINTS = {

    "pharmacy": (
        0.0,
        0.0,
    ),

    "lab": (
        10.0,
        0.0,
    ),

    "storage": (
        0.0,
        15.0,
    ),

    "nurse_station": (
        15.0,
        10.0,
    ),

    "ward_a": (
        20.0,
        5.0,
    ),

    "ward_b": (
        30.0,
        5.0,
    ),

    "ward_c": (
        40.0,
        5.0,
    ),
}


# ==========================================================
# Helper：建立 Robot
# ==========================================================

def create_robot(
    robot_id: str,
    x: float,
    y: float,
    battery: float,
    capabilities: set[str],
) -> RobotState:

    return RobotState(

        robot_id=robot_id,

        fleet_name=(
            "hospital_fleet"
        ),

        status=(
            "idle"
        ),

        battery=(
            battery
        ),

        x=(
            x
        ),

        y=(
            y
        ),

        map_name=(
            "L1"
        ),

        capabilities=(
            capabilities
        ),

        current_task=(
            None
        ),

        available=(
            True
        ),
    )


# ==========================================================
# Helper：建立 Task
# ==========================================================

def create_task(
    task_id: str,
    task_type: str,
    source: str,
    destination: str,
    priority: int,
    required_capabilities: list[str],
) -> Task:

    return Task(

        task_id=(
            task_id
        ),

        task_type=(
            task_type
        ),

        source=(
            source
        ),

        destination=(
            destination
        ),

        priority=(
            priority
        ),

        required_capabilities=(
            required_capabilities
        ),
    )


# ==========================================================
# Scenario 1
#
# 基本 Priority 測試
#
# 目的：
# 驗證 FCFS 與 Priority 的差異。
# ==========================================================

def scenario_priority_basic() -> Scenario:

    robots = [

        create_robot(
            robot_id="robot_1",
            x=3.0,
            y=0.0,
            battery=0.90,
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
        ),

        create_robot(
            robot_id="robot_2",
            x=8.0,
            y=0.0,
            battery=0.90,
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
        ),

        create_robot(
            robot_id="robot_3",
            x=15.0,
            y=0.0,
            battery=0.90,
            capabilities={
                "navigation",
                "specimen_delivery",
                "general_delivery",
            },
        ),
    ]

    tasks = [

        create_task(
            task_id="T1",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_a",
            priority=1,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),

        create_task(
            task_id="T2",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_b",
            priority=2,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),

        create_task(
            task_id="T3",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_c",
            priority=3,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),
    ]

    return Scenario(

        name=(
            "priority_basic"
        ),

        description=(
            "驗證 FCFS 與 Priority "
            "在不同任務優先級下的差異"
        ),

        waypoints=(
            BASE_WAYPOINTS.copy()
        ),

        robots=(
            robots
        ),

        tasks=(
            tasks
        ),

        task_arrival_times={
            task.task_id: 0.0
            for task in tasks
        },
    )


# ==========================================================
# Scenario 2
#
# Low Battery 測試
#
# 目的：
# 驗證 Nearest 與 Rule-based 的差異。
# ==========================================================

def scenario_low_battery() -> Scenario:

    robots = [

        # 最近，但低電量
        create_robot(
            robot_id="robot_1",
            x=3.0,
            y=0.0,
            battery=0.10,
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
        ),

        # 較遠，但高電量
        create_robot(
            robot_id="robot_2",
            x=8.0,
            y=0.0,
            battery=0.90,
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
        ),

        create_robot(
            robot_id="robot_3",
            x=15.0,
            y=0.0,
            battery=0.90,
            capabilities={
                "navigation",
                "specimen_delivery",
                "general_delivery",
            },
        ),
    ]

    tasks = [

        create_task(
            task_id="T1",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_a",
            priority=1,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),

        create_task(
            task_id="T2",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_b",
            priority=2,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),

        create_task(
            task_id="T3",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_c",
            priority=3,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),
    ]

    return Scenario(

        name=(
            "low_battery"
        ),

        description=(
            "驗證 Nearest 與 Rule-based "
            "面對低電量 Robot 時的差異"
        ),

        waypoints=(
            BASE_WAYPOINTS.copy()
        ),

        robots=(
            robots
        ),

        tasks=(
            tasks
        ),
        task_arrival_times={
            task.task_id: 0.0
            for task in tasks
        }
    )


# ==========================================================
# Scenario 3
#
# Heterogeneous Robot Capability
#
# 目的：
# 驗證不同 Task Type 是否只會派給
# Capability 相容的 Robot。
# ==========================================================

def scenario_heterogeneous_capability() -> Scenario:

    robots = [

        create_robot(
            robot_id="robot_1",
            x=2.0,
            y=1.0,
            battery=0.90,
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
        ),

        create_robot(
            robot_id="robot_2",
            x=12.0,
            y=1.0,
            battery=0.85,
            capabilities={
                "navigation",
                "specimen_delivery",
                "general_delivery",
            },
        ),

        create_robot(
            robot_id="robot_3",
            x=5.0,
            y=12.0,
            battery=0.80,
            capabilities={
                "navigation",
                "general_delivery",
                "manipulation",
            },
        ),
    ]

    tasks = [

        create_task(
            task_id="T1",
            task_type="medicine_delivery",
            source="pharmacy",
            destination="ward_a",
            priority=2,
            required_capabilities=[
                "navigation",
                "medicine_delivery",
            ],
        ),

        create_task(
            task_id="T2",
            task_type="specimen_delivery",
            source="ward_b",
            destination="lab",
            priority=3,
            required_capabilities=[
                "navigation",
                "specimen_delivery",
            ],
        ),

        create_task(
            task_id="T3",
            task_type="general_delivery",
            source="storage",
            destination="nurse_station",
            priority=1,
            required_capabilities=[
                "navigation",
                "general_delivery",
            ],
        ),
    ]

    return Scenario(

        name=(
            "heterogeneous_capability"
        ),

        description=(
            "驗證異質 Robot Capability "
            "與 Capability Matching"
        ),

        waypoints=(
            BASE_WAYPOINTS.copy()
        ),

        robots=(
            robots
        ),

        tasks=(
            tasks
        ),

        task_arrival_times={
            task.task_id: 0.0
            for task in tasks
        },
    )


# ==========================================================
# Scenario Registry
#
# 之後新增 Scenario 時，
# 只需要加到這裡。
# ==========================================================

SCENARIOS: dict[
    str,
    Callable[[], Scenario],
] = {

    "priority_basic":
        scenario_priority_basic,

    "low_battery":
        scenario_low_battery,

    "heterogeneous_capability":
        scenario_heterogeneous_capability,
}


# ==========================================================
# Public Helper
# ==========================================================

def get_scenario(
    name: str,
) -> Scenario:

    if name not in SCENARIOS:

        raise ValueError(
            "Unknown scenario: "
            f"{name}. "
            "Available scenarios: "
            + ", ".join(
                SCENARIOS.keys()
            )
        )

    return SCENARIOS[name]()


def list_scenarios() -> list[str]:

    return list(
        SCENARIOS.keys()
    )