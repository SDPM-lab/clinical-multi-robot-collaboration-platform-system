#!/usr/bin/env python3
"""Record synchronized Gazebo, TF, odometry, sensor, and Nav2 state to CSV."""

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

import rclpy
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener


STATUS_NAMES = {
    0: "unknown",
    1: "accepted",
    2: "executing",
    3: "canceling",
    4: "succeeded",
    5: "canceled",
    6: "aborted",
}


def stamp_seconds(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def yaw_from_quaternion(q):
    return yaw_from_components(q.x, q.y, q.z, q.w)


def yaw_from_components(x, y, z, w):
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )


def make_fields():
    fields = [
        "wall_time",
        "sim_time",
        "gazebo_model",
        "gazebo_stamp",
        "gazebo_receive_age_wall",
        "gazebo_x",
        "gazebo_y",
        "gazebo_yaw",
    ]
    for label in ("map_odom", "odom_base", "map_base"):
        fields.extend(
            [
                f"{label}_x",
                f"{label}_y",
                f"{label}_yaw",
                f"{label}_tf_stamp",
                f"{label}_stamp_minus_clock",
            ]
        )
    fields.extend(
        [
            "map_odom_at_gazebo_stamp_x",
            "map_odom_at_gazebo_stamp_y",
            "map_odom_at_gazebo_stamp_yaw",
            "odom_base_at_gazebo_stamp_x",
            "odom_base_at_gazebo_stamp_y",
            "odom_base_at_gazebo_stamp_yaw",
            "map_base_at_gazebo_stamp_x",
            "map_base_at_gazebo_stamp_y",
            "map_base_at_gazebo_stamp_yaw",
            "exact_tf_lookup_errors",
            "odom_stamp",
            "odom_age",
            "odom_rate_hz",
            "odom_frame",
            "odom_child_frame",
            "odom_pose_x",
            "odom_pose_y",
            "odom_pose_yaw",
            "odom_linear_x",
            "odom_angular_z",
            "scan_stamp",
            "scan_age",
            "scan_rate_hz",
            "scan_frame",
            "scan_ranges",
            "cmd_vel_receive_sim_time",
            "cmd_vel_linear_x",
            "cmd_vel_angular_z",
            "navigation_state",
            "navigation_goal_id",
            "distance_remaining",
            "feedback_stamp",
            "feedback_pose_x",
            "feedback_pose_y",
            "feedback_pose_yaw",
        ]
    )
    return fields


class GazeboPoseStream:
    def __init__(self, topic, callback):
        self._callback = callback
        self._stop = threading.Event()
        self._process = None
        self._thread = None
        if shutil.which("gz") is None:
            raise RuntimeError("Gazebo CLI 'gz' is not available in PATH")
        self._process = subprocess.Popen(
            ["gz", "topic", "-e", "-t", topic],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    @staticmethod
    def _parse(block):
        stamp = re.search(
            r"header\s*\{\s*stamp\s*\{\s*sec:\s*(\d+)\s*nsec:\s*(\d+)",
            block,
            re.DOTALL,
        )
        name = re.search(r'\bname:\s*"([^"]+)"', block)
        position = re.search(
            r"position\s*\{\s*x:\s*([-+0-9.eE]+)\s*"
            r"y:\s*([-+0-9.eE]+)\s*z:\s*([-+0-9.eE]+)",
            block,
            re.DOTALL,
        )
        orientation = re.search(
            r"orientation\s*\{\s*x:\s*([-+0-9.eE]+)\s*"
            r"y:\s*([-+0-9.eE]+)\s*z:\s*([-+0-9.eE]+)\s*"
            r"w:\s*([-+0-9.eE]+)",
            block,
            re.DOTALL,
        )
        if not (stamp and position and orientation):
            return None
        sec, nanosec = map(int, stamp.groups())
        x, y, z = map(float, position.groups())
        qx, qy, qz, qw = map(float, orientation.groups())
        return {
            "name": name.group(1) if name else "",
            "stamp": sec + nanosec * 1e-9,
            "x": x,
            "y": y,
            "z": z,
            "yaw": yaw_from_components(qx, qy, qz, qw),
            "arrival_wall": time.monotonic(),
        }

    def _read(self):
        block = []
        try:
            for line in self._process.stdout:
                if self._stop.is_set():
                    break
                if not line.strip():
                    parsed = self._parse("".join(block))
                    if parsed is not None:
                        self._callback(parsed)
                    block.clear()
                else:
                    block.append(line)
            parsed = self._parse("".join(block))
            if parsed is not None:
                self._callback(parsed)
        except (OSError, ValueError):
            return

    def close(self):
        self._stop.set()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


class Recorder:
    def __init__(self, args):
        self.args = args
        self.node = rclpy.create_node(
            "record_nav2_alignment",
            parameter_overrides=[
                Parameter("use_sim_time", Parameter.Type.BOOL, True)
            ],
        )
        self.lock = threading.Lock()
        self.latest = {}
        self.previous_stamp = {}
        self.rates = {}
        self.tf_buffer = Buffer(
            cache_time=Duration(seconds=30.0),
            node=self.node,
        )
        self.tf_listener = TransformListener(
            self.tf_buffer,
            self.node,
            spin_thread=False,
        )

        self.node.create_subscription(Clock, "/clock", self._clock_callback, 10)
        self.node.create_subscription(
            LaserScan,
            args.scan_topic,
            lambda msg: self._message_callback("scan", msg),
            qos_profile_sensor_data,
        )
        self.node.create_subscription(
            Odometry,
            args.odom_topic,
            lambda msg: self._message_callback("odom", msg),
            10,
        )
        self.node.create_subscription(
            Twist,
            args.cmd_vel_topic,
            lambda msg: self._message_callback("cmd_vel", msg),
            10,
        )
        self.node.create_subscription(
            NavigateToPose.Impl.FeedbackMessage,
            f"{args.action_name}/_action/feedback",
            lambda msg: self._message_callback("feedback", msg),
            10,
        )
        self.node.create_subscription(
            GoalStatusArray,
            f"{args.action_name}/_action/status",
            lambda msg: self._message_callback("status", msg),
            10,
        )

    def _clock_callback(self, msg):
        with self.lock:
            self.latest["clock"] = (
                time.monotonic(),
                stamp_seconds(msg.clock),
                msg,
            )

    def _message_callback(self, key, msg):
        now = time.monotonic()
        stamp = (
            stamp_seconds(msg.header.stamp)
            if hasattr(msg, "header")
            else None
        )
        with self.lock:
            self.latest[key] = (now, stamp, msg)
            if stamp is not None:
                previous = self.previous_stamp.get(key)
                if previous is not None and stamp > previous:
                    self.rates[key] = 1.0 / (stamp - previous)
                self.previous_stamp[key] = stamp

    def set_gazebo_pose(self, pose):
        with self.lock:
            self.latest["gazebo"] = (
                pose["arrival_wall"],
                pose["stamp"],
                pose,
            )

    def snapshot(self):
        with self.lock:
            return dict(self.latest), dict(self.rates)

    def _lookup(self, target, source, stamp=None):
        query_time = (
            Time()
            if stamp is None
            else Time(
                nanoseconds=int(stamp * 1e9),
                clock_type=self.node.get_clock().clock_type,
            )
        )
        transform = self.tf_buffer.lookup_transform(
            target,
            source,
            query_time,
            timeout=Duration(seconds=0.02),
        )
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        tf_stamp = stamp_seconds(transform.header.stamp)
        return {
            "x": translation.x,
            "y": translation.y,
            "yaw": yaw_from_quaternion(rotation),
            "stamp": tf_stamp,
        }

    def sample(self):
        latest, rates = self.snapshot()
        row = {field: "" for field in make_fields()}
        row["wall_time"] = datetime.now().astimezone().isoformat()
        clock_entry = latest.get("clock")
        sim_time = clock_entry[1] if clock_entry else ""
        row["sim_time"] = sim_time

        gazebo_entry = latest.get("gazebo")
        gazebo_pose = gazebo_entry[2] if gazebo_entry else None
        if gazebo_pose:
            row.update(
                {
                    "gazebo_model": gazebo_pose["name"],
                    "gazebo_stamp": gazebo_pose["stamp"],
                    "gazebo_receive_age_wall": max(
                        0.0, time.monotonic() - gazebo_entry[0]
                    ),
                    "gazebo_x": gazebo_pose["x"],
                    "gazebo_y": gazebo_pose["y"],
                    "gazebo_yaw": gazebo_pose["yaw"],
                }
            )

        transform_pairs = (
            ("map_odom", self.args.map_frame, self.args.odom_frame),
            ("odom_base", self.args.odom_frame, self.args.base_frame),
            ("map_base", self.args.map_frame, self.args.base_frame),
        )
        for label, target, source in transform_pairs:
            try:
                value = self._lookup(target, source)
                row[f"{label}_x"] = value["x"]
                row[f"{label}_y"] = value["y"]
                row[f"{label}_yaw"] = value["yaw"]
                row[f"{label}_tf_stamp"] = value["stamp"]
                if sim_time != "":
                    row[f"{label}_stamp_minus_clock"] = value["stamp"] - sim_time
            except Exception as exc:
                row[f"{label}_tf_stamp"] = f"ERROR: {exc}"

        exact_errors = []
        if gazebo_pose:
            for label, target, source in transform_pairs:
                try:
                    value = self._lookup(
                        target,
                        source,
                        stamp=gazebo_pose["stamp"],
                    )
                    row[f"{label}_at_gazebo_stamp_x"] = value["x"]
                    row[f"{label}_at_gazebo_stamp_y"] = value["y"]
                    row[f"{label}_at_gazebo_stamp_yaw"] = value["yaw"]
                except Exception as exc:
                    exact_errors.append(f"{label}: {exc}")
        row["exact_tf_lookup_errors"] = " | ".join(exact_errors)

        odom_entry = latest.get("odom")
        if odom_entry:
            odom = odom_entry[2]
            row.update(
                {
                    "odom_stamp": odom_entry[1],
                    "odom_age": (
                        sim_time - odom_entry[1]
                        if sim_time != "" and odom_entry[1] is not None
                        else ""
                    ),
                    "odom_rate_hz": rates.get("odom", ""),
                    "odom_frame": odom.header.frame_id,
                    "odom_child_frame": odom.child_frame_id,
                    "odom_pose_x": odom.pose.pose.position.x,
                    "odom_pose_y": odom.pose.pose.position.y,
                    "odom_pose_yaw": yaw_from_quaternion(
                        odom.pose.pose.orientation
                    ),
                    "odom_linear_x": odom.twist.twist.linear.x,
                    "odom_angular_z": odom.twist.twist.angular.z,
                }
            )

        scan_entry = latest.get("scan")
        if scan_entry:
            scan = scan_entry[2]
            row.update(
                {
                    "scan_stamp": scan_entry[1],
                    "scan_age": (
                        sim_time - scan_entry[1]
                        if sim_time != "" and scan_entry[1] is not None
                        else ""
                    ),
                    "scan_rate_hz": rates.get("scan", ""),
                    "scan_frame": scan.header.frame_id,
                    "scan_ranges": len(scan.ranges),
                }
            )

        cmd_entry = latest.get("cmd_vel")
        if cmd_entry:
            cmd = cmd_entry[2]
            row.update(
                {
                    "cmd_vel_receive_sim_time": sim_time,
                    "cmd_vel_linear_x": cmd.linear.x,
                    "cmd_vel_angular_z": cmd.angular.z,
                }
            )

        status_entry = latest.get("status")
        if status_entry and status_entry[2].status_list:
            status = status_entry[2].status_list[-1]
            row["navigation_state"] = STATUS_NAMES.get(
                status.status, str(status.status)
            )
            row["navigation_goal_id"] = bytes(status.goal_info.goal_id.uuid).hex()

        feedback_entry = latest.get("feedback")
        if feedback_entry:
            feedback = feedback_entry[2].feedback
            row.update(
                {
                    "distance_remaining": feedback.distance_remaining,
                    "feedback_stamp": stamp_seconds(
                        feedback.current_pose.header.stamp
                    ),
                    "feedback_pose_x": feedback.current_pose.pose.position.x,
                    "feedback_pose_y": feedback.current_pose.pose.position.y,
                    "feedback_pose_yaw": yaw_from_quaternion(
                        feedback.current_pose.pose.orientation
                    ),
                }
            )
        return row


def parse_args():
    parser = argparse.ArgumentParser(
        description="Record Robot1 Gazebo/Nav2 pose and timing data to CSV."
    )
    parser.add_argument("--robot", default="hospital_robot_1")
    parser.add_argument("--period", type=float, default=0.5)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--output", default="")
    parser.add_argument("--map-frame", default="map")
    parser.add_argument("--odom-frame", default="")
    parser.add_argument("--base-frame", default="")
    parser.add_argument("--scan-topic", default="")
    parser.add_argument("--odom-topic", default="")
    parser.add_argument("--cmd-vel-topic", default="")
    parser.add_argument("--action-name", default="")
    parser.add_argument("--gazebo-topic", default="")
    args = parser.parse_args()
    args.odom_frame = args.odom_frame or f"{args.robot}/odom"
    args.base_frame = args.base_frame or f"{args.robot}/base_link"
    args.scan_topic = args.scan_topic or f"/{args.robot}/scan"
    args.odom_topic = (
        args.odom_topic or f"/{args.robot}/diff_drive_controller/odom"
    )
    args.cmd_vel_topic = args.cmd_vel_topic or f"/{args.robot}/cmd_vel"
    args.action_name = (
        args.action_name or f"/{args.robot}/navigate_to_pose"
    )
    args.gazebo_topic = (
        args.gazebo_topic or f"/model/{args.robot}/pose"
    )
    if args.period <= 0.0:
        parser.error("--period must be positive")
    return args


def main():
    args = parse_args()
    output = Path(
        args.output
        or f"nav_alignment_{datetime.now().astimezone():%Y%m%d_%H%M%S}.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    rclpy.init()
    recorder = Recorder(args)
    executor = MultiThreadedExecutor()
    executor.add_node(recorder.node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    pose_stream = None
    try:
        pose_stream = GazeboPoseStream(
            args.gazebo_topic,
            recorder.set_gazebo_pose,
        )
        print(f"Writing synchronized samples to {output}", flush=True)
        print(
            f"Sampling every {args.period:.3f}s; press Ctrl-C to stop.",
            flush=True,
        )
        start = time.monotonic()
        next_sample = start
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=make_fields())
            writer.writeheader()
            while rclpy.ok():
                now = time.monotonic()
                if args.duration > 0.0 and now - start >= args.duration:
                    break
                if now >= next_sample:
                    writer.writerow(recorder.sample())
                    stream.flush()
                    next_sample += args.period
                time.sleep(min(0.02, max(0.0, next_sample - time.monotonic())))
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as exc:
        print(f"Diagnostic recorder failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if pose_stream is not None:
            pose_stream.close()
        executor.shutdown()
        recorder.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
