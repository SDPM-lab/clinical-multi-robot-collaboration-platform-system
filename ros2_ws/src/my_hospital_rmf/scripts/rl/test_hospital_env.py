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

from rl.hospital_env import (
    HospitalRLEnv,
)


# ==========================================================
# RL Core Environment Test
#
# 目的：
#
# 1. 確認 Observation 維度
# 2. 確認 Action Mask
# 3. 確認 Busy Robot 仍可被選
# 4. 確認每次 Step 只做 Assignment
# 5. 確認 Robot Local Priority Queue 正常執行
# 6. 確認最終 execution_records 正確產生
#
# 測試階段：
#
# 每一步固定選「第一個合法 Action」。
#
# 注意：
# 這不是 PPO。
# ==========================================================


def main():

    # ======================================================
    # 1. 建立測試 Scenario
    # ======================================================

    scenario = (
        generate_random_scenario(

            task_count=10,

            seed=42,

            load="medium",

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    # ======================================================
    # 2. 建立 Core Environment
    # ======================================================

    env = HospitalRLEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    # ======================================================
    # 3. Reset
    # ======================================================

    observation = (
        env.reset()
    )

    print("=" * 100)
    print("RL ENVIRONMENT TEST")
    print("=" * 100)

    print(
        "Observation shape:",
        observation.shape,
    )

    print(
        "Robot IDs:",
        env.robot_ids,
    )

    print(
        "Task Count:",
        env.task_count,
    )

    print()

    # ======================================================
    # Observation 應為：
    #
    # Task = 6
    #
    # Robot = 8 × robot_count
    #
    # 3 Robots：
    #
    # 6 + 3 * 8
    # =
    # 30
    # ======================================================

    expected_observation_size = (
        6
        +
        env.robot_count
        *
        9
    )

    assert (
        observation.shape
        ==
        (
            expected_observation_size,
        )
    )

    print(
        "Observation size test: PASS"
    )

    print()

    # ======================================================
    # 4. Assignment Loop
    # ======================================================

    step_count = 0

    while not env.done:

        step_count += 1

        # --------------------------------------------------
        # Action Mask
        #
        # True：
        # Robot Capability 相容
        #
        # Busy Robot 仍然可能是 True。
        # --------------------------------------------------

        mask = (
            env.action_masks()
        )

        valid_actions = (
            np.flatnonzero(
                mask
            )
        )

        if len(
            valid_actions
        ) == 0:

            raise RuntimeError(
                "No valid action available."
            )

        # ==================================================
        # 測試階段：
        #
        # 固定選第一個合法 Action。
        #
        # 這只是測環境邏輯，
        # 還不是 PPO。
        # ==================================================

        action = int(
            valid_actions[
                0
            ]
        )

        (
            observation,
            reward,
            done,
            info,
        ) = (
            env.step(
                action
            )
        )

        print(
            f"Step {step_count:02d}"
            f" | decision={info['decision_time']:.2f}"
            f" | task={info['task_id']}"
            f" | P={info['priority']}"
            f" | robot={info['robot_id']}"
            f" | workload={info['projected_workload_before_task']:.2f}"
            f" | queue_before={info['projected_queue_length_before_task']}"
            f" | source_dist={info['projected_distance_to_source']:.2f}"
            f" | travel={info['projected_travel_distance']:.2f}"
            f" | battery={info['battery']:.2f}"
            f" | reward={reward:.3f}"
        )

        # --------------------------------------------------
        # Observation 必須維持相同 Shape。
        # --------------------------------------------------

        assert (
            observation.shape
            ==
            (
                expected_observation_size,
            )
        )

        # --------------------------------------------------
        # Observation 正規化後應落在 0 ~ 1。
        # --------------------------------------------------

        assert (
            np.all(
                observation
                >= 0.0
            )
        )

        assert (
            np.all(
                observation
                <= 1.0
            )
        )

    # ======================================================
    # 5. Episode Completed
    # ======================================================

    print()

    print("=" * 100)
    print("EPISODE COMPLETED")
    print("=" * 100)

    print(
        "Assigned Tasks:",
        env.assigned_task_count,
    )

    print(
        "Completed Tasks:",
        env.completed_task_count,
    )

    print(
        "Total Reward:",
        round(
            env.total_reward,
            3,
        ),
    )

    print(
        "Final Simulator Time:",
        round(
            env.current_time,
            2,
        ),
    )

    print(
        "Simulation End Time:",
        round(
            env.get_simulation_end_time(),
            2,
        ),
    )

    print(
        "Observation Shape:",
        observation.shape,
    )

    # ======================================================
    # 6. Assignment / Completion 數量檢查
    # ======================================================

    assert (
        env.assigned_task_count
        ==
        env.task_count
    )

    assert (
        env.completed_task_count
        ==
        env.task_count
    )

    assert (
        len(
            env.execution_records
        )
        ==
        env.task_count
    )

    print()

    print(
        "Assignment count test: PASS"
    )

    print(
        "Completion count test: PASS"
    )

    print(
        "Execution record count test: PASS"
    )

    # ======================================================
    # 7. Final Execution Records
    #
    # 這裡才是真正的：
    #
    # start_time
    # completion_time
    # waiting_time
    #
    # 因為 Task 在 Assignment 後，
    # 還可能被後到的高 Priority Task 插隊。
    # ======================================================

    print()

    print("=" * 100)
    print("FINAL EXECUTION RECORDS")
    print("=" * 100)

    records = sorted(

        env.execution_records,

        key=lambda record:
            (
                record.start_time,
                record.robot_id,
            ),
    )

    for record in (
        records
    ):

        print(
            f"{record.task_id}"
            f" | P={record.priority}"
            f" | robot={record.robot_id}"
            f" | arrival={record.arrival_time:.2f}"
            f" | start={record.start_time:.2f}"
            f" | complete={record.completion_time:.2f}"
            f" | wait={record.waiting_time:.2f}"
            f" | service={record.service_time:.2f}"
            f" | distance={record.travel_distance:.2f}"
        )

    # ======================================================
    # 8. Execution Time Sanity Check
    # ======================================================

    for record in (
        records
    ):

        assert (
            record.start_time
            >=
            record.arrival_time
        )

        assert (
            record.completion_time
            >=
            record.start_time
        )

        assert abs(
            record.waiting_time
            -
            (
                record.start_time
                -
                record.arrival_time
            )
        ) < 1e-6

    print()

    print(
        "Execution timing sanity: PASS"
    )

    print()

    print("=" * 100)

    print(
        "RL ENV TEST: PASS"
    )


if __name__ == "__main__":
    main()