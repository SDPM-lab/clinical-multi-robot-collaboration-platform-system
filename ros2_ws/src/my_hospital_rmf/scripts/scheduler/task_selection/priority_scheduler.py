from scheduler.models import Task


class PriorityScheduler:
    """
    Priority-based Task Scheduler.

    規則：
    1. Priority 越高越優先
    2. Priority 相同時，維持原本 Queue 順序（FCFS）

    Priority 定義：
        0 = Low
        1 = Normal
        2 = High
        3 = Emergency

    這個 Scheduler 只負責：
        Task Selection

    不負責：
        Capability Matching
        Robot Selection
        RMF Dispatch
    """

    name = "priority"

    def select(
        self,
        tasks,
    ) -> Task | None:

        # Queue 為空
        if not tasks:
            return None

        # --------------------------------------------------
        # 找出最高 Priority
        # --------------------------------------------------

        highest_priority = max(
            task.priority
            for task in tasks
        )

        # --------------------------------------------------
        # 從 Queue 前面開始找
        #
        # 第一個符合最高 Priority 的 Task
        # 就是：
        #
        # Priority 高者優先
        # 同 Priority 時 FCFS
        # --------------------------------------------------

        for task in tasks:

            if (
                task.priority
                == highest_priority
            ):
                return task

        return None