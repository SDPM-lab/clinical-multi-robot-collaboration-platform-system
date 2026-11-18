from __future__ import annotations

import csv
import statistics
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)

from experiments.fleet_sizing.rl.reward import (
    RewardConfig,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
)

OUTPUT_DIR = (
    RESULTS_DIR
    / "scale_sensitivity_eval"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REFERENCE_FLEET = (
    2,
    2,
    3,
)

WORKLOAD_MULTIPLIER = 4.0

VALIDATION_SEEDS = tuple(
    range(
        9501,
        9531,
    )
)

SCALES = (
    150,
    200,
    300,
    600,
)

WAITING_SCALE_S = 600.0


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

    x = np.asarray(
        values,
        dtype=np.float64,
    )

    denominator = (
        len(x)
        * float(
            np.sum(
                x ** 2
            )
        )
    )

    if denominator <= 0.0:
        return 1.0

    numerator = float(
        np.sum(x) ** 2
    )

    return float(
        numerator / denominator
    )


def evaluate_one(
    *,
    model: MaskablePPO,
    scale: int,
    seed: int,
    observation_scale: float | None = None,
) -> dict[str, float | int]:

    reward_config = RewardConfig(
        approach_weight=0.30,
        queue_weight=0.15,
        imbalance_weight=0.05,
        waiting_weight=0.50,
        approach_scale_s=float(
            scale
        ),
        waiting_scale_s=(
            WAITING_SCALE_S
        ),
    )

    env = HospitalSchedulingEnv(
        seed=seed,
        fleet_configuration=(
            REFERENCE_FLEET
        ),
        workload_multiplier=(
            WORKLOAD_MULTIPLIER
        ),
        enable_battery_model=True,
        reward_config=(
            reward_config
        ),

        observation_approach_scale_s=(
            float(observation_scale)
            if observation_scale is not None
            else float(scale)
        ),
    )

    observation, _ = env.reset(
        seed=seed
    )

    terminated = False

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

        (
            observation,
            _,
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

    simulator = env.simulator

    if simulator is None:
        raise RuntimeError(
            "Simulator unavailable "
            "after evaluation."
        )

    tasks = simulator.tasks
    robots = simulator.robots
    assignments = simulator.assignments

    completed_tasks = [
        task
        for task
        in tasks
        if task.status == "completed"
    ]

    total_tasks = len(
        tasks
    )

    waiting_times = []
    high_waiting_times = []
    emergency_waiting_times = []

    for task in completed_tasks:

        if task.start_time_s is None:
            continue

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

        if int(task.priority) == 2:
            high_waiting_times.append(
                waiting
            )

        elif int(task.priority) == 3:
            emergency_waiting_times.append(
                waiting
            )

    robot_task_counts = [
        float(
            robot.completed_tasks
        )
        for robot
        in robots
    ]

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

    total_travel = (
        total_approach_time_s
        + total_task_travel_time_s
    )

    result = {
        "scale":
        scale,

        "seed":
        seed,

        "completion_rate":
        (
            len(completed_tasks)
            / total_tasks
            if total_tasks > 0
            else 0.0
        ),

        "avg_waiting_time_s":
        safe_mean(
            waiting_times
        ),

        "p95_waiting_time_s":
        percentile(
            waiting_times,
            95,
        ),

        "high_waiting_time_s":
        safe_mean(
            high_waiting_times
        ),

        "emergency_waiting_time_s":
        safe_mean(
            emergency_waiting_times
        ),

        "total_travel":
        total_travel,

        "jain_fairness":
        jain_fairness(
            robot_task_counts
        ),
    }

    env.close()

    return result


def main() -> None:

    all_rows = []

    for scale in SCALES:

        model_path = (
            RESULTS_DIR
            / "models"
            / (
                f"scale_sensitivity_a"
                f"{scale}_seed7001_50k"
            )
            / "final_model.zip"
        )

        if not model_path.exists():
            raise FileNotFoundError(
                model_path
            )

        print()
        print("=" * 72)
        print(
            f"Loading scale={scale}"
        )
        print("=" * 72)

        model = MaskablePPO.load(
            model_path
        )

        scale_rows = []

        for seed in VALIDATION_SEEDS:

            row = evaluate_one(
                model=model,
                scale=scale,
                seed=seed,
            )

            scale_rows.append(
                row
            )

            all_rows.append(
                row
            )

            print(
                f"scale={scale} "
                f"seed={seed} "
                f"avg_wait="
                f"{row['avg_waiting_time_s']:.2f} "
                f"p95="
                f"{row['p95_waiting_time_s']:.2f}"
            )

        print()
        print(
            f"SCALE {scale} SUMMARY"
        )

        for metric in (
            "completion_rate",
            "avg_waiting_time_s",
            "p95_waiting_time_s",
            "high_waiting_time_s",
            "emergency_waiting_time_s",
            "total_travel",
            "jain_fairness",
        ):

            values = [
                float(
                    row[
                        metric
                    ]
                )
                for row
                in scale_rows
            ]

            print(
                f"{metric}: "
                f"{safe_mean(values):.6f}"
            )

    episode_csv = (
        OUTPUT_DIR
        / "episode_results.csv"
    )

    with episode_csv.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=(
                list(
                    all_rows[0]
                    .keys()
                )
            ),
        )

        writer.writeheader()
        writer.writerows(
            all_rows
        )

    summary_rows = []

    for scale in SCALES:

        scale_rows = [
            row
            for row
            in all_rows
            if row[
                "scale"
            ] == scale
        ]

        summary = {
            "scale":
            scale,
        }

        for metric in (
            "completion_rate",
            "avg_waiting_time_s",
            "p95_waiting_time_s",
            "high_waiting_time_s",
            "emergency_waiting_time_s",
            "total_travel",
            "jain_fairness",
        ):

            summary[
                metric
            ] = safe_mean(
                [
                    float(
                        row[
                            metric
                        ]
                    )
                    for row
                    in scale_rows
                ]
            )

        summary_rows.append(
            summary
        )

    summary_csv = (
        OUTPUT_DIR
        / "summary.csv"
    )

    with summary_csv.open(
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=(
                list(
                    summary_rows[0]
                    .keys()
                )
            ),
        )

        writer.writeheader()
        writer.writerows(
            summary_rows
        )

    print()
    print("=" * 72)
    print("DONE")
    print("=" * 72)
    print(
        episode_csv
    )
    print(
        summary_csv
    )


if __name__ == "__main__":
    main()
