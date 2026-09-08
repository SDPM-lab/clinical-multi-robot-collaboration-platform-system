#!/usr/bin/env python3

import os
from collections import Counter

from sb3_contrib import MaskablePPO

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


# ==========================================================
# Diagnostic Scenario
# ==========================================================

TASK_COUNT = 100
LOAD = "medium"
SEED = 5000


# ==========================================================
# Paths
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RL_DIR = os.path.join(
    os.path.dirname(SCRIPT_DIR),
    "rl",
)

MODEL_DIR = os.path.join(
    RL_DIR,
    "models",
)

OLD_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_50k.zip",
)

MULTIDIST_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_multidist_100k.zip",
)

BALANCED_MULTIDIST_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_balanced_multidist_100k.zip",
)

WARMSTART_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "maskable_ppo_hospital_33d_reward_v3_warmstart_balanced_ft50k.zip",
)


# ==========================================================
# Run PPO
# ==========================================================

def run_policy(
    model,
    label,
):

    scenario = generate_random_scenario(
        task_count=TASK_COUNT,
        seed=SEED,
        load=LOAD,
        battery_profile=BATTERY_PROFILE,
        capability_profile=CAPABILITY_PROFILE,
    )

    env = HospitalGymEnv(
        scenario=scenario,
        robot_speed=ROBOT_SPEED,
        service_time=SERVICE_TIME,
    )

    observation, info = env.reset()

    action_counts = Counter()

    step_count = 0

    while True:

        mask = env.action_masks()

        action, _ = model.predict(
            observation,
            action_masks=mask,
            deterministic=True,
        )

        action = int(action)

        action_counts[action] += 1

        observation, reward, terminated, truncated, info = (
            env.step(action)
        )

        step_count += 1

        if terminated or truncated:
            break

    core = env.core_env

    execution_records = core.execution_records

    robot_completion_counts = Counter(
        record.robot_id
        for record
        in execution_records
    )

    simulation_end_time = (
        core.get_simulation_end_time()
    )

    print()
    print("=" * 100)
    print(label)
    print("=" * 100)

    print(
        "Task Count:",
        TASK_COUNT,
    )

    print(
        "Load:",
        LOAD,
    )

    print(
        "Seed:",
        SEED,
    )

    print(
        "Decision Steps:",
        step_count,
    )

    print(
        "Simulation End Time:",
        f"{simulation_end_time:.2f}",
    )

    print()

    # ======================================================
    # Action Distribution
    # ======================================================

    print(
        "ACTION DISTRIBUTION"
    )

    print("-" * 100)

    for action_index in sorted(
        action_counts
    ):

        count = action_counts[
            action_index
        ]

        percentage = (
            count
            /
            step_count
            *
            100.0
        )

        print(
            f"action {action_index}: "
            f"{count:3d}"
            f" | "
            f"{percentage:6.2f}%"
        )

    print()

    # ======================================================
    # Robot State
    # ======================================================

    print(
        "ROBOT STATE SUMMARY"
    )

    print("-" * 100)

    for (
        robot_id,
        sim_state,
    ) in core.robot_states.items():

        completed_tasks = (
            robot_completion_counts[
                robot_id
            ]
        )

        if simulation_end_time > 0.0:

            utilization = (
                sim_state.total_busy_time
                /
                simulation_end_time
            )

        else:

            utilization = 0.0

        print(
            f"{robot_id}"
        )

        print(
            "  completed_tasks :",
            completed_tasks,
        )

        print(
            "  total_distance  :",
            f"{sim_state.total_distance:.2f}",
        )

        print(
            "  total_busy_time :",
            f"{sim_state.total_busy_time:.2f}",
        )

        print(
            "  utilization     :",
            f"{utilization:.3f}",
        )

        print(
            "  final_position  :",
            f"({sim_state.x:.2f}, "
            f"{sim_state.y:.2f})",
        )

        print()

    # ======================================================
    # Waiting Time
    # ======================================================

    waiting_times = [
        record.waiting_time
        for record
        in execution_records
    ]

    average_waiting = (
        sum(waiting_times)
        /
        len(waiting_times)
    )

    print(
        "Average Waiting Time:",
        f"{average_waiting:.2f}",
    )

    print(
        "Completed Records:",
        len(execution_records),
    )

    env.close()


# ==========================================================
# Main
# ==========================================================

def main():

    for path in [
        OLD_MODEL_PATH,
        MULTIDIST_MODEL_PATH,
        BALANCED_MULTIDIST_MODEL_PATH,
        WARMSTART_MODEL_PATH,
    ]:

        if not os.path.exists(
            path
        ):

            raise FileNotFoundError(
                path
            )

    print("=" * 100)

    print(
        "RL POLICY COLLAPSE DIAGNOSTIC"
    )

    print("=" * 100)

    print(
        "Scenario:",
        f"{TASK_COUNT} tasks"
        f" / {LOAD}"
        f" / seed {SEED}",
    )

    old_model = MaskablePPO.load(
        OLD_MODEL_PATH,
        device="cpu",
    )

    multidist_model = MaskablePPO.load(
        MULTIDIST_MODEL_PATH,
        device="cpu",
    )

    balanced_multidist_model = MaskablePPO.load(
        BALANCED_MULTIDIST_MODEL_PATH,
        device="cpu",
    )

    warmstart_model = MaskablePPO.load(
        WARMSTART_MODEL_PATH,
        device="cpu",
    )

    run_policy(
        old_model,
        "OLD PPO 50K",
    )

    run_policy(
        multidist_model,
        "MULTIDIST PPO 100K",
    )

    run_policy(
        balanced_multidist_model,
        "BALANCED MULTIDIST PPO 100K",
    )

    run_policy(
        warmstart_model,
        "WARMSTART BALANCED PPO FT50K",
    )


if __name__ == "__main__":
    main()