#!/usr/bin/env python3

import argparse
import statistics

import numpy as np

from sb3_contrib import MaskablePPO

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.reassignment_env import (
    ReassignmentHospitalRLEnv,
)


def run_episode(
    scenario,
    assignment_model,
    reassignment_model,
    seed,
    mode,
):

    env = ReassignmentHospitalRLEnv(
        scenario=scenario,
        assignment_policy=assignment_model,
        seed=seed,
    )

    obs, info = env.reset(
        seed=seed
    )

    # reset() 中 Frozen Assignment 已經產生的
    # system reward 也加回來，得到完整 episode return。
    total_return = float(
        info.get(
            "automatic_assignment_reward_before_first_decision",
            0.0,
        )
    )

    steps = 0

    while True:

        mask = env.action_masks()

        current_robot = (
            env.kernel
            .current_previous_robot
        )

        if mode == "stay":

            action = (
                env.robot_ids.index(
                    current_robot
                )
            )

            if not bool(
                mask[action]
            ):

                action = int(
                    np.flatnonzero(
                        mask
                    )[0]
                )

        elif mode == "deterministic":

            action, _ = (
                reassignment_model.predict(
                    obs,
                    action_masks=mask,
                    deterministic=True,
                )
            )

            action = int(
                np.asarray(
                    action
                ).reshape(-1)[0]
            )

        elif mode == "stochastic":

            action, _ = (
                reassignment_model.predict(
                    obs,
                    action_masks=mask,
                    deterministic=False,
                )
            )

            action = int(
                np.asarray(
                    action
                ).reshape(-1)[0]
            )

        else:

            raise ValueError(
                f"Unknown mode: {mode}"
            )

        (
            obs,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        total_return += float(
            reward
        )

        steps += 1

        if terminated or truncated:
            break

    result = (
        env.get_simulation_result()
    )

    metrics = (
        calculate_metrics(
            result
        )
    )

    weighted_waiting = float(
        env.kernel
        .accumulated_priority_waiting_cost
    )

    return {
        "return":
            total_return,

        "weighted_wait":
            weighted_waiting,

        "waiting":
            metrics.average_task_waiting_time,

        "emergency":
            metrics.waiting_time_by_priority.get(
                3,
                0.0,
            ),

        "completion":
            metrics.average_task_completion_time,

        "makespan":
            metrics.makespan,

        "distance":
            metrics.total_travel_distance,

        "jain":
            metrics.jain_fairness_index,

        "steps":
            steps,

        "reassign":
            metrics.reassignment_count,
    }


def mean(
    rows,
    key,
):

    return statistics.mean(
        row[key]
        for row in rows
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--assignment-model",
        default=(
            "rl_v2/models/"
            "long_horizon_ppo_102k_seed42.zip"
        ),
    )

    parser.add_argument(
        "--reassignment-model",
        default=(
            "rl_v2/models/"
            "reassignment_ppo_102k_seed42.zip"
        ),
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

    assignment_model = (
        MaskablePPO.load(
            args.assignment_model,
            device="cpu",
        )
    )

    reassignment_model = (
        MaskablePPO.load(
            args.reassignment_model,
            device="cpu",
        )
    )

    modes = (
        "stay",
        "deterministic",
        "stochastic",
    )

    results = {
        mode: []
        for mode in modes
    }

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

        for mode in modes:

            row = run_episode(
                scenario=scenario,
                assignment_model=(
                    assignment_model
                ),
                reassignment_model=(
                    reassignment_model
                ),
                seed=seed,
                mode=mode,
            )

            results[
                mode
            ].append(
                row
            )

    names = {
        "stay":
            "static_assign_stay",

        "deterministic":
            "dedicated_deterministic",

        "stochastic":
            "dedicated_stochastic",
    }

    print()
    print("=" * 145)
    print(
        "DEDICATED REASSIGNMENT OBJECTIVE DIAGNOSTIC"
    )
    print("=" * 145)

    print(
        f"{'Method':<28}"
        f"{'Return':>11}"
        f"{'WeightedWait':>15}"
        f"{'Wait':>10}"
        f"{'Emer':>10}"
        f"{'Complete':>11}"
        f"{'Makespan':>11}"
        f"{'Distance':>11}"
        f"{'Jain':>9}"
        f"{'Steps':>9}"
        f"{'Reassign':>10}"
    )

    print("-" * 145)

    for mode in modes:

        rows = results[
            mode
        ]

        print(
            f"{names[mode]:<28}"
            f"{mean(rows, 'return'):>11.3f}"
            f"{mean(rows, 'weighted_wait'):>15.3f}"
            f"{mean(rows, 'waiting'):>10.3f}"
            f"{mean(rows, 'emergency'):>10.3f}"
            f"{mean(rows, 'completion'):>11.3f}"
            f"{mean(rows, 'makespan'):>11.3f}"
            f"{mean(rows, 'distance'):>11.3f}"
            f"{mean(rows, 'jain'):>9.3f}"
            f"{mean(rows, 'steps'):>9.1f}"
            f"{mean(rows, 'reassign'):>10.1f}"
        )

    print("=" * 145)


if __name__ == "__main__":
    main()
