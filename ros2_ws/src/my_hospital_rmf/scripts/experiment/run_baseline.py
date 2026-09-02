#!/usr/bin/env python3

from experiment.scenarios import (
    get_scenario,
    list_scenarios,
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
# Run One Experiment
# ==========================================================

def run_experiment(
    scenario_name,
    baseline_config,
):

    scenario = get_scenario(
        scenario_name
    )

    task_scheduler = (
        create_task_scheduler(
            baseline_config[
                "task_scheduler"
            ]
        )
    )

    robot_scheduler = (
        create_robot_scheduler(
            baseline_config[
                "robot_scheduler"
            ],
            scenario.waypoints,
        )
    )

    simulator = BaselineSimulator(
        scenario=scenario,
        task_scheduler=task_scheduler,
        robot_scheduler=robot_scheduler,
        robot_speed=1.0,
        service_time=5.0,
    )

    simulation_result = (
        simulator.run()
    )

    metrics = calculate_metrics(
        simulation_result
    )

    return {
        "scenario":
            scenario_name,

        "baseline":
            baseline_config[
                "name"
            ],

        "simulation_result":
            simulation_result,

        "metrics":
            metrics,
    }


# ==========================================================
# Print Detailed Result
# ==========================================================

def print_experiment_result(
    result,
):

    scenario_name = (
        result["scenario"]
    )

    baseline_name = (
        result["baseline"]
    )

    simulation_result = (
        result[
            "simulation_result"
        ]
    )

    metrics = (
        result["metrics"]
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

    print()
    print("=" * 100)

    print(
        f"Scenario: {scenario_name}"
    )

    print(
        f"Baseline: {baseline_name}"
    )

    print("=" * 100)

    # ------------------------------------------------------
    # Task Execution
    # ------------------------------------------------------

    print()
    print("Task execution")

    print("-" * 100)

    for record in simulation_result[
        "records"
    ]:

        if record.success:

            print(
                f"{record.task_id}"
                f" | P={record.priority}"
                f" | robot={record.robot_id}"
                f" | wait={record.waiting_time:.2f}"
                f" | complete={record.completion_time:.2f}"
                f" | distance={record.travel_distance:.2f}"
            )

        else:

            print(
                f"{record.task_id}"
                f" | P={record.priority}"
                " | FAILED"
            )

    # ------------------------------------------------------
    # Metrics
    # ------------------------------------------------------

    print()
    print("Metrics")

    print("-" * 100)

    print(
        "Success rate          :",
        f"{task_metrics['success_rate']:.3f}",
    )

    print(
        "Average waiting time  :",
        f"{task_metrics['average_waiting_time']:.2f}",
    )

    print(
        "Average completion    :",
        f"{task_metrics['average_completion_time']:.2f}",
    )

    print(
        "Total travel distance :",
        f"{task_metrics['total_travel_distance']:.2f}",
    )

    print(
        "Makespan              :",
        f"{metrics['simulation_end_time']:.2f}",
    )

    print(
        "Average utilization   :",
        f"{robot_metrics['average_robot_utilization']:.3f}",
    )

    print(
        "Task load std         :",
        f"{robot_metrics['task_load_std']:.3f}",
    )

    print(
        "Utilization std       :",
        f"{robot_metrics['utilization_std']:.3f}",
    )

    priority_waiting = (
        task_metrics[
            "priority_waiting_time"
        ]
    )

    print(
        "Emergency wait (P3)   :",
        f"{priority_waiting[3]:.2f}",
    )


# ==========================================================
# Summary Table
# ==========================================================

def print_summary(
    results,
):

    print()
    print()
    print("=" * 145)
    print("BASELINE SUMMARY")
    print("=" * 145)

    header = (
        f"{'Scenario':<28}"
        f"{'Baseline':<28}"
        f"{'Wait':>10}"
        f"{'Complete':>12}"
        f"{'P3 Wait':>12}"
        f"{'Distance':>12}"
        f"{'Makespan':>12}"
        f"{'Util':>10}"
        f"{'Success':>10}"
    )

    print(
        header
    )

    print("-" * 145)

    for result in results:

        task_metrics = (
            result[
                "metrics"
            ][
                "task_metrics"
            ]
        )

        robot_metrics = (
            result[
                "metrics"
            ][
                "robot_metrics"
            ]
        )

        makespan = (
            result[
                "metrics"
            ][
                "simulation_end_time"
            ]
        )

        priority_waiting = (
            task_metrics[
                "priority_waiting_time"
            ]
        )

        print(
            f"{result['scenario']:<28}"
            f"{result['baseline']:<28}"
            f"{task_metrics['average_waiting_time']:>10.2f}"
            f"{task_metrics['average_completion_time']:>12.2f}"
            f"{priority_waiting[3]:>12.2f}"
            f"{task_metrics['total_travel_distance']:>12.2f}"
            f"{makespan:>12.2f}"
            f"{robot_metrics['average_robot_utilization']:>10.3f}"
            f"{task_metrics['success_rate']:>10.3f}"
        )


# ==========================================================
# Main
# ==========================================================

def main():

    results = []

    # ------------------------------------------------------
    # 所有 Scenario
    # ×
    # 所有 Baseline
    # ------------------------------------------------------

    for scenario_name in (
        list_scenarios()
    ):

        for baseline in BASELINES:

            result = run_experiment(
                scenario_name,
                baseline,
            )

            results.append(
                result
            )

            print_experiment_result(
                result
            )

    # ------------------------------------------------------
    # 最後總表
    # ------------------------------------------------------

    print_summary(
        results
    )


if __name__ == "__main__":
    main()