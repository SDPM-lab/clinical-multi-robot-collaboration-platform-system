#!/usr/bin/env python3

import csv
import json
import math
import os
import statistics
import time
import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
)

from rmf_fleet_msgs.msg import FleetState
from rmf_task_msgs.msg import ApiRequest


# ============================================================
# Settings
# ============================================================

ROBOT_NAME = "hospital_robot_1"
FLEET_NAME = "hospital_fleet"
LEVEL_NAME = "L1"

RUNS_PER_ROUTE = 5

# 與 hospital_g1_navigation_bridge.py 保持一致
ARRIVAL_TOLERANCE = 0.15

# 一個 run 完成後稍微等一下，再派下一個
INTER_RUN_DELAY_SIM = 3.0

# 防止某條路線永遠卡住
JOB_TIMEOUT_SIM = 1800.0

NAV_GRAPH = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system/"
    "ros2_ws/src/my_hospital_rmf/nav_graphs/0.yaml"
)

DETAIL_CSV = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system/"
    "ros2_ws/batch_route_results.csv"
)

SUMMARY_CSV = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system/"
    "ros2_ws/batch_route_summary.csv"
)


# ============================================================
# 31 routes
# ============================================================

ROUTES = []

# ----------------------------
# Waste Transport: 11
# ----------------------------

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
        ("waste_transport", source, "waste_return_2")
    )

# ----------------------------
# Clothes Collection: 6
# ----------------------------

for source in [
    "ward_a_2",
    "ward_b_2",
    "x-ray",
    "ultrasound_2",
    "ecg_2",
    "therapy_room",
]:
    ROUTES.append(
        ("clothes_collection", source, "clothes_return_2")
    )

# ----------------------------
# Specimen Delivery: 6
# ----------------------------

for source in [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "blood_draw",
]:
    ROUTES.append(
        ("specimen_delivery", source, "lab")
    )

# ----------------------------
# Medication Delivery: 6
# ----------------------------

for destination in [
    "ward_a_2",
    "ward_b_2",
    "consult_1_2",
    "consult_2_2",
    "consult_3_2",
    "nurse_station",
]:
    ROUTES.append(
        ("medication_delivery", "pharmacy", destination)
    )

# ----------------------------
# Ward Service: 2
# ----------------------------

for destination in [
    "ward_a_2",
    "ward_b_2",
]:
    ROUTES.append(
        ("ward_service", "nurse_station", destination)
    )


# ============================================================
# Utility
# ============================================================

def stamp_to_seconds(stamp):
    return (
        float(stamp.sec)
        + float(stamp.nanosec) / 1_000_000_000.0
    )


def load_waypoints():
    with open(NAV_GRAPH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    result = {}

    for vertex in data["levels"][LEVEL_NAME]["vertices"]:
        x, y, params = vertex
        name = params.get("name", "")

        if name:
            result[name] = (
                float(x),
                float(y),
            )

    return result


def percentile(values, p):
    values = sorted(values)

    if not values:
        return 0.0

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * p

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

class BatchRouteExperiment(Node):

    def __init__(self):
        super().__init__("batch_route_experiment")

        self.waypoints = load_waypoints()

        self.validate_routes()

        # ------------------------------------------
        # QoS
        # ------------------------------------------

        task_qos = QoSProfile(depth=100)
        task_qos.reliability = (
            ReliabilityPolicy.RELIABLE
        )
        task_qos.durability = (
            DurabilityPolicy.TRANSIENT_LOCAL
        )

        fleet_qos = QoSProfile(depth=100)
        fleet_qos.reliability = (
            ReliabilityPolicy.RELIABLE
        )
        fleet_qos.durability = (
            DurabilityPolicy.VOLATILE
        )

        self.task_pub = self.create_publisher(
            ApiRequest,
            "/task_api_requests",
            task_qos,
        )

        self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_callback,
            fleet_qos,
        )

        # ------------------------------------------
        # Runtime state
        # ------------------------------------------

        self.jobs = self.build_jobs()

        self.current_job = None

        self.source_reached = False

        self.start_time = None
        self.end_time = None

        self.actual_distance = 0.0
        self.last_position = None

        self.latest_sim_time = None
        self.job_dispatch_time = None

        self.next_job_after = None

        self.finished = False

        self.timer = self.create_timer(
            0.5,
            self.control_loop,
        )

        print("=" * 90)
        print("RMF / Gazebo Automatic Route Experiment")
        print("=" * 90)
        print(f"Robot            : {ROBOT_NAME}")
        print(f"Routes           : {len(ROUTES)}")
        print(f"Runs / route     : {RUNS_PER_ROUTE}")
        print(
            f"Total target runs: "
            f"{len(ROUTES) * RUNS_PER_ROUTE}"
        )
        print(
            f"Remaining runs   : "
            f"{len(self.jobs)}"
        )
        print(
            f"Arrival tolerance: "
            f"{ARRIVAL_TOLERANCE:.2f} m"
        )
        print("=" * 90)

    # --------------------------------------------------------
    # Route validation
    # --------------------------------------------------------

    def validate_routes(self):
        missing = set()

        for _, source, destination in ROUTES:
            if source not in self.waypoints:
                missing.add(source)

            if destination not in self.waypoints:
                missing.add(destination)

        if missing:
            print()
            print("ERROR: Missing waypoint(s):")

            for name in sorted(missing):
                print(f"  - {name}")

            raise RuntimeError(
                "Route waypoint validation failed"
            )

        if len(ROUTES) != 31:
            raise RuntimeError(
                f"Expected 31 routes, got {len(ROUTES)}"
            )

    # --------------------------------------------------------
    # Resume
    # --------------------------------------------------------

    def completed_runs(self):
        completed = set()

        if not os.path.exists(DETAIL_CSV):
            return completed

        with open(
            DETAIL_CSV,
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:
                if row.get("status") != "success":
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

        for route_id, (
            task_type,
            source,
            destination,
        ) in enumerate(ROUTES, start=1):

            for run_id in range(
                1,
                RUNS_PER_ROUTE + 1,
            ):
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

    # --------------------------------------------------------
    # Control loop
    # --------------------------------------------------------

    def control_loop(self):

        if self.finished:
            return

        # 等 task_api_requests subscriber 出現
        if self.task_pub.get_subscription_count() == 0:
            print(
                "\rWaiting for /task_api_requests subscriber...",
                end="",
                flush=True,
            )
            return

        if self.current_job is not None:
            self.check_timeout()
            return

        if (
            self.next_job_after is not None
            and self.latest_sim_time is not None
            and self.latest_sim_time
                < self.next_job_after
        ):
            return

        if not self.jobs:
            self.finish_all()
            return

        self.start_next_job()

    # --------------------------------------------------------
    # Dispatch one RMF task
    # --------------------------------------------------------

    def start_next_job(self):

        self.current_job = self.jobs.pop(0)

        job = self.current_job

        self.source_reached = False
        self.start_time = None
        self.end_time = None

        self.actual_distance = 0.0
        self.last_position = None

        self.job_dispatch_time = (
            self.latest_sim_time
        )

        request_id = (
            f"batch_"
            f"r{job['route_id']:02d}_"
            f"run{job['run_id']:02d}_"
            f"{int(time.time() * 1000)}"
        )

        job["request_id"] = request_id

        # 一個 task 兩個 phase：
        # 1. 去 source
        # 2. 自動去 destination
        payload = {
            "type": "robot_task_request",
            "robot": ROBOT_NAME,
            "fleet": FLEET_NAME,
            "request": {
                "category": "compose",
                "description": {
                    "category": (
                        "batch_route_experiment"
                    ),
                    "detail": (
                        f"{job['source']} -> "
                        f"{job['destination']}"
                    ),
                    "phases": [
                        {
                            "activity": {
                                "category":
                                    "go_to_place",
                                "description":
                                    job["source"],
                            }
                        },
                        {
                            "activity": {
                                "category":
                                    "go_to_place",
                                "description":
                                    job["destination"],
                            }
                        },
                    ],
                },
            },
        }

        msg = ApiRequest()

        msg.request_id = request_id
        msg.json_msg = json.dumps(
            payload,
            separators=(",", ":"),
        )

        self.task_pub.publish(msg)

        source_xy = self.waypoints[
            job["source"]
        ]

        destination_xy = self.waypoints[
            job["destination"]
        ]

        straight_distance = math.dist(
            source_xy,
            destination_xy,
        )

        print()
        print("=" * 90)
        print(
            f"Route {job['route_id']:02d}/"
            f"{len(ROUTES):02d} | "
            f"Run {job['run_id']}/"
            f"{RUNS_PER_ROUTE}"
        )
        print(
            f"Task type   : "
            f"{job['task_type']}"
        )
        print(
            f"Route       : "
            f"{job['source']} "
            f"-> {job['destination']}"
        )
        print(
            f"Straight    : "
            f"{straight_distance:.3f} m"
        )
        print(
            f"Request ID  : "
            f"{request_id}"
        )
        print(
            f"RMF first goes to "
            f"{job['source']}..."
        )
        print("=" * 90)

    # --------------------------------------------------------
    # Fleet callback
    # --------------------------------------------------------

    def fleet_callback(self, msg):

        if msg.name != FLEET_NAME:
            return

        robot = None

        for candidate in msg.robots:
            if candidate.name == ROBOT_NAME:
                robot = candidate
                break

        if robot is None:
            return

        if robot.location.level_name != LEVEL_NAME:
            return

        x = float(robot.location.x)
        y = float(robot.location.y)

        sim_time = stamp_to_seconds(
            robot.location.t
        )

        self.latest_sim_time = sim_time

        if self.current_job is None:
            return

        job = self.current_job

        source_xy = self.waypoints[
            job["source"]
        ]

        destination_xy = self.waypoints[
            job["destination"]
        ]

        d_source = math.hypot(
            x - source_xy[0],
            y - source_xy[1],
        )

        d_destination = math.hypot(
            x - destination_xy[0],
            y - destination_xy[1],
        )

        # ------------------------------------------
        # Phase 1: waiting for source
        # ------------------------------------------

        if not self.source_reached:

            if d_source <= ARRIVAL_TOLERANCE:

                self.source_reached = True
                self.start_time = sim_time

                self.actual_distance = 0.0
                self.last_position = (
                    x,
                    y,
                )

                print()
                print(
                    f"[START] "
                    f"{job['source']}"
                )
                print(
                    f"Position       : "
                    f"x={x:.3f}, y={y:.3f}"
                )
                print(
                    f"Simulation time: "
                    f"{sim_time:.3f} s"
                )
                print(
                    f"RMF now continues automatically "
                    f"to {job['destination']}"
                )

            return

        # ------------------------------------------
        # Phase 2: source -> destination
        # ------------------------------------------

        if self.last_position is not None:

            step = math.hypot(
                x - self.last_position[0],
                y - self.last_position[1],
            )

            # 避免 DDS / localization 異常跳點
            if step < 2.0:
                self.actual_distance += step

        self.last_position = (
            x,
            y,
        )

        if d_destination > ARRIVAL_TOLERANCE:
            return

        self.end_time = sim_time

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
        print("[FINISHED]")
        print(
            f"{job['source']} "
            f"-> {job['destination']}"
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

        self.save_success(
            job,
            travel_time,
            avg_speed,
        )

        # 每次完成都重新產生 summary
        self.write_summary()

        self.current_job = None

        self.next_job_after = (
            sim_time
            + INTER_RUN_DELAY_SIM
        )

    # --------------------------------------------------------
    # Timeout
    # --------------------------------------------------------

    def check_timeout(self):

        if (
            self.latest_sim_time is None
            or self.job_dispatch_time is None
        ):
            return

        elapsed = (
            self.latest_sim_time
            - self.job_dispatch_time
        )

        if elapsed <= JOB_TIMEOUT_SIM:
            return

        job = self.current_job

        print()
        print("=" * 90)
        print("ERROR: Experiment timeout")
        print(
            f"Route: "
            f"{job['source']} -> "
            f"{job['destination']}"
        )
        print(
            "Stopping batch so the problem "
            "can be inspected safely."
        )
        print(
            "Run this script again afterwards; "
            "completed runs will be skipped."
        )
        print("=" * 90)

        self.finished = True

        self.write_summary()

        rclpy.shutdown()

    # --------------------------------------------------------
    # Save detailed result
    # --------------------------------------------------------

    def save_success(
        self,
        job,
        travel_time,
        avg_speed,
    ):

        source_xy = self.waypoints[
            job["source"]
        ]

        destination_xy = self.waypoints[
            job["destination"]
        ]

        straight_distance = math.dist(
            source_xy,
            destination_xy,
        )

        new_file = not os.path.exists(
            DETAIL_CSV
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
            ])

        print(
            f"Saved: {DETAIL_CSV}"
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

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

                if row.get("status") != "success":
                    continue

                key = (
                    int(row["route_id"]),
                    row["task_type"],
                    row["source"],
                    row["destination"],
                )

                if key not in groups:
                    groups[key] = []

                groups[key].append(row)

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
                    float(r["travel_time_s"])
                    for r in rows
                ]

                distances = [
                    float(r["actual_distance_m"])
                    for r in rows
                ]

                speeds = [
                    float(r["average_speed_mps"])
                    for r in rows
                ]

                mean_time = statistics.mean(
                    times
                )

                sd_time = (
                    statistics.stdev(times)
                    if len(times) > 1
                    else 0.0
                )

                med_time = statistics.median(
                    times
                )

                p95_time = percentile(
                    times,
                    0.95,
                )

                writer.writerow([
                    key[0],
                    key[1],
                    key[2],
                    key[3],
                    len(times),
                    round(mean_time, 3),
                    round(sd_time, 3),
                    round(med_time, 3),
                    round(p95_time, 3),
                    round(min(times), 3),
                    round(max(times), 3),
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

    # --------------------------------------------------------
    # End
    # --------------------------------------------------------

    def finish_all(self):

        self.finished = True

        self.write_summary()

        print()
        print("=" * 90)
        print("ALL ROUTE EXPERIMENTS COMPLETED")
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

        rclpy.shutdown()


# ============================================================
# Main
# ============================================================

def main():

    rclpy.init()

    node = BatchRouteExperiment()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        print()
        print("Experiment interrupted.")
        print(
            "Completed runs are already saved. "
            "Run the script again to resume."
        )

    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()