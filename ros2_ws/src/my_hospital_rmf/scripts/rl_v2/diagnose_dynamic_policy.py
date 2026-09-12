#!/usr/bin/env python3

import argparse
import statistics

from collections import defaultdict

import numpy as np

from sb3_contrib import (
    MaskablePPO,
)

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.dynamic_env import (
    DynamicHospitalRLEnv,
)

from rl_v2.dynamic_action_mask import (
    DECISION_ASSIGNMENT,
    DECISION_REASSIGNMENT,
)

from rl_v2.observation import (
    build_observation,
)

from rl_v2.env import (
    HospitalRLEnv,
)


# ==========================================================
# Metrics
# ==========================================================

def extract_result(
    env,
    step_count: int,
    reassignment_count: int,
):

    result = (
        env.get_simulation_result()
    )

    metrics = (
        calculate_metrics(
            result
        )
    )

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
            metrics
            .total_travel_distance,

        "success":
            metrics
            .task_success_rate,

        "jain":
            metrics
            .jain_fairness_index,

        "steps":
            float(
                step_count
            ),

        "reassign":
            float(
                reassignment_count
            ),
    }


# ==========================================================
# Static PPO
# ==========================================================

def run_static(
    model,
    scenario,
    seed,
):

    env = HospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = (
        env.reset(
            seed=seed
        )
    )

    step_count = 0

    while True:

        mask = (
            env.action_masks()
        )

        action, _ = (
            model.predict(
                observation,
                action_masks=mask,
                deterministic=True,
            )
        )

        action = int(
            np.asarray(
                action
            )
            .reshape(-1)[0]
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

        if terminated:
            break

    return extract_result(
        env=env,
        step_count=step_count,
        reassignment_count=0,
    )


# ==========================================================
# Static Observation For Dynamic Kernel
# ==========================================================

def build_static_assignment_observation(
    env,
):

    kernel = env.kernel

    if kernel is None:

        raise RuntimeError(
            "Kernel missing"
        )

    task = kernel.current_task

    if task is None:

        raise RuntimeError(
            "Current task missing"
        )

    return build_observation(
        task=task,
        robot_ids=(
            env.robot_ids
        ),
        runtimes=(
            kernel.runtimes
        ),
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


# ==========================================================
# Dynamic Episode
# ==========================================================

def run_dynamic(
    dynamic_model,
    static_model,
    scenario,
    seed,
    mode,
):

    env = DynamicHospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )

    observation, info = (
        env.reset(
            seed=seed
        )
    )

    step_count = 0
    reassignment_count = 0

    while True:

        kernel = env.kernel

        decision_type = (
            kernel.current_decision_type
        )

        mask = (
            env.action_masks()
        )

        # ==================================================
        # Full Dynamic Deterministic
        # ==================================================

        if (
            mode
            ==
            "dynamic_deterministic"
        ):

            action, _ = (
                dynamic_model.predict(
                    observation,
                    action_masks=mask,
                    deterministic=True,
                )
            )

            action = int(
                np.asarray(
                    action
                )
                .reshape(-1)[0]
            )

        # ==================================================
        # Full Dynamic Stochastic
        # ==================================================

        elif (
            mode
            ==
            "dynamic_stochastic"
        ):

            action, _ = (
                dynamic_model.predict(
                    observation,
                    action_masks=mask,
                    deterministic=False,
                )
            )

            action = int(
                np.asarray(
                    action
                )
                .reshape(-1)[0]
            )

        # ==================================================
        # Dynamic Model Assignment
        # +
        # Stay Reassignment
        #
        # 用來檢查 Dynamic PPO 的 Initial Assignment
        # 到底學得好不好。
        # ==================================================

        elif (
            mode
            ==
            "dynamic_assign_stay"
        ):

            if (
                decision_type
                ==
                DECISION_ASSIGNMENT
            ):

                action, _ = (
                    dynamic_model.predict(
                        observation,
                        action_masks=mask,
                        deterministic=True,
                    )
                )

                action = int(
                    np.asarray(
                        action
                    )
                    .reshape(-1)[0]
                )

            else:

                current_robot = (
                    kernel
                    .current_previous_robot
                )

                current_action = (
                    env.robot_ids.index(
                        current_robot
                    )
                )

                if bool(
                    mask[
                        current_action
                    ]
                ):

                    action = (
                        current_action
                    )

                else:

                    # Current Robot 已 infeasible
                    # 才允許 safety-forced move。
                    action = int(
                        np.flatnonzero(
                            mask
                        )[0]
                    )

        # ==================================================
        # Static PPO Assignment
        # +
        # Dynamic PPO Reassignment
        #
        # 用來單獨檢查 Dynamic PPO
        # 的 reassignment 能力。
        # ==================================================

        elif (
            mode
            ==
            "static_assign_dynamic_reassign"
        ):

            if (
                decision_type
                ==
                DECISION_ASSIGNMENT
            ):

                static_observation = (
                    build_static_assignment_observation(
                        env
                    )
                )

                action, _ = (
                    static_model.predict(
                        static_observation,
                        action_masks=mask,
                        deterministic=True,
                    )
                )

                action = int(
                    np.asarray(
                        action
                    )
                    .reshape(-1)[0]
                )

            else:

                action, _ = (
                    dynamic_model.predict(
                        observation,
                        action_masks=mask,
                        deterministic=True,
                    )
                )

                action = int(
                    np.asarray(
                        action
                    )
                    .reshape(-1)[0]
                )

        # ==================================================
        # Static PPO Assignment
        # +
        # Always Stay
        #
        # 理論上應該接近原 Static PPO。
        # 這也是 Dynamic env invariant check。
        # ==================================================

        elif (
            mode
            ==
            "static_assign_stay"
        ):

            if (
                decision_type
                ==
                DECISION_ASSIGNMENT
            ):

                static_observation = (
                    build_static_assignment_observation(
                        env
                    )
                )

                action, _ = (
                    static_model.predict(
                        static_observation,
                        action_masks=mask,
                        deterministic=True,
                    )
                )

                action = int(
                    np.asarray(
                        action
                    )
                    .reshape(-1)[0]
                )

            else:

                current_robot = (
                    kernel
                    .current_previous_robot
                )

                current_action = (
                    env.robot_ids.index(
                        current_robot
                    )
                )

                if bool(
                    mask[
                        current_action
                    ]
                ):

                    action = (
                        current_action
                    )

                else:

                    action = int(
                        np.flatnonzero(
                            mask
                        )[0]
                    )

        else:

            raise ValueError(
                f"Unknown mode: {mode}"
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

        if (
            info[
                "decision_type"
            ]
            ==
            DECISION_REASSIGNMENT
            and
            info[
                "changed"
            ]
        ):

            reassignment_count += 1

        if terminated:
            break

    return extract_result(
        env=env,
        step_count=step_count,
        reassignment_count=(
            reassignment_count
        ),
    )


# ==========================================================
# Main
# ==========================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dynamic-model",
        required=True,
    )

    parser.add_argument(
        "--static-model",
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

    dynamic_model = (
        MaskablePPO.load(
            args.dynamic_model,
            device="cpu",
        )
    )

    static_model = (
        MaskablePPO.load(
            args.static_model,
            device="cpu",
        )
    )

    methods = [
        "static_ppo",
        "dynamic_deterministic",
        "dynamic_stochastic",
        "dynamic_assign_stay",
        "static_assign_dynamic_reassign",
        "static_assign_stay",
    ]

    results = defaultdict(
        lambda: defaultdict(list)
    )

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

        static_result = (
            run_static(
                model=static_model,
                scenario=scenario,
                seed=seed,
            )
        )

        for key, value in (
            static_result.items()
        ):

            if value is not None:

                results[
                    "static_ppo"
                ][
                    key
                ].append(
                    float(value)
                )

        for mode in methods[1:]:

            values = (
                run_dynamic(
                    dynamic_model=(
                        dynamic_model
                    ),
                    static_model=(
                        static_model
                    ),
                    scenario=scenario,
                    seed=seed,
                    mode=mode,
                )
            )

            for key, value in (
                values.items()
            ):

                if value is not None:

                    results[
                        mode
                    ][
                        key
                    ].append(
                        float(value)
                    )

    # ======================================================
    # Print
    # ======================================================

    print()
    print(
        "=" * 135
    )

    print(
        "DYNAMIC POLICY ABLATION"
    )

    print(
        "=" * 135
    )

    print(
        f"{'Method':<31}"
        f"{'Wait':>10}"
        f"{'Emer':>10}"
        f"{'Complete':>11}"
        f"{'Makespan':>11}"
        f"{'Distance':>11}"
        f"{'Jain':>9}"
        f"{'Steps':>10}"
        f"{'Reassign':>10}"
    )

    print(
        "-" * 135
    )

    for method in methods:

        def mean(
            metric,
        ):

            values = (
                results[
                    method
                ][
                    metric
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
            f"{method:<31}"
            f"{mean('wait'):>10.3f}"
            f"{mean('emergency'):>10.3f}"
            f"{mean('completion'):>11.3f}"
            f"{mean('makespan'):>11.3f}"
            f"{mean('distance'):>11.3f}"
            f"{mean('jain'):>9.3f}"
            f"{mean('steps'):>10.1f}"
            f"{mean('reassign'):>10.1f}"
        )

    print(
        "=" * 135
    )


if __name__ == "__main__":

    main()
