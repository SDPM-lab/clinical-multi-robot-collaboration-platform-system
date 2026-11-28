from pathlib import Path
import importlib.util
import hashlib
import json
import os
import sys
import time
import traceback

import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
)

from std_msgs.msg import String
from rmf_fleet_msgs.msg import FleetState, RobotState
from rmf_task_msgs.msg import ApiRequest


ROOT = Path.cwd()

SOURCE = (
    ROOT / "ros2_ws/src/my_hospital_rmf/scripts"
    / "hospital_ppo_scheduler.py"
)

assert os.environ.get("ROS_DOMAIN_ID") == "187"
assert os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE") == "LOCALHOST"
assert os.environ.get("HOSPITAL_SCHEDULING_ONLY") == "0"
assert os.environ.get("HOSPITAL_TEST_FORCE_LOW_BATTERY") == "0"

spec = importlib.util.spec_from_file_location(
    "hospital_ppo_scheduler",
    SOURCE,
)

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

RUN_ID = str(time.time_ns())

results = []
assignments = []
requests = []
predictions = []

LOCATIONS = {
    "C01": "charging_station_2",
    "C02": "nurse_station",
    "M01": "pharmacy",
    "M02": "lab",
    "W01": "ward_a_2",
    "W02": "ward_b_2",
    "W03": "consult_1_2",
}


def record(case, passed, **details):

    result = {
        "test_id": case,
        "result": "PASS" if passed else "FAIL",
        **details,
    }

    results.append(result)

    print(
        "[TEST RESULT]",
        json.dumps(result, ensure_ascii=False),
        flush=True,
    )


rclpy.init()

scheduler = None
probe = None
executor = SingleThreadedExecutor()

try:

    scheduler = module.HospitalPpoScheduler()
    assert not scheduler.scheduling_only

    probe = Node("ppo_runtime_test_probe")

    task_pub = probe.create_publisher(
        String,
        module.TASK_TOPIC,
        10,
    )

    fleet_pub = probe.create_publisher(
        FleetState,
        module.FLEET_TOPIC,
        10,
    )

    completion_pub = probe.create_publisher(
        String,
        module.RMF_COMPLETION_TOPIC,
        10,
    )

    def on_assignment(msg):
        payload = json.loads(msg.data)
        assignments.append(payload)
        print("[ASSIGNMENT]", json.dumps(payload))

    def on_rmf_request(msg):
        payload = {
            "request_id": msg.request_id,
            "payload": json.loads(msg.json_msg),
        }
        requests.append(payload)
        print("[RMF REQUEST]", json.dumps(payload))

    probe.create_subscription(
        String,
        module.PPO_ASSIGNMENT_TOPIC,
        on_assignment,
        10,
    )

    rmf_qos = QoSProfile(
        depth=100,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )

    probe.create_subscription(
        ApiRequest,
        module.RMF_TASK_API_TOPIC,
        on_rmf_request,
        rmf_qos,
    )

    executor.add_node(scheduler)
    executor.add_node(probe)

    original_predict = scheduler.model.predict

    def traced_predict(observation, *args, **kwargs):

        action, state = original_predict(
            observation,
            *args,
            **kwargs,
        )

        predictions.append({
            "observation": observation.tolist(),
            "observation_shape": list(observation.shape),
            "action_mask": np.asarray(
                kwargs["action_masks"],
                dtype=int,
            ).tolist(),
            "action": int(np.asarray(action).item()),
        })

        return action, state

    scheduler.model.predict = traced_predict

    def spin_for(seconds):

        deadline = time.monotonic() + seconds

        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)

    def wait_until(predicate, timeout_s=8.0):

        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:

            if predicate():
                return True

            executor.spin_once(timeout_sec=0.05)

        return predicate()

    assert wait_until(
        lambda: (
            task_pub.get_subscription_count() >= 1
            and fleet_pub.get_subscription_count() >= 1
            and completion_pub.get_subscription_count() >= 1
            and scheduler.assignment_publisher
                .get_subscription_count() >= 1
            and scheduler.rmf_task_publisher
                .get_subscription_count() >= 1
        ),
        timeout_s=15.0,
    ), "ROS discovery timeout"

    print("ROS DISCOVERY: PASS")

    # --------------------------------------------------------
    # Synthetic FleetState publisher
    # --------------------------------------------------------

    fleet_sequence = 0

    def send_fleet(
        overrides=None,
        omit=(),
    ):

        global fleet_sequence

        overrides = overrides or {}
        fleet_sequence += 1

        msg = FleetState()
        msg.name = module.RMF_FLEET_NAME

        expected_ids = []

        for rid in module.LOGICAL_ROBOT_IDS:

            if rid in omit:
                continue

            settings = overrides.get(rid, {})

            location = settings.get(
                "location",
                LOCATIONS[rid],
            )

            wp = scheduler.nav_graph.waypoints_by_name[
                location
            ]

            robot = RobotState()

            robot.name = module.LOGICAL_TO_RMF[rid]
            robot.model = "G1"
            robot.seq = fleet_sequence

            robot.task_id = settings.get("task_id", "")
            robot.mode.mode = settings.get("mode", 0)

            # RMF battery percentage convention: 0..100.
            robot.battery_percent = float(
                settings.get("soc", 1.0) * 100.0
            )

            robot.location.x = float(wp.x)
            robot.location.y = float(wp.y)
            robot.location.yaw = 0.0
            robot.location.level_name = "L1"

            robot.location.t = (
                probe.get_clock().now().to_msg()
            )

            msg.robots.append(robot)
            expected_ids.append(rid)

        sent_at = time.monotonic()

        fleet_pub.publish(msg)

        assert wait_until(
            lambda: all(
                scheduler.latest_robot_data.get(rid, {})
                    .get("received_at", 0.0) >= sent_at
                for rid in expected_ids
            )
        ), "FleetState was not received"

    def reset_state(overrides=None, omit=()):

        spin_for(0.2)

        scheduler.pending_scheduled_tasks.clear()
        scheduler.tasks_by_id.clear()
        scheduler.latest_robot_data.clear()

        scheduler.parking_operations.clear()
        scheduler.parking_nav_status.clear()

        scheduler.charging_robots.clear()
        scheduler.charging_start_time_s.clear()
        scheduler.charging_end_time_s.clear()
        scheduler.charging_start_soc.clear()

        scheduler.runtime_battery_soc_override.clear()
        scheduler.test_low_battery_robots.clear()

        for rid in module.LOGICAL_ROBOT_IDS:
            scheduler.running_task_ids[rid] = None
            scheduler.source_reached[rid] = False
            scheduler.returning_to_charge[rid] = False
            scheduler.queued_task_ids[rid].clear()

        assignments.clear()
        requests.clear()
        predictions.clear()

        send_fleet(overrides, omit)

    def send_task(
        case,
        kind="specimen_delivery",
        source="consult_3_2",
        destination="lab",
        priority=1,
    ):

        task_id = f"{RUN_ID}_{case}"

        payload = {
            "task_id": task_id,
            "task_type": kind,
            "source": source,
            "destination": destination,
            "priority": priority,
            "created_at": time.time(),
            "scheduled_at": time.time(),
        }

        msg = String()
        msg.data = json.dumps(payload)
        task_pub.publish(msg)

        return task_id

    def send_completion(rid, destination):

        msg = String()

        msg.data = json.dumps({
            "robot_id": module.LOGICAL_TO_RMF[rid],
            "destination": destination,
        })

        completion_pub.publish(msg)
        spin_for(0.3)

    def matching_assignments(task_id):

        return [
            a for a in assignments
            if a.get("task_id") == task_id
        ]

    def matching_requests(task_id):

        prefix = f"ppo_{task_id}_"

        return [
            r for r in requests
            if r["request_id"].startswith(prefix)
        ]

    def selected_robot(task_id):

        matched = matching_assignments(task_id)

        if not matched:
            return None

        return matched[0].get(
            "assignment", {}
        ).get("expected_robot_name")

    def wait_assignment(task_id):

        return wait_until(
            lambda: bool(matching_assignments(task_id))
        )

    def successful_dispatch(task_id, expected_robot):

        matched = matching_assignments(task_id)
        rmf = matching_requests(task_id)

        return (
            len(matched) == 1
            and matched[0].get("status") == 3
            and selected_robot(task_id) == expected_robot
            and len(rmf) == 1
            and rmf[0]["payload"].get("robot") == expected_robot
        )


    # ========================================================
    # RT-13: Fresh state remains eligible
    # ========================================================

    reset_state()

    scheduler.latest_robot_data["M01"]["received_at"] = (
        time.monotonic() - 10.0
    )

    task_id = send_task("RT-13")

    arrived = wait_assignment(task_id)
    wait_until(lambda: bool(matching_requests(task_id)))

    mask = predictions[-1]["action_mask"] if predictions else []

    record(
        "RT-13",
        arrived
        and mask == [0, 0, 1, 1, 0, 0, 0]
        and len(matching_requests(task_id)) == 1,
        injected_state_age_s=10.0,
        actual_mask=mask,
        assignments=matching_assignments(task_id),
        predictions=list(predictions),
    )

    # --------------------------------------------------------
    # Observe the behavior when no robot is available.
    # --------------------------------------------------------

    def observe_unavailable(case_id, task_id):

        spin_for(3.2)

        matched = matching_assignments(task_id)

        pending = (
            task_id in scheduler.pending_scheduled_tasks
        )

        if pending and not matched:
            behavior = "pending"

        elif (
            len(matched) == 1
            and matched[0].get("status") == 4
            and not pending
        ):
            behavior = "failed"

        else:
            behavior = "unexpected"

        safe = (
            not predictions
            and not requests
            and behavior in ("pending", "failed")
        )

        record(
            case_id,
            safe,
            behavior=behavior,
            pending=pending,
            assignment_messages=matched,
            prediction_count=len(predictions),
            rmf_request_count=len(requests),
            observation_window_s=3.2,
        )

        return behavior

    # ========================================================
    # RT-14: Both medical robots stale
    # ========================================================

    reset_state()

    for rid in ("M01", "M02"):
        scheduler.latest_robot_data[rid]["received_at"] = (
            time.monotonic() - 31.0
        )

    task_id = send_task("RT-14")

    observe_unavailable("RT-14", task_id)

    # ========================================================
    # RT-15: Stale robot recovers through new FleetState
    # ========================================================

    reset_state()

    scheduler.latest_robot_data["M01"]["received_at"] = (
        time.monotonic() - 31.0
    )

    before_status = {
        r.robot_id: r.status
        for r in scheduler._build_robot_states()
    }["M01"]

    send_fleet({
        "M02": {
            "mode": 2,
            "task_id": "external_busy",
        }
    })

    after_status = {
        r.robot_id: r.status
        for r in scheduler._build_robot_states()
    }["M01"]

    task_id = send_task("RT-15")

    arrived = wait_assignment(task_id)
    wait_until(lambda: bool(matching_requests(task_id)))

    record(
        "RT-15",
        before_status == "offline"
        and after_status == "idle"
        and arrived
        and successful_dispatch(
            task_id, "hospital_robot_3"
        )
        and bool(predictions)
        and predictions[-1]["action_mask"]
            == [0, 0, 1, 0, 0, 0, 0],
        before_status=before_status,
        after_status=after_status,
        assignments=matching_assignments(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-16: Preserve active task when robot state becomes stale
    # ========================================================

    reset_state()

    task_id = send_task("RT-16-A")

    assert wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    rid = module.RMF_TO_LOGICAL[
        selected_robot(task_id)
    ]

    other = "M02" if rid == "M01" else "M01"

    scheduler.latest_robot_data[rid]["received_at"] = (
        time.monotonic() - 31.0
    )

    robots = {
        r.robot_id: r
        for r in scheduler._build_robot_states()
    }

    stale_status = robots[rid].status

    next_task_id = send_task("RT-16-B")

    arrived = wait_assignment(next_task_id)

    wait_until(
        lambda: bool(matching_requests(next_task_id))
    )

    record(
        "RT-16",
        stale_status == "offline"
        and task_id in scheduler.tasks_by_id
        and scheduler.tasks_by_id[task_id].status == "active"
        and scheduler.running_task_ids[rid] == task_id
        and arrived
        and successful_dispatch(
            next_task_id,
            module.LOGICAL_TO_RMF[other],
        )
        and predictions[-1]["action_mask"][
            module.LOGICAL_ROBOT_IDS.index(rid)
        ] == 0,
        stale_robot=rid,
        stale_status=stale_status,
        original_task_status=(
            scheduler.tasks_by_id[task_id].status
        ),
        original_task_preserved=(
            scheduler.running_task_ids[rid] == task_id
        ),
        next_task_robot=selected_robot(next_task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-17: Both medical robots charging
    # ========================================================

    reset_state({
        "M01": {"mode": 1, "soc": 0.40},
        "M02": {"mode": 1, "soc": 0.40},
    })

    task_id = send_task("RT-17")

    observe_unavailable("RT-17", task_id)

    # ========================================================
    # RT-18: Both medical robots offline
    # ========================================================

    reset_state(omit=("M01", "M02"))

    task_id = send_task("RT-18")

    observe_unavailable("RT-18", task_id)

    # ========================================================
    # RT-19: Both medical robots in error
    # ========================================================

    reset_state({
        "M01": {"mode": 8},
        "M02": {"mode": 8},
    })

    task_id = send_task("RT-19")

    observe_unavailable("RT-19", task_id)

    # ========================================================
    # RT-20: Recover unavailable robot and retry pending task
    # ========================================================

    reset_state({
        "M01": {"mode": 1, "soc": 0.40},
        "M02": {"mode": 1, "soc": 0.40},
    })

    task_id = send_task("RT-20")

    spin_for(3.2)

    was_pending = (
        task_id in scheduler.pending_scheduled_tasks
    )

    earlier_assignments = list(
        matching_assignments(task_id)
    )

    earlier_predictions = len(predictions)
    earlier_requests = len(requests)

    safe_while_unavailable = (
        earlier_predictions == 0
        and earlier_requests == 0
        and (
            (
                was_pending
                and not earlier_assignments
            )
            or (
                not was_pending
                and len(earlier_assignments) == 1
                and earlier_assignments[0].get("status") == 4
            )
        )
    )

    recovered_at = time.monotonic()

    send_fleet({
        "M01": {"mode": 1, "soc": 0.40},
        "M02": {"mode": 0, "soc": 0.80},
    })

    recovered = wait_until(
        lambda: any(
            a.get("status") == 3
            for a in matching_assignments(task_id)
        ),
        timeout_s=3.0,
    )

    if recovered:
        wait_until(lambda: bool(matching_requests(task_id)))

    observed_delay_s = (
        time.monotonic() - recovered_at
        if recovered
        else None
    )

    record(
        "RT-20",
        safe_while_unavailable
        and was_pending
        and recovered
        and successful_dispatch(
            task_id, "hospital_robot_4"
        )
        and len(predictions) == 1
        and task_id not in scheduler.pending_scheduled_tasks,
        was_pending=was_pending,
        earlier_assignments=earlier_assignments,
        earlier_predictions=earlier_predictions,
        earlier_requests=earlier_requests,
        recovered_dispatch=recovered,
        observed_recovery_delay_s=observed_delay_s,
        final_assignments=matching_assignments(task_id),
        requests=matching_requests(task_id),
        predictions=list(predictions),
    )

except Exception as exc:

    traceback.print_exc()

    record(
        "TEST-HARNESS-ERROR",
        False,
        error_type=type(exc).__name__,
        error_message=str(exc),
    )

finally:

    executor.shutdown()

    if probe is not None:
        probe.destroy_node()

    if scheduler is not None:
        scheduler.destroy_node()

    if rclpy.ok():
        rclpy.shutdown()

    passed = sum(
        item["result"] == "PASS"
        for item in results
    )

    failed = len(results) - passed

    report = {
        "run_id": RUN_ID,
        "model_sha256": hashlib.sha256(
            module.MODEL_PATH.read_bytes()
        ).hexdigest(),
        "scheduler_sha256": hashlib.sha256(
            SOURCE.read_bytes()
        ).hexdigest(),
        "ros_domain_id": os.environ["ROS_DOMAIN_ID"],
        "scheduling_only": False,
        "synthetic_fleet_state": True,
        "synthetic_completion_events": True,
        "gazebo_started": False,
        "rmf_adapter_started": False,
        "full_system_verified": False,
        "expected_tests": 8,
        "executed_tests": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    output = Path(
        f"/tmp/ppo_runtime_extended_results_{RUN_ID}.json"
    )

    with output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print()
    print("===== PPO EXTENDED TEST SUMMARY =====")

    for item in results:
        print(item["test_id"], item["result"])

    print("Expected tests: 8")
    print("Executed tests:", len(results))
    print("Passed:", passed)
    print("Failed:", failed)
    print("Result file:", output)

    if len(results) == 8 and failed == 0:
        print("PPO RUNTIME TEST: PASS")
    else:
        print("PPO RUNTIME TEST: REVIEW REQUIRED")

sys.exit(
    0 if len(results) == 8 and failed == 0 else 1
)
