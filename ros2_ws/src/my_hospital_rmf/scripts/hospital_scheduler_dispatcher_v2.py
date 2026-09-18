#!/usr/bin/env python3

import json
import os
import time
import uuid

import rclpy

from rclpy.node import Node

from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
)

from ament_index_python.packages import (
    get_package_share_directory,
)

from std_msgs.msg import String

from rmf_fleet_msgs.msg import (
    FleetState,
)

from rmf_task_msgs.msg import (
    ApiRequest,
)


from scheduler_v2.backend_task_adapter import (
    build_scheduler_task,
)

from scheduler_v2.rmf_places import (
    load_places_from_nav_graph,
)

from scheduler_v2.runtime import (
    Place,
)

from scheduler_v2.task_selector import (
    sort_tasks,
)

from scheduler_v2.projection import (
    calculate_task_duration,
)

from scheduler_v2.config import (
    DEFAULT_TASK_SERVICE_TIME_SECONDS,
)

from scheduler_v2.robot_selection.nearest import (
    select_nearest_feasible_robot,
)

from rl_v2.rmf_runtime_adapter import (
    RMFFleetStateAggregator,
)

from rl_v2.frozen_scheduler import (
    FrozenInitialAssignmentScheduler,
)

from rl_v2.frozen_reassignment_scheduler import (
    FrozenReassignmentScheduler,
)


# ==========================================================
# Configuration
# ==========================================================

FLEET_NAME = "hospital_fleet"

NAV_GRAPH = os.path.join(
    get_package_share_directory(
        "my_hospital_rmf"
    ),
    "nav_graphs",
    "0.yaml",
)

# 正式 RMF fleet_config 的 nominal velocity。
#
# Experiment I 的 synthetic simulator
# 仍維持原本 1.0 m/s，不修改。
ROBOT_SPEED_MPS = 1.0

SERVICE_TIME_SECONDS = (
    DEFAULT_TASK_SERVICE_TIME_SECONDS
)

INITIAL_ASSIGNMENT_MODEL = os.path.join(
    get_package_share_directory(
        "my_hospital_rmf"
    ),
    "rl_v2",
    "models",
    "long_horizon_ppo_102k_seed42.zip",
)

REASSIGNMENT_MODEL = os.path.join(
    get_package_share_directory(
        "my_hospital_rmf"
    ),
    "rl_v2",
    "models",
    "reassignment_ppo_shaping025_102k_seed42.zip",
)


# ==========================================================
# Scheduler Dispatcher v2
# ==========================================================

class HospitalSchedulerDispatcherV2(
    Node
):

    def __init__(
        self,
    ):

        super().__init__(
            "hospital_scheduler_dispatcher_v2"
        )

        # ==================================================
        # RMF Places
        # ==================================================

        self.places = (
            load_places_from_nav_graph(
                NAV_GRAPH
            )
        )

        # ==================================================
        # RMF Robot State Adapter
        # ==================================================

        self.fleet_aggregator = (
            RMFFleetStateAggregator()
        )

        self.runtime_manager = None

        # ==================================================
        # Frozen Initial Assignment PPO
        #
        # Model is loaded once at Scheduler startup.
        # Each incoming task only performs inference.
        # ==================================================

        self.initial_assignment_scheduler = (
            FrozenInitialAssignmentScheduler(
                model_path=(
                    INITIAL_ASSIGNMENT_MODEL
                ),
                service_time_seconds=(
                    SERVICE_TIME_SECONDS
                ),
                device="cpu",
            )
        )

        # ==================================================
        # Frozen Dedicated Reassignment PPO
        #
        # 只對 Waiting Task 做 Stay / Reassign。
        # Running Task 維持 non-preemptive。
        # ==================================================

        self.reassignment_scheduler = (
            FrozenReassignmentScheduler(
                model_path=(
                    REASSIGNMENT_MODEL
                ),
                service_time_seconds=(
                    SERVICE_TIME_SECONDS
                ),
                device="cpu",
            )
        )

        # ==================================================
        # Running Task Lifecycle
        #
        # Scheduler Task ID
        # 和 RMF Request ID
        # 是不同的東西。
        # ==================================================

        self.rmf_request_ids: dict[
            str,
            str,
        ] = {}

        self.running_started_monotonic: dict[
            str,
            float,
        ] = {}

        self.running_initial_remaining: dict[
            str,
            float,
        ] = {}

        # ==================================================
        # Service Hold
        #
        # RMF 到達 Hospital Task 最終 destination 後，
        # Task 仍需保持 Running SERVICE_TIME_SECONDS，
        # 使正式 Runtime 與 Experiment / RL 的
        # travel + fixed service time 語意一致。
        #
        # robot_id -> service deadline (time.monotonic)
        # ==================================================

        self.service_deadlines_monotonic: dict[
            str,
            float,
        ] = {}

        # ==================================================
        # RMF Task Publisher
        # ==================================================

        task_qos = QoSProfile(
            history=(
                HistoryPolicy.KEEP_LAST
            ),
            depth=10,
            reliability=(
                ReliabilityPolicy.RELIABLE
            ),
            durability=(
                DurabilityPolicy.TRANSIENT_LOCAL
            ),
        )

        self.task_pub = (
            self.create_publisher(
                ApiRequest,
                "/task_api_requests",
                task_qos,
            )
        )

        # ==================================================
        # Backend Task Subscriber
        # ==================================================

        self.create_subscription(
            String,
            "/hospital_task_request",
            self.task_request_cb,
            10,
        )

        # ==================================================
        # RMF Fleet State Subscriber
        # ==================================================

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_state_cb,
            10,
        )

        # ==================================================
        # RMF Activity Completion Subscriber
        #
        # 由 hospital_fleet_adapter 發布。
        #
        # 每個 Easy Full Control navigation command
        # 真正完成後都會收到一筆事件。
        # ==================================================

        self.create_subscription(
            String,
            "/hospital_rmf_activity_completed",
            self.rmf_activity_completed_cb,
            10,
        )

        # ==================================================
        # Runtime Timer
        # ==================================================

        self.runtime_timer = (
            self.create_timer(
                0.5,
                self.runtime_timer_cb,
            )
        )

        # ==================================================
        # Startup
        # ==================================================

        self.get_logger().info(
            "Hospital Scheduler Dispatcher v2 started"
        )

        self.get_logger().info(
            "Robot selector: "
            "frozen_long_horizon_ppo"
        )

        self.get_logger().info(
            "Initial PPO model: "
            f"{INITIAL_ASSIGNMENT_MODEL}"
        )

        self.get_logger().info(
            "Queue model: "
            "per-robot Priority + Aging"
        )

        self.get_logger().info(
            "Loaded RMF places: "
            f"{len(self.places)}"
        )


    # ======================================================
    # Fleet State
    # ======================================================

    def fleet_state_cb(
        self,
        msg: FleetState,
    ):

        if msg.name != FLEET_NAME:
            return

        self.fleet_aggregator.ingest(
            msg
        )

        # --------------------------------------------------
        # 等三台 Robot 都出現後，
        # 才建立 RuntimeStateManager。
        # --------------------------------------------------

        if self.runtime_manager is None:

            if not (
                self.fleet_aggregator
                .ready()
            ):

                return

            self.runtime_manager = (
                self.fleet_aggregator
                .create_runtime_manager(
                    robot_speed_mps=(
                        ROBOT_SPEED_MPS
                    )
                )
            )

            self.get_logger().info(
                "RuntimeStateManager ready: "
                + ", ".join(
                    sorted(
                        self.runtime_manager
                        .get_runtimes()
                        .keys()
                    )
                )
            )

        else:

            self.fleet_aggregator\
                .update_runtime_manager(
                    self.runtime_manager
                )

        # --------------------------------------------------
        # FleetState 只負責更新 Robot telemetry。
        #
        # Task completion 已改由：
        #
        # /hospital_rmf_activity_completed
        #
        # 處理。
        # --------------------------------------------------

        self.try_start_all_idle_robots()


    # ======================================================
    # RMF Activity Completion
    # ======================================================

    def rmf_activity_completed_cb(
        self,
        msg: String,
    ):

        try:

            payload = json.loads(
                msg.data
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ):

            self.get_logger().warning(
                "Invalid RMF activity completion "
                f"payload: {msg.data}"
            )

            return

        robot_id = payload.get(
            "robot_id"
        )

        destination = payload.get(
            "destination"
        )

        cmd_id = payload.get(
            "cmd_id"
        )

        if (
            not isinstance(
                robot_id,
                str,
            )
            or
            not isinstance(
                destination,
                str,
            )
        ):

            self.get_logger().warning(
                "Incomplete RMF activity "
                "completion payload: "
                f"{msg.data}"
            )

            return

        if self.runtime_manager is None:

            self.get_logger().warning(
                "Ignoring RMF activity "
                "completion before "
                "RuntimeStateManager is ready: "
                f"{msg.data}"
            )

            return

        runtime = (
            self.runtime_manager
            .get_runtimes()
            .get(
                robot_id
            )
        )

        if runtime is None:

            self.get_logger().warning(
                "RMF activity completion "
                "received for unknown robot: "
                f"{robot_id}"
            )

            return

        running_task = (
            runtime.running_task
        )

        if running_task is None:
            return

        expected_destination = (
            running_task.destination
        )

        # 中間 waypoint / source phase
        # 不能視為整筆 Hospital Task 完成。
        if (
            destination
            !=
            expected_destination
        ):
            return

        # 同一個 final command 若重複收到 completion，
        # 不可以重新開始 service timer。
        if (
            robot_id
            in
            self.service_deadlines_monotonic
        ):
            return

        # --------------------------------------------------
        # RMF navigation 已完成。
        #
        # 但 Hospital Task 還需要固定 Service Time：
        #
        #   delivery / handoff / confirmation
        #
        # 因此此時仍保持 running_task，
        # 等 Service Time 結束才真正 complete。
        # --------------------------------------------------

        service_deadline = (
            time.monotonic()
            +
            SERVICE_TIME_SECONDS
        )

        self.service_deadlines_monotonic[
            robot_id
        ] = service_deadline

        self.runtime_manager            .update_running_remaining_time(
                robot_id=robot_id,
                remaining_time=(
                    SERVICE_TIME_SECONDS
                ),
            )

        self.get_logger().info(
            "Task service started: "
            f"task={running_task.task_id}, "
            f"robot={robot_id}, "
            f"destination={destination}, "
            f"cmd_id={cmd_id}, "
            f"service_time="
            f"{SERVICE_TIME_SECONDS:.2f}s"
        )


    # ======================================================
    # Dynamic Reassignment Pass
    # ======================================================

    def run_reassignment_pass(
        self,
        *,
        root_event_id: str,
        current_time: float,
    ) -> None:
        """
        對 root event 當下所有 Waiting Tasks
        拍一次 snapshot，依 Priority + Aging 排序後，
        逐筆交給 Frozen Reassignment PPO。

        與 Experiment I 的 Dynamic RL 語意一致：

            Root Event
            -> snapshot waiting tasks
            -> reassignment decisions
            -> start idle robots

        此函式本身不啟動 Robot。
        """

        if self.runtime_manager is None:
            return

        current_time = float(
            current_time
        )

        runtimes = (
            self.runtime_manager
            .get_runtimes()
        )

        # --------------------------------------------------
        # Snapshot
        #
        # 必須先固定這次 root event 要處理的 task 集合。
        # 後續 migration 不可以讓新 queue 內容
        # 額外插入同一次 pass。
        # --------------------------------------------------

        waiting_snapshot = []

        for runtime in runtimes.values():

            waiting_snapshot.extend(
                list(
                    runtime.waiting_tasks
                )
            )

        if not waiting_snapshot:

            self.get_logger().info(
                "Reassignment pass completed: "
                f"root_event={root_event_id}, "
                "decisions=0, changed=0"
            )

            return

        waiting_snapshot = (
            sort_tasks(
                tasks=waiting_snapshot,
                current_time=(
                    current_time
                ),
            )
        )

        decision_count = 0
        changed_count = 0

        # --------------------------------------------------
        # Dedicated Reassignment PPO
        # --------------------------------------------------

        for task in waiting_snapshot:

            # Task 可能在前一個 decision 後
            # 已不再符合 waiting reassignment 條件。
            if task.status != "assigned":
                continue

            previous_robot = (
                task.assigned_robot
            )

            if previous_robot is None:

                raise RuntimeError(
                    "Waiting task has no "
                    "assigned robot: "
                    f"{task.task_id}"
                )

            previous_runtime = (
                self.runtime_manager
                .get_runtime(
                    previous_robot
                )
            )

            # Running Task 不允許 reassignment。
            #
            # Snapshot 中的物件若在輪到它之前
            # 已經不在原 Robot waiting queue，
            # 就跳過，與 Dynamic Env 相同。
            if task not in (
                previous_runtime
                .waiting_tasks
            ):
                continue

            decision = (
                self.reassignment_scheduler
                .decide(
                    task=task,
                    current_robot_id=(
                        previous_robot
                    ),
                    runtimes=(
                        self.runtime_manager
                        .get_runtimes()
                    ),
                    places=self.places,
                    current_time=(
                        current_time
                    ),
                )
            )

            decision_count += 1

            if decision.changed:

                self.runtime_manager                    .move_waiting_task(
                        task_id=(
                            task.task_id
                        ),
                        from_robot_id=(
                            decision
                            .previous_robot
                        ),
                        to_robot_id=(
                            decision
                            .selected_robot
                        ),
                        current_time=(
                            current_time
                        ),
                    )

                # 只有 migration 成功後，
                # 才更新 Immediate Reversal Guard。
                self.reassignment_scheduler                    .record_reassignment(
                        task_id=(
                            task.task_id
                        ),
                        departed_robot_id=(
                            decision
                            .previous_robot
                        ),
                    )

                changed_count += 1

            self.get_logger().info(
                "Reassignment decision: "
                f"root_event={root_event_id}, "
                f"task={task.task_id}, "
                f"previous="
                f"{decision.previous_robot}, "
                f"selected="
                f"{decision.selected_robot}, "
                f"action="
                f"{decision.action_index}, "
                f"feasible="
                f"{list(decision.feasible_robot_ids)}, "
                f"changed="
                f"{decision.changed}, "
                f"decision_ms="
                f"{decision.decision_time_ms:.3f}"
            )

        self.get_logger().info(
            "Reassignment pass completed: "
            f"root_event={root_event_id}, "
            f"decisions={decision_count}, "
            f"changed={changed_count}"
        )


    # ======================================================
    # Incoming Backend Task
    # ======================================================

    def task_request_cb(
        self,
        msg: String,
    ):

        if self.runtime_manager is None:

            self.get_logger().error(
                "Task rejected because "
                "RuntimeStateManager is not ready"
            )

            return

        self.get_logger().info(
            "Received hospital task: "
            f"{msg.data}"
        )

        try:

            raw_task = json.loads(
                msg.data
            )

            # ----------------------------------------------
            # Backend JSON
            # -> Scheduler v2 Task
            # ----------------------------------------------

            task = (
                build_scheduler_task(
                    task_id=(
                        raw_task[
                            "task_id"
                        ]
                    ),
                    task_type=(
                        raw_task[
                            "task_type"
                        ]
                    ),
                    source=(
                        raw_task[
                            "source"
                        ]
                    ),
                    destination=(
                        raw_task[
                            "destination"
                        ]
                    ),
                    priority=(
                        raw_task.get(
                            "priority",
                            1,
                        )
                    ),
                    required_capabilities=(
                        raw_task.get(
                            "required_capabilities",
                            [],
                        )
                    ),
                    places=self.places,
                    created_at=(
                        raw_task.get(
                            "created_at"
                        )
                    ),
                )
            )

            current_time = (
                time.time()
            )

            runtimes = (
                self.runtime_manager
                .get_runtimes()
            )

            # ==============================================
            # Frozen Long-Horizon Maskable PPO
            #
            # Capability Matching is enforced by the
            # action mask. The PPO only chooses among
            # feasible Robots.
            # ==============================================

            decision = (
                self.initial_assignment_scheduler
                .assign_task(
                    task=task,
                    runtimes=runtimes,
                    places=self.places,
                    current_time=(
                        current_time
                    ),
                )
            )

            if decision.selected_robot is None:

                self.get_logger().error(
                    "No feasible robot for task: "
                    f"{task.task_id}"
                )

                return

            robot_id = (
                decision.selected_robot
            )

            # ----------------------------------------------
            # Assignment
            # -> Robot Waiting Queue
            # ----------------------------------------------

            self.runtime_manager\
                .enqueue_task(
                    task=task,
                    robot_id=robot_id,
                    current_time=(
                        current_time
                    ),
                )

            runtime = (
                self.runtime_manager
                .get_runtime(
                    robot_id
                )
            )

            self.get_logger().info(
                "Scheduler assignment: "
                f"task={task.task_id}, "
                f"robot={robot_id}, "
                "selector=frozen_long_horizon_ppo, "
                f"action={decision.action_index}, "
                f"feasible={list(decision.feasible_robot_ids)}, "
                f"decision_ms={decision.decision_time_ms:.3f}, "
                f"robot_status="
                f"{runtime.robot.status}, "
                "waiting="
                f"{[
                    queued.task_id
                    for queued
                    in runtime.waiting_tasks
                ]}"
            )

            # ==============================================
            # Arrival Root Event
            #
            # Experiment I / Dynamic RL：
            #
            # Initial Assignment
            # -> snapshot all waiting tasks
            # -> Reassignment PPO
            # -> start all idle robots
            # ==============================================

            root_event_id = (
                "arrival:"
                f"{task.task_id}"
            )

            self.run_reassignment_pass(
                root_event_id=(
                    root_event_id
                ),
                current_time=(
                    current_time
                ),
            )

            self.try_start_all_idle_robots()

        except Exception as exc:

            self.get_logger().error(
                "Failed to process "
                "hospital task: "
                f"{exc}"
            )


    # ======================================================
    # Start Waiting Tasks
    # ======================================================

    def try_start_all_idle_robots(
        self,
    ):

        if self.runtime_manager is None:
            return

        for robot_id in sorted(
            self.runtime_manager
            .get_runtimes()
        ):

            self.try_start_robot(
                robot_id
            )


    def try_start_robot(
        self,
        robot_id: str,
    ):

        if self.runtime_manager is None:
            return

        runtime = (
            self.runtime_manager
            .get_runtime(
                robot_id
            )
        )

        # 已經有 Running Task。
        if runtime.running_task is not None:
            return

        # RMF 還不是 Idle。
        if runtime.robot.status != "idle":
            return

        if not runtime.robot.available:
            return

        if not runtime.waiting_tasks:
            return

        current_time = (
            time.time()
        )

        # ----------------------------------------------
        # Aging 會隨時間改變，
        # 因此真正開始 Task 前
        # 再重新排序一次。
        # ----------------------------------------------

        runtime.waiting_tasks = (
            sort_tasks(
                tasks=(
                    runtime.waiting_tasks
                ),
                current_time=(
                    current_time
                ),
            )
        )

        task = (
            runtime.waiting_tasks[0]
        )

        # ----------------------------------------------
        # Estimate remaining time
        # ----------------------------------------------

        start_place = Place(
            place_id=(
                f"{robot_id}:current"
            ),
            x=runtime.robot.x,
            y=runtime.robot.y,
            map_name=(
                runtime.robot.map_name
            ),
        )

        estimated_duration = (
            calculate_task_duration(
                task=task,
                start_place=(
                    start_place
                ),
                places=self.places,
                robot_speed_mps=(
                    runtime.robot_speed_mps
                ),
                service_time_seconds=(
                    SERVICE_TIME_SECONDS
                ),
            )
        )

        # ----------------------------------------------
        # 先送 RMF request。
        #
        # 成功 publish 後才將 Task
        # 從 Waiting -> Running。
        # ----------------------------------------------

        request_id = (
            self.send_source_destination_task(
                robot_name=robot_id,
                source=task.source,
                destination=(
                    task.destination
                ),
                backend_task_id=(
                    task.task_id
                ),
            )
        )

        self.runtime_manager.start_task(
            robot_id=robot_id,
            task_id=task.task_id,
            remaining_time=(
                estimated_duration
            ),
        )

        self.rmf_request_ids[
            robot_id
        ] = request_id

        self.running_started_monotonic[
            robot_id
        ] = time.monotonic()

        self.running_initial_remaining[
            robot_id
        ] = estimated_duration

        self.get_logger().info(
            "Task started: "
            f"task={task.task_id}, "
            f"robot={robot_id}, "
            f"source={task.source}, "
            "destination="
            f"{task.destination}, "
            "estimated_duration="
            f"{estimated_duration:.2f}s"
        )


    # ======================================================
    # Remaining Time
    # ======================================================

    def runtime_timer_cb(
        self,
    ):

        if self.runtime_manager is None:
            return

        now_monotonic = (
            time.monotonic()
        )

        # ==================================================
        # Completion Root Event
        #
        # 同一個 timer tick 內所有完成的 Hospital Tasks
        # 先全部 complete，再統一做一次 Reassignment。
        #
        # 與 Experiment I：
        #
        # completions
        # -> snapshot waiting tasks
        # -> Reassignment PPO
        # -> start idle robots
        #
        # 保持相同順序。
        # ==================================================

        completed_task_ids = []

        for (
            robot_id,
            runtime,
        ) in (
            self.runtime_manager
            .get_runtimes()
            .items()
        ):

            if runtime.running_task is None:
                continue

            # ==============================================
            # Service Phase
            # ==============================================

            service_deadline = (
                self.service_deadlines_monotonic
                .get(
                    robot_id
                )
            )

            if service_deadline is not None:

                remaining = max(
                    0.0,
                    service_deadline
                    -
                    now_monotonic,
                )

                self.runtime_manager\
                    .update_running_remaining_time(
                        robot_id=robot_id,
                        remaining_time=(
                            remaining
                        ),
                    )

                if remaining > 0.0:
                    continue

                completed = (
                    self.runtime_manager
                    .complete_running_task(
                        robot_id=robot_id
                    )
                )

                completed_task_ids.append(
                    completed.task_id
                )

                self.service_deadlines_monotonic.pop(
                    robot_id,
                    None,
                )

                self.rmf_request_ids.pop(
                    robot_id,
                    None,
                )

                self.running_started_monotonic.pop(
                    robot_id,
                    None,
                )

                self.running_initial_remaining.pop(
                    robot_id,
                    None,
                )

                self.get_logger().info(
                    "Task completed after service: "
                    f"task={completed.task_id}, "
                    f"robot={robot_id}, "
                    f"service_time="
                    f"{SERVICE_TIME_SECONDS:.2f}s"
                )

                # 注意：
                # 這裡不能立刻 start 下一個 task。
                #
                # 必須先讓同一 timer tick
                # 的所有 completion 完成，
                # 再統一跑 Reassignment pass。
                continue

            # ==============================================
            # Navigation Phase
            # ==============================================

            started = (
                self.running_started_monotonic
                .get(
                    robot_id
                )
            )

            initial = (
                self.running_initial_remaining
                .get(
                    robot_id
                )
            )

            if (
                started is None
                or
                initial is None
            ):
                continue

            elapsed = (
                now_monotonic
                -
                started
            )

            remaining = max(
                0.0,
                initial
                -
                elapsed,
            )

            self.runtime_manager\
                .update_running_remaining_time(
                    robot_id=robot_id,
                    remaining_time=(
                        remaining
                    ),
                )

        # ==================================================
        # One Dynamic Pass Per Completion Root Event
        # ==================================================

        if not completed_task_ids:
            return

        completed_task_ids = sorted(
            completed_task_ids
        )

        if len(completed_task_ids) == 1:

            root_event_id = (
                "completion:"
                f"{completed_task_ids[0]}"
            )

        else:

            root_event_id = (
                "batch:"
                +
                "|".join(
                    "completion:"
                    f"{task_id}"
                    for task_id
                    in completed_task_ids
                )
            )

        # Reassignment / Aging 使用 wall-clock epoch time，
        # 不能使用 time.monotonic()。
        current_time = (
            time.time()
        )

        self.run_reassignment_pass(
            root_event_id=(
                root_event_id
            ),
            current_time=(
                current_time
            ),
        )

        # 所有 reassignment 決策完成後，
        # 才允許 Idle Robots 開始下一個 Waiting Task。
        self.try_start_all_idle_robots()


    # ======================================================
    # RMF Source -> Destination
    # ======================================================

    def send_source_destination_task(
        self,
        *,
        robot_name: str,
        source: str,
        destination: str,
        backend_task_id: str,
    ) -> str:

        if source not in self.places:

            raise RuntimeError(
                "Unknown source waypoint: "
                f"{source}"
            )

        if destination not in self.places:

            raise RuntimeError(
                "Unknown destination waypoint: "
                f"{destination}"
            )

        now_ms = int(
            time.time()
            *
            1000
        )

        # ----------------------------------------------
        # 一個 RMF Compose Task
        #
        # Phase 1:
        # Robot -> Source
        #
        # Phase 2:
        # Source -> Destination
        # ----------------------------------------------

        phases = [

            {
                "activity": {

                    "category":
                        "go_to_place",

                    "description": {

                        "one_of": [

                            {
                                "waypoint":
                                    source
                            }

                        ]
                    },
                }
            },

            {
                "activity": {

                    "category":
                        "go_to_place",

                    "description": {

                        "one_of": [

                            {
                                "waypoint":
                                    destination
                            }

                        ]
                    },
                }
            },

        ]

        task_json = {

            "type":
                "robot_task_request",

            "robot":
                robot_name,

            "fleet":
                FLEET_NAME,

            "request": {

                "category":
                    "compose",

                "description": {

                    # 保留舊 Dispatcher
                    # 已經由目前 RMF 驗證成功的格式，
                    # 只將 phases 擴充為兩段。
                    "category":
                        "go_to_place",

                    "phases":
                        phases,
                },

                "unix_millis_request_time":
                    now_ms,

                "unix_millis_earliest_start_time":
                    now_ms,

                "requester":
                    "hospital_scheduler_dispatcher_v2",

                "fleet_name":
                    FLEET_NAME,
            },
        }

        request_id = (
            "hospital_v2_"
            f"{backend_task_id}_"
            f"{uuid.uuid4()}"
        )

        msg = ApiRequest()

        msg.request_id = (
            request_id
        )

        msg.json_msg = (
            json.dumps(
                task_json
            )
        )

        self.get_logger().info(
            "Sending RMF source->destination task: "
            f"backend_task_id="
            f"{backend_task_id}, "
            f"robot={robot_name}, "
            f"source={source}, "
            f"destination={destination}, "
            f"request_id={request_id}"
        )

        self.task_pub.publish(
            msg
        )

        return request_id


# ==========================================================
# Main
# ==========================================================

def main():

    rclpy.init()

    node = (
        HospitalSchedulerDispatcherV2()
    )

    try:

        rclpy.spin(
            node
        )

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == "__main__":

    main()
