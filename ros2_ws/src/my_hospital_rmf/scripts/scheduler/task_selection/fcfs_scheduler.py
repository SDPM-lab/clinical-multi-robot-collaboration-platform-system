from scheduler.models import Task


class FCFSScheduler:
    """
    First Come, First Served Task Scheduler.

    Queue 中最早進入的 Task 優先處理。

    這個 Scheduler 只負責：
        Task Selection

    不負責：
        Capability Matching
        Robot Selection
        RMF Dispatch
    """

    name = "fcfs"

    def select(
        self,
        tasks,
    ) -> Task | None:

        # Queue 沒有任何 Task
        if not tasks:
            return None

        # deque[0] 就是最早進入 Queue 的 Task
        return tasks[0]