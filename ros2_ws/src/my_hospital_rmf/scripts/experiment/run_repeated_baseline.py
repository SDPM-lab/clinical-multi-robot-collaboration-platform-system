#!/usr/bin/env python3

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
        "name": "FCFS + Nearest",
        "task_scheduler": "fcfs",
        "robot_scheduler": "nearest",
    },

    {
        "name": "FCFS + Rule-based",
        "task_scheduler": "fcfs",
        "robot_scheduler": "rule_based",
    },

    {
        "name": "Priority + Nearest",
        "task_scheduler": "priority",
        "robot_scheduler": "nearest",
    },

    {
        "name": "Priority + Rule-based",
        "task_scheduler": "priority",
        "robot_scheduler": "rule_based",
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

    # ------------------------------------------------------
    # 忽略 None
    #
    # None 代表：
    # 該 seed 中沒有這類 Priority Task，
    # 不能當成等待時間 0 秒。
    # ------------------------------------------------------

    values = [

        value

        for value
        in values

        if value is not None
    ]

    if not values:

        return (
            0.0,
            0.0,
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
    battery_profile,
    capability_profile,
    seed,
    baseline,
):

    scenario = generate_random_scenario(
        task_count=task_count,
        seed=seed,
        load=load,
        battery_profile=battery_profile,
        capability_profile=capability_profile,
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

        robot_speed=1.0,

        service_time=5.0,
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
# Aggregate Multiple Seeds
# ==========================================================

def aggregate_results(
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
# Run One Baseline Across Seeds
# ==========================================================

def run_repeated_experiment(
    task_count,
    load,
    battery_profile,
    capability_profile,
    seeds,
    baseline,
):

    seed_results = []

    for seed in seeds:

        result = run_single_seed(
            task_count=task_count,
            load=load,
            battery_profile=battery_profile,
            capability_profile=capability_profile,
            seed=seed,
            baseline=baseline,
        )

        seed_results.append(
            result
        )

    summary = (
        aggregate_results(
            seed_results
        )
    )

    return {

        "task_count":
            task_count,

        "load":
            load,

        "battery_profile":
            battery_profile,

        "baseline":
            baseline[
                "name"
            ],

        "runs":
            len(
                seed_results
            ),

        "seed_results":
            seed_results,

        "summary":
            summary,
    }


# ==========================================================
# Print Result
# ==========================================================

def print_result(
    result,
):

    print()
    print("=" * 110)

    print(
        "Task Count:",
        result[
            "task_count"
        ],
        "| Load:",
        result[
            "load"
        ],
        "| Battery:",
        result[
            "battery_profile"
        ],
        "| Baseline:",
        result[
            "baseline"
        ],
        "| Runs:",
        result[
            "runs"
        ],
    )

    print("=" * 110)

    summary = (
        result[
            "summary"
        ]
    )

    def show(
        label,
        key,
    ):

        mean_value = (
            summary[
                key
            ][
                "mean"
            ]
        )

        std_value = (
            summary[
                key
            ][
                "std"
            ]
        )

        print(
            f"{label:<30}"
            f"{mean_value:>12.2f}"
            f" ± "
            f"{std_value:.2f}"
        )

    show(
        "Average waiting",
        "average_waiting_time",
    )

    show(
        "Average completion",
        "average_completion_time",
    )

    show(
        "Emergency waiting",
        "emergency_waiting_time",
    )

    show(
        "High priority waiting",
        "high_waiting_time",
    )

    show(
        "Total travel distance",
        "total_travel_distance",
    )

    show(
        "Makespan",
        "makespan",
    )

    show(
        "Success rate",
        "success_rate",
    )

    show(
        "Average utilization",
        "average_robot_utilization",
    )

    show(
        "Task load std",
        "task_load_std",
    )

    show(
        "Utilization std",
        "utilization_std",
    )


# ==========================================================
# Comparison Summary
# ==========================================================

def print_comparison(
    results,
):

    print()
    print()
    print("=" * 160)
    print("REPEATED BASELINE SUMMARY")
    print("=" * 160)

    print(
        f"{'Baseline':<30}"
        f"{'Wait Mean':>12}"
        f"{'Wait Std':>12}"
        f"{'P3 Mean':>12}"
        f"{'Complete':>12}"
        f"{'Distance':>14}"
        f"{'Makespan':>12}"
        f"{'Util':>10}"
        f"{'Success':>10}"
    )

    print("-" * 160)

    for result in results:

        summary = (
            result[
                "summary"
            ]
        )

        print(
            f"{result['baseline']:<30}"

            f"{summary['average_waiting_time']['mean']:>12.2f}"

            f"{summary['average_waiting_time']['std']:>12.2f}"

            f"{summary['emergency_waiting_time']['mean']:>12.2f}"

            f"{summary['average_completion_time']['mean']:>12.2f}"

            f"{summary['total_travel_distance']['mean']:>14.2f}"

            f"{summary['makespan']['mean']:>12.2f}"

            f"{summary['average_robot_utilization']['mean']:>10.3f}"

            f"{summary['success_rate']['mean']:>10.3f}"
        )


# ==========================================================
# Main
# ==========================================================

def main():

    # ------------------------------------------------------
    # 第一輪先測：
    #
    # 20 Tasks
    # Medium Load
    # 10 Seeds
    #
    # 確認流程完全正常後，
    # 再升級到 30 Seeds + 20/50/100 Tasks。
    # ------------------------------------------------------

    task_count = 20

    load = "medium"

    battery_profile = "stress"

    capability_profile = "competitive"

    seeds = range(
        10
    )

    results = []

    for baseline in BASELINES:

        result = run_repeated_experiment(
            task_count=task_count,
            load=load,
            battery_profile=battery_profile,
            capability_profile=capability_profile,
            seeds=seeds,
            baseline=baseline,
        )

        results.append(
            result
        )

        print_result(
            result
        )

    print_comparison(
        results
    )


if __name__ == "__main__":
    main()