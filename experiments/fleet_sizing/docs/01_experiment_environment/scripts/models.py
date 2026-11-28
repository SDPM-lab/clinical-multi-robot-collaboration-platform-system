from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================
# Task State
# ============================================================

@dataclass
class TaskState:
    task_id: str
    task_type: str

    source: str
    destination: str

    priority: int

    arrival_time_s: float
    service_time_s: float

    # --------------------------------------------------------
    # Assignment
    # --------------------------------------------------------

    assigned_robot: Optional[str] = None
    assignment_time_s: Optional[float] = None

    # --------------------------------------------------------
    # Execution timing
    # --------------------------------------------------------

    # Robot starts travelling toward task source
    start_time_s: Optional[float] = None

    # Robot reaches task source
    source_arrival_time_s: Optional[float] = None

    # Task finishes at destination
    completion_time_s: Optional[float] = None

    # --------------------------------------------------------
    # Travel
    # --------------------------------------------------------

    approach_time_s: float = 0.0
    task_travel_time_s: float = 0.0

    # --------------------------------------------------------
    # Queue
    # --------------------------------------------------------

    queue_position: Optional[int] = None

    # waiting / queued / active / completed / unserved
    status: str = "waiting"

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    @property
    def waiting_time_s(
        self,
    ) -> Optional[float]:

        if self.start_time_s is None:
            return None

        return (
            self.start_time_s
            - self.arrival_time_s
        )

    @property
    def source_response_time_s(
        self,
    ) -> Optional[float]:

        if self.source_arrival_time_s is None:
            return None

        return (
            self.source_arrival_time_s
            - self.arrival_time_s
        )

    @property
    def total_time_s(
        self,
    ) -> Optional[float]:

        if self.completion_time_s is None:
            return None

        return (
            self.completion_time_s
            - self.arrival_time_s
        )


# ============================================================
# Robot State
# ============================================================

@dataclass
class RobotState:

    robot_id: str
    robot_type: str

    capabilities: List[str]

    # Robot's latest physically confirmed location.
    current_location: str

    # idle / busy
    status: str = "idle"

    # ========================================================
    # Currently executing task
    # ========================================================

    current_task_id: Optional[str] = None

    current_task_start_time_s: Optional[float] = None
    current_task_completion_time_s: Optional[float] = None

    current_task_destination: Optional[str] = None

    # ========================================================
    # Explicit future queue
    #
    # IMPORTANT:
    # Does NOT include current_task_id.
    #
    # Example:
    #
    # current_task_id = T001
    #
    # queued_task_ids =
    # [
    #     T002,
    #     T003,
    # ]
    #
    # T001 cannot be interrupted.
    # T002/T003 may later be reordered by scheduler.
    # ========================================================

    queued_task_ids: List[str] = field(
        default_factory=list
    )

    # ========================================================
    # Cached schedule state
    #
    # These are retained because they are useful for
    # earliest-available assignment.
    # ========================================================

    # Time when current task + all queued tasks finish.
    available_time_s: float = 0.0

    # Location after all queued work finishes.
    future_location: Optional[str] = None

    # ========================================================
    # Statistics
    # ========================================================

    busy_time_s: float = 0.0

    completed_tasks: int = 0

    assigned_task_ids: List[str] = field(
        default_factory=list
    )

    # ========================================================
    # Battery State
    # ========================================================

    # Current normalized State of Charge.
    #
    # 0.0 = empty
    # 1.0 = fully charged
    battery_soc: float = 1.0

    minimum_battery_soc: float = 1.0

    return_to_charge_count: int = 0

    charging_count: int = 0

    # Charging state information.
    charging_start_time_s: Optional[float] = None
    charging_end_time_s: Optional[float] = None
    charging_start_soc: Optional[float] = None

    # ========================================================
    # Battery Statistics
    # ========================================================

    total_energy_consumed_soc: float = 0.0

    total_charging_time_s: float = 0.0

    charging_cycles: int = 0

    # ========================================================
    # State helpers
    # ========================================================

    def is_idle(
        self,
    ) -> bool:

        return (
            self.current_task_id is None
            and not self.queued_task_ids
        )

    def is_busy(
        self,
    ) -> bool:

        return not self.is_idle()

    def has_active_task(
        self,
    ) -> bool:

        return (
            self.current_task_id
            is not None
        )

    def queue_length(
        self,
    ) -> int:

        return len(
            self.queued_task_ids
        )

    def scheduled_task_count(
        self,
    ) -> int:

        count = len(
            self.queued_task_ids
        )

        if self.current_task_id is not None:
            count += 1

        return count

    # ========================================================
    # Compatibility helpers
    # ========================================================

    def is_available_at(
        self,
        current_time_s: float,
    ) -> bool:

        return (
            self.available_time_s
            <= current_time_s
        )

    def remaining_busy_time(
        self,
        current_time_s: float,
    ) -> float:

        return max(
            0.0,
            self.available_time_s
            - current_time_s,
        )

    def get_assignment_origin(
        self,
        current_time_s: float,
    ) -> str:

        # Entire schedule already completed
        if self.is_available_at(
            current_time_s
        ):
            return self.current_location

        # Future queue exists.
        if self.future_location is None:
            raise RuntimeError(
                f"{self.robot_id} has scheduled work "
                "but future_location is None."
            )

        return self.future_location