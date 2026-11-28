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
    # RT-01: FleetState conversion
    # ========================================================

    reset_state({
        "C01": {"soc": 0.75},
        "M01": {"mode": 2, "task_id": "external_task"},
        "W01": {"mode": 1, "soc": 0.50},
        "W02": {"mode": 8},
    })

    robots = scheduler._build_robot_states()

    snapshot = {
        r.robot_id: {
            "status": r.status,
            "soc": r.battery_soc,
            "location": r.current_location,
            "capabilities": list(r.capabilities),
        }
        for r in robots
    }

    passed = (
        [r.robot_id for r in robots]
        == list(module.LOGICAL_ROBOT_IDS)
        and snapshot["M01"]["status"] == "busy"
        and snapshot["W01"]["status"] == "charging"
        and snapshot["W02"]["status"] == "error"
        and np.isclose(snapshot["C01"]["soc"], 0.75)
        and np.isclose(snapshot["W01"]["soc"], 0.50)
        and all(
            snapshot[rid]["location"] == LOCATIONS[rid]
            for rid in LOCATIONS
        )
    )

    record("RT-01", passed, robots=snapshot)

    # ========================================================
    # RT-02: M01 busy, M02 idle
    # ========================================================

    reset_state({
        "M01": {
            "mode": 2,
            "task_id": "external_busy",
        }
    })

    task_id = send_task("RT-02")
    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    mask = predictions[-1]["action_mask"] if predictions else []

    record(
        "RT-02",
        arrived
        and successful_dispatch(task_id, "hospital_robot_4")
        and mask == [0, 0, 0, 1, 0, 0, 0],
        assignments=matching_assignments(task_id),
        requests=matching_requests(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-03: Both medical robots busy
    # ========================================================

    reset_state({
        "M01": {"mode": 2, "task_id": "busy_1"},
        "M02": {"mode": 2, "task_id": "busy_2"},
    })

    task_id = send_task("RT-03")

    spin_for(2.5)

    deferred = (
        task_id in scheduler.pending_scheduled_tasks
        and task_id not in scheduler.tasks_by_id
        and not matching_assignments(task_id)
        and not matching_requests(task_id)
        and not predictions
    )

    record(
        "RT-03",
        deferred,
        pending=task_id in scheduler.pending_scheduled_tasks,
        assignments=matching_assignments(task_id),
        requests=matching_requests(task_id),
        prediction_count=len(predictions),
    )

    # ========================================================
    # RT-04: Robot becomes available
    # ========================================================

    send_fleet({
        "M01": {"mode": 2, "task_id": "busy_1"},
        "M02": {"mode": 0, "task_id": ""},
    })

    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    record(
        "RT-04",
        deferred
        and arrived
        and successful_dispatch(task_id, "hospital_robot_4")
        and task_id not in scheduler.pending_scheduled_tasks
        and len(predictions) == 1,
        assignments=matching_assignments(task_id),
        requests=matching_requests(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-05: Never-received / offline robot
    # ========================================================

    reset_state(omit=("M01",))

    task_id = send_task("RT-05")
    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    record(
        "RT-05",
        arrived
        and successful_dispatch(task_id, "hospital_robot_4")
        and bool(predictions)
        and predictions[-1]["action_mask"][2] == 0,
        assignments=matching_assignments(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-06: Robot adapter error
    # ========================================================

    reset_state({
        "M01": {"mode": 8},
    })

    task_id = send_task("RT-06")
    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    record(
        "RT-06",
        arrived
        and successful_dispatch(task_id, "hospital_robot_4")
        and bool(predictions)
        and predictions[-1]["action_mask"][2] == 0,
        assignments=matching_assignments(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-07: Stale FleetState
    # ========================================================

    reset_state()

    # Test-time injection: simulate that the last M01
    # FleetState was received 31 seconds earlier.
    scheduler.latest_robot_data["M01"]["received_at"] = (
        time.monotonic() - 31.0
    )

    task_id = send_task("RT-07")
    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    mask = predictions[-1]["action_mask"] if predictions else []

    record(
        "RT-07",
        arrived
        and successful_dispatch(task_id, "hospital_robot_4")
        and len(mask) == 7
        and mask[2] == 0,
        injected_state_age_s=31.0,
        expected_stale_robot_excluded=True,
        actual_mask=mask,
        assignments=matching_assignments(task_id),
        requests=matching_requests(task_id),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-08: Three concurrent specimen tasks
    # ========================================================

    reset_state()

    ids = [
        send_task(f"RT-08-{i}")
        for i in range(1, 4)
    ]

    wait_until(
        lambda: sum(
            bool(matching_assignments(tid))
            for tid in ids
        ) >= 2
    )

    spin_for(1.5)

    assigned_ids = [
        tid for tid in ids
        if matching_assignments(tid)
        and matching_assignments(tid)[0].get("status") == 3
    ]

    assigned_robots = [
        selected_robot(tid)
        for tid in assigned_ids
    ]

    pending_ids = [
        tid for tid in ids
        if tid in scheduler.pending_scheduled_tasks
    ]

    record(
        "RT-08",
        len(assigned_ids) == 2
        and set(assigned_robots) == {
            "hospital_robot_3",
            "hospital_robot_4",
        }
        and len(pending_ids) == 1
        and len(predictions) == 2
        and len(requests) == 2,
        assigned_ids=assigned_ids,
        assigned_robots=assigned_robots,
        pending_ids=pending_ids,
        requests=list(requests),
        predictions=list(predictions),
    )

    # ========================================================
    # RT-09: Targeted RMF request payload
    # ========================================================

    reset_state()

    task_id = send_task("RT-09")
    arrived = wait_assignment(task_id)

    wait_until(lambda: bool(matching_requests(task_id)))

    matched = matching_requests(task_id)

    payload = matched[0]["payload"] if matched else {}

    phases = (
        payload.get("request", {})
        .get("description", {})
        .get("phases", [])
    )

    expected_robot = None

    if predictions:
        action = predictions[-1]["action"]
        expected_robot = module.LOGICAL_TO_RMF[
            module.LOGICAL_ROBOT_IDS[action]
        ]

    record(
        "RT-09",
        arrived
        and len(matched) == 1
        and expected_robot is not None
        and selected_robot(task_id) == expected_robot
        and payload.get("robot") == expected_robot
        and payload.get("fleet") == "hospital_fleet"
        and payload.get("type") == "robot_task_request"
        and len(phases) == 2
        and [
            phase["activity"]["category"]
            for phase in phases
        ] == ["go_to_place", "go_to_place"]
        and [
            phase["activity"]["description"]
            for phase in phases
        ] == ["consult_3_2", "lab"],
        assignments=matching_assignments(task_id),
        rmf_payload=payload,
        predictions=list(predictions),
    )

    # ========================================================
    # RT-10: Destination reached before source
    # ========================================================

    reset_state()

    task_id = send_task("RT-10")

    assert wait_assignment(task_id)

    rmf_robot = selected_robot(task_id)
    assert rmf_robot in module.RMF_TO_LOGICAL

    rid = module.RMF_TO_LOGICAL[rmf_robot]

    send_completion(rid, "lab")

    task = scheduler.tasks_by_id[task_id]

    record(
        "RT-10",
        task.status == "active"
        and not scheduler.source_reached[rid]
        and task.completion_time_s is None,
        task_status=task.status,
        source_reached=scheduler.source_reached[rid],
        completion_time_s=task.completion_time_s,
    )

    # ========================================================
    # RT-11: Correct source and destination sequence
    # ========================================================

    send_completion(rid, "consult_3_2")

    source_confirmed = (
        scheduler.source_reached[rid]
        and task.status == "active"
    )

    send_completion(rid, "lab")

    record(
        "RT-11",
        source_confirmed
        and task.status == "completed"
        and task.completion_time_s is not None
        and scheduler.running_task_ids[rid] is None,
        source_confirmed=source_confirmed,
        final_status=task.status,
        completion_time_s=task.completion_time_s,
        running_task_id=scheduler.running_task_ids[rid],
        parking_requested=rid in scheduler.parking_operations,
    )

    # ========================================================
    # RT-12: Low battery after task completion
    # ========================================================

    reset_state()

    task_id = send_task("RT-12")

    assert wait_assignment(task_id)

    rmf_robot = selected_robot(task_id)
    assert rmf_robot in module.RMF_TO_LOGICAL

    rid = module.RMF_TO_LOGICAL[rmf_robot]

    # Inject updated battery through actual FleetState.
    send_fleet({
        rid: {
            "mode": 2,
            "task_id": "test_active_task",
            "soc": 0.20,
        },
    })

    send_completion(rid, "consult_3_2")
    send_completion(rid, "lab")

    wait_until(
        lambda: any(
            r["request_id"].startswith("charge_")
            for r in requests
        )
    )

    charge_requests = [
        r for r in requests
        if r["request_id"].startswith("charge_")
    ]

    charge_payload = (
        charge_requests[0]["payload"]
        if charge_requests else {}
    )

    charge_phases = (
        charge_payload.get("request", {})
        .get("description", {})
        .get("phases", [])
    )

    record(
        "RT-12",
        scheduler.tasks_by_id[task_id].status == "completed"
        and scheduler.returning_to_charge[rid]
        and len(charge_requests) == 1
        and charge_payload.get("robot") == rmf_robot
        and len(charge_phases) == 1
        and charge_phases[0]["activity"]["description"]
            == module.CHARGING_WAYPOINT,
        selected_robot=rmf_robot,
        battery_soc=scheduler._get_runtime_battery_soc(rid),
        returning_to_charge=scheduler.returning_to_charge[rid],
        charge_requests=charge_requests,
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
        "expected_tests": 12,
        "executed_tests": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    output = Path(
        f"/tmp/ppo_runtime_results_{RUN_ID}.json"
    )

    with output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print()
    print("===== PPO RUNTIME TEST SUMMARY =====")

    for item in results:
        print(item["test_id"], item["result"])

    print("Expected tests: 12")
    print("Executed tests:", len(results))
    print("Passed:", passed)
    print("Failed:", failed)
    print("Result file:", output)

    if len(results) == 12 and failed == 0:
        print("PPO RUNTIME TEST: PASS")
    else:
        print("PPO RUNTIME TEST: REVIEW REQUIRED")

sys.exit(
    0 if len(results) == 12 and failed == 0 else 1
)
