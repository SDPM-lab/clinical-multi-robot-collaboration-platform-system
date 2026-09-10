#!/usr/bin/env python3

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.robot_selection.nearest import (
    calculate_projected_distance_to_source,
    select_nearest_feasible_robot,
)


# ==========================================================
# Helpers
# ==========================================================

def make_task(
    task_id: str = "NEW",
    priority: int = 1,
    source: str = "SOURCE",
    destination: str = "DESTINATION",
    created_at: float = 10.0,
) -> Task:

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source=source,
        destination=destination,
        priority=priority,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=created_at,
    )


def make_robot(
    robot_id: str,
    x: float,
    y: float = 0.0,
    status: str = "idle",
    battery: float = 0.80,
    capabilities: set[str] | None = None,
    available: bool = True,
) -> RobotState:

    if capabilities is None:

        capabilities = {
            "navigation",
            "general_delivery",
        }

    return RobotState(
        robot_id=robot_id,
        fleet_name="hospital_fleet",
        status=status,
        battery=battery,
        x=x,
        y=y,
        map_name="L1",
        capabilities=capabilities,
        available=available,
    )


def make_places():

    return {
        "SOURCE": Place(
            "SOURCE",
            0.0,
            0.0,
            "L1",
        ),
        "DESTINATION": Place(
            "DESTINATION",
            30.0,
            0.0,
            "L1",
        ),

        "WAIT_SOURCE": Place(
            "WAIT_SOURCE",
            10.0,
            0.0,
            "L1",
        ),

        "FAR_END": Place(
            "FAR_END",
            20.0,
            0.0,
            "L1",
        ),

        "NEAR_END": Place(
            "NEAR_END",
            1.0,
            0.0,
            "L1",
        ),
    }


# ==========================================================
# Simple Projected Distance
# ==========================================================

def test_idle_robot_projected_distance():

    task = make_task()

    runtime = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=3.0,
            y=4.0,
        )
    )

    distance = (
        calculate_projected_distance_to_source(
            task=task,
            runtime=runtime,
            places=make_places(),
            current_time=10.0,
        )
    )

    assert distance == 5.0


# ==========================================================
# Projected Nearest
# ==========================================================

def test_projected_nearest_can_differ_from_current_nearest():

    task = make_task(
        priority=1,
        created_at=10.0,
    )

    # ------------------------------------------------------
    # R1 現在離 SOURCE 只有 1 m。
    #
    # 但 R1 前面有一個較高 Priority 的 Waiting Task。
    # 該 Task 執行完後會停在 FAR_END=(20,0)。
    #
    # 因此 NEW 真正開始時：
    #
    # R1 -> SOURCE = 20 m
    # ------------------------------------------------------

    waiting_high = make_task(
        task_id="WAIT_HIGH",
        priority=2,
        source="WAIT_SOURCE",
        destination="FAR_END",
        created_at=0.0,
    )

    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
        ),
        waiting_tasks=[
            waiting_high,
        ],
    )

    # ------------------------------------------------------
    # R2 現在離 SOURCE = 8 m，
    # 而且沒有前置 Task。
    #
    # 所以 projected distance 仍為 8 m。
    # ------------------------------------------------------

    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=8.0,
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=task,
            runtimes=[
                runtime_r1,
                runtime_r2,
            ],
            places=make_places(),
            current_time=10.0,
            service_time_seconds=0.0,
        )
    )

    # 如果錯誤使用 current position，
    # 會選 R1。
    #
    # 正確使用 projected position，
    # 應選 R2。
    assert selected.robot_id == "R2"


# ==========================================================
# Priority Insertion
# ==========================================================

def test_high_priority_new_task_can_jump_queue():

    new_emergency = make_task(
        task_id="EMERGENCY",
        priority=3,
        created_at=10.0,
    )

    old_low = make_task(
        task_id="OLD_LOW",
        priority=0,
        source="WAIT_SOURCE",
        destination="FAR_END",
        created_at=0.0,
    )

    # R1 現在距 SOURCE 1 m。
    #
    # 雖然 Queue 裡有 OLD_LOW，
    # 但 Emergency 會插到 OLD_LOW 前面。
    #
    # 所以 Emergency 的 projected position
    # 仍然是 R1 current position。
    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
        ),
        waiting_tasks=[
            old_low,
        ],
    )

    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=5.0,
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=new_emergency,
            runtimes=[
                runtime_r1,
                runtime_r2,
            ],
            places=make_places(),
            current_time=10.0,
            service_time_seconds=0.0,
        )
    )

    assert selected.robot_id == "R1"


# ==========================================================
# Candidate Filter
# ==========================================================

def test_infeasible_projected_nearest_is_rejected():

    task = make_task()

    # 距離最近但 offline。
    runtime_invalid = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
            status="offline",
        )
    )

    runtime_valid = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=6.0,
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=task,
            runtimes=[
                runtime_invalid,
                runtime_valid,
            ],
            places=make_places(),
            current_time=10.0,
        )
    )

    assert selected.robot_id == "R2"


# ==========================================================
# Workload Is Not A Selection Cost
# ==========================================================

def test_nearest_does_not_directly_penalize_workload():

    task = make_task(
        priority=1,
        created_at=10.0,
    )

    # ------------------------------------------------------
    # R1 前面有一個 High Task。
    #
    # 此 Task 最後停在 NEAR_END=(1,0)，
    # 所以 NEW 真正開始時：
    #
    # projected distance = 1 m
    #
    # 但我們故意把 service_time 設非常大，
    # 讓 workload_before_task 很高。
    # ------------------------------------------------------

    waiting_high = make_task(
        task_id="WAIT_HIGH",
        priority=2,
        source="WAIT_SOURCE",
        destination="NEAR_END",
        created_at=0.0,
    )

    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=10.0,
        ),
        waiting_tasks=[
            waiting_high,
        ],
    )

    # R2 沒有 workload，
    # 但 projected distance = 5 m。
    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=5.0,
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=task,
            runtimes=[
                runtime_r1,
                runtime_r2,
            ],
            places=make_places(),
            current_time=10.0,

            # 故意給超大的服務時間，
            # 讓 R1 workload 很高。
            service_time_seconds=1000.0,
        )
    )

    # Nearest 仍然只看 projected distance：
    #
    # R1 = 1 m
    # R2 = 5 m
    #
    # 所以仍選 R1。
    assert selected.robot_id == "R1"


# ==========================================================
# Deterministic Tie Break
# ==========================================================

def test_equal_projected_distance_uses_robot_id():

    task = make_task()

    runtime_r2 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=-5.0,
        )
    )

    runtime_r1 = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=5.0,
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=task,
            runtimes=[
                runtime_r2,
                runtime_r1,
            ],
            places=make_places(),
            current_time=10.0,
        )
    )

    # 都距離 SOURCE 5 m。
    #
    # 輸入故意先 R2，
    # 最後仍應 deterministic 選 R1。
    assert selected.robot_id == "R1"


# ==========================================================
# No Candidate
# ==========================================================

def test_no_feasible_robot_returns_none():

    task = make_task()

    runtime_low_battery = RobotRuntimeState(
        robot=make_robot(
            robot_id="R1",
            x=1.0,
            battery=0.10,
        )
    )

    runtime_offline = RobotRuntimeState(
        robot=make_robot(
            robot_id="R2",
            x=2.0,
            status="offline",
        )
    )

    selected = (
        select_nearest_feasible_robot(
            task=task,
            runtimes=[
                runtime_low_battery,
                runtime_offline,
            ],
            places=make_places(),
            current_time=10.0,
            battery_threshold=0.20,
        )
    )

    assert selected is None