#!/usr/bin/env python3

import os
from collections import Counter

from sb3_contrib import (
    MaskablePPO,
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
    os.path.dirname(
        SCRIPT_DIR
    ),
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


# ==========================================================
# Create Fresh Environment
#
# 每次都重新產生完全相同的 scenario。
#
# 這樣我們可以：
#
# 1. Replay 過去 action
# 2. 在目前 decision state 測試每個合法 action
# 3. 取得 Environment 真正回傳的 immediate reward
#
# 不需要自己重新實作 Reward v3。
# ==========================================================

def create_env():

    scenario = (
        generate_random_scenario(

            task_count=(
                TASK_COUNT
            ),

            seed=(
                SEED
            ),

            load=(
                LOAD
            ),

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    env = (
        HospitalGymEnv(

            scenario=(
                scenario
            ),

            robot_speed=(
                ROBOT_SPEED
            ),

            service_time=(
                SERVICE_TIME
            ),
        )
    )

    return env


# ==========================================================
# Replay To Current State
#
# action_history:
#
# 已經實際執行過的 action sequence。
#
# 我們建立新的環境後，
# 完整 replay 一次，
# 就可以回到相同 decision state。
# ==========================================================

def replay_to_state(
    action_history,
):

    env = (
        create_env()
    )

    observation, info = (
        env.reset()
    )

    for action in (
        action_history
    ):

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

        if (
            terminated
            or truncated
        ):

            raise RuntimeError(
                "Episode terminated during replay."
            )

    return (
        env,
        observation,
    )


# ==========================================================
# Evaluate Immediate Reward
#
# 在「完全相同的 current state」下，
# 分別試每一個合法 action。
#
# 回傳：
#
# action -> immediate reward
# ==========================================================

def evaluate_valid_actions(
    action_history,
):

    reference_env, _ = (
        replay_to_state(
            action_history
        )
    )

    mask = (
        reference_env.action_masks()
    )

    valid_actions = [
        index
        for index, valid
        in enumerate(mask)
        if valid
    ]

    reference_env.close()

    rewards = {}

    for action in (
        valid_actions
    ):

        candidate_env, _ = (
            replay_to_state(
                action_history
            )
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = (
            candidate_env.step(
                action
            )
        )

        rewards[
            action
        ] = float(
            reward
        )

        candidate_env.close()

    return (
        valid_actions,
        rewards,
    )


# ==========================================================
# Robot Label
# ==========================================================

def action_label(
    action,
):

    labels = {
        0: "robot_1",
        1: "robot_2",
        2: "robot_3",
    }

    return labels.get(
        action,
        f"action_{action}",
    )


# ==========================================================
# Run Policy Diagnostic
# ==========================================================

def run_policy(
    model,
    label,
):

    env = (
        create_env()
    )

    observation, info = (
        env.reset()
    )

    action_history = []

    policy_action_counts = Counter()

    reward_best_counts = Counter()

    agreement_count = 0

    valid_decision_count = 0

    total_regret = 0.0

    disagreement_records = []

    step_index = 0

    while True:

        # ==================================================
        # Current Valid Actions
        # ==================================================

        mask = (
            env.action_masks()
        )

        valid_actions = [
            index
            for index, valid
            in enumerate(mask)
            if valid
        ]

        # ==================================================
        # Policy Action
        # ==================================================

        (
            action,
            _
        ) = (
            model.predict(

                observation,

                action_masks=(
                    mask
                ),

                deterministic=True,
            )
        )

        action = int(
            action
        )

        policy_action_counts[
            action
        ] += 1

        # ==================================================
        # Counterfactual Immediate Rewards
        # ==================================================

        (
            diagnostic_valid_actions,
            action_rewards,
        ) = (
            evaluate_valid_actions(
                action_history
            )
        )

        if (
            set(
                diagnostic_valid_actions
            )
            !=
            set(
                valid_actions
            )
        ):

            raise RuntimeError(
                "Replay action mask mismatch."
            )

        # ==================================================
        # Reward-best Action
        #
        # Reward 是負成本，
        # 所以數值越大越好：
        #
        # -0.3 > -0.8
        # ==================================================

        best_reward = max(
            action_rewards.values()
        )

        tolerance = 1e-9

        best_actions = [
            candidate_action

            for (
                candidate_action,
                candidate_reward,
            )
            in action_rewards.items()

            if abs(
                candidate_reward
                -
                best_reward
            )
            <= tolerance
        ]

        for best_action in (
            best_actions
        ):

            reward_best_counts[
                best_action
            ] += (
                1.0
                /
                len(
                    best_actions
                )
            )

        chosen_reward = (
            action_rewards[
                action
            ]
        )

        regret = (
            best_reward
            -
            chosen_reward
        )

        total_regret += (
            regret
        )

        valid_decision_count += 1

        # ==================================================
        # Agreement
        # ==================================================

        if action in (
            best_actions
        ):

            agreement_count += 1

        else:

            disagreement_records.append(
                {
                    "step":
                        step_index,

                    "chosen":
                        action,

                    "chosen_reward":
                        chosen_reward,

                    "best_actions":
                        list(
                            best_actions
                        ),

                    "best_reward":
                        best_reward,

                    "regret":
                        regret,

                    "valid_actions":
                        list(
                            valid_actions
                        ),

                    "action_rewards":
                        dict(
                            action_rewards
                        ),
                }
            )

        # ==================================================
        # Execute Real Policy Action
        # ==================================================

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

        action_history.append(
            action
        )

        step_index += 1

        if (
            terminated
            or truncated
        ):

            break

    # ======================================================
    # Final Environment Metrics
    # ======================================================

    execution_records = (
        env.core_env
        .execution_records
    )

    waiting_times = [
        record.waiting_time
        for record
        in execution_records
    ]

    average_waiting_time = (
        sum(
            waiting_times
        )
        /
        len(
            waiting_times
        )
    )

    simulation_end_time = (
        env.core_env
        .get_simulation_end_time()
    )

    # ======================================================
    # Summary
    # ======================================================

    agreement_rate = (
        agreement_count
        /
        valid_decision_count
    )

    average_regret = (
        total_regret
        /
        valid_decision_count
    )

    print()

    print("=" * 110)

    print(
        label
    )

    print("=" * 110)

    print(
        "Decision Steps:",
        valid_decision_count,
    )

    print(
        "Average Waiting Time:",
        f"{average_waiting_time:.2f}",
    )

    print(
        "Makespan:",
        f"{simulation_end_time:.2f}",
    )

    print()

    # ======================================================
    # Policy Action Distribution
    # ======================================================

    print(
        "POLICY ACTION DISTRIBUTION"
    )

    print("-" * 110)

    for action in range(
        3
    ):

        count = (
            policy_action_counts[
                action
            ]
        )

        percentage = (
            count
            /
            valid_decision_count
            *
            100.0
        )

        print(
            f"{action_label(action):<10}"
            f" | count={count:>3}"
            f" | {percentage:>6.2f}%"
        )

    # ======================================================
    # Reward-best Distribution
    # ======================================================

    print()

    print(
        "IMMEDIATE REWARD-BEST DISTRIBUTION"
    )

    print("-" * 110)

    for action in range(
        3
    ):

        count = (
            reward_best_counts[
                action
            ]
        )

        percentage = (
            count
            /
            valid_decision_count
            *
            100.0
        )

        print(
            f"{action_label(action):<10}"
            f" | count={count:>6.2f}"
            f" | {percentage:>6.2f}%"
        )

    # ======================================================
    # Agreement
    # ======================================================

    print()

    print(
        "POLICY vs IMMEDIATE REWARD"
    )

    print("-" * 110)

    print(
        "Reward-best agreement:",
        f"{agreement_count}"
        f"/"
        f"{valid_decision_count}",
        f"({agreement_rate * 100.0:.2f}%)",
    )

    print(
        "Average immediate regret:",
        f"{average_regret:.6f}",
    )

    print(
        "Disagreement count:",
        len(
            disagreement_records
        ),
    )

    # ======================================================
    # Largest Disagreements
    # ======================================================

    print()

    print(
        "TOP IMMEDIATE-REWARD DISAGREEMENTS"
    )

    print("-" * 110)

    disagreement_records.sort(
        key=lambda row: (
            row[
                "regret"
            ]
        ),
        reverse=True,
    )

    top_records = (
        disagreement_records[
            :15
        ]
    )

    if not top_records:

        print(
            "No disagreements."
        )

    else:

        for row in (
            top_records
        ):

            reward_text = " | ".join(
                (
                    f"{action_label(candidate_action)}="
                    f"{candidate_reward:.4f}"
                )

                for (
                    candidate_action,
                    candidate_reward,
                )
                in sorted(
                    row[
                        "action_rewards"
                    ].items()
                )
            )

            best_text = ",".join(
                action_label(
                    action
                )
                for action
                in row[
                    "best_actions"
                ]
            )

            print(
                f"step={row['step']:>3}"
                f" | chosen="
                f"{action_label(row['chosen']):<7}"
                f" | best="
                f"{best_text:<15}"
                f" | regret="
                f"{row['regret']:.4f}"
                f" | "
                f"{reward_text}"
            )

    env.close()

    return {
        "label":
            label,

        "agreement_rate":
            agreement_rate,

        "average_regret":
            average_regret,

        "average_waiting_time":
            average_waiting_time,

        "makespan":
            simulation_end_time,

        "policy_action_counts":
            policy_action_counts,

        "reward_best_counts":
            reward_best_counts,
    }


# ==========================================================
# Main
# ==========================================================

def main():

    for model_path in [
        OLD_MODEL_PATH,
        MULTIDIST_MODEL_PATH,
        BALANCED_MULTIDIST_MODEL_PATH,
    ]:

        if not os.path.exists(
            model_path
        ):

            raise FileNotFoundError(
                model_path
            )

    print("=" * 110)

    print(
        "RL ACTION PREFERENCE DIAGNOSTIC"
    )

    print("=" * 110)

    print(
        "Scenario:",
        f"{TASK_COUNT} tasks"
        f" / {LOAD}"
        f" / seed {SEED}",
    )

    print()

    print(
        "Question:"
    )

    print(
        "Does the PPO policy choose the action "
        "with the best immediate environment reward?"
    )

    # ======================================================
    # Load Models
    # ======================================================

    old_model = (
        MaskablePPO.load(

            OLD_MODEL_PATH,

            device="cpu",
        )
    )

    multidist_model = (
        MaskablePPO.load(

            MULTIDIST_MODEL_PATH,

            device="cpu",
        )
    )

    balanced_multidist_model = (
        MaskablePPO.load(

            BALANCED_MULTIDIST_MODEL_PATH,

            device="cpu",
        )
    )

    # ======================================================
    # Run Diagnostics
    # ======================================================

    old_result = (
        run_policy(

            old_model,

            "OLD PPO 50K",
        )
    )

    multidist_result = (
        run_policy(

            multidist_model,

            "MULTIDIST PPO 100K",
        )
    )

    balanced_multidist_result = (
        run_policy(

            balanced_multidist_model,

            "BALANCED MULTIDIST PPO 100K",
        )
    )

    # ======================================================
    # Final Comparison
    # ======================================================

    print()

    print("=" * 110)

    print(
        "FINAL ACTION-PREFERENCE COMPARISON"
    )

    print("=" * 110)

    print(
        f"{'Model':<25}"
        f" | "
        f"{'Agreement':>12}"
        f" | "
        f"{'Avg Regret':>12}"
        f" | "
        f"{'Avg Wait':>12}"
        f" | "
        f"{'Makespan':>12}"
    )

    print("-" * 110)

    for result in [
        old_result,
        multidist_result,
        balanced_multidist_result,
    ]:29 36 43

        print(
            f"{result['label']:<25}"
            f" | "
            f"{result['agreement_rate'] * 100.0:>11.2f}%"
            f" | "
            f"{result['average_regret']:>12.6f}"
            f" | "
            f"{result['average_waiting_time']:>12.2f}"
            f" | "
            f"{result['makespan']:>12.2f}"
        )


if __name__ == "__main__":
    main()