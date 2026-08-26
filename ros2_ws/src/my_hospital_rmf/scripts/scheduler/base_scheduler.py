from abc import ABC, abstractmethod

from .models import (
    Task,
    RobotState,
    Assignment,
)


class BaseScheduler(ABC):
    """
    所有 Scheduler 的共同介面。

    FCFS、Nearest、Rule-based、RL
    都必須實作 schedule()。
    """

    @abstractmethod
    def schedule(
        self,
        task: Task,
        robots: list[RobotState],
    ) -> Assignment:
        """
        根據任務與候選機器人，
        回傳一個 Assignment。
        """

        raise NotImplementedError