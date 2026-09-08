#!/usr/bin/env python3

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


def main():

    scenario = (
        generate_random_scenario(

            task_count=5,

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

    env = HospitalRLEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    env.reset()

    # ======================================================
    # Case 1
    #
    # Near
    # No Workload
    # Normal Battery
    #
    # distance_cost:
    #
    # 10 / 100
    # = 0.1
    #
    # reward:
    #
    # -0.1
    # ======================================================

    near_reward = (
        env._calculate_reward(

            travel_distance=10.0,

            workload_before_task=0.0,

            battery=0.90,
        )
    )

    # ======================================================
    # Case 2
    #
    # Far
    #
    # distance_cost:
    #
    # 60 / 100
    # = 0.6
    #
    # reward:
    #
    # -0.6
    # ======================================================

    far_reward = (
        env._calculate_reward(

            travel_distance=60.0,

            workload_before_task=0.0,

            battery=0.90,
        )
    )

    # ======================================================
    # Case 3
    #
    # High Workload
    #
    # workload_cost:
    #
    # 300 / (300 + 300)
    # = 0.5
    #
    # total:
    #
    # distance = 0.1
    # workload = 0.5
    #
    # reward:
    #
    # -(0.1 + 0.5)
    # = -0.6
    # ======================================================

    high_workload_reward = (
        env._calculate_reward(

            travel_distance=10.0,

            workload_before_task=300.0,

            battery=0.90,
        )
    )

    # ======================================================
    # Case 4
    #
    # Low Battery
    #
    # distance = 0.1
    # battery penalty = 0.3
    #
    # reward:
    #
    # -(0.1 + 0.3)
    # = -0.4
    # ======================================================

    low_battery_reward = (
        env._calculate_reward(

            travel_distance=10.0,

            workload_before_task=0.0,

            battery=0.15,
        )
    )

    # ======================================================
    # Case 5
    #
    # Far + High Workload + Low Battery
    #
    # distance = 0.6
    # workload = 0.5
    # battery = 0.3
    #
    # total:
    #
    # 1.4
    #
    # reward:
    #
    # -1.4
    # ======================================================

    worst_reward = (
        env._calculate_reward(

            travel_distance=60.0,

            workload_before_task=300.0,

            battery=0.15,
        )
    )

    # ======================================================
    # Output
    # ======================================================

    print("=" * 80)
    print("REWARD V3 SANITY TEST")
    print("=" * 80)

    print(
        "Near + normal battery + no workload:",
        round(
            near_reward,
            3,
        ),
    )

    print(
        "Far:",
        round(
            far_reward,
            3,
        ),
    )

    print(
        "High workload:",
        round(
            high_workload_reward,
            3,
        ),
    )

    print(
        "Low battery:",
        round(
            low_battery_reward,
            3,
        ),
    )

    print(
        "Far + high workload + low battery:",
        round(
            worst_reward,
            3,
        ),
    )

    print()

    # ======================================================
    # Exact Value Tests
    # ======================================================

    assert abs(
        near_reward
        -
        (-0.1)
    ) < 1e-6

    assert abs(
        far_reward
        -
        (-0.6)
    ) < 1e-6

    assert abs(
        high_workload_reward
        -
        (-0.6)
    ) < 1e-6

    assert abs(
        low_battery_reward
        -
        (-0.4)
    ) < 1e-6

    assert abs(
        worst_reward
        -
        (-1.4)
    ) < 1e-6

    # ======================================================
    # Preference Tests
    # ======================================================

    assert (
        near_reward
        >
        far_reward
    )

    assert (
        near_reward
        >
        high_workload_reward
    )

    assert (
        near_reward
        >
        low_battery_reward
    )

    assert (
        low_battery_reward
        >
        worst_reward
    )

    # ======================================================
    # Result
    # ======================================================

    print(
        "Distance preference: PASS"
    )

    print(
        "Workload preference: PASS"
    )

    print(
        "Battery preference: PASS"
    )

    print(
        "Combined penalty test: PASS"
    )

    print()

    print(
        "REWARD V3 SANITY TEST: PASS"
    )


if __name__ == "__main__":
    main()