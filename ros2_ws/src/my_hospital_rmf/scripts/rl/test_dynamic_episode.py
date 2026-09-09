#!/usr/bin/env python3

import numpy as np

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from rl.hospital_gym_env import (
    HospitalGymEnv,
)

from collections import Counter

def test_dynamic_episode():

    scenario = (
        generate_random_scenario(

            task_count=50,

            seed=6000,

            load="high",

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    env = HospitalGymEnv(

        scenario=scenario,

        robot_speed=ROBOT_SPEED,

        service_time=SERVICE_TIME,

        enable_dynamic_reassignment=True,
    )

    observation, info = env.reset()

    rng = np.random.default_rng(
        12345
    )

    step_count = 0
    reassignment_decisions = 0

    terminated = False
    truncated = False

    while not (
        terminated
        or truncated
    ):

        mask = env.action_masks()

        valid_actions = np.flatnonzero(
            mask
        )

        assert len(
            valid_actions
        ) > 0

        action = int(
            rng.choice(
                valid_actions
            )
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        step_count += 1

        if info.get(
            "is_reassignment",
            False,
        ):
            reassignment_decisions += 1

    core = env.core_env

    # ======================================================
    # Dynamic Reassignment Diagnostics
    # ======================================================

    events = (
        core.reassignment_events
    )

    changed_events = [
        event
        for event in events
        if event[
            "changed_robot"
        ]
    ]

    stayed_events = [
        event
        for event in events
        if not event[
            "changed_robot"
        ]
    ]

    # 每個 Cascade Depth 出現幾次。
    depth_counts = Counter(
        event[
            "cascade_depth"
        ]
        for event in events
    )

    # 每個 Task 被重新評估幾次。
    task_reassignment_counts = Counter(
        event[
            "task_id"
        ]
        for event in events
    )

    # 每個 Root Trigger 造成多少次 Reassignment。
    root_reassignment_counts = Counter(
        event[
            "root_trigger_task_id"
        ]
        for event in events
    )

    # 同一個 Root Cascade 中，
    # 同一 Task 被重新評估幾次。
    root_task_counts = Counter(
        (
            event[
                "root_trigger_task_id"
            ],
            event[
                "task_id"
            ],
        )
        for event in events
    )

    max_depth = max(
        depth_counts,
        default=0,
    )

    max_task_reassignments = max(
        task_reassignment_counts.values(),
        default=0,
    )

    max_root_reassignments = max(
        root_reassignment_counts.values(),
        default=0,
    )

    max_same_task_same_root = max(
        root_task_counts.values(),
        default=0,
    )

    print()
    print("=" * 80)
    print("DYNAMIC REASSIGNMENT DIAGNOSTICS")
    print("=" * 80)

    print(
        "Total reassignment decisions:",
        len(events),
    )

    print(
        "Changed robot:",
        len(changed_events),
    )

    print(
        "Stayed on same robot:",
        len(stayed_events),
    )

    print(
        "Unique reassigned tasks:",
        len(
            task_reassignment_counts
        ),
    )

    print(
        "Max cascade depth:",
        max_depth,
    )

    print(
        "Depth distribution:",
        dict(
            sorted(
                depth_counts.items()
            )
        ),
    )

    print(
        "Max reassignments for one task:",
        max_task_reassignments,
    )

    print(
        "Max decisions from one root trigger:",
        max_root_reassignments,
    )

    print(
        "Max same task under same root:",
        max_same_task_same_root,
    )

    print()

    print(
        "Top reassigned tasks:"
    )

    for (
        task_id,
        count,
    ) in task_reassignment_counts.most_common(
        10
    ):

        print(
            f"  {task_id}: {count}"
        )

    print()

    print(
        "Top root triggers:"
    )

    for (
        task_id,
        count,
    ) in root_reassignment_counts.most_common(
        10
    ):

        print(
            f"  {task_id}: {count}"
        )

    # 同一條 Cascade 裡，
    # 同一 Task 在同一 Robot 只允許重新評估一次。
    #
    # 目前只有 3 台 Robot，
    # 所以同一 Task / Root
    # 理論上最多經過 3 個不同 Robot state。
    assert (
        max_same_task_same_root
        <=
        core.robot_count
    )

    print(
        "Original Tasks:",
        core.task_count,
    )

    print(
        "RL Decision Steps:",
        step_count,
    )

    print(
        "Reassignment Decisions:",
        reassignment_decisions,
    )

    print(
        "Reassignment Events:",
        len(
            core.reassignment_events
        ),
    )

    print(
        "Assigned Tasks:",
        core.assigned_task_count,
    )

    print(
        "Completed Tasks:",
        core.completed_task_count,
    )

    assert (
        core.assigned_task_count
        ==
        core.task_count
    )

    assert (
        core.completed_task_count
        ==
        core.task_count
    )

    assert (
        len(
            core.execution_records
        )
        ==
        core.task_count
    )

    # 每次 Reassignment 都是額外的 RL Decision。
    assert (
        step_count
        ==
        core.task_count
        +
        reassignment_decisions
    )

    assert (
        reassignment_decisions
        ==
        len(
            core.reassignment_events
        )
    )

    print(
        "Dynamic episode sanity test: PASS"
    )


if __name__ == "__main__":

    test_dynamic_episode()