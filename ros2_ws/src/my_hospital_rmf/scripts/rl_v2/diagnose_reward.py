#!/usr/bin/env python3

import argparse
import statistics

from collections import defaultdict

from sb3_contrib import MaskablePPO

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.run_baselines import (
    BASELINE_METHODS,
    run_baseline,
)

from experiment_v2.run_multi_seed import (
    extract_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from scheduler_v2.projection import (
    project_task_on_robot,
)

from rl_v2.env import (
    HospitalRLEnv,
)

from rl_v2.reward import (
    calculate_assignment_reward,
)


# ==========================================================
# Reward-Greedy Policy
# ==========================================================

def run_reward_greedy(
    scenario,
    seed: int,
):

    env = HospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = env.reset(
        seed=seed
    )

    terminated = False

    action_counts = {
        robot_id: 0
        for robot_id
        in env.robot_ids
    }

    while not terminated:

        kernel = env.kernel

        task = kernel.current_task

        mask = env.action_masks()

        candidates = []

        for action, robot_id in enumerate(
            env.robot_ids
        ):

            if not mask[action]:
                continue

            runtime = (
                kernel.runtimes[
                    robot_id
                ]
            )

            projection = (
                project_task_on_robot(
                    task=task,
                    runtime=runtime,
                    places=(
                        kernel
                        .scenario
                        .places
                    ),
                    current_time=(
                        kernel.current_time
                    ),
                    service_time_seconds=(
                        kernel
                        .scenario
                        .service_time_seconds
                    ),
                )
            )

            reward = (
                calculate_assignment_reward(
                    task=task,
                    projection=projection,
                ).reward
            )

            candidates.append(
                (
                    reward,
                    action,
                    robot_id,
                )
            )

        if not candidates:
            raise RuntimeError(
                "No feasible action"
            )

        # Reward 最大 = cost 最低
        (
            best_reward,
            best_action,
            best_robot,
        ) = max(
            candidates,
            key=lambda item: (
                item[0],
                -item[1],
            ),
        )

        action_counts[
            best_robot
        ] += 1

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            best_action
        )

        if truncated:
            raise RuntimeError(
                "Unexpected truncation"
            )

    result = (
        env.get_simulation_result()
    )

    return (
        calculate_metrics(
            result
        ),
        action_counts,
    )


# ==========================================================
# PPO Policy
# ==========================================================

def run_ppo(
    model,
    scenario,
    seed: int,
    deterministic: bool,
):

    env = HospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = env.reset(
        seed=seed
    )

    terminated = False

    action_counts = {
        robot_id: 0
        for robot_id
        in env.robot_ids
    }

    while not terminated:

        mask = env.action_masks()

        action, _ = model.predict(
            observation,
            action_masks=mask,
            deterministic=deterministic,
        )

        action = int(action)

        robot_id = (
            env.robot_ids[
                action
            ]
        )

        action_counts[
            robot_id
        ] += 1

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        if truncated:
            raise RuntimeError(
                "Unexpected truncation"
            )

    return (
        calculate_metrics(
            env.get_simulation_result()
        ),
        action_counts,
    )


# ==========================================================
# Metric Helper
# ==========================================================

def metric_values(
    metrics,
):

    return {
        "wait":
            metrics
            .average_task_waiting_time,

        "emergency":
            metrics
            .waiting_time_by_priority
            .get(3),

        "completion":
            metrics
            .average_task_completion_time,

        "makespan":
            metrics.makespan,

        "distance":
            metrics.total_travel_distance,

        "success":
            metrics.task_success_rate,

        "jain":
            metrics.jain_fairness_index,
    }


# ==========================================================
# Main
# ==========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=7800,
    )

    parser.add_argument(
        "--seed-end",
        type=int,
        default=7819,
    )

    args = parser.parse_args()

    model = MaskablePPO.load(
        args.model,
        device="cpu",
    )

    results = defaultdict(
        lambda: defaultdict(list)
    )

    action_totals = defaultdict(
        lambda: defaultdict(int)
    )

    methods = [
        "weighted",
        "dynamic",
        "reward_greedy",
        "ppo_deterministic",
        "ppo_stochastic",
    ]

    for seed in range(
        args.seed_start,
        args.seed_end + 1,
    ):

        print(
            f"seed={seed}"
        )

        scenario = (
            generate_hospital_scenario(
                seed=seed,
                task_count=50,
            )
        )

        # ==============================================
        # Weighted
        # ==============================================

        weighted = run_baseline(
            scenario=scenario,
            method=(
                BASELINE_METHODS[2]
            ),
            seed=seed,
        )

        for key, value in metric_values(
            weighted.metrics
        ).items():

            if value is not None:
                results[
                    "weighted"
                ][key].append(
                    float(value)
                )

        # ==============================================
        # Dynamic Weighted
        # ==============================================

        dynamic = run_baseline(
            scenario=scenario,
            method=(
                BASELINE_METHODS[3]
            ),
            seed=seed,
        )

        for key, value in metric_values(
            dynamic.metrics
        ).items():

            if value is not None:
                results[
                    "dynamic"
                ][key].append(
                    float(value)
                )

        # ==============================================
        # Reward Greedy
        # ==============================================

        (
            greedy_metrics,
            greedy_actions,
        ) = run_reward_greedy(
            scenario=scenario,
            seed=seed,
        )

        for key, value in metric_values(
            greedy_metrics
        ).items():

            if value is not None:
                results[
                    "reward_greedy"
                ][key].append(
                    float(value)
                )

        for robot_id, count in (
            greedy_actions.items()
        ):

            action_totals[
                "reward_greedy"
            ][robot_id] += count

        # ==============================================
        # PPO deterministic
        # ==============================================

        (
            ppo_det_metrics,
            ppo_det_actions,
        ) = run_ppo(
            model=model,
            scenario=scenario,
            seed=seed,
            deterministic=True,
        )

        for key, value in metric_values(
            ppo_det_metrics
        ).items():

            if value is not None:
                results[
                    "ppo_deterministic"
                ][key].append(
                    float(value)
                )

        for robot_id, count in (
            ppo_det_actions.items()
        ):

            action_totals[
                "ppo_deterministic"
            ][robot_id] += count

        # ==============================================
        # PPO stochastic
        # ==============================================

        (
            ppo_sto_metrics,
            ppo_sto_actions,
        ) = run_ppo(
            model=model,
            scenario=scenario,
            seed=seed,
            deterministic=False,
        )

        for key, value in metric_values(
            ppo_sto_metrics
        ).items():

            if value is not None:
                results[
                    "ppo_stochastic"
                ][key].append(
                    float(value)
                )

        for robot_id, count in (
            ppo_sto_actions.items()
        ):

            action_totals[
                "ppo_stochastic"
            ][robot_id] += count

    # ======================================================
    # Summary
    # ======================================================

    print()
    print(
        "=" * 110
    )
    print(
        "REWARD / POLICY DIAGNOSTIC"
    )
    print(
        "=" * 110
    )

    print(
        f"{'Method':<22}"
        f"{'Wait':>11}"
        f"{'Emer':>11}"
        f"{'Complete':>12}"
        f"{'Makespan':>12}"
        f"{'Distance':>12}"
        f"{'Success':>10}"
        f"{'Jain':>9}"
    )

    print(
        "-" * 110
    )

    for method in methods:

        def mean(
            key,
        ):

            values = (
                results[
                    method
                ][
                    key
                ]
            )

            if not values:
                return float(
                    "nan"
                )

            return statistics.mean(
                values
            )

        print(
            f"{method:<22}"
            f"{mean('wait'):>11.3f}"
            f"{mean('emergency'):>11.3f}"
            f"{mean('completion'):>12.3f}"
            f"{mean('makespan'):>12.3f}"
            f"{mean('distance'):>12.3f}"
            f"{mean('success'):>10.3f}"
            f"{mean('jain'):>9.3f}"
        )

    # ======================================================
    # Action Distribution
    # ======================================================

    print()
    print(
        "=" * 90
    )
    print(
        "ACTION DISTRIBUTION"
    )
    print(
        "=" * 90
    )

    for method in [
        "reward_greedy",
        "ppo_deterministic",
        "ppo_stochastic",
    ]:

        counts = (
            action_totals[
                method
            ]
        )

        total = sum(
            counts.values()
        )

        print()
        print(
            method
        )

        for robot_id in sorted(
            counts
        ):

            count = (
                counts[
                    robot_id
                ]
            )

            ratio = (
                0.0
                if total == 0
                else
                count / total
            )

            print(
                f"  {robot_id:<20}"
                f"{count:>6}"
                f"  "
                f"{ratio:>7.2%}"
            )


if __name__ == "__main__":
    main()
