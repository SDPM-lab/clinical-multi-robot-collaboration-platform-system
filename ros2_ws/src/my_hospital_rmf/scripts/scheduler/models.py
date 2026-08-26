from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """
    Scheduler 使用的標準任務資料格式。
    """

    task_id: str
    task_type: str
    source: str
    destination: str
    priority: int

    required_capabilities: list[str] = field(
        default_factory=list
    )


@dataclass
class RobotState:
    """
    Scheduler 使用的標準 Robot State。
    """

    robot_id: str
    fleet_name: str
    status: str
    battery: float

    x: float
    y: float
    map_name: str

    capabilities: set[str] = field(
        default_factory=set
    )

    current_task: Optional[str] = None

    available: bool = True


@dataclass
class Assignment:
    """
    Scheduler 的標準輸出格式。
    """

    task_id: str

    robot_id: Optional[str]

    scheduler: str

    decision_status: str

    score: Optional[float] = None