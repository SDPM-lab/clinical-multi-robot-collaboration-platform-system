#!/usr/bin/env python3

from experiment_v2.run_baselines import (
    run_all_baselines,
)


def test_all_baselines_run():

    results = run_all_baselines(
        seed=8000,
        task_count=20,
    )

    assert len(
        results
    ) == 4

    methods = [
        result.method
        for result
        in results
    ]

    assert methods == [
        "random_feasible",
        "projected_nearest",
        "weighted_heuristic",
        "dynamic_weighted_heuristic",
    ]


def test_all_baseline_metrics_are_valid():

    results = run_all_baselines(
        seed=8000,
        task_count=20,
    )

    for result in results:

        metrics = result.metrics

        assert (
            metrics.total_tasks
            ==
            20
        )

        assert (
            0.0
            <=
            metrics.task_success_rate
            <=
            1.0
        )

        assert (
            metrics.total_travel_distance
            >=
            0.0
        )

        assert (
            0.0
            <=
            metrics.jain_fairness_index
            <=
            1.0
        )

        assert (
            metrics
            .average_decision_time_seconds
            >=
            0.0
        )

        assert (
            metrics
            .reassignment_decision_count
            >=
            0
        )

        assert (
            metrics.reassignment_count
            >=
            0
        )

        assert (
            0.0
            <=
            metrics.reassignment_rate
            <=
            1.0
        )