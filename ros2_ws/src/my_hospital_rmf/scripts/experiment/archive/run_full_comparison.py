#!/usr/bin/env python3

import csv
import os
import statistics

from sb3_contrib import (
    MaskablePPO,
)

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    TASK_COUNTS,
    LOADS,
    SEEDS,
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from experiment.simulator import (
    BaselineSimulator,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)

from scheduler.robot_selection.rule_based_scheduler import (
    RuleBasedScheduler,
)

from rl.hospital_gym_env import (
    HospitalGymEnv,
)


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

MODEL_PATH = os.path.join(
    RL_DIR,
    "models",
    "maskable_ppo_hospital_33d_reward_v3_50k.zip",
)

OUTPUT_DIR = os.path.join(
    SCRIPT_DIR,
    "results",
)

RAW_CSV = os.path.join(
    OUTPUT_DIR,
    "full_comparison_raw_results.csv",
)

SUMMARY_CSV = os.path.join(
    OUTPUT_DIR,
    "full_comparison_summary.csv",
)


# ==========================================================
# Methods
# ==========================================================

METHODS = [
    "Priority + Nearest",
    "Priority + Rule-based",
    "Priority + PPO 33D Reward v3 50K",
]


# ==========================================================
# Mean / Std
# ==========================================================

def mean_std(
    values,
):

    values = [
        value
        for value
        in values
        if value is not None
    ]

    if not values:
        return (
            None,
            None,
        )

    mean_value = (
        statistics.mean(
            values
        )
    )

    std_value = (
        statistics.stdev(
            values
        )
        if len(values) >= 2
        else 0.0
    )

    return (
        mean_value,
        std_value,
    )


# ==========================================================
# Execution Record Success
# ==========================================================

def is_successful_record(
    record,
):

    success = getattr(
        record,
        "success",
        True,
    )

    start_time = getattr(
        record,
        "start_time",
        None,
    )

    completion_time = getattr(
        record,
        "completion_time",
        None,
    )

    return (
        bool(success)
        and start_time is not None
        and completion_time is not None
    )


# ==========================================================
# Common Metrics
#
# Baseline 與 RL 都從 final execution records
# 使用同一套 metric 計算。
# ==========================================================

def calculate_common_metrics(
    execution_records,
    robot_states,
    simulation_end_time,
    task_count,
):

    successful_records = [
        record
        for record
        in execution_records
        if is_successful_record(
            record
        )
    ]

    if not successful_records:
        raise RuntimeError(
            "No successful execution records."
        )

    # ======================================================
    # Task Metrics
    # ======================================================

    waiting_times = [
        record.waiting_time
        for record
        in successful_records
    ]

    completion_times = [
        (
            record.completion_time
            -
            record.arrival_time
        )
        for record
        in successful_records
    ]

    emergency_waiting_times = [
        record.waiting_time
        for record
        in successful_records
        if record.priority == 3
    ]

    high_waiting_times = [
        record.waiting_time
        for record
        in successful_records
        if record.priority == 2
    ]

    total_travel_distance = sum(
        record.travel_distance
        for record
        in successful_records
    )

    # ======================================================
    # Robot Task Counts
    # ======================================================

    robot_task_counts = {
        robot_id: 0
        for robot_id
        in robot_states
    }

    for record in successful_records:

        if (
            record.robot_id
            not in robot_task_counts
        ):
            robot_task_counts[
                record.robot_id
            ] = 0

        robot_task_counts[
            record.robot_id
        ] += 1

    # ======================================================
    # Robot Utilization
    # ======================================================

    robot_utilizations = []

    for sim_state in (
        robot_states.values()
    ):

        if simulation_end_time > 0.0:

            utilization = (
                sim_state.total_busy_time
                /
                simulation_end_time
            )

        else:

            utilization = 0.0

        robot_utilizations.append(
            utilization
        )

    # ======================================================
    # Return
    # ======================================================

    return {
        "average_waiting_time":
            statistics.mean(
                waiting_times
            ),

        "average_completion_time":
            statistics.mean(
                completion_times
            ),

        "emergency_waiting_time":
            (
                statistics.mean(
                    emergency_waiting_times
                )
                if emergency_waiting_times
                else None
            ),

        "high_waiting_time":
            (
                statistics.mean(
                    high_waiting_times
                )
                if high_waiting_times
                else None
            ),

        "total_travel_distance":
            total_travel_distance,

        "makespan":
            simulation_end_time,

        "success_rate":
            (
                len(
                    successful_records
                )
                /
                task_count
            ),

        "average_robot_utilization":
            statistics.mean(
                robot_utilizations
            ),

        "task_load_std":
            statistics.pstdev(
                robot_task_counts.values()
            ),

        "utilization_std":
            statistics.pstdev(
                robot_utilizations
            ),
    }


# ==========================================================
# Robot Scheduler Factory
# ==========================================================

def create_robot_scheduler(
    scheduler_name,
    waypoints,
):

    if scheduler_name == "nearest":

        return NearestScheduler(
            waypoints
        )

    if scheduler_name == "rule_based":

        return RuleBasedScheduler(
            waypoints
        )

    raise ValueError(
        "Unknown robot scheduler: "
        f"{scheduler_name}"
    )


# ==========================================================
# Baseline Episode
# ==========================================================

def run_baseline_episode(
    task_count,
    load,
    seed,
    robot_scheduler_name,
):

    scenario = (
        generate_random_scenario(

            task_count=task_count,

            seed=seed,

            load=load,

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    robot_scheduler = (
        create_robot_scheduler(

            scheduler_name=(
                robot_scheduler_name
            ),

            waypoints=(
                scenario.waypoints
            ),
        )
    )

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            PriorityScheduler()
        ),

        robot_scheduler=(
            robot_scheduler
        ),

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    result = (
        simulator.run()
    )

    metrics = (
        calculate_common_metrics(

            execution_records=(
                result[
                    "records"
                ]
            ),

            robot_states=(
                simulator.robot_states
            ),

            simulation_end_time=(
                result[
                    "simulation_end_time"
                ]
            ),

            task_count=(
                task_count
            ),
        )
    )

    return metrics


# ==========================================================
# PPO Episode
# ==========================================================

def run_rl_episode(
    model,
    task_count,
    load,
    seed,
):

    scenario = (
        generate_random_scenario(

            task_count=task_count,

            seed=seed,

            load=load,

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    env = HospitalGymEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    (
        observation,
        info,
    ) = (
        env.reset()
    )

    while True:

        mask = (
            env.action_masks()
        )

        (
            action,
            _
        ) = (
            model.predict(

                observation,

                action_masks=mask,

                deterministic=True,
            )
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

        if (
            terminated
            or truncated
        ):
            break

    metrics = (
        calculate_common_metrics(

            execution_records=(
                env.core_env
                .execution_records
            ),

            robot_states=(
                env.core_env
                .robot_states
            ),

            simulation_end_time=(
                env.core_env
                .get_simulation_end_time()
            ),

            task_count=(
                task_count
            ),
        )
    )

    env.close()

    return metrics


# ==========================================================
# Result Row
# ==========================================================

def build_result_row(
    task_count,
    load,
    seed,
    method,
    metrics,
):

    return {
        "task_count":
            task_count,

        "load":
            load,

        "battery_profile":
            BATTERY_PROFILE,

        "capability_profile":
            CAPABILITY_PROFILE,

        "method":
            method,

        "seed":
            seed,

        **metrics,
    }


# ==========================================================
# Save CSV
# ==========================================================

def save_csv(
    filepath,
    rows,
):

    if not rows:
        return

    os.makedirs(
        os.path.dirname(
            filepath
        ),
        exist_ok=True,
    )

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=(
                rows[0].keys()
            ),
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ==========================================================
# Aggregate Condition
# ==========================================================

def aggregate_condition(
    seed_results,
):

    metric_names = [
        "average_waiting_time",
        "average_completion_time",
        "emergency_waiting_time",
        "high_waiting_time",
        "total_travel_distance",
        "makespan",
        "success_rate",
        "average_robot_utilization",
        "task_load_std",
        "utilization_std",
    ]

    summary = {}

    for metric_name in (
        metric_names
    ):

        values = [
            result[
                metric_name
            ]
            for result
            in seed_results
        ]

        (
            mean_value,
            std_value,
        ) = (
            mean_std(
                values
            )
        )

        summary[
            metric_name
        ] = {
            "mean":
                mean_value,

            "std":
                std_value,
        }

    return summary


# ==========================================================
# Summary Row
# ==========================================================

def build_summary_row(
    task_count,
    load,
    method,
    seed_results,
):

    summary = (
        aggregate_condition(
            seed_results
        )
    )

    row = {
        "task_count":
            task_count,

        "load":
            load,

        "battery_profile":
            BATTERY_PROFILE,

        "capability_profile":
            CAPABILITY_PROFILE,

        "method":
            method,

        "runs":
            len(
                seed_results
            ),
    }

    for (
        metric_name,
        metric_result,
    ) in summary.items():

        row[
            f"{metric_name}_mean"
        ] = (
            metric_result[
                "mean"
            ]
        )

        row[
            f"{metric_name}_std"
        ] = (
            metric_result[
                "std"
            ]
        )

    return row


# ==========================================================
# Print Summary
# ==========================================================

def print_condition_summary(
    row,
):

    print(
        f"{row['task_count']:>4} tasks"
        f" | {row['load']:<6}"
        f" | {row['method']:<38}"
        f" | wait="
        f"{row['average_waiting_time_mean']:.2f}"
        f" ± "
        f"{row['average_waiting_time_std']:.2f}"
        f" | P3="
        f"{row['emergency_waiting_time_mean']:.2f}"
        f" ± "
        f"{row['emergency_waiting_time_std']:.2f}"
        f" | makespan="
        f"{row['makespan_mean']:.2f}"
    )


# ==========================================================
# Main
# ==========================================================

def main():

    if not os.path.exists(
        MODEL_PATH
    ):

        raise FileNotFoundError(
            "PPO model not found: "
            f"{MODEL_PATH}"
        )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    print("=" * 120)

    print(
        "FULL PRIORITY SCHEDULER COMPARISON"
    )

    print("=" * 120)

    print(
        "Task Counts:",
        TASK_COUNTS,
    )

    print(
        "Loads:",
        LOADS,
    )

    print(
        "Seeds:",
        f"{SEEDS[0]} ~ {SEEDS[-1]}",
    )

    print(
        "Battery Profile:",
        BATTERY_PROFILE,
    )

    print(
        "Capability Profile:",
        CAPABILITY_PROFILE,
    )

    print(
        "PPO Model:",
        MODEL_PATH,
    )

    total_runs = (
        len(TASK_COUNTS)
        *
        len(LOADS)
        *
        len(SEEDS)
        *
        len(METHODS)
    )

    print(
        "Total runs:",
        total_runs,
    )

    print()

    # ======================================================
    # Load PPO Once
    # ======================================================

    model = (
        MaskablePPO.load(

            MODEL_PATH,

            device="cpu",
        )
    )

    all_results = []

    completed_runs = 0

    # ======================================================
    # Full Experiment
    # ======================================================

    for task_count in TASK_COUNTS:

        for load in LOADS:

            condition_results = {
                method: []
                for method
                in METHODS
            }

            print("=" * 120)

            print(
                f"START CONDITION"
                f" | tasks={task_count}"
                f" | load={load}"
            )

            print("=" * 120)

            for seed in SEEDS:

                # ==================================================
                # Priority + Nearest
                # ==================================================

                nearest_metrics = (
                    run_baseline_episode(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,

                        robot_scheduler_name=(
                            "nearest"
                        ),
                    )
                )

                nearest_row = (
                    build_result_row(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,

                        method=(
                            "Priority + Nearest"
                        ),

                        metrics=(
                            nearest_metrics
                        ),
                    )
                )

                all_results.append(
                    nearest_row
                )

                condition_results[
                    "Priority + Nearest"
                ].append(
                    nearest_row
                )

                completed_runs += 1

                save_csv(
                    RAW_CSV,
                    all_results,
                )

                # ==================================================
                # Priority + Rule-based
                # ==================================================

                rule_metrics = (
                    run_baseline_episode(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,

                        robot_scheduler_name=(
                            "rule_based"
                        ),
                    )
                )

                rule_row = (
                    build_result_row(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,

                        method=(
                            "Priority + Rule-based"
                        ),

                        metrics=(
                            rule_metrics
                        ),
                    )
                )

                all_results.append(
                    rule_row
                )

                condition_results[
                    "Priority + Rule-based"
                ].append(
                    rule_row
                )

                completed_runs += 1

                save_csv(
                    RAW_CSV,
                    all_results,
                )

                # ==================================================
                # Priority + PPO
                # ==================================================

                rl_metrics = (
                    run_rl_episode(

                        model=model,

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,
                    )
                )

                rl_row = (
                    build_result_row(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        seed=seed,

                        method=(
                            "Priority + PPO 33D Reward v3 50K"
                        ),

                        metrics=(
                            rl_metrics
                        ),
                    )
                )

                all_results.append(
                    rl_row
                )

                condition_results[
                    "Priority + PPO 33D Reward v3 50K"
                ].append(
                    rl_row
                )

                completed_runs += 1

                save_csv(
                    RAW_CSV,
                    all_results,
                )

                # ==================================================
                # Progress
                # ==================================================

                print(
                    f"[{completed_runs:>4}"
                    f"/{total_runs}] "
                    f"tasks={task_count:<3}"
                    f" | load={load:<6}"
                    f" | seed={seed:02d}"
                    f" | wait:"
                    f" Near="
                    f"{nearest_metrics['average_waiting_time']:.2f}"
                    f" Rule="
                    f"{rule_metrics['average_waiting_time']:.2f}"
                    f" PPO="
                    f"{rl_metrics['average_waiting_time']:.2f}"
                )

    # ======================================================
    # Final Summary
    # ======================================================

    summary_rows = []

    for task_count in TASK_COUNTS:

        for load in LOADS:

            for method in METHODS:

                seed_results = [
                    result

                    for result
                    in all_results

                    if (
                        result[
                            "task_count"
                        ]
                        ==
                        task_count
                    )
                    and
                    (
                        result[
                            "load"
                        ]
                        ==
                        load
                    )
                    and
                    (
                        result[
                            "method"
                        ]
                        ==
                        method
                    )
                ]

                if not seed_results:
                    continue

                row = (
                    build_summary_row(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        method=method,

                        seed_results=(
                            seed_results
                        ),
                    )
                )

                summary_rows.append(
                    row
                )

    save_csv(
        SUMMARY_CSV,
        summary_rows,
    )

    # ======================================================
    # Print Summaries
    # ======================================================

    print()

    print("=" * 120)

    print(
        "FULL COMPARISON SUMMARY"
    )

    print("=" * 120)

    for row in summary_rows:

        print_condition_summary(
            row
        )

    # ======================================================
    # Complete
    # ======================================================

    print()

    print("=" * 120)

    print(
        "FULL COMPARISON COMPLETED"
    )

    print("=" * 120)

    print(
        "Raw results:",
        RAW_CSV,
    )

    print(
        "Summary:",
        SUMMARY_CSV,
    )

    print(
        "Total raw runs:",
        len(
            all_results
        ),
    )

    print(
        "Summary rows:",
        len(
            summary_rows
        ),
    )


if __name__ == "__main__":
    main()