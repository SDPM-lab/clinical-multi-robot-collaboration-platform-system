#!/usr/bin/env python3

from collections import deque

from scheduler.models import (
    Task,
    RobotState,
)

from scheduler.capability_matcher import (
    capability_matching,
)

from scheduler.task_selection.fcfs_scheduler import (
    FCFSScheduler,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)

from scheduler.robot_selection.rule_based_scheduler import (
    RuleBasedScheduler,
)


# ==========================================================
# 測試 Waypoints
#
# 第一版先寫固定座標，
# 不依賴 RMF nav_graph。
# ==========================================================

WAYPOINTS = {
    "pharmacy": (
        0.0,
        0.0,
    ),

    "lab": (
        10.0,
        0.0,
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
# 建立固定 Robot State
# ==========================================================

def create_robots():

    return [

        RobotState(
            robot_id="robot_1",
            fleet_name="hospital_fleet",
            status="idle",
            battery=0.10,
            x=3.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
            current_task=None,
            available=True,
        ),

        RobotState(
            robot_id="robot_2",
            fleet_name="hospital_fleet",
            status="idle",
            battery=0.70,
            x=8.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
            current_task=None,
            available=True,
        ),

        RobotState(
            robot_id="robot_3",
            fleet_name="hospital_fleet",
            status="idle",
            battery=0.95,
            x=15.0,
            y=0.0,
            map_name="L1",
            capabilities={
                "navigation",
                "specimen_delivery",
                "general_delivery",
            },
            current_task=None,
            available=True,
        ),
    ]


# ==========================================================
# 建立固定 Tasks
#
# 注意：
# 加入 Queue 的順序是：
#
# T1 Normal
# T2 High
# T3 Emergency
#
# FCFS 應該：
# T1 → T2 → T3
#
# Priority 應該：
# T3 → T2 → T1
# ==========================================================

def create_tasks():

    return deque([

        Task(
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

        Task(
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

        Task(
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
    ])


# ==========================================================
# 執行一組 Baseline
# ==========================================================

def run_baseline(
    name,
    task_scheduler,
    robot_scheduler,
):

    print()
    print("=" * 80)
    print(
        f"Baseline: {name}"
    )
    print("=" * 80)

    # 每組 Baseline 都重新建立
    # 相同 Task / Robot State
    #
    # 確保實驗公平。
    tasks = create_tasks()
    robots = create_robots()

    task_order = []
    assignments = []

    while tasks:

        # --------------------------------------------------
        # Task Selection
        # --------------------------------------------------

        task = task_scheduler.select(
            tasks
        )

        if task is None:
            break

        task_order.append(
            task.task_id
        )

        # --------------------------------------------------
        # Capability Matching
        # --------------------------------------------------

        candidates = (
            capability_matching(
                task.required_capabilities,
                robots,
            )
        )

        # --------------------------------------------------
        # Availability
        # --------------------------------------------------

        available_candidates = [
            robot
            for robot in candidates
            if robot.available
        ]

        if not available_candidates:

            print(
                f"{task.task_id}: "
                "沒有可用 Robot"
            )

            tasks.remove(
                task
            )

            continue

        # --------------------------------------------------
        # Robot Selection
        # --------------------------------------------------

        assignment = (
            robot_scheduler.schedule(
                task,
                available_candidates,
            )
        )

        assignments.append(
            assignment
        )

        print(
            f"{task.task_id}"
            f" | priority={task.priority}"
            f" | robot={assignment.robot_id}"
            f" | score={assignment.score}"
        )

        # --------------------------------------------------
        # 測試版：
        #
        # 每一筆 Task 完成後，
        # Robot 立即重新 available。
        #
        # 這一版主要測 Scheduler 邏輯，
        # 還不是時間模擬。
        # --------------------------------------------------

        tasks.remove(
            task
        )

    print()
    print(
        "Task execution order:",
        " -> ".join(
            task_order
        ),
    )

    return {
        "name": name,
        "task_order": task_order,
        "assignments": assignments,
    }


# ==========================================================
# Main
# ==========================================================

def main():

    baselines = [

        (
            "FCFS + Nearest",
            FCFSScheduler(),
            NearestScheduler(
                WAYPOINTS
            ),
        ),

        (
            "FCFS + Rule-based",
            FCFSScheduler(),
            RuleBasedScheduler(
                WAYPOINTS
            ),
        ),

        (
            "Priority + Nearest",
            PriorityScheduler(),
            NearestScheduler(
                WAYPOINTS
            ),
        ),

        (
            "Priority + Rule-based",
            PriorityScheduler(),
            RuleBasedScheduler(
                WAYPOINTS
            ),
        ),
    ]

    results = []

    for (
        name,
        task_scheduler,
        robot_scheduler,
    ) in baselines:

        result = run_baseline(
            name,
            task_scheduler,
            robot_scheduler,
        )

        results.append(
            result
        )

    # ======================================================
    # Summary
    # ======================================================

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)

    for result in results:

        print(
            f"{result['name']}: "
            + " -> ".join(
                result["task_order"]
            )
        )


if __name__ == "__main__":
    main()