#!/usr/bin/env python3

import csv
import os
import statistics

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.simulator import (
    BaselineSimulator,
)

from experiment.metrics import (
    calculate_metrics,
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

from scheduler.task_selection.fcfs_scheduler import (
    FCFSScheduler,
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


# ==========================================================
# Baseline Config
# ==========================================================

BASELINES = [

    {
        "name":
            "FCFS + Nearest",

        "task_scheduler":
            "fcfs",

        "robot_scheduler":
            "nearest",
    },

    {
        "name":
            "FCFS + Rule-based",

        "task_scheduler":
            "fcfs",

        "robot_scheduler":
            "rule_based",
    },

    {
        "name":
            "Priority + Nearest",

        "task_scheduler":
            "priority",

        "robot_scheduler":
            "nearest",
    },

    {
        "name":
            "Priority + Rule-based",

        "task_scheduler":
            "priority",

        "robot_scheduler":
            "rule_based",
    },
]


# ==========================================================
# Scheduler Factory
# ==========================================================

def create_task_scheduler(
    name,
):

    if name == "fcfs":
        return FCFSScheduler()

    if name == "priority":
        return PriorityScheduler()

    raise ValueError(
        f"Unknown task scheduler: {name}"
    )


def create_robot_scheduler(
    name,
    waypoints,
):

    if name == "nearest":

        return NearestScheduler(
            waypoints
        )

    if name == "rule_based":

        return RuleBasedScheduler(
            waypoints
        )

    raise ValueError(
        f"Unknown robot scheduler: {name}"
    )


# ==========================================================
# Statistics Helper
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

    if len(values) >= 2:

        std_value = (
            statistics.stdev(
                values
            )
        )

    else:

        std_value = 0.0

    return (
        mean_value,
        std_value,
    )


# ==========================================================
# Run One Seed
# ==========================================================

def run_single_seed(
    task_count,
    load,
    seed,
    baseline,
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

    task_scheduler = (
        create_task_scheduler(
            baseline[
                "task_scheduler"
            ]
        )
    )

    robot_scheduler = (
        create_robot_scheduler(

            baseline[
                "robot_scheduler"
            ],

            scenario.waypoints,
        )
    )

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            task_scheduler
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

    simulation_result = (
        simulator.run()
    )

    metrics = calculate_metrics(
        simulation_result
    )

    task_metrics = (
        metrics[
            "task_metrics"
        ]
    )

    robot_metrics = (
        metrics[
            "robot_metrics"
        ]
    )

    return {

        "task_count":
            task_count,

        "load":
            load,

        "battery_profile":
            BATTERY_PROFILE,

        "capability_profile":
            CAPABILITY_PROFILE,

        "baseline":
            baseline[
                "name"
            ],

        "seed":
            seed,

        "average_waiting_time":
            task_metrics[
                "average_waiting_time"
            ],

        "average_completion_time":
            task_metrics[
                "average_completion_time"
            ],

        "emergency_waiting_time":
            task_metrics[
                "priority_waiting_time"
            ][3],

        "high_waiting_time":
            task_metrics[
                "priority_waiting_time"
            ][2],

        "total_travel_distance":
            task_metrics[
                "total_travel_distance"
            ],

        "makespan":
            metrics[
                "simulation_end_time"
            ],

        "success_rate":
            task_metrics[
                "success_rate"
            ],

        "average_robot_utilization":
            robot_metrics[
                "average_robot_utilization"
            ],

        "task_load_std":
            robot_metrics[
                "task_load_std"
            ],

        "utilization_std":
            robot_metrics[
                "utilization_std"
            ],
    }


# ==========================================================
# Aggregate One Experiment Condition
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

    for metric_name in metric_names:

        values = [

            result[
                metric_name
            ]

            for result
            in seed_results
        ]

        mean_value, std_value = (
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
# Convert Summary To CSV Row
# ==========================================================

def summary_to_row(
    task_count,
    load,
    baseline_name,
    summary,
):

    row = {

        "task_count":
            task_count,

        "load":
            load,

        "battery_profile":
            BATTERY_PROFILE,

        "capability_profile":
            CAPABILITY_PROFILE,

        "baseline":
            baseline_name,

        "runs":
            len(
                SEEDS
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

        writer = (
            csv.DictWriter(

                file,

                fieldnames=(
                    rows[0].keys()
                ),
            )
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ==========================================================
# Print One Summary
# ==========================================================

def print_condition_summary(
    row,
):

    print(
        f"{row['task_count']:>4} tasks"
        f" | {row['load']:<6}"
        f" | {row['baseline']:<24}"
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

    all_seed_results = []

    all_summary_rows = []

    total_conditions = (
        len(TASK_COUNTS)
        * len(LOADS)
        * len(BASELINES)
    )

    current_condition = 0

    print("=" * 120)
    print("FULL BASELINE EXPERIMENT")
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
        "Battery Profile:",
        BATTERY_PROFILE,
    )

    print(
        "Capability Profile:",
        CAPABILITY_PROFILE,
    )

    print(
        "Seeds:",
        f"{SEEDS[0]} ~ {SEEDS[-1]}",
    )

    print(
        "Total runs:",
        (
            len(TASK_COUNTS)
            * len(LOADS)
            * len(SEEDS)
            * len(BASELINES)
        ),
    )

    print()

    # ======================================================
    # Task Count × Load × Baseline
    # ======================================================

    for task_count in TASK_COUNTS:

        for load in LOADS:

            for baseline in BASELINES:

                current_condition += 1

                print(
                    f"[{current_condition}"
                    f"/{total_conditions}] "
                    f"{task_count} tasks"
                    f" | {load}"
                    f" | "
                    f"{baseline['name']}"
                )

                seed_results = []

                # ------------------------------------------
                # 30 Seeds
                # ------------------------------------------

                for seed in SEEDS:

                    result = (
                        run_single_seed(

                            task_count=(
                                task_count
                            ),

                            load=load,

                            seed=seed,

                            baseline=baseline,
                        )
                    )

                    seed_results.append(
                        result
                    )

                    all_seed_results.append(
                        result
                    )

                # ------------------------------------------
                # Mean ± Std
                # ------------------------------------------

                summary = (
                    aggregate_condition(
                        seed_results
                    )
                )

                row = (
                    summary_to_row(

                        task_count=(
                            task_count
                        ),

                        load=load,

                        baseline_name=(
                            baseline[
                                "name"
                            ]
                        ),

                        summary=summary,
                    )
                )

                all_summary_rows.append(
                    row
                )

                print_condition_summary(
                    row
                )

    # ======================================================
    # Save Results
    # ======================================================

    script_dir = os.path.dirname(
        os.path.abspath(
            __file__
        )
    )

    output_dir = os.path.join(
        script_dir,
        "results",
    )

    raw_csv = os.path.join(
        output_dir,
        "baseline_raw_results.csv",
    )

    summary_csv = os.path.join(
        output_dir,
        "baseline_summary.csv",
    )

    save_csv(
        raw_csv,
        all_seed_results,
    )

    save_csv(
        summary_csv,
        all_summary_rows,
    )

    print()
    print("=" * 120)
    print("EXPERIMENT COMPLETED")
    print("=" * 120)

    print(
        "Raw results:",
        raw_csv,
    )

    print(
        "Summary:",
        summary_csv,
    )

    print(
        "Raw runs:",
        len(
            all_seed_results
        ),
    )

    print(
        "Summary rows:",
        len(
            all_summary_rows
        ),
    )


if __name__ == "__main__":
    main()