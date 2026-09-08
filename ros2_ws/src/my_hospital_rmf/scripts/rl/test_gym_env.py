#!/usr/bin/env python3

import numpy as np

from gymnasium.utils.env_checker import (
    check_env,
)

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


def main():

    # ======================================================
    # 建立 Scenario
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
    # 建立 Gym Environment
    # ======================================================

    env = HospitalGymEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    print("=" * 100)
    print("GYM ENVIRONMENT TEST")
    print("=" * 100)

    print(
        "Observation Space:",
        env.observation_space,
    )

    print(
        "Action Space:",
        env.action_space,
    )

    print()

    # ======================================================
    # Observation Space
    #
    # Task = 6
    #
    # Robot = 8 × 3
    #
    # Total = 30
    # ======================================================

    expected_observation_size = (
        6
        +
        env.core_env.robot_count
        *
        9
    )

    assert (
        env.observation_space.shape
        ==
        (
            expected_observation_size,
        )
    )

    print(
        "Observation space size test: PASS"
    )

    # ======================================================
    # Action Space
    # ======================================================

    assert (
        env.action_space.n
        ==
        env.core_env.robot_count
    )

    print(
        "Action space size test: PASS"
    )

    print()

    # ======================================================
    # Gymnasium API Check
    # ======================================================

    check_env(
        env,
        skip_render_check=True,
    )

    print(
        "Gymnasium check_env: PASS"
    )

    print()

    # ======================================================
    # Manual Episode Test
    # ======================================================

    (
        observation,
        info,
    ) = (
        env.reset(
            seed=42
        )
    )

    print(
        "Observation shape:",
        observation.shape,
    )

    print(
        "Observation min:",
        round(
            float(
                observation.min()
            ),
            4,
        ),
    )

    print(
        "Observation max:",
        round(
            float(
                observation.max()
            ),
            4,
        ),
    )

    assert (
        observation.shape
        ==
        (
            expected_observation_size,
        )
    )

    assert (
        observation.min()
        >= 0.0
    )

    assert (
        observation.max()
        <= 1.0
    )

    print(
        "Observation range test: PASS"
    )

    print()

    # ======================================================
    # Episode
    #
    # 測試階段固定選第一個合法 Action。
    #
    # 這不是 PPO。
    # ======================================================

    step_count = 0

    while True:

        step_count += 1

        mask = (
            env.action_masks()
        )

        # --------------------------------------------------
        # Mask Shape
        # --------------------------------------------------

        assert (
            mask.shape
            ==
            (
                env.core_env.robot_count,
            )
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
                "No valid actions."
            )

        action = int(
            valid_actions[
                0
            ]
        )

        (
            observation,
            reward,
            terminated,
            truncated,
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
            f" | reward={reward:.3f}"
        )

        # --------------------------------------------------
        # Observation Shape
        # --------------------------------------------------

        assert (
            observation.shape
            ==
            (
                expected_observation_size,
            )
        )

        # --------------------------------------------------
        # Observation Range
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

        if (
            terminated
            or truncated
        ):

            break

    # ======================================================
    # Final Information
    # ======================================================

    print()

    print("=" * 100)
    print("EPISODE COMPLETED")
    print("=" * 100)

    print(
        "Assigned Tasks:",
        info[
            "assigned_tasks"
        ],
    )

    print(
        "Completed Tasks:",
        info[
            "completed_tasks"
        ],
    )

    print(
        "Simulation End Time:",
        round(
            info[
                "simulation_end_time"
            ],
            2,
        ),
    )

    print(
        "Total Reward:",
        round(
            info[
                "total_reward"
            ],
            3,
        ),
    )

    # ======================================================
    # Final Assertions
    # ======================================================

    assert (
        info[
            "assigned_tasks"
        ]
        ==
        10
    )

    assert (
        info[
            "completed_tasks"
        ]
        ==
        10
    )

    assert (
        step_count
        ==
        10
    )

    print()

    print(
        "Assigned task count test: PASS"
    )

    print(
        "Completed task count test: PASS"
    )

    print(
        "Step count test: PASS"
    )

    print()

    print(
        "GYM ENV TEST: PASS"
    )


if __name__ == "__main__":
    main()