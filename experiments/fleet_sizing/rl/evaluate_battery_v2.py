from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)


# ============================================================
# Validation Configuration
# ============================================================

VALIDATION_SEEDS = tuple(
    range(
        8101,
        8121,
    )
)

REFERENCE_FLEET = (
    2,
    2,
    3,
)

WORKLOAD_MULTIPLIER = 4.0


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RL_RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

VALIDATION_DIR = (
    RL_RESULTS_DIR
    / "validation_battery_v2"
)


# ============================================================
# Helpers
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
# One Validation Episode
# ============================================================

def evaluate_seed(
    *,
    model: MaskablePPO,
    seed: int,
) -> dict[str, float | int]:

    env = (
        HospitalSchedulingEnv(
            seed=seed,
            fleet_configuration=(
                REFERENCE_FLEET
            ),
            workload_multiplier=(
                WORKLOAD_MULTIPLIER
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

    decision_count = 0

    while not terminated:

        mask = (
            env.action_masks()
        )

        action, _ = (
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

        if not bool(
            mask[
                action
            ]
        ):

            raise RuntimeError(
                "Model selected an "
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
                "Unexpected environment "
                "truncation."
            )

        episode_reward += float(
            reward
        )

        decision_count += 1

    simulator = (
        env.simulator
    )

    if simulator is None:
        raise RuntimeError(
            "Simulator unavailable "
            "after evaluation."
        )

    tasks = (
        simulator.tasks
    )

    robots = (
        simulator.robots
    )

    assignments = (
        simulator.assignments
    )

    # --------------------------------------------------------
    # Completion
    # --------------------------------------------------------

    completed_tasks = [
        task
        for task
        in tasks
        if (
            task.status
            == "completed"
        )
    ]

    generated_task_count = len(
        tasks
    )

    completed_task_count = len(
        completed_tasks
    )

    completion_rate = (
        completed_task_count
        / generated_task_count
        if generated_task_count
        else 0.0
    )

    # --------------------------------------------------------
    # Waiting Time
    #
    # Realized waiting:
    # task start - task arrival
    # --------------------------------------------------------

    waiting_times: list[
        float
    ] = []

    priority_waiting: dict[
        int,
        list[float],
    ] = {
        0: [],
        1: [],
        2: [],
        3: [],
    }

    total_times: list[
        float
    ] = []

    response_times: list[
        float
    ] = []

    for task in (
        completed_tasks
    ):

        if (
            task.start_time_s
            is None
        ):
            continue

        waiting_time_s = max(
            0.0,
            float(
                task.start_time_s
            )
            - float(
                task.arrival_time_s
            ),
        )

        waiting_times.append(
            waiting_time_s
        )

        priority_waiting[
            int(
                task.priority
            )
        ].append(
            waiting_time_s
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
    # Makespan / Utilization
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

    robot_utilizations: list[
        float
    ] = []

    for robot in robots:

        if makespan_s <= 0.0:

            utilization = 0.0

        else:

            utilization = (
                float(
                    robot.busy_time_s
                )
                / makespan_s
            )

        robot_utilizations.append(
            utilization
        )

    completed_counts = [
        float(
            robot.completed_tasks
        )
        for robot
        in robots
    ]

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

    env.close()

    return {
        "seed":
        seed,

        "generated_tasks":
        generated_task_count,

        "completed_tasks":
        completed_task_count,

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
        episode_reward,

        "decision_count":
        decision_count,
    }


# ============================================================
# One Model
# ============================================================

def evaluate_model(
    *,
    model_path: Path,
    model_name: str,
) -> list[
    dict[
        str,
        float | int | str,
    ]
]:

    print()
    print(
        "=" * 80
    )

    print(
        "Evaluating:",
        model_name,
    )

    print(
        "Model:",
        model_path,
    )

    print(
        "Seeds:",
        f"{VALIDATION_SEEDS[0]}"
        f"–{VALIDATION_SEEDS[-1]}",
    )

    print(
        "=" * 80
    )

    model = (
        MaskablePPO.load(
            str(
                model_path
            ),
            device="cpu",
        )
    )

    rows = []

    for seed in (
        VALIDATION_SEEDS
    ):

        metrics = (
            evaluate_seed(
                model=model,
                seed=seed,
            )
        )

        row = {
            "model":
            model_name,

            **metrics,
        }

        rows.append(
            row
        )

        print(
            f"{model_name:<20} "
            f"seed={seed} "
            f"wait="
            f"{metrics['average_waiting_time_s']:.2f}s "
            f"p95="
            f"{metrics['p95_waiting_time_s']:.2f}s "
            f"emer="
            f"{metrics['emergency_waiting_time_s']:.2f}s "
            f"reward="
            f"{metrics['episode_reward']:.2f}"
        )

    return rows


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

    "episode_reward",
)


def aggregate_model(
    model_name: str,
    rows: list[dict],
) -> dict:

    summary = {
        "model":
        model_name,

        "validation_seed_count":
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
        ] = float(
            statistics.median(
                values
            )
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

        writer = (
            csv.DictWriter(
                file,
                fieldnames=list(
                    rows[0].keys()
                ),
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# Pipeline Checkpoint Discovery
# ============================================================

def get_pipeline_models(
    run_name: str,
) -> list[
    tuple[
        str,
        Path,
    ]
]:

    checkpoint_dir = (
        RL_RESULTS_DIR
        / "checkpoints"
        / run_name
    )

    if not checkpoint_dir.exists():

        raise FileNotFoundError(
            f"Checkpoint directory "
            f"does not exist: "
            f"{checkpoint_dir}"
        )

    discovered = []

    for path in (
        checkpoint_dir.glob(
            "maskable_ppo_*_steps.zip"
        )
    ):

        name = (
            path.stem
        )

        prefix = (
            "maskable_ppo_"
        )

        suffix = (
            "_steps"
        )

        if not (
            name.startswith(
                prefix
            )
            and name.endswith(
                suffix
            )
        ):

            continue

        step_text = (
            name[
                len(prefix):
                -len(suffix)
            ]
        )

        try:

            steps = int(
                step_text
            )

        except ValueError:

            continue

        discovered.append(
            (
                steps,
                path,
            )
        )

    if not discovered:

        raise FileNotFoundError(
            "No PPO checkpoints found in "
            f"{checkpoint_dir}"
        )

    discovered.sort(
        key=lambda item:
        item[0]
    )

    return [
        (
            (
                f"{steps // 1000}k"
                if (
                    steps
                    % 1000
                    == 0
                )
                else str(
                    steps
                )
            ),
            path,
        )
        for (
            steps,
            path,
        )
        in discovered
    ]


# ============================================================
# Main
# ============================================================

def main():

    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--run-name",
        default="pipeline_test",
    )

    args = (
        parser.parse_args()
    )

    models = (
        get_pipeline_models(
            args.run_name
        )
    )

    all_rows = []

    summaries = []

    for (
        model_name,
        model_path,
    ) in models:

        rows = (
            evaluate_model(
                model_path=(
                    model_path
                ),
                model_name=(
                    model_name
                ),
            )
        )

        all_rows.extend(
            rows
        )

        summaries.append(
            aggregate_model(
                model_name,
                rows,
            )
        )

    output_dir = (
        VALIDATION_DIR
        / args.run_name
    )

    runs_path = (
        output_dir
        / "validation_runs.csv"
    )

    summary_path = (
        output_dir
        / "validation_summary.csv"
    )

    write_csv(
        runs_path,
        all_rows,
    )

    write_csv(
        summary_path,
        summaries,
    )

    print()
    print(
        "=" * 100
    )

    print(
        "VALIDATION SUMMARY"
    )

    print(
        "=" * 100
    )

    print(
        f"{'Model':<8}"
        f"{'Wait':>12}"
        f"{'P95':>12}"
        f"{'High':>12}"
        f"{'Emergency':>12}"
        f"{'Travel':>14}"
        f"{'Jain':>10}"
        f"{'Reward':>12}"
    )

    print(
        "-" * 100
    )

    for summary in (
        summaries
    ):

        print(
            f"{summary['model']:<8}"

            f"{summary['average_waiting_time_s_mean']:>12.2f}"

            f"{summary['p95_waiting_time_s_mean']:>12.2f}"

            f"{summary['high_waiting_time_s_mean']:>12.2f}"

            f"{summary['emergency_waiting_time_s_mean']:>12.2f}"

            f"{summary['total_travel_time_s_mean']:>14.2f}"

            f"{summary['jain_task_fairness_mean']:>10.3f}"

            f"{summary['episode_reward_mean']:>12.2f}"
        )

    print(
        "=" * 100
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