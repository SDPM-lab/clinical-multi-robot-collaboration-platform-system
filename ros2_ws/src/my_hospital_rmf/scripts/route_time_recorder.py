#!/usr/bin/env python3

import csv
import math
import os
import sys
import yaml

import rclpy
from rclpy.node import Node
from rmf_fleet_msgs.msg import FleetState


ROBOT_NAME = "hospital_robot_1"
FLEET_NAME = "hospital_fleet"
LEVEL_NAME = "L1"

ARRIVAL_TOLERANCE = 0.15  # meters

NAV_GRAPH = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system/"
    "ros2_ws/src/my_hospital_rmf/nav_graphs/0.yaml"
)

OUTPUT_CSV = os.path.expanduser(
    "~/clinical-multi-robot-collaboration-platform-system/"
    "ros2_ws/route_travel_times.csv"
)


def load_waypoints():
    with open(NAV_GRAPH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    waypoints = {}

    for vertex in data["levels"][LEVEL_NAME]["vertices"]:
        x, y, params = vertex
        name = params.get("name", "")

        if name:
            waypoints[name] = (
                float(x),
                float(y),
            )

    return waypoints


def stamp_to_seconds(stamp):
    return (
        float(stamp.sec)
        + float(stamp.nanosec) / 1_000_000_000.0
    )


class RouteTimeRecorder(Node):

    def __init__(self, source_name, destination_name):
        super().__init__("route_time_recorder")

        self.source_name = source_name
        self.destination_name = destination_name

        self.waypoints = load_waypoints()

        if source_name not in self.waypoints:
            raise RuntimeError(
                f"Unknown source waypoint: {source_name}"
            )

        if destination_name not in self.waypoints:
            raise RuntimeError(
                f"Unknown destination waypoint: {destination_name}"
            )

        self.source_xy = self.waypoints[source_name]
        self.destination_xy = self.waypoints[destination_name]

        self.started = False
        self.finished = False

        self.start_time = None
        self.end_time = None

        # 實際行駛距離
        self.actual_distance = 0.0
        self.last_position = None

        self.subscription = self.create_subscription(
            FleetState,
            "/fleet_states",
            self.fleet_state_callback,
            100
        )

        straight_distance = math.dist(
            self.source_xy,
            self.destination_xy
        )

        print("=" * 80)
        print("RMF / Gazebo Route Travel-Time Recorder")
        print("=" * 80)
        print(f"Robot       : {ROBOT_NAME}")
        print(
            f"Source      : {source_name} "
            f"{self.source_xy}"
        )
        print(
            f"Destination : {destination_name} "
            f"{self.destination_xy}"
        )
        print(
            f"Straight distance : "
            f"{straight_distance:.3f} m"
        )
        print(
            f"Arrival tolerance : "
            f"{ARRIVAL_TOLERANCE:.2f} m"
        )
        print()
        print(
            f"Waiting for robot to reach "
            f"{source_name}..."
        )
        print("=" * 80)

    def distance_to(self, x, y, waypoint_xy):
        return math.hypot(
            x - waypoint_xy[0],
            y - waypoint_xy[1]
        )

    def fleet_state_callback(self, msg):

        if msg.name != FLEET_NAME:
            return

        for robot in msg.robots:

            if robot.name != ROBOT_NAME:
                continue

            if robot.location.level_name != LEVEL_NAME:
                return

            x = float(robot.location.x)
            y = float(robot.location.y)

            current_time = stamp_to_seconds(
                robot.location.t
            )

            # 開始計時後，累積 robot 實際走過的距離
            if self.started and not self.finished:

                if self.last_position is not None:
                    dx = x - self.last_position[0]
                    dy = y - self.last_position[1]

                    step_distance = math.hypot(dx, dy)

                    # 避免異常跳點
                    if step_distance < 2.0:
                        self.actual_distance += step_distance

                self.last_position = (x, y)

            d_source = self.distance_to(
                x,
                y,
                self.source_xy
            )

            d_destination = self.distance_to(
                x,
                y,
                self.destination_xy
            )

            # -----------------------------
            # Wait until robot reaches source
            # -----------------------------
            if not self.started:

                if d_source <= ARRIVAL_TOLERANCE:

                    self.started = True
                    self.start_time = current_time

                    self.actual_distance = 0.0
                    self.last_position = (x, y)

                    print()
                    print("=" * 80)
                    print(
                        f"[START] Robot reached "
                        f"{self.source_name}"
                    )
                    print(
                        f"Position : "
                        f"x={x:.3f}, y={y:.3f}"
                    )
                    print(
                        f"Simulation time : "
                        f"{self.start_time:.3f} s"
                    )
                    print()
                    print(
                        f"Now send robot to "
                        f"{self.destination_name}"
                    )
                    print("=" * 80)

                return

            # -----------------------------
            # Wait until destination reached
            # -----------------------------
            if (
                self.started
                and not self.finished
                and d_destination <= ARRIVAL_TOLERANCE
            ):

                self.finished = True
                self.end_time = current_time

                travel_time = (
                    self.end_time
                    - self.start_time
                )

                average_speed = (
                    self.actual_distance / travel_time
                    if travel_time > 0.0
                    else 0.0
                )

                print()
                print("=" * 80)
                print("[FINISHED]")
                print(
                    f"{self.source_name}"
                    f" -> "
                    f"{self.destination_name}"
                )
                print(
                    f"Destination position : "
                    f"x={x:.3f}, y={y:.3f}"
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
                    f"{average_speed:.3f} m/s"
                )
                print("=" * 80)

                self.save_result(
                    travel_time,
                    average_speed
                )

                rclpy.shutdown()

    def save_result(self, travel_time, average_speed):

        new_file = not os.path.exists(
            OUTPUT_CSV
        )

        with open(
            OUTPUT_CSV,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            if new_file:
                writer.writerow([
                    "robot",
                    "task_type",
                    "source",
                    "destination",
                    "source_x",
                    "source_y",
                    "destination_x",
                    "destination_y",
                    "start_sim_time_s",
                    "end_sim_time_s",
                    "travel_time_s",
                    "actual_distance_m",
                    "average_speed_mps",
                ])

            writer.writerow([
                ROBOT_NAME,
                self.source_name,
                self.destination_name,
                self.source_xy[0],
                self.source_xy[1],
                self.destination_xy[0],
                self.destination_xy[1],
                round(self.start_time, 3),
                round(self.end_time, 3),
                round(travel_time, 3),
                round(self.actual_distance, 3),
                round(average_speed, 3),
            ])

        print()
        print(
            f"Saved result to:"
            f"\n{OUTPUT_CSV}"
        )


def main():

    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python3 route_time_recorder.py "
            "<source> <destination>"
        )
        sys.exit(1)

    source = sys.argv[1]
    destination = sys.argv[2]

    rclpy.init()

    node = RouteTimeRecorder(
        source,
        destination
    )

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()