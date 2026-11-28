from pathlib import Path
import importlib.util
import hashlib
import json
import os
import sys
import time

import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
from rmf_task_msgs.msg import ApiRequest


ROOT = Path.cwd()

SOURCE = (
    ROOT / "ros2_ws/src/my_hospital_rmf/scripts"
    / "hospital_ppo_scheduler.py"
)

assert os.environ.get("ROS_DOMAIN_ID") == "187"
assert os.environ.get("HOSPITAL_SCHEDULING_ONLY") == "1"

spec = importlib.util.spec_from_file_location(
    "hospital_ppo_scheduler",
    SOURCE,
)

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

results = []
assignments = []
predictions = []
rmf_requests = []

RUN_ID = str(time.time_ns())


def record(case_id, passed, **details):

    result = {
        "test_id": case_id,
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

    assert scheduler.scheduling_only

    probe = Node("ppo_integration_test_probe")

    publisher = probe.create_publisher(
        String,
        module.TASK_TOPIC,
        10,
    )

    def assignment_callback(msg):

        payload = json.loads(msg.data)

        assignments.append(payload)

        print(
            "[ASSIGNMENT RECEIVED]",
            json.dumps(payload),
            flush=True,
        )

    def rmf_callback(msg):

        rmf_requests.append(msg.request_id)

    assignment_subscription = probe.create_subscription(
        String,
        module.PPO_ASSIGNMENT_TOPIC,
        assignment_callback,
        10,
    )

    rmf_subscription = probe.create_subscription(
        ApiRequest,
        module.RMF_TASK_API_TOPIC,
        rmf_callback,
        10,
    )

    executor.add_node(scheduler)
    executor.add_node(probe)

    # Capture the actual inputs and outputs used by
    # the real scheduler without changing its decisions.

    original_predict = scheduler.model.predict

    def traced_predict(
        observation,
        *args,
        **kwargs,
    ):

        mask = np.asarray(
            kwargs["action_masks"],
            dtype=bool,
        )

        action, state = original_predict(
            observation,
            *args,
            **kwargs,
        )

        selected = int(
            np.asarray(action).item()
        )

        predictions.append({
            "observation": observation.tolist(),
            "observation_shape": list(
                observation.shape
            ),
            "observation_dtype": str(
                observation.dtype
            ),
            "action_mask": mask.astype(int).tolist(),
            "action": selected,
            "observation_valid": bool(
                scheduler.model.observation_space
                .contains(observation)
            ),
            "deterministic": bool(
                kwargs.get("deterministic", False)
            ),
        })

        return action, state

    scheduler.model.predict = traced_predict


    def spin_for(seconds):

        deadline = time.monotonic() + seconds

        while time.monotonic() < deadline:

            executor.spin_once(
                timeout_sec=0.05
            )


    def wait_until(predicate, timeout_s=10.0):

        deadline = (
            time.monotonic() + timeout_s
        )

        while time.monotonic() < deadline:

            if predicate():
                return True

            executor.spin_once(
                timeout_sec=0.05
            )

        return predicate()


    def reset_test_state():

        assert not scheduler.pending_scheduled_tasks

        scheduler.tasks_by_id.clear()

        for rid in module.LOGICAL_ROBOT_IDS:

            scheduler.queued_task_ids[rid].clear()
            scheduler.running_task_ids[rid] = None
            scheduler.source_reached[rid] = False
            scheduler.returning_to_charge[rid] = False

        scheduler.runtime_battery_soc_override.clear()
        scheduler.test_low_battery_robots.clear()

        assert not scheduler.charging_robots
        assert not scheduler.parking_operations

        scheduler.latest_robot_data.clear()

        scheduler._ensure_scheduling_only_robot_data()


    def make_task(
        case_id,
        task_type,
        source,
        destination,
        priority=1,
        delay_s=0.0,
    ):

        return {
            "task_id": f"{RUN_ID}_{case_id}",
            "task_type": task_type,
            "source": source,
            "destination": destination,
            "priority": priority,
            "created_at": time.time(),
            "scheduled_at": time.time() + delay_s,
        }


    def publish(payload):

        msg = String()

        msg.data = json.dumps(payload)

        publisher.publish(msg)


    def matching_assignments(task_id):

        return [
            item for item in assignments
            if item.get("task_id") == task_id
        ]


    def test_success(
        case_id,
        payload,
        expected_mask,
        reset=True,
    ):

        if reset:
            reset_test_state()

        start = len(predictions)

        publish(payload)

        arrived = wait_until(
            lambda: bool(
                matching_assignments(
                    payload["task_id"]
                )
            )
        )

        matched = matching_assignments(
            payload["task_id"]
        )

        trace = predictions[start:]

        passed = False
        robot = None

        if arrived and len(trace) == 1:

            decision = trace[0]

            assignment = matched[0]

            action = decision["action"]

            robot = module.LOGICAL_TO_RMF[
                module.LOGICAL_ROBOT_IDS[action]
            ]

            returned_robot = (
                assignment.get("assignment", {})
                .get("expected_robot_name")
            )

            passed = (
                len(matched) == 1
                and assignment.get("status") == 3
                and assignment.get("assignment", {})
                    .get("is_assigned") is True
                and returned_robot == robot
                and decision["action_mask"] == expected_mask
                and expected_mask[action] == 1
                and decision["observation_valid"]
                and decision["observation_shape"] == [98]
                and decision["observation_dtype"] == "float32"
                and decision["deterministic"]
            )

        record(
            case_id,
            passed,
            task=payload,
            expected_mask=expected_mask,
            actual_assignment=matched,
            predictions=trace,
            selected_rmf_robot=robot,
        )

        return passed


    # Wait for ROS graph discovery before publishing.

    ready = wait_until(
        lambda: (
            publisher.get_subscription_count() >= 1
            and scheduler.assignment_publisher
                .get_subscription_count() >= 1
        ),
        timeout_s=15.0,
    )

    assert ready, "ROS topic discovery timed out"

    print("ROS TOPIC DISCOVERY: PASS", flush=True)

    # ========================================================
    # TC-08: Five task types
    # ========================================================

    cases = [
        (
            "TC-08A",
            "waste_transport",
            "ward_a_2",
            "waste_return_2",
            [1, 1, 0, 0, 0, 0, 0],
        ),
        (
            "TC-08B",
            "clothes_collection",
            "ward_b_2",
            "clothes_return_2",
            [1, 1, 0, 0, 0, 0, 0],
        ),
        (
            "TC-08C",
            "specimen_delivery",
            "consult_3_2",
            "lab",
            [0, 0, 1, 1, 0, 0, 0],
        ),
        (
            "TC-08D",
            "medication_delivery",
            "pharmacy",
            "ward_a_2",
            [0, 0, 1, 1, 1, 1, 1],
        ),
        (
            "TC-08E",
            "ward_service",
            "nurse_station",
            "ward_b_2",
            [0, 0, 0, 0, 1, 1, 1],
        ),
    ]

    for case_id, kind, src, dst, mask in cases:

        payload = make_task(
            case_id,
            kind,
            src,
            dst,
        )

        test_success(
            case_id,
            payload,
            mask,
        )

    # ========================================================
    # TC-09A: Exclude a low-battery robot
    # ========================================================

    reset_test_state()

    scheduler.runtime_battery_soc_override["M01"] = 0.10

    payload = make_task(
        "TC-09A",
        "specimen_delivery",
        "consult_3_2",
        "lab",
        priority=3,
    )

    test_success(
        "TC-09A",
        payload,
        [0, 0, 0, 1, 0, 0, 0],
        reset=False,
    )

    # ========================================================
    # TC-09B: No feasible robot
    # ========================================================

    reset_test_state()

    scheduler.runtime_battery_soc_override["M01"] = 0.10
    scheduler.runtime_battery_soc_override["M02"] = 0.10

    payload = make_task(
        "TC-09B",
        "specimen_delivery",
        "consult_3_2",
        "lab",
        priority=3,
    )

    before = len(predictions)

    publish(payload)

    arrived = wait_until(
        lambda: bool(
            matching_assignments(
                payload["task_id"]
            )
        )
    )

    matched = matching_assignments(
        payload["task_id"]
    )

    passed = (
        arrived
        and len(matched) == 1
        and matched[0].get("status") == 4
        and len(predictions) == before
        and all(
            not queue
            for queue in scheduler.queued_task_ids.values()
        )
    )

    record(
        "TC-09B",
        passed,
        task=payload,
        expected_status=4,
        actual_assignment=matched,
        ppo_prediction_calls=len(predictions) - before,
    )

    # ========================================================
    # TC-10A: Duplicate task ID
    # ========================================================

    reset_test_state()

    payload = make_task(
        "TC-10A",
        "specimen_delivery",
        "consult_3_2",
        "lab",
    )

    start = len(predictions)

    publish(payload)

    arrived = wait_until(
        lambda: bool(
            matching_assignments(
                payload["task_id"]
            )
        )
    )

    publish(payload)

    spin_for(2.5)

    matched = matching_assignments(
        payload["task_id"]
    )

    queue_occurrences = sum(
        queue.count(payload["task_id"])
        for queue in scheduler.queued_task_ids.values()
    )

    record(
        "TC-10A",
        arrived
        and len(matched) == 1
        and matched[0].get("status") == 3
        and len(predictions) - start == 1
        and queue_occurrences == 1,
        task=payload,
        assignment_count=len(matched),
        ppo_prediction_calls=len(predictions) - start,
        queue_occurrences=queue_occurrences,
    )

    # ========================================================
    # TC-10B: Scheduled task must wait until due
    # ========================================================

    reset_test_state()

    payload = make_task(
        "TC-10B",
        "medication_delivery",
        "pharmacy",
        "ward_a_2",
        priority=2,
        delay_s=5.0,
    )

    start = len(predictions)

    publish(payload)

    spin_for(2.0)

    early_assignment_count = len(
        matching_assignments(
            payload["task_id"]
        )
    )

    early_prediction_count = (
        len(predictions) - start
    )

    arrived = wait_until(
        lambda: bool(
            matching_assignments(
                payload["task_id"]
            )
        ),
        timeout_s=10.0,
    )

    received_at = time.time()

    matched = matching_assignments(
        payload["task_id"]
    )

    trace = predictions[start:]

    record(
        "TC-10B",
        arrived
        and early_assignment_count == 0
        and early_prediction_count == 0
        and len(matched) == 1
        and matched[0].get("status") == 3
        and len(trace) == 1
        and received_at >= payload["scheduled_at"],
        task=payload,
        early_assignment_count=early_assignment_count,
        early_prediction_count=early_prediction_count,
        received_at=received_at,
        actual_assignment=matched,
        predictions=trace,
    )

    # ========================================================
    # Safety: No real RMF dispatch
    # ========================================================

    spin_for(1.0)

    record(
        "TC-SAFETY",
        len(rmf_requests) == 0,
        rmf_requests=rmf_requests,
        scheduling_only=scheduler.scheduling_only,
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
    "model_path": str(module.MODEL_PATH),
    "model_sha256": hashlib.sha256(
        module.MODEL_PATH.read_bytes()
    ).hexdigest(),
    "scheduler_sha256": hashlib.sha256(
        SOURCE.read_bytes()
    ).hexdigest(),
    "ros_domain_id": os.environ["ROS_DOMAIN_ID"],
    "scheduling_only": True,
    "synthetic_robot_states": True,
    "gazebo_started": False,
    "passed": passed,
    "failed": failed,
    "results": results,
}

output = Path(
    f"/tmp/ppo_dispatch_results_{RUN_ID}.json"
)

output.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== PPO DISPATCH TEST SUMMARY =====")

for item in results:
    print(item["test_id"], item["result"])

print("Total tests:", len(results))
print("Passed:", passed)
print("Failed:", failed)
print("RMF requests:", len(rmf_requests))
print("Result file:", output)

assert len(results) == 10
assert failed == 0

print("PPO DISPATCH TEST: COMPLETE")
