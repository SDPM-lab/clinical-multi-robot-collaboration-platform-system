#!/usr/bin/env python3

from dataclasses import dataclass

from experiment.simulator import (
    BaselineSimulator,
)

from scheduler.models import (
    Task,
    RobotState,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)


@dataclass
class ScenarioStub:
    waypoints: dict
    robots: list
    tasks: list
    task_arrival_times: dict


def make_task(
    task_id,
    priority,
    source="storage",
    destination="ward_a",
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


def build_simulator():

    scenario = ScenarioStub(
        waypoints={
            "storage": (0.0, 0.0),
            "ward_a": (10.0, 0.0),
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
            )
        ],
        tasks=[],
        task_arrival_times={},
    )

    return BaselineSimulator(
        scenario=scenario,
        task_scheduler=PriorityScheduler(),
        robot_scheduler=NearestScheduler(
            scenario.waypoints
        ),
    )


def build_reassignment_simulator(
    tasks,
):

    scenario = ScenarioStub(
        waypoints={
            # Robot1 區域
            "r1_source": (
                0.0,
                0.0,
            ),
            "r1_destination": (
                0.0,
                0.0,
            ),

            # Robot2 區域
            "r2_source": (
                100.0,
                0.0,
            ),
            "r2_destination": (
                100.0,
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
        ],

        tasks=tasks,

        task_arrival_times={
            task.task_id: float(index)
            for index, task
            in enumerate(tasks)
        },
    )

    return BaselineSimulator(
        scenario=scenario,
        task_scheduler=PriorityScheduler(),
        robot_scheduler=NearestScheduler(
            scenario.waypoints
        ),

        # 這個測試明確啟用 Dynamic Reassignment。
        enable_dynamic_reassignment=True,
    )


def build_cascade_simulator(
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

    return BaselineSimulator(
        scenario=scenario,
        task_scheduler=PriorityScheduler(),
        robot_scheduler=NearestScheduler(
            scenario.waypoints
        ),
        enable_dynamic_reassignment=True,
    )


def test_lower_priority_does_not_trigger():

    simulator = build_simulator()

    sim_state = simulator.robot_states[
        "robot1"
    ]

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

    sim_state.waiting_tasks = [
        task_a,
        task_b,
        task_c,
    ]

    displaced = (
        simulator.get_displaced_tasks(
            sim_state,
            task_d,
        )
    )

    assert (
        [task.task_id for task in displaced]
        ==
        []
    )


def test_high_priority_displaces_lower_tasks():

    simulator = build_simulator()

    sim_state = simulator.robot_states[
        "robot1"
    ]

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
        3,
    )

    sim_state.waiting_tasks = [
        task_a,
        task_b,
        task_c,
    ]

    displaced = (
        simulator.get_displaced_tasks(
            sim_state,
            task_d,
        )
    )

    assert (
        [
            task.task_id
            for task in displaced
        ]
        ==
        [
            "B",
            "C",
        ]
    )


def test_displaced_tasks_can_move_to_other_robot():

    # A 與 D 都適合 Robot1。
    #
    # B、C 的工作地點則非常靠近 Robot2。
    #
    # 原本故意把 A/B/C 都放在 Robot1，
    # 模擬它們是之前已經完成 Assignment 的 Tasks。

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

    # D 是新到達的高優先任務，
    # 且位置非常靠近 Robot1。
    task_d = make_task(
        "D",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    simulator = (
        build_reassignment_simulator(
            [
                task_a,
                task_b,
                task_c,
                task_d,
            ]
        )
    )

    robot1 = (
        simulator.robot_states[
            "robot1"
        ]
    )

    # 模擬原本：
    #
    # Robot1:
    # A(P3) -> B(P2) -> C(P1)
    #
    # Robot2:
    # empty
    robot1.waiting_tasks = [
        task_a,
        task_b,
        task_c,
    ]

    # D 會先因距離選到 Robot1。
    #
    # Priority order 變成：
    #
    # A(P3)
    # D(P3)
    # B(P2)
    # C(P1)
    #
    # 因此 B、C 被插隊，
    # 取得重新選 Robot 的機會。
    simulator.assign_task_to_robot(
        task_d
    )

    # ------------------------------------------
    # A 沒有被 D 延後
    # -> 仍留 Robot1
    # ------------------------------------------

    assert (
        simulator.find_waiting_task_robot(
            "A"
        )
        ==
        "robot1"
    )

    # ------------------------------------------
    # D 本身這一輪不重新派
    # -> 留 Robot1
    # ------------------------------------------

    assert (
        simulator.find_waiting_task_robot(
            "D"
        )
        ==
        "robot1"
    )

    # ------------------------------------------
    # B、C 被 D 延後，
    # 重新計算後 Robot2 明顯比較適合。
    # ------------------------------------------

    assert (
        simulator.find_waiting_task_robot(
            "B"
        )
        ==
        "robot2"
    )

    assert (
        simulator.find_waiting_task_robot(
            "C"
        )
        ==
        "robot2"
    )

    # ------------------------------------------
    # 最終 projected execution order
    # ------------------------------------------

    robot1_order = [
        task.task_id
        for task
        in simulator.get_projected_queue_order(
            simulator.robot_states[
                "robot1"
            ].waiting_tasks
        )
    ]

    robot2_order = [
        task.task_id
        for task
        in simulator.get_projected_queue_order(
            simulator.robot_states[
                "robot2"
            ].waiting_tasks
        )
    ]

    assert robot1_order == [
        "A",
        "D",
    ]

    assert robot2_order == [
        "B",
        "C",
    ]

    # ------------------------------------------
    # Reassignment log
    # ------------------------------------------

    changed_events = [
        event
        for event
        in simulator.reassignment_events
        if event[
            "changed_robot"
        ]
    ]

    assert [
        (
            event["task_id"],
            event["from_robot_id"],
            event["to_robot_id"],
        )
        for event
        in changed_events
    ] == [
        (
            "B",
            "robot1",
            "robot2",
        ),
        (
            "C",
            "robot1",
            "robot2",
        ),
    ]


def test_cascade_reassignment_when_moved_task_displaces_target_queue():

    # Robot1 原本：
    #
    # A(P3)
    # B(P2)
    #
    # Robot2 原本：
    #
    # E(P1)
    # F(P0)
    #
    # Robot3：
    # empty
    #
    # D(P3) 到 Robot1：
    #
    # A -> D -> B
    #
    # B 被 D 延後
    # -> B 重新派工
    #
    # B 工作位置靠近 Robot2
    # -> B 搬 Robot2
    #
    # Robot2：
    #
    # B(P2) -> E(P1) -> F(P0)
    #
    # B 又造成 E/F 延後
    # -> E/F 也要重新派工
    #
    # E/F 工作位置靠近 Robot3
    # -> 最後搬到 Robot3

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

    simulator = (
        build_cascade_simulator(
            [
                task_a,
                task_b,
                task_e,
                task_f,
                task_d,
            ]
        )
    )

    robot1 = simulator.robot_states[
        "robot1"
    ]

    robot2 = simulator.robot_states[
        "robot2"
    ]

    # 手動建立派工完成、
    # 但尚未開始執行的 Queue。
    robot1.waiting_tasks = [
        task_a,
        task_b,
    ]

    robot2.waiting_tasks = [
        task_e,
        task_f,
    ]

    # D 應先選 Robot1。
    simulator.assign_task_to_robot(
        task_d
    )

    # ------------------------------------------
    # 最終 Task 所屬 Robot
    # ------------------------------------------

    assert (
        simulator.find_waiting_task_robot(
            "A"
        )
        ==
        "robot1"
    )

    assert (
        simulator.find_waiting_task_robot(
            "D"
        )
        ==
        "robot1"
    )

    # B 被 D 插隊後，
    # 重新派往 Robot2。
    assert (
        simulator.find_waiting_task_robot(
            "B"
        )
        ==
        "robot2"
    )

    # E/F 又被 B 插隊，
    # 得到重新規劃機會，
    # 最後移往 Robot3。
    assert (
        simulator.find_waiting_task_robot(
            "E"
        )
        ==
        "robot3"
    )

    assert (
        simulator.find_waiting_task_robot(
            "F"
        )
        ==
        "robot3"
    )

    # ------------------------------------------
    # Reassignment Chain
    # ------------------------------------------

    changed_events = [
        event
        for event
        in simulator.reassignment_events
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
            "direct_trigger_task_id"
        ]
        ==
        "D"
    )

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
            "direct_trigger_task_id"
        ]
        ==
        "B"
    )

    assert (
        changed_map[
            "F"
        ][
            "direct_trigger_task_id"
        ]
        ==
        "B"
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


def test_cascade_stops_when_moved_task_does_not_displace_target_queue():

    task_a = make_task(
        "A",
        3,
        source="r1_source",
        destination="r1_destination",
    )

    # B 被 D 影響，
    # 會搬去 Robot2。
    task_b = make_task(
        "B",
        2,
        source="r2_source",
        destination="r2_destination",
    )

    # E/F Priority 都比 B 高。
    #
    # 所以 B 搬到 Robot2 後：
    #
    # E -> F -> B
    #
    # B 沒有插隊，
    # E/F 不准重新規劃。
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

    simulator = (
        build_cascade_simulator(
            [
                task_a,
                task_b,
                task_e,
                task_f,
                task_d,
            ]
        )
    )

    simulator.robot_states[
        "robot1"
    ].waiting_tasks = [
        task_a,
        task_b,
    ]

    simulator.robot_states[
        "robot2"
    ].waiting_tasks = [
        task_e,
        task_f,
    ]

    simulator.assign_task_to_robot(
        task_d
    )

    # B 有被 D 影響，因此可以搬 Robot2。
    assert (
        simulator.find_waiting_task_robot(
            "B"
        )
        ==
        "robot2"
    )

    # 但是 B 沒有插到 E/F 前面，
    # 所以 E/F 完全不能被重新派工。
    assert (
        simulator.find_waiting_task_robot(
            "E"
        )
        ==
        "robot2"
    )

    assert (
        simulator.find_waiting_task_robot(
            "F"
        )
        ==
        "robot2"
    )

    # E/F 不應該出現在 Reassignment Event。
    reassigned_task_ids = {
        event[
            "task_id"
        ]
        for event
        in simulator.reassignment_events
    }

    assert (
        "E"
        not in reassigned_task_ids
    )

    assert (
        "F"
        not in reassigned_task_ids
    )


def test_dynamic_reassignment_disabled_preserves_old_behavior():

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
        ],

        tasks=[
            task_a,
            task_b,
            task_c,
            task_d,
        ],

        task_arrival_times={
            "A": 0.0,
            "B": 1.0,
            "C": 2.0,
            "D": 3.0,
        },
    )

    simulator = BaselineSimulator(
        scenario=scenario,
        task_scheduler=PriorityScheduler(),
        robot_scheduler=NearestScheduler(
            scenario.waypoints
        ),

        # 明確關閉。
        enable_dynamic_reassignment=False,
    )

    simulator.robot_states[
        "robot1"
    ].waiting_tasks = [
        task_a,
        task_b,
        task_c,
    ]

    simulator.assign_task_to_robot(
        task_d
    )

    # D 雖然會插到 B/C 前面，
    # 但 Dynamic Reassignment 關閉。
    #
    # 所以 B/C 仍然固定在 Robot1。
    assert (
        simulator.find_waiting_task_robot(
            "B"
        )
        ==
        "robot1"
    )

    assert (
        simulator.find_waiting_task_robot(
            "C"
        )
        ==
        "robot1"
    )

    # 不應產生任何 Reassignment Event。
    assert (
        simulator.reassignment_events
        ==
        []
    )


def test_running_task_is_never_reassigned():

    task_running = make_task(
        "RUNNING",
        1,
        source="r1_source",
        destination="r1_destination",
    )

    task_waiting = make_task(
        "WAITING",
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

    simulator = (
        build_reassignment_simulator(
            [
                task_running,
                task_waiting,
                task_d,
            ]
        )
    )

    robot1 = simulator.robot_states[
        "robot1"
    ]

    # 直接建立一筆正在執行中的 Task。
    #
    # 用正式 RunningTaskState。
    from experiment.simulator import (
        RunningTaskState,
    )

    robot1.running_task = (
        RunningTaskState(
            task=task_running,
            arrival_time=0.0,
            start_time=0.0,
            completion_time=100.0,
            service_time=100.0,
            travel_distance=0.0,
            destination_x=0.0,
            destination_y=0.0,
        )
    )

    robot1.waiting_tasks = [
        task_waiting,
    ]

    simulator.current_time = 10.0

    simulator.assign_task_to_robot(
        task_d
    )

    # Running Task 還必須是原本那一筆。
    assert (
        simulator.robot_states[
            "robot1"
        ].running_task.task.task_id
        ==
        "RUNNING"
    )

    # Running Task 不得出現在 Reassignment Event。
    reassigned_task_ids = {
        event[
            "task_id"
        ]
        for event
        in simulator.reassignment_events
    }

    assert (
        "RUNNING"
        not in reassigned_task_ids
    )


if __name__ == "__main__":

    test_lower_priority_does_not_trigger()

    test_high_priority_displaces_lower_tasks()

    test_displaced_tasks_can_move_to_other_robot()

    test_cascade_reassignment_when_moved_task_displaces_target_queue()

    test_cascade_stops_when_moved_task_does_not_displace_target_queue()

    test_dynamic_reassignment_disabled_preserves_old_behavior()

    test_running_task_is_never_reassigned()

    print(
        "Dynamic reassignment tests passed."
    )