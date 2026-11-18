#!/usr/bin/env python3

import csv
import heapq
import math
import os
import statistics
import time
import uuid
import yaml

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import (
    ClearEntireCostmap,
    GetCostmap,
)
from nav_msgs.msg import Odometry
from rmf_door_msgs.msg import DoorRequest, DoorMode
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


# ============================================================
# Settings
# ============================================================

ROBOT_NAME = "hospital_robot_1"
LEVEL_NAME = "L1"

RUNS_PER_ROUTE = 5

ARRIVAL_TOLERANCE = 0.15

INTER_RUN_DELAY_SIM = 3.0

# 防止一個 job 無限卡住
JOB_TIMEOUT_WALL = 1800.0

# Door control:
# 門必須先完全移開，才清除 global costmap。
DOOR_OPEN_WAIT_WALL = 2.0

GLOBAL_CLEAR_SERVICE = (
    "/global_costmap/"
    "clear_entirely_global_costmap"
)


# ============================================================
# Test mode
# ============================================================

# TEST_MODE:
#   True  -> 第 1 條 route × 1 次
#
# VALIDATION_MODE:
#   True  -> 31 routes × 1 次
#
# 正式實驗:
#   TEST_MODE = False
#   VALIDATION_MODE = False
#   -> 31 routes × 5 = 155 runs

TEST_MODE = False
VALIDATION_MODE = False


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system"
)

NAV_GRAPH = os.path.join(
    PROJECT_ROOT,
    "ros2_ws/src/my_hospital_rmf/nav_graphs/0.yaml",
)

if TEST_MODE:
    DETAIL_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_results_nav2_dryrun.csv",
    )

    SUMMARY_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_summary_nav2_dryrun.csv",
    )

elif VALIDATION_MODE:
    DETAIL_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_results_nav2_validation.csv",
    )

    SUMMARY_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_summary_nav2_validation.csv",
    )

else:
    DETAIL_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_results_nav2.csv",
    )

    SUMMARY_CSV = os.path.join(
        PROJECT_ROOT,
        "ros2_ws/batch_route_summary_nav2.csv",
    )


# ============================================================
# 31 routes
# ============================================================

ROUTES = []


# ------------------------------------------------------------
# Waste Transport: 11
# ------------------------------------------------------------

for source in [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "nurse_station",
    "blood_draw",
    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",
]:
    ROUTES.append(
        (
            "waste_transport",
            source,
            "waste_return_2",
        )
    )


# ------------------------------------------------------------
# Clothes Collection: 6
# ------------------------------------------------------------

for source in [
    "ward_a_2",
    "ward_b_2",
    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",
]:
    ROUTES.append(
        (
            "clothes_collection",
            source,
            "clothes_return_2",
        )
    )


# ------------------------------------------------------------
# Specimen Delivery: 6
# ------------------------------------------------------------

for source in [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "blood_draw",
]:
    ROUTES.append(
        (
            "specimen_delivery",
            source,
            "lab",
        )
    )


# ------------------------------------------------------------
# Medication Delivery: 6
# ------------------------------------------------------------

for destination in [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "nurse_station",
]:
    ROUTES.append(
        (
            "medication_delivery",
            "pharmacy",
            destination,
        )
    )


# ------------------------------------------------------------
# Ward Service: 2
# ------------------------------------------------------------

for destination in [
    "ward_a_2",
    "ward_b_2",
]:
    ROUTES.append(
        (
            "ward_service",
            "nurse_station",
            destination,
        )
    )


# ============================================================
# Utility
# ============================================================

def load_waypoints():

    with open(
        NAV_GRAPH,
        "r",
        encoding="utf-8",
    ) as f:
        data = yaml.safe_load(f)

    result = {}

    for vertex in data["levels"][LEVEL_NAME]["vertices"]:

        x, y, params = vertex

        name = params.get(
            "name",
            "",
        )

        if name:
            result[name] = (
                float(x),
                float(y),
            )

    return result



def _extract_door_name(props):

    if not isinstance(
        props,
        dict,
    ):
        return None

    for key in (
        "door_name",
        "door",
    ):

        if key not in props:
            continue

        value = props[key]

        if isinstance(
            value,
            dict,
        ):
            value = value.get(
                "value",
                value.get(
                    "name",
                ),
            )

        if value:
            return str(value)

    return None


def load_experiment_doors():

    with open(
        NAV_GRAPH,
        "r",
        encoding="utf-8",
    ) as f:
        data = yaml.safe_load(f)

    level = data[
        "levels"
    ][LEVEL_NAME]

    vertices = level[
        "vertices"
    ]

    lanes = level[
        "lanes"
    ]

    name_to_index = {}

    xy = {}

    for index, vertex in enumerate(
        vertices
    ):

        x, y, params = vertex

        xy[index] = (
            float(x),
            float(y),
        )

        name = params.get(
            "name",
            "",
        )

        if name:
            name_to_index[
                name
            ] = index

    graph = {
        i: []
        for i in range(
            len(vertices)
        )
    }

    for lane in lanes:

        a = int(
            lane[0]
        )

        b = int(
            lane[1]
        )

        props = (
            lane[2]
            if len(lane) >= 3
            else {}
        )

        ax, ay = xy[a]
        bx, by = xy[b]

        distance = math.hypot(
            bx - ax,
            by - ay,
        )

        door = _extract_door_name(
            props
        )

        graph[a].append(
            (
                b,
                distance,
                door,
            )
        )

    def route_doors(
        source_name,
        destination_name,
    ):

        source = name_to_index[
            source_name
        ]

        destination = (
            name_to_index[
                destination_name
            ]
        )

        distances = {
            source: 0.0
        }

        previous = {}

        queue = [
            (
                0.0,
                source,
            )
        ]

        while queue:

            cost, u = heapq.heappop(
                queue
            )

            if (
                cost
                != distances.get(u)
            ):
                continue

            if u == destination:
                break

            for (
                v,
                weight,
                door,
            ) in graph[u]:

                new_cost = (
                    cost
                    + weight
                )

                if (
                    new_cost
                    >= distances.get(
                        v,
                        float("inf"),
                    )
                ):
                    continue

                distances[v] = (
                    new_cost
                )

                previous[v] = (
                    u,
                    door,
                )

                heapq.heappush(
                    queue,
                    (
                        new_cost,
                        v,
                    )
                )

        if destination not in distances:

            raise RuntimeError(
                "No nav-graph path: "
                f"{source_name} -> "
                f"{destination_name}"
            )

        doors = []

        current = destination

        while current != source:

            previous_vertex, door = (
                previous[current]
            )

            if (
                door
                and door not in doors
            ):
                doors.append(
                    door
                )

            current = (
                previous_vertex
            )

        doors.reverse()

        return doors

    all_doors = []

    for (
        _task_type,
        source,
        destination,
    ) in ROUTES:

        for door in route_doors(
            source,
            destination,
        ):

            if door not in all_doors:
                all_doors.append(
                    door
                )

    return all_doors


def percentile(values, p):

    values = sorted(values)

    if not values:
        return 0.0

    if len(values) == 1:
        return values[0]

    k = (
        (len(values) - 1)
        * p
    )

    lower = math.floor(k)
    upper = math.ceil(k)

    if lower == upper:
        return values[int(k)]

    return (
        values[lower] * (upper - k)
        + values[upper] * (k - lower)
    )


# ============================================================
# Node
# ============================================================

class BatchRouteExperimentNav2(Node):

    def __init__(self):

        super().__init__(
            "batch_route_experiment_nav2",
            parameter_overrides=[
                Parameter(
                    "use_sim_time",
                    Parameter.Type.BOOL,
                    True,
                )
            ],
        )

        self.waypoints = load_waypoints()

        self.validate_routes()

        self.tf_buffer = Buffer()

        self.tf_listener = TransformListener(
            self.tf_buffer,
            self,
        )

        self.experiment_doors = (
            load_experiment_doors()
        )

        # ----------------------------------------------------
        # Door control
        # ----------------------------------------------------

        self.door_pub = (
            self.create_publisher(
                DoorRequest,
                "/door_requests",
                10,
            )
        )

        # ----------------------------------------------------
        # Global costmap clear
        # ----------------------------------------------------

        self.clear_global_client = (
            self.create_client(
                ClearEntireCostmap,
                GLOBAL_CLEAR_SERVICE,
            )
        )

        # ----------------------------------------------------
        # NavigateToPose
        # ----------------------------------------------------

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            "/navigate_to_pose",
        )

        # ----------------------------------------------------
        # Odom
        #
        # 不假設目前 controller 實際使用哪個名稱。
        # 兩個候選都監聽，第一個真正有資料的會被選為 active。
        # ----------------------------------------------------

        self.active_odom_topic = None

        self.latest_odom_xy = None

        self.create_subscription(
            Odometry,
            f"/{ROBOT_NAME}/diff_drive_controller/odom",
            lambda msg: self.odom_callback(
                msg,
                f"/{ROBOT_NAME}/diff_drive_controller/odom",
            ),
            50,
        )

        self.create_subscription(
            Odometry,
            f"/{ROBOT_NAME}/odom",
            lambda msg: self.odom_callback(
                msg,
                f"/{ROBOT_NAME}/odom",
            ),
            50,
        )

        # ----------------------------------------------------
        # Runtime
        # ----------------------------------------------------

        self.jobs = self.build_jobs()

        self.current_job = None

        self.phase = "idle"

        self.current_goal_handle = None

        self.start_time = None
        self.end_time = None

        self.actual_distance = 0.0
        self.last_odom_position = None

        self.measure_distance = False

        self.job_dispatch_wall = None

        self.next_job_after = None

        self.finished = False

        self.wait_message_printed = False

        self.timer = self.create_timer(
            0.2,
            self.control_loop,
        )

        print()
        print("=" * 90)
        print("Nav2 / Gazebo Automatic Route Experiment")
        print("=" * 90)

        print(
            f"Robot            : "
            f"{ROBOT_NAME}"
        )

        print(
            f"Mode             : "
            f"{'DRY RUN' if TEST_MODE else ('31 ROUTE VALIDATION' if VALIDATION_MODE else 'FULL 155 RUNS')}"
        )

        print(
            f"Defined routes   : "
            f"{len(ROUTES)}"
        )

        print(
            f"Runs / route     : "
            f"{1 if (TEST_MODE or VALIDATION_MODE) else RUNS_PER_ROUTE}"
        )

        print(
            f"Jobs this launch : "
            f"{len(self.jobs)}"
        )

        print(
            f"Experiment doors : "
            f"{len(self.experiment_doors)}"
        )

        print(
            "Doors            : "
            + ", ".join(
                self.experiment_doors
            )
        )

        print(
            f"Detail CSV       : "
            f"{DETAIL_CSV}"
        )

        print(
            f"Summary CSV      : "
            f"{SUMMARY_CSV}"
        )

        print("=" * 90)
        print()


    # ========================================================
    # Time
    # ========================================================

    def sim_time(self):

        return (
            self.get_clock()
            .now()
            .nanoseconds
            / 1_000_000_000.0
        )


    # ========================================================
    # Validate routes
    # ========================================================

    def validate_routes(self):

        if len(ROUTES) != 31:
            raise RuntimeError(
                f"Expected 31 routes, got {len(ROUTES)}"
            )

        missing = set()

        for _, source, destination in ROUTES:

            if source not in self.waypoints:
                missing.add(source)

            if destination not in self.waypoints:
                missing.add(destination)

        if missing:

            print(
                "ERROR: Missing waypoint(s):"
            )

            for name in sorted(missing):
                print(
                    f"  - {name}"
                )

            raise RuntimeError(
                "Route waypoint validation failed"
            )


    # ========================================================
    # Resume
    # ========================================================

    def completed_runs(self):

        completed = set()

        if not os.path.exists(
            DETAIL_CSV
        ):
            return completed

        with open(
            DETAIL_CSV,
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row.get(
                    "status"
                ) != "success":
                    continue

                key = (
                    row["task_type"],
                    row["source"],
                    row["destination"],
                    int(row["run_id"]),
                )

                completed.add(key)

        return completed


    def build_jobs(self):

        completed = self.completed_runs()

        jobs = []

        route_source = (
            ROUTES[:1]
            if TEST_MODE
            else ROUTES
        )

        if TEST_MODE:
            runs = range(1, 2)

        elif VALIDATION_MODE:
            runs = range(1, 2)

        else:
            runs = range(
                1,
                RUNS_PER_ROUTE + 1,
            )

        for route_id, (
            task_type,
            source,
            destination,
        ) in enumerate(
            route_source,
            start=1,
        ):

            for run_id in runs:

                key = (
                    task_type,
                    source,
                    destination,
                    run_id,
                )

                if key in completed:
                    continue

                jobs.append({
                    "route_id": route_id,
                    "task_type": task_type,
                    "source": source,
                    "destination": destination,
                    "run_id": run_id,
                })

        return jobs


    # ========================================================
    # Odom
    # ========================================================

    def odom_callback(
        self,
        msg,
        topic_name,
    ):

        if self.active_odom_topic is None:

            self.active_odom_topic = (
                topic_name
            )

            print(
                f"[ODOM] Using: "
                f"{self.active_odom_topic}"
            )

        if (
            topic_name
            != self.active_odom_topic
        ):
            return

        x = float(
            msg.pose.pose.position.x
        )

        y = float(
            msg.pose.pose.position.y
        )

        self.latest_odom_xy = (
            x,
            y,
        )

        if not self.measure_distance:
            return

        if self.last_odom_position is None:

            self.last_odom_position = (
                x,
                y,
            )

            return

        step = math.hypot(
            x - self.last_odom_position[0],
            y - self.last_odom_position[1],
        )

        # 避免異常跳點
        if (
            step >= 0.0001
            and step < 2.0
        ):
            self.actual_distance += (
                step
            )

        self.last_odom_position = (
            x,
            y,
        )


    # ========================================================
    # Control loop
    # ========================================================

    def control_loop(self):

        if self.finished:
            return

        # ----------------------------------------------------
        # Wait for simulation clock
        # ----------------------------------------------------

        if self.sim_time() <= 0.0:

            if not self.wait_message_printed:

                print(
                    "Waiting for /clock..."
                )

                self.wait_message_printed = (
                    True
                )

            return

        # ----------------------------------------------------
        # Wait for odom
        # ----------------------------------------------------

        if self.latest_odom_xy is None:

            if not self.wait_message_printed:

                print(
                    "Waiting for odometry..."
                )

                self.wait_message_printed = (
                    True
                )

            return

        # ----------------------------------------------------
        # Wait for Nav2 action
        # ----------------------------------------------------

        if not self.nav_client.server_is_ready():

            if not self.wait_message_printed:

                print(
                    "Waiting for "
                    "/navigate_to_pose..."
                )

                self.wait_message_printed = (
                    True
                )

            return

        self.wait_message_printed = False

        # ----------------------------------------------------
        # Current job timeout
        # ----------------------------------------------------

        if self.current_job is not None:

            self.check_timeout()

            return

        # ----------------------------------------------------
        # Inter-run delay
        # ----------------------------------------------------

        if (
            self.next_job_after
            is not None
            and self.sim_time()
            < self.next_job_after
        ):
            return

        # ----------------------------------------------------
        # All done
        # ----------------------------------------------------

        if not self.jobs:

            self.finish_all()

            return

        # ----------------------------------------------------
        # Start next
        # ----------------------------------------------------

        self.start_next_job()


    # ========================================================
    # Start one job
    # ========================================================

    def start_next_job(self):

        self.current_job = (
            self.jobs.pop(0)
        )

        job = self.current_job

        job["request_id"] = (
            f"nav2_"
            f"r{job['route_id']:02d}_"
            f"run{job['run_id']:02d}_"
            f"{uuid.uuid4().hex[:8]}"
        )

        self.phase = "preparing_source"

        self.start_time = None
        self.end_time = None

        self.actual_distance = 0.0
        self.last_odom_position = None
        self.measure_distance = False

        self.job_dispatch_wall = (
            time.monotonic()
        )

        source_xy = (
            self.waypoints[
                job["source"]
            ]
        )

        destination_xy = (
            self.waypoints[
                job["destination"]
            ]
        )

        straight_distance = (
            math.dist(
                source_xy,
                destination_xy,
            )
        )

        print()
        print("=" * 90)

        print(
            f"Route "
            f"{job['route_id']:02d}/"
            f"{len(ROUTES):02d}"
            f" | Run "
            f"{job['run_id']}/"
            f"{1 if (TEST_MODE or VALIDATION_MODE) else RUNS_PER_ROUTE}"
        )

        print(
            f"Task type   : "
            f"{job['task_type']}"
        )

        print(
            f"Route       : "
            f"{job['source']} "
            f"-> "
            f"{job['destination']}"
        )

        print(
            f"Source XY   : "
            f"({source_xy[0]:.3f}, "
            f"{source_xy[1]:.3f})"
        )

        print(
            f"Dest XY     : "
            f"({destination_xy[0]:.3f}, "
            f"{destination_xy[1]:.3f})"
        )

        print(
            f"Straight    : "
            f"{straight_distance:.3f} m"
        )

        print(
            f"Request ID  : "
            f"{job['request_id']}"
        )

        print()
        print(
            "[PREP] Open experiment doors "
            "before source navigation"
        )

        print("=" * 90)

        self.prepare_source_navigation()


    # ========================================================
    # Door + costmap preparation
    # ========================================================

    def publish_experiment_doors_open(
        self,
    ):

        subscriber_count = (
            self.door_pub
            .get_subscription_count()
        )

        print(
            f"[DOOR] "
            f"/door_requests subscribers="
            f"{subscriber_count}"
        )

        if subscriber_count < 1:

            raise RuntimeError(
                "No subscriber on "
                "/door_requests"
            )

        for door_name in (
            self.experiment_doors
        ):

            msg = DoorRequest()

            msg.request_time = (
                self.get_clock()
                .now()
                .to_msg()
            )

            msg.requester_id = (
                "route_calibration"
            )

            msg.door_name = (
                door_name
            )

            msg.requested_mode.value = (
                DoorMode.MODE_OPEN
            )

            # Repeat a few times so transient
            # startup/discovery timing does not
            # lose a door command.
            for _ in range(3):

                self.door_pub.publish(
                    msg
                )

                time.sleep(
                    0.03
                )

            print(
                f"[DOOR] OPEN -> "
                f"{door_name}"
            )


    def prepare_source_navigation(
        self,
    ):

        try:

            self.publish_experiment_doors_open()

        except Exception as exc:

            self.fail_current_job(
                "door_open_failed: "
                f"{exc}"
            )

            return

        print(
            f"[DOOR] Waiting "
            f"{DOOR_OPEN_WAIT_WALL:.1f} s "
            "for doors to move..."
        )

        time.sleep(
            DOOR_OPEN_WAIT_WALL
        )

        if not (
            self.clear_global_client
            .wait_for_service(
                timeout_sec=5.0,
            )
        ):

            self.fail_current_job(
                "global_costmap_clear_"
                "service_unavailable"
            )

            return

        self.phase = (
            "clearing_costmap"
        )

        print(
            "[COSTMAP] Clearing global "
            "costmap..."
        )

        future = (
            self.clear_global_client
            .call_async(
                ClearEntireCostmap.Request()
            )
        )

        future.add_done_callback(
            self.source_costmap_clear_callback
        )


    def source_costmap_clear_callback(
        self,
        future,
    ):

        if self.current_job is None:
            return

        try:

            future.result()

        except Exception as exc:

            self.fail_current_job(
                "global_costmap_clear_"
                f"failed: {exc}"
            )

            return

        job = self.current_job

        print(
            "[COSTMAP] Global costmap "
            "cleared ✅"
        )

        print()
        print(
            f"[PHASE 1] "
            f"Navigate to source: "
            f"{job['source']}"
        )

        print("=" * 90)

        self.phase = (
            "going_source"
        )

        self.send_navigation_goal(
            waypoint_name=job["source"],
            phase="source",
        )


    # ========================================================
    # Send NavigateToPose
    # ========================================================

    def send_navigation_goal(
        self,
        waypoint_name,
        phase,
    ):

        x, y = self.waypoints[
            waypoint_name
        ]

        goal = NavigateToPose.Goal()

        goal.pose = PoseStamped()

        goal.pose.header.frame_id = (
            "map"
        )

        goal.pose.header.stamp = (
            self.get_clock()
            .now()
            .to_msg()
        )

        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y

        # 目前 route calibration
        # 不要求特定朝向
        goal.pose.pose.orientation.w = (
            1.0
        )

        future = (
            self.nav_client
            .send_goal_async(goal)
        )

        future.add_done_callback(
            lambda f:
                self.goal_response_callback(
                    f,
                    phase,
                    waypoint_name,
                )
        )


    # ========================================================
    # Goal response
    # ========================================================

    def goal_response_callback(
        self,
        future,
        phase,
        waypoint_name,
    ):

        try:
            goal_handle = (
                future.result()
            )

        except Exception as exc:

            self.fail_current_job(
                f"{phase}_goal_exception: "
                f"{exc}"
            )

            return

        if (
            goal_handle is None
            or not goal_handle.accepted
        ):

            self.fail_current_job(
                f"{phase}_goal_rejected"
            )

            return

        self.current_goal_handle = (
            goal_handle
        )

        print(
            f"[NAV2] Goal accepted: "
            f"{waypoint_name}"
        )

        result_future = (
            goal_handle
            .get_result_async()
        )

        result_future.add_done_callback(
            lambda f:
                self.navigation_result_callback(
                    f,
                    phase,
                    waypoint_name,
                )
        )


    # ========================================================
    # Navigation result
    # ========================================================

    def navigation_result_callback(
        self,
        future,
        phase,
        waypoint_name,
    ):

        try:
            wrapped = (
                future.result()
            )

        except Exception as exc:

            self.fail_current_job(
                f"{phase}_result_exception: "
                f"{exc}"
            )

            return

        status = wrapped.status

        result = wrapped.result

        error_code = getattr(
            result,
            "error_code",
            -1,
        )

        error_msg = getattr(
            result,
            "error_msg",
            "",
        )

        print(
            f"[NAV2] Result "
            f"{waypoint_name}: "
            f"status={status}, "
            f"error_code={error_code}"
        )

        success = (
            status
            == GoalStatus.STATUS_SUCCEEDED
            and error_code == 0
        )

        if not success:

            self.fail_current_job(
                f"{phase}_navigation_failed"
                f"(status={status},"
                f"error={error_code},"
                f"msg={error_msg})"
            )

            return

        if phase == "source":

            self.source_arrived()

        elif phase == "destination":

            self.destination_arrived()


    # ========================================================
    # Source reached
    # ========================================================

    def source_arrived(self):

        job = self.current_job

        self.phase = (
            "going_destination"
        )

        self.start_time = (
            self.sim_time()
        )

        self.actual_distance = 0.0

        self.last_odom_position = (
            self.latest_odom_xy
        )

        self.measure_distance = True

        print()
        print(
            f"[START] "
            f"Reached source: "
            f"{job['source']}"
        )

        print(
            f"Simulation time: "
            f"{self.start_time:.3f} s"
        )

        print(
            f"Start odom XY  : "
            f"({self.latest_odom_xy[0]:.3f}, "
            f"{self.latest_odom_xy[1]:.3f})"
        )

        print()

        print(
            f"[PHASE 2] "
            f"Navigate to destination: "
            f"{job['destination']}"
        )

        self.send_navigation_goal(
            waypoint_name=(
                job["destination"]
            ),
            phase="destination",
        )


    # ========================================================
    # Destination reached
    # ========================================================

    def destination_arrived(self):

        job = self.current_job

        self.measure_distance = False

        self.end_time = (
            self.sim_time()
        )

        travel_time = (
            self.end_time
            - self.start_time
        )

        avg_speed = (
            self.actual_distance
            / travel_time
            if travel_time > 0.0
            else 0.0
        )

        print()
        print("=" * 90)
        print("[FINISHED]")

        print(
            f"{job['source']} "
            f"-> "
            f"{job['destination']}"
        )

        print(
            f"Start sim time : "
            f"{self.start_time:.3f} s"
        )

        print(
            f"End sim time   : "
            f"{self.end_time:.3f} s"
        )

        print(
            f"Travel time    : "
            f"{travel_time:.3f} s"
        )

        print(
            f"Actual distance: "
            f"{self.actual_distance:.3f} m"
        )

        print(
            f"Average speed  : "
            f"{avg_speed:.3f} m/s"
        )

        print("=" * 90)

        self.save_success(
            job,
            travel_time,
            avg_speed,
        )

        self.write_summary()

        self.current_job = None

        self.phase = "idle"

        self.job_dispatch_wall = None

        self.next_job_after = (
            self.sim_time()
            + INTER_RUN_DELAY_SIM
        )


    # ========================================================
    # Timeout
    # ========================================================

    def check_timeout(self):

        if self.job_dispatch_wall is None:
            return

        elapsed = (
            time.monotonic()
            - self.job_dispatch_wall
        )

        if elapsed <= JOB_TIMEOUT_WALL:
            return

        self.fail_current_job(
            "job_timeout"
        )


    # ========================================================
    # Failure diagnostic
    # ========================================================

    def print_failure_diagnostic(
        self,
    ):

        print()
        print(
            "[FAIL DIAG]"
        )

        try:

            tf = (
                self.tf_buffer
                .lookup_transform(
                    "map",
                    f"{ROBOT_NAME}/base_link",
                    Time(),
                )
            )

            x = float(
                tf.transform.translation.x
            )

            y = float(
                tf.transform.translation.y
            )

            print(
                f"Robot map XY = "
                f"({x:.3f}, {y:.3f})"
            )

        except Exception as exc:

            print(
                "Robot map XY = "
                f"UNAVAILABLE ({exc})"
            )

            return

        try:

            client = self.create_client(
                GetCostmap,
                "/global_costmap/get_costmap",
            )

            if not client.wait_for_service(
                timeout_sec=3.0,
            ):

                print(
                    "Master cost = "
                    "UNAVAILABLE "
                    "(service unavailable)"
                )

                return

            future = client.call_async(
                GetCostmap.Request()
            )

            deadline = (
                time.monotonic()
                + 5.0
            )

            while (
                rclpy.ok()
                and not future.done()
                and time.monotonic()
                < deadline
            ):

                rclpy.spin_once(
                    self,
                    timeout_sec=0.05,
                )

            if not future.done():

                print(
                    "Master cost = "
                    "UNAVAILABLE "
                    "(timeout)"
                )

                return

            response = (
                future.result()
            )

            if response is None:

                print(
                    "Master cost = "
                    "UNAVAILABLE "
                    "(empty response)"
                )

                return

            cm = response.map

            resolution = (
                cm.metadata.resolution
            )

            origin_x = (
                cm.metadata.origin.position.x
            )

            origin_y = (
                cm.metadata.origin.position.y
            )

            mx = int(
                (x - origin_x)
                / resolution
            )

            my = int(
                (y - origin_y)
                / resolution
            )

            print(
                f"Costmap grid = "
                f"({mx}, {my})"
            )

            if (
                mx < 0
                or my < 0
                or mx >= cm.metadata.size_x
                or my >= cm.metadata.size_y
            ):

                print(
                    "Master cost = "
                    "OUTSIDE MAP"
                )

                return

            index = (
                my
                * cm.metadata.size_x
                + mx
            )

            cost = int(
                cm.data[index]
            )

            if cost == 0:

                label = (
                    "FREE ✅"
                )

            elif cost < 253:

                label = (
                    "INFLATED ⚠️"
                )

            elif cost == 253:

                label = (
                    "INSCRIBED ❌"
                )

            elif cost == 254:

                label = (
                    "LETHAL ❌"
                )

            elif cost == 255:

                label = (
                    "UNKNOWN"
                )

            else:

                label = (
                    "OTHER"
                )

            print(
                f"Master cost = "
                f"{cost}"
            )

            print(
                f"Classification = "
                f"{label}"
            )

        except Exception as exc:

            print(
                "Master cost diagnostic "
                f"failed: {exc}"
            )


    # ========================================================
    # Failure
    # ========================================================

    def fail_current_job(
        self,
        reason,
    ):

        if self.current_job is None:
            return

        self.measure_distance = False

        job = self.current_job

        print()
        print("=" * 90)
        print("ERROR: ROUTE EXPERIMENT FAILED")

        print(
            f"Route : "
            f"{job['source']} "
            f"-> "
            f"{job['destination']}"
        )

        print(
            f"Phase : "
            f"{self.phase}"
        )

        print(
            f"Reason: "
            f"{reason}"
        )

        self.print_failure_diagnostic()

        print()
        print(
            "Batch stopped intentionally."
        )

        print(
            "Fix the problem and run "
            "the script again."
        )

        print(
            "Successful runs will be skipped."
        )

        print("=" * 90)

        self.save_failure(
            job,
            reason,
        )

        self.write_summary()

        self.finished = True

        if rclpy.ok():
            rclpy.shutdown()


    # ========================================================
    # Save success
    # ========================================================

    def save_success(
        self,
        job,
        travel_time,
        avg_speed,
    ):

        source_xy = (
            self.waypoints[
                job["source"]
            ]
        )

        destination_xy = (
            self.waypoints[
                job["destination"]
            ]
        )

        straight_distance = (
            math.dist(
                source_xy,
                destination_xy,
            )
        )

        new_file = (
            not os.path.exists(
                DETAIL_CSV
            )
        )

        with open(
            DETAIL_CSV,
            "a",
            encoding="utf-8",
            newline="",
        ) as f:

            writer = csv.writer(f)

            if new_file:

                writer.writerow([
                    "route_id",
                    "task_type",
                    "source",
                    "destination",
                    "run_id",
                    "request_id",
                    "straight_distance_m",
                    "start_sim_time_s",
                    "end_sim_time_s",
                    "travel_time_s",
                    "actual_distance_m",
                    "average_speed_mps",
                    "status",
                    "failure_reason",
                ])

            writer.writerow([
                job["route_id"],
                job["task_type"],
                job["source"],
                job["destination"],
                job["run_id"],
                job["request_id"],
                round(
                    straight_distance,
                    3,
                ),
                round(
                    self.start_time,
                    3,
                ),
                round(
                    self.end_time,
                    3,
                ),
                round(
                    travel_time,
                    3,
                ),
                round(
                    self.actual_distance,
                    3,
                ),
                round(
                    avg_speed,
                    3,
                ),
                "success",
                "",
            ])

        print(
            f"Saved: "
            f"{DETAIL_CSV}"
        )


    # ========================================================
    # Save failure
    # ========================================================

    def save_failure(
        self,
        job,
        reason,
    ):

        source_xy = (
            self.waypoints[
                job["source"]
            ]
        )

        destination_xy = (
            self.waypoints[
                job["destination"]
            ]
        )

        straight_distance = (
            math.dist(
                source_xy,
                destination_xy,
            )
        )

        new_file = (
            not os.path.exists(
                DETAIL_CSV
            )
        )

        with open(
            DETAIL_CSV,
            "a",
            encoding="utf-8",
            newline="",
        ) as f:

            writer = csv.writer(f)

            if new_file:

                writer.writerow([
                    "route_id",
                    "task_type",
                    "source",
                    "destination",
                    "run_id",
                    "request_id",
                    "straight_distance_m",
                    "start_sim_time_s",
                    "end_sim_time_s",
                    "travel_time_s",
                    "actual_distance_m",
                    "average_speed_mps",
                    "status",
                    "failure_reason",
                ])

            writer.writerow([
                job["route_id"],
                job["task_type"],
                job["source"],
                job["destination"],
                job["run_id"],
                job.get(
                    "request_id",
                    "",
                ),
                round(
                    straight_distance,
                    3,
                ),
                (
                    round(
                        self.start_time,
                        3,
                    )
                    if self.start_time
                    is not None
                    else ""
                ),
                "",
                "",
                round(
                    self.actual_distance,
                    3,
                ),
                "",
                "failed",
                reason,
            ])


    # ========================================================
    # Summary
    # ========================================================

    def write_summary(self):

        if not os.path.exists(
            DETAIL_CSV
        ):
            return

        groups = {}

        with open(
            DETAIL_CSV,
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row.get(
                    "status"
                ) != "success":
                    continue

                key = (
                    int(
                        row["route_id"]
                    ),
                    row["task_type"],
                    row["source"],
                    row["destination"],
                )

                if key not in groups:
                    groups[key] = []

                groups[key].append(
                    row
                )

        with open(
            SUMMARY_CSV,
            "w",
            encoding="utf-8",
            newline="",
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                "route_id",
                "task_type",
                "source",
                "destination",
                "n",
                "mean_travel_time_s",
                "sd_travel_time_s",
                "median_travel_time_s",
                "p95_travel_time_s",
                "min_travel_time_s",
                "max_travel_time_s",
                "mean_actual_distance_m",
                "mean_average_speed_mps",
            ])

            for key in sorted(groups):

                rows = groups[key]

                times = [
                    float(
                        r[
                            "travel_time_s"
                        ]
                    )
                    for r in rows
                ]

                distances = [
                    float(
                        r[
                            "actual_distance_m"
                        ]
                    )
                    for r in rows
                ]

                speeds = [
                    float(
                        r[
                            "average_speed_mps"
                        ]
                    )
                    for r in rows
                ]

                mean_time = (
                    statistics.mean(
                        times
                    )
                )

                sd_time = (
                    statistics.stdev(
                        times
                    )
                    if len(times) > 1
                    else 0.0
                )

                med_time = (
                    statistics.median(
                        times
                    )
                )

                p95_time = (
                    percentile(
                        times,
                        0.95,
                    )
                )

                writer.writerow([
                    key[0],
                    key[1],
                    key[2],
                    key[3],
                    len(times),
                    round(
                        mean_time,
                        3,
                    ),
                    round(
                        sd_time,
                        3,
                    ),
                    round(
                        med_time,
                        3,
                    ),
                    round(
                        p95_time,
                        3,
                    ),
                    round(
                        min(times),
                        3,
                    ),
                    round(
                        max(times),
                        3,
                    ),
                    round(
                        statistics.mean(
                            distances
                        ),
                        3,
                    ),
                    round(
                        statistics.mean(
                            speeds
                        ),
                        3,
                    ),
                ])


    # ========================================================
    # Finish
    # ========================================================

    def finish_all(self):

        if self.finished:
            return

        self.finished = True

        self.write_summary()

        print()
        print("=" * 90)

        if TEST_MODE:

            print(
                "NAV2 DRY RUN COMPLETED"
            )

        elif VALIDATION_MODE:

            print(
                "31-ROUTE NAV2 "
                "VALIDATION COMPLETED"
            )

        else:

            print(
                "ALL 155 NAV2 ROUTE "
                "EXPERIMENTS COMPLETED"
            )

        print("=" * 90)

        print(
            f"Detailed results:"
            f"\n{DETAIL_CSV}"
        )

        print()

        print(
            f"Summary:"
            f"\n{SUMMARY_CSV}"
        )

        print("=" * 90)

        if rclpy.ok():
            rclpy.shutdown()


# ============================================================
# Main
# ============================================================

def main():

    rclpy.init()

    node = (
        BatchRouteExperimentNav2()
    )

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        print()
        print(
            "Experiment interrupted."
        )

        print(
            "Successful runs are already "
            "saved and can be resumed."
        )

    finally:

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
