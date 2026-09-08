#!/usr/bin/env python3

from dataclasses import dataclass

from rl.hospital_env import (
    HospitalRLEnv,
)

from scheduler.models import (
    Task,
    RobotState,
)


@dataclass
class ScenarioStub:
    waypoints: dict
    robots: list
    tasks: list
    task_arrival_times: dict


# ==========================================================
# Task Helper
# ==========================================================

def make_task(
    task_id,
    priority,
    source="r1_source",
    destination="r1_destination",
):

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source=source,
        destination=destination,
        priority=priority,
        required_capabilities=[
            "navigation",
            "general_delivery",
        ],
    )


# ==========================================================
# Environment
# ==========================================================

def build_env(
    tasks,
):

    scenario = ScenarioStub(
        waypoints={
            "r1_source": (
                0.0,
                0.0,
            ),
            "r1_destination": (
                0.0,
                0.0,
            ),

            "r2_source": (
                100.0,
                0.0,
            ),
            "r2_destination": (
                100.0,
                0.0,
            ),

            "r3_source": (
                200.0,
                0.0,
            ),
            "r3_destination": (
                200.0,
                0.0,
            ),
        },

        robots=[
            RobotState(
                robot_id="robot1",
                fleet_name="hospital",
                map_name="test_map",
                status="idle",
                battery=1.0,
                x=0.0,
                y=0.0,
                capabilities=[
                    "navigation",
                    "general_delivery",
                ],
                current_task=None,
                available=True,
            ),

            RobotState(
                robot_id="robot2",
                fleet_name="hospital",
                map_name="test_map",
                status="idle",
                battery=1.0,
                x=100.0,
                y=0.0,
                capabilities=[
                    "navigation",
                    "general_delivery",
                ],
                current_task=None,
                available=True,
            ),

            RobotState(
                robot_id="robot3",
                fleet_name="hospital",
                map_name="test_map",
                status="idle",
                battery=1.0,
                x=200.0,
                y=0.0,
                capabilities=[
                    "navigation",
                    "general_delivery",
                ],
                current_task=None,
                available=True,
            ),
        ],

        tasks=tasks,

        task_arrival_times={
            task.task_id: float(index)
            for index, task
            in enumerate(tasks)
        },
    )

    env = HospitalRLEnv(
        scenario=scenario,

        enable_dynamic_reassignment=True,
    )

    env.reset()

    return env


# ==========================================================
# Manual State Helper
#
# 這些測試不是在驗證 Task Arrival，
# 而是在驗證 Dynamic RL Assignment。
#
# 因此直接建立：
#
# Robot waiting queues
# +
# current task
# ==========================================================

def prepare_manual_state(
    env,
    current_task,
    waiting_by_robot,
    already_assigned_count,
):

    # 不讓原 Scenario 的 future arrival
    # 干擾人工建立的測試狀態。
    env.future_tasks = []

    env.pending_tasks = [
        current_task
    ]

    env.current_task = (
        current_task
    )

    env.current_time = (
        env.task_arrival_times[
            current_task.task_id
        ]
    )

    env.done = False

    env.assigned_task_count = (
        already_assigned_count
    )

    env.completed_task_count = 0

    env.execution_records = []

    env.reassignment_context = {}

    env.reassignment_events = []

    env.processed_reassignment_states = {}

    for sim_state in (
        env.robot_states.values()
    ):
        sim_state.running_task = None
        sim_state.waiting_tasks = []

    for robot_id, tasks in (
        waiting_by_robot.items()
    ):

        env.robot_states[
            robot_id
        ].waiting_tasks = list(
            tasks
        )


# ==========================================================
# Test 1
#
# D 沒插隊
# -> 不產生額外 RL Decision
# ==========================================================

def test_no_reassignment_when_new_task_does_not_displace():

    task_a = make_task(
        "A",
        3,
    )

    task_b = make_task(
        "B",
        2,
    )

    task_c = make_task(
        "C",
        1,
    )

    task_d = make_task(
        "D",
        0,
    )

    env = build_env(
        [
            task_a,
            task_b,
            task_c,
            task_d,
        ]
    )

    prepare_manual_state(
        env=env,

        current_task=task_d,

        waiting_by_robot={
            "robot1": [
                task_a,
                task_b,
                task_c,
            ],
        },

        already_assigned_count=3,
    )

    # Action 0 = robot1
    _, _, done, info = (
        env.step(
            0
        )
    )

    assert (
        info[
            "is_reassignment"
        ]
        is False
    )

    assert (
        env.reassignment_events
        ==
        []
    )

    assert (
        env.reassignment_context
        ==
        {}
    )

    # A/B/C 已派工 + D 第一次派工。
    assert (
        env.assigned_task_count
        ==
        4
    )

    # 沒有額外 RL decision，
    # 所以 simulator 可以直接繼續跑完。
    assert done is True


# ==========================================================
# Test 2
#
# D 插隊 B/C
# -> B/C 重新成為 RL Decisions
# -> Reassignment 不增加 assigned_task_count
# ==========================================================

def test_displaced_tasks_become_rl_decisions():

    task_a = make_task(
        "A",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    task_b = make_task(
        "B",
        2,
        source="r2_source",
        destination="r2_destination",
    )

    task_c = make_task(
        "C",
        1,
        source="r2_source",
        destination="r2_destination",
    )

    task_d = make_task(
        "D",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    env = build_env(
        [
            task_a,
            task_b,
            task_c,
            task_d,
        ]
    )

    prepare_manual_state(
        env=env,

        current_task=task_d,

        waiting_by_robot={
            "robot1": [
                task_a,
                task_b,
                task_c,
            ],
        },

        already_assigned_count=3,
    )

    # ------------------------------------------
    # D -> Robot1
    # ------------------------------------------

    _, _, done, info_d = (
        env.step(
            0
        )
    )

    assert done is False

    assert (
        info_d[
            "is_reassignment"
        ]
        is False
    )

    # D 是第 4 筆真正 Assignment。
    assert (
        env.assigned_task_count
        ==
        4
    )

    # B 應該立即變成下一個 RL Decision。
    assert (
        env.current_task.task_id
        ==
        "B"
    )

    context_b = (
        env.reassignment_context[
            "B"
        ]
    )

    assert (
        context_b.from_robot_id
        ==
        "robot1"
    )

    assert (
        context_b.root_trigger_task_id
        ==
        "D"
    )

    assert (
        context_b.direct_trigger_task_id
        ==
        "D"
    )

    assert (
        context_b.cascade_depth
        ==
        1
    )

    # ------------------------------------------
    # B -> Robot2
    # ------------------------------------------

    _, _, done, info_b = (
        env.step(
            1
        )
    )

    assert (
        info_b[
            "is_reassignment"
        ]
        is True
    )

    assert (
        info_b[
            "reassignment_from_robot"
        ]
        ==
        "robot1"
    )

    # Reassignment 不可增加 Assignment Count。
    assert (
        env.assigned_task_count
        ==
        4
    )

    # 下一筆應該是 C。
    assert done is False

    assert (
        env.current_task.task_id
        ==
        "C"
    )

    # ------------------------------------------
    # C -> Robot2
    # ------------------------------------------

    _, _, _, info_c = (
        env.step(
            1
        )
    )

    assert (
        info_c[
            "is_reassignment"
        ]
        is True
    )

    assert (
        env.assigned_task_count
        ==
        4
    )

    # B/C 都要留下 Reassignment Event。
    changed_events = [
        event
        for event
        in env.reassignment_events
        if event[
            "changed_robot"
        ]
    ]

    changed_task_ids = [
        event[
            "task_id"
        ]
        for event
        in changed_events
    ]

    assert (
        changed_task_ids
        ==
        [
            "B",
            "C",
        ]
    )


# ==========================================================
# Test 3
#
# D -> B -> E/F
#
# B 搬到 Robot2 後插隊 E/F，
# E/F 必須成為第二層 RL Decisions。
# ==========================================================

def test_cascade_reassignment_creates_next_level_rl_decisions():

    task_a = make_task(
        "A",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    task_b = make_task(
        "B",
        2,
        source="r2_source",
        destination="r2_destination",
    )

    task_e = make_task(
        "E",
        1,
        source="r3_source",
        destination="r3_destination",
    )

    task_f = make_task(
        "F",
        0,
        source="r3_source",
        destination="r3_destination",
    )

    task_d = make_task(
        "D",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    env = build_env(
        [
            task_a,
            task_b,
            task_e,
            task_f,
            task_d,
        ]
    )

    prepare_manual_state(
        env=env,

        current_task=task_d,

        waiting_by_robot={
            "robot1": [
                task_a,
                task_b,
            ],

            "robot2": [
                task_e,
                task_f,
            ],
        },

        already_assigned_count=4,
    )

    # D -> Robot1
    env.step(
        0
    )

    assert (
        env.current_task.task_id
        ==
        "B"
    )

    # B -> Robot2
    env.step(
        1
    )

    # B(P2) 插到 E(P1)/F(P0) 前面。
    # E 必須成為下一個 RL Decision。
    assert (
        env.current_task.task_id
        ==
        "E"
    )

    context_e = (
        env.reassignment_context[
            "E"
        ]
    )

    context_f = (
        env.reassignment_context[
            "F"
        ]
    )

    assert (
        context_e.root_trigger_task_id
        ==
        "D"
    )

    assert (
        context_e.direct_trigger_task_id
        ==
        "B"
    )

    assert (
        context_e.cascade_depth
        ==
        2
    )

    assert (
        context_f.direct_trigger_task_id
        ==
        "B"
    )

    assert (
        context_f.cascade_depth
        ==
        2
    )

    # E -> Robot3
    _, _, done, info_e = (
        env.step(
            2
        )
    )

    assert done is False

    assert (
        info_e[
            "is_reassignment"
        ]
        is True
    )

    assert (
        env.current_task.task_id
        ==
        "F"
    )

    # F -> Robot3
    _, _, _, info_f = (
        env.step(
            2
        )
    )

    assert (
        info_f[
            "is_reassignment"
        ]
        is True
    )

    # 只有 D 是新 Assignment。
    #
    # 原本 A/B/E/F 已算 4，
    # D 加入後總數必須只有 5。
    assert (
        env.assigned_task_count
        ==
        5
    )

    changed_events = [
        event
        for event
        in env.reassignment_events
        if event[
            "changed_robot"
        ]
    ]

    changed_map = {
        event[
            "task_id"
        ]: event
        for event
        in changed_events
    }

    assert (
        changed_map[
            "B"
        ][
            "cascade_depth"
        ]
        ==
        1
    )

    assert (
        changed_map[
            "E"
        ][
            "cascade_depth"
        ]
        ==
        2
    )

    assert (
        changed_map[
            "F"
        ][
            "cascade_depth"
        ]
        ==
        2
    )


# ==========================================================
# Test 4
#
# B 搬 Robot2，
# 但沒有插隊 E/F
#
# -> Cascade 必須停止。
# ==========================================================

def test_cascade_stops_when_reassigned_task_does_not_displace():

    task_a = make_task(
        "A",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    task_b = make_task(
        "B",
        2,
        source="r2_source",
        destination="r2_destination",
    )

    # 比 B 高 Priority，
    # 因此 Robot2 最終：
    #
    # E -> F -> B
    task_e = make_task(
        "E",
        3,
        source="r2_source",
        destination="r2_destination",
    )

    task_f = make_task(
        "F",
        3,
        source="r2_source",
        destination="r2_destination",
    )

    task_d = make_task(
        "D",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    env = build_env(
        [
            task_a,
            task_b,
            task_e,
            task_f,
            task_d,
        ]
    )

    prepare_manual_state(
        env=env,

        current_task=task_d,

        waiting_by_robot={
            "robot1": [
                task_a,
                task_b,
            ],

            "robot2": [
                task_e,
                task_f,
            ],
        },

        already_assigned_count=4,
    )

    # D -> Robot1
    env.step(
        0
    )

    assert (
        env.current_task.task_id
        ==
        "B"
    )

    # B -> Robot2
    _, _, _, info_b = (
        env.step(
            1
        )
    )

    assert (
        info_b[
            "is_reassignment"
        ]
        is True
    )

    # E/F 不應該取得 Reassignment Context。
    assert (
        "E"
        not in env.reassignment_context
    )

    assert (
        "F"
        not in env.reassignment_context
    )

    reassignment_task_ids = {
        event[
            "task_id"
        ]
        for event
        in env.reassignment_events
    }

    assert (
        "E"
        not in reassignment_task_ids
    )

    assert (
        "F"
        not in reassignment_task_ids
    )

    # Assignment count 仍然只有 5。
    assert (
        env.assigned_task_count
        ==
        5
    )


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    test_no_reassignment_when_new_task_does_not_displace()

    test_displaced_tasks_become_rl_decisions()

    test_cascade_reassignment_creates_next_level_rl_decisions()

    test_cascade_stops_when_reassigned_task_does_not_displace()

    print(
        "RL dynamic reassignment tests passed."
    )