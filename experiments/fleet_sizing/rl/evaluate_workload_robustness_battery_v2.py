from __future__ import annotations

import csv
import statistics
from pathlib import Path

import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.baseline.random_feasible import (
    RandomFeasibleScheduler,
)

from experiments.fleet_sizing.baseline.projected_nearest import (
    ProjectedNearestScheduler,
)

from experiments.fleet_sizing.baseline.static_weighted import (
    StaticWeightedScheduler,
)

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
)


# ============================================================
# Workload Robustness Configuration
# ============================================================

REFERENCE_FLEET = (
    2,
    2,
    3,
)

WORKLOAD_LEVELS = (
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
)

ROBUSTNESS_EVAL_SEEDS = tuple(
    range(
        9201,
        9231,
    )
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]


RESULTS_RL_ROOT = (
    Path(__file__).resolve().parents[1]
    / "results_rl"
)


RESULTS_DIR = (
    RESULTS_RL_ROOT
    / "workload_robustness_battery_v2"
)


PPO_MODELS = {
    7001: (
        RESULTS_RL_ROOT
        / "checkpoints"
        / "ppo_battery_v2_fixed_200k"
        / "maskable_ppo_180000_steps.zip"
    ),

    7101: (
        RESULTS_RL_ROOT
        / "checkpoints"
        / "ppo_battery_v2_seed7101_180k"
        / "maskable_ppo_180000_steps.zip"
    ),

    7102: (
        RESULTS_RL_ROOT
        / "checkpoints"
        / "ppo_battery_v2_seed7102_180k"
        / "maskable_ppo_180000_steps.zip"
    ),

    7103: (
        RESULTS_RL_ROOT
        / "checkpoints"
        / "ppo_battery_v2_seed7103_180k"
        / "maskable_ppo_180000_steps.zip"
    ),

    7104: (
        RESULTS_RL_ROOT
        / "checkpoints"
        / "ppo_battery_v2_seed7104_180k"
        / "maskable_ppo_180000_steps.zip"
    ),
}


# ============================================================
# Helper Functions
# ============================================================

def safe_mean(
    values: list[float],
) -> float:

    if not values:
        return 0.0

    return float(
        statistics.mean(
            values
        )
    )


def safe_std(
    values: list[float],
) -> float:

    if len(
        values
    ) < 2:
        return 0.0

    return float(
        statistics.stdev(
            values
        )
    )


def safe_median(
    values: list[float],
) -> float:

    if not values:
        return 0.0

    return float(
        statistics.median(
            values
        )
    )


def percentile(
    values: list[float],
    p: float,
) -> float:

    if not values:
        return 0.0

    return float(
        np.percentile(
            np.asarray(
                values,
                dtype=np.float64,
            ),
            p,
        )
    )


def jain_fairness(
    values: list[float],
) -> float:

    if not values:
        return 0.0

    array = np.asarray(
        values,
        dtype=np.float64,
    )

    denominator = (
        len(array)
        * float(
            np.sum(
                array ** 2
            )
        )
    )

    if denominator <= 0.0:
        return 1.0

    numerator = float(
        np.sum(
            array
        )
        ** 2
    )

    return (
        numerator
        / denominator
    )


# ============================================================
# Common Metrics
# ============================================================

def calculate_episode_metrics(
    *,
    seed: int,
    method: str,
    tasks,
    robots,
    assignments,
    episode_reward: float | None = None,
) -> dict:

    completed_tasks = [
        task
        for task
        in tasks
        if (
            task.status
            == "completed"
        )
    ]

    generated_tasks = len(
        tasks
    )

    completed_count = len(
        completed_tasks
    )

    completion_rate = (
        completed_count
        / generated_tasks
        if generated_tasks
        else 0.0
    )

    # --------------------------------------------------------
    # Waiting / Response / Total Time
    # --------------------------------------------------------

    waiting_times = []

    priority_waiting = {
        0: [],
        1: [],
        2: [],
        3: [],
    }

    response_times = []

    total_times = []

    for task in (
        completed_tasks
    ):

        if (
            task.start_time_s
            is not None
        ):

            waiting = max(
                0.0,
                float(
                    task.start_time_s
                )
                - float(
                    task.arrival_time_s
                ),
            )

            waiting_times.append(
                waiting
            )

            priority_waiting[
                int(
                    task.priority
                )
            ].append(
                waiting
            )

        if (
            task.source_arrival_time_s
            is not None
        ):

            response_times.append(
                max(
                    0.0,
                    float(
                        task.source_arrival_time_s
                    )
                    - float(
                        task.arrival_time_s
                    ),
                )
            )

        if (
            task.completion_time_s
            is not None
        ):

            total_times.append(
                max(
                    0.0,
                    float(
                        task.completion_time_s
                    )
                    - float(
                        task.arrival_time_s
                    ),
                )
            )

    # --------------------------------------------------------
    # Travel
    # --------------------------------------------------------

    total_approach_time_s = sum(
        float(
            record.approach_time_s
        )
        for record
        in assignments
    )

    total_task_travel_time_s = sum(
        float(
            record.task_travel_time_s
        )
        for record
        in assignments
    )

    total_travel_time_s = (
        total_approach_time_s
        + total_task_travel_time_s
    )

    # --------------------------------------------------------
    # Makespan
    # --------------------------------------------------------

    completion_times = [
        float(
            task.completion_time_s
        )
        for task
        in completed_tasks
        if (
            task.completion_time_s
            is not None
        )
    ]

    makespan_s = (
        max(
            completion_times
        )
        if completion_times
        else 0.0
    )

    # --------------------------------------------------------
    # Robot Utilization / Load Fairness
    # --------------------------------------------------------

    robot_utilizations = []

    completed_counts = []

    for robot in robots:

        utilization = (
            float(
                robot.busy_time_s
            )
            / makespan_s
            if makespan_s > 0.0
            else 0.0
        )

        robot_utilizations.append(
            utilization
        )

        completed_counts.append(
            float(
                robot.completed_tasks
            )
        )

    total_return_to_charge_count = sum(
        int(
            robot.return_to_charge_count
        )
        for robot
        in robots
    )

    total_charging_count = sum(
        int(
            robot.charging_count
        )
        for robot
        in robots
    )

    minimum_robot_soc = (
        min(
            float(
                robot.minimum_battery_soc
            )
            for robot
            in robots
        )
        if robots
        else 0.0
    )

    average_final_soc = safe_mean(
        [
            float(
                robot.battery_soc
            )
            for robot
            in robots
        ]
    )

    return {
        "method":
        method,

        "seed":
        seed,

        "generated_tasks":
        generated_tasks,

        "completed_tasks":
        completed_count,

        "completion_rate":
        completion_rate,

        "average_waiting_time_s":
        safe_mean(
            waiting_times
        ),

        "p95_waiting_time_s":
        percentile(
            waiting_times,
            95.0,
        ),

        "low_waiting_time_s":
        safe_mean(
            priority_waiting[
                0
            ]
        ),

        "normal_waiting_time_s":
        safe_mean(
            priority_waiting[
                1
            ]
        ),

        "high_waiting_time_s":
        safe_mean(
            priority_waiting[
                2
            ]
        ),

        "emergency_waiting_time_s":
        safe_mean(
            priority_waiting[
                3
            ]
        ),

        "average_response_time_s":
        safe_mean(
            response_times
        ),

        "p95_response_time_s":
        percentile(
            response_times,
            95.0,
        ),

        "average_total_time_s":
        safe_mean(
            total_times
        ),

        "p95_total_time_s":
        percentile(
            total_times,
            95.0,
        ),

        "total_approach_time_s":
        total_approach_time_s,

        "total_task_travel_time_s":
        total_task_travel_time_s,

        "total_travel_time_s":
        total_travel_time_s,

        "makespan_s":
        makespan_s,

        "average_robot_utilization":
        safe_mean(
            robot_utilizations
        ),

        "max_robot_utilization":
        (
            max(
                robot_utilizations
            )
            if robot_utilizations
            else 0.0
        ),

        "jain_task_fairness":
        jain_fairness(
            completed_counts
        ),

        "total_return_to_charge_count":
        total_return_to_charge_count,

        "total_charging_count":
        total_charging_count,

        "minimum_robot_soc":
        minimum_robot_soc,

        "average_final_soc":
        average_final_soc,

        "episode_reward":
        (
            episode_reward
            if episode_reward
            is not None
            else ""
        ),
    }


# ============================================================
# Baseline Episodes
# ============================================================

def create_baseline_scheduler(
    method: str,
    seed: int,
):

    if (
        method
        == "random_feasible"
    ):

        return (
            RandomFeasibleScheduler(
                seed=seed
            )
        )

    if (
        method
        == "projected_nearest"
    ):

        return (
            ProjectedNearestScheduler()
        )

    if (
        method
        == "static_weighted"
    ):

        return (
            StaticWeightedScheduler(
                alpha=0.5
            )
        )

    if (
        method
        == "dynamic_weighted"
    ):

        return (
            DynamicWeightedScheduler(
                alpha_min=0.4,
                alpha_max=0.8,
            )
        )

    raise ValueError(
        f"Unknown baseline: "
        f"{method}"
    )


def run_baseline_episode(
    *,
    method: str,
    seed: int,
    workload_multiplier: float,
) -> dict:

    scheduler = (
        create_baseline_scheduler(
            method=method,
            seed=seed,
        )
    )

    simulator = (
        SchedulingSimulator(
            fleet_configuration=(
                REFERENCE_FLEET
            ),

            seed=seed,

            scheduler=(
                scheduler
            ),

            workload_multiplier=(
                workload_multiplier
            ),

            enable_battery_model=True,
        )
    )

    result = (
        simulator.run()
    )

    return (
        calculate_episode_metrics(
            seed=seed,

            method=method,

            tasks=result.tasks,

            robots=result.robots,

            assignments=(
                result.assignments
            ),
        )
    )


# ============================================================
# PPO Episode
# ============================================================

def run_ppo_episode(
    *,
    model,
    seed: int,
    method_name: str,
    workload_multiplier: float,
) -> dict:

    env = (
        HospitalSchedulingEnv(
            seed=seed,

            fleet_configuration=(
                REFERENCE_FLEET
            ),

            workload_multiplier=(
                workload_multiplier
            ),

            enable_battery_model=True,
        )
    )

    observation, _ = (
        env.reset(
            seed=seed
        )
    )

    terminated = False

    episode_reward = 0.0

    while not terminated:

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
            action
        )

        if not bool(
            mask[
                action
            ]
        ):

            raise RuntimeError(
                "PPO selected an "
                "infeasible action."
            )

        (
            observation,
            reward,
            terminated,
            truncated,
            _,
        ) = env.step(
            action
        )

        if truncated:

            raise RuntimeError(
                "Unexpected truncation."
            )

        episode_reward += float(
            reward
        )

    simulator = (
        env.simulator
    )

    if simulator is None:

        raise RuntimeError(
            "Missing PPO simulator."
        )

    metrics = (
        calculate_episode_metrics(
            seed=seed,

            method=(
                method_name
            ),

            tasks=(
                simulator.tasks
            ),

            robots=(
                simulator.robots
            ),

            assignments=(
                simulator.assignments
            ),

            episode_reward=(
                episode_reward
            ),
        )
    )

    env.close()

    return metrics


# ============================================================
# Aggregate
# ============================================================

SUMMARY_METRICS = (
    "completion_rate",

    "average_waiting_time_s",
    "p95_waiting_time_s",

    "low_waiting_time_s",
    "normal_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",

    "average_response_time_s",
    "p95_response_time_s",

    "average_total_time_s",
    "p95_total_time_s",

    "total_approach_time_s",
    "total_task_travel_time_s",
    "total_travel_time_s",

    "makespan_s",

    "average_robot_utilization",
    "max_robot_utilization",

    "jain_task_fairness",

    "total_return_to_charge_count",
    "total_charging_count",
    "minimum_robot_soc",
    "average_final_soc",
)


def aggregate_method(
    method: str,
    rows: list[dict],
) -> dict:

    summary = {
        "method":
        method,

        "seed_count":
        len(
            rows
        ),
    }

    for metric in (
        SUMMARY_METRICS
    ):

        values = [
            float(
                row[
                    metric
                ]
            )
            for row
            in rows
        ]

        summary[
            f"{metric}_mean"
        ] = safe_mean(
            values
        )

        summary[
            f"{metric}_std"
        ] = safe_std(
            values
        )

        summary[
            f"{metric}_median"
        ] = safe_median(
            values
        )

    return summary


# ============================================================
# CSV
# ============================================================

def write_csv(
    path: Path,
    rows: list[dict],
) -> None:

    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# Main
# ============================================================

def main():

    for model_seed, model_path in (
        PPO_MODELS.items()
    ):

        if not (
            model_path.exists()
        ):

            raise FileNotFoundError(
                f"PPO model missing "
                f"for seed {model_seed}: "
                f"{model_path}"
            )

    print(
        "=" * 110
    )

    print(
        "BATTERY V2 WORKLOAD ROBUSTNESS EVALUATION"
    )

    print(
        "=" * 110
    )

    print(
        "Evaluation seeds:",
        f"{ROBUSTNESS_EVAL_SEEDS[0]}"
        f"–{ROBUSTNESS_EVAL_SEEDS[-1]}",
    )

    print(
        "Fleet:",
        REFERENCE_FLEET,
    )

    print(
        "Workloads:",
        WORKLOAD_LEVELS,
    )

    print(
        "PPO training seeds:",
        list(
            PPO_MODELS.keys()
        ),
    )

    print(
        "=" * 110
    )

    all_rows = []

    summaries = []


    # ============================================================
    # Workload Loop
    # ============================================================

    for workload in (
        WORKLOAD_LEVELS
    ):

        print()
        print(
            "=" * 110
        )

        print(
            f"WORKLOAD = "
            f"{workload:.1f}"
        )

        print(
            "=" * 110
        )

        # --------------------------------------------------------
        # Dynamic Weighted
        # --------------------------------------------------------

        method = (
            "dynamic_weighted"
        )

        dynamic_rows = []

        print()
        print(
            "Running "
            "dynamic_weighted..."
        )

        for seed in (
            ROBUSTNESS_EVAL_SEEDS
        ):

            result = (
                run_baseline_episode(
                    method=method,
                    seed=seed,
                    workload_multiplier=(
                        workload
                    ),
                )
            )

            result[
                "training_seed"
            ] = ""

            result[
                "workload_multiplier"
            ] = workload

            dynamic_rows.append(
                result
            )

            all_rows.append(
                result
            )

            print(
                f"{method:<20} "
                f"workload="
                f"{workload:.1f} "
                f"seed={seed} "
                f"wait="
                f"{result['average_waiting_time_s']:.2f}s "
                f"p95="
                f"{result['p95_waiting_time_s']:.2f}s "
                f"emer="
                f"{result['emergency_waiting_time_s']:.2f}s"
            )

        dynamic_summary = (
            aggregate_method(
                method,
                dynamic_rows,
            )
        )

        dynamic_summary[
            "workload_multiplier"
        ] = workload

        summaries.append(
            dynamic_summary
        )

        # --------------------------------------------------------
        # PPO Multi-seed
        # --------------------------------------------------------

        for model_seed, model_path in (
            PPO_MODELS.items()
        ):

            method_name = (
                f"ppo_seed_{model_seed}"
            )

            print()
            print(
                f"Loading PPO "
                f"training seed "
                f"{model_seed} "
                f"for workload "
                f"{workload:.1f}..."
            )

            model = (
                MaskablePPO.load(
                    str(
                        model_path
                    ),
                    device="cpu",
                )
            )

            ppo_rows = []

            for seed in (
                ROBUSTNESS_EVAL_SEEDS
            ):

                result = (
                    run_ppo_episode(
                        model=model,
                        seed=seed,
                        method_name=(
                            method_name
                        ),
                        workload_multiplier=(
                            workload
                        ),
                    )
                )

                result[
                    "training_seed"
                ] = model_seed

                result[
                    "workload_multiplier"
                ] = workload

                ppo_rows.append(
                    result
                )

                all_rows.append(
                    result
                )

                print(
                    f"{method_name:<20} "
                    f"workload="
                    f"{workload:.1f} "
                    f"eval_seed={seed} "
                    f"wait="
                    f"{result['average_waiting_time_s']:.2f}s "
                    f"p95="
                    f"{result['p95_waiting_time_s']:.2f}s "
                    f"emer="
                    f"{result['emergency_waiting_time_s']:.2f}s"
                )

            ppo_summary = (
                aggregate_method(
                    method_name,
                    ppo_rows,
                )
            )

            ppo_summary[
                "workload_multiplier"
            ] = workload

            summaries.append(
                ppo_summary
            )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    runs_path = (
        RESULTS_DIR
        / "comparison_runs.csv"
    )

    summary_path = (
        RESULTS_DIR
        / "comparison_summary.csv"
    )

    write_csv(
        runs_path,
        all_rows,
    )

    write_csv(
        summary_path,
        summaries,
    )

    # --------------------------------------------------------
    # Console Table
    # --------------------------------------------------------

    print()
    print(
        "=" * 125
    )

    print(
        "FINAL COMPARISON"
    )

    print(
        "=" * 125
    )

    print(
        f"{'Method':<22}"
        f"{'Wait':>10}"
        f"{'P95':>11}"
        f"{'High':>11}"
        f"{'Emer':>11}"
        f"{'Travel':>14}"
        f"{'Jain':>10}"
        f"{'Complete':>11}"
    )

    print(
        "-" * 125
    )

    for summary in (
        summaries
    ):

        print(
            f"{summary['method']:<22}"

            f"{summary['average_waiting_time_s_mean']:>10.2f}"

            f"{summary['p95_waiting_time_s_mean']:>11.2f}"

            f"{summary['high_waiting_time_s_mean']:>11.2f}"

            f"{summary['emergency_waiting_time_s_mean']:>11.2f}"

            f"{summary['total_travel_time_s_mean']:>14.2f}"

            f"{summary['jain_task_fairness_mean']:>10.3f}"

            f"{summary['completion_rate_mean']:>11.4f}"
        )

    print(
        "=" * 125
    )

    print(
        "Seed-level:",
        runs_path,
    )

    print(
        "Summary:",
        summary_path,
    )


if __name__ == "__main__":
    main()