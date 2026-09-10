#!/usr/bin/env python3

from experiment_v2.run_multi_seed import (
    run_multi_seed,
    summarize_values,
)


def test_summarize_values():

    summary = summarize_values(
        [
            1.0,
            2.0,
            3.0,
        ]
    )

    assert (
        summary["mean"]
        ==
        2.0
    )

    assert (
        summary["median"]
        ==
        2.0
    )

    assert (
        summary["std"]
        >
        0.0
    )


def test_multi_seed_runs_four_paired_baselines():

    raw_results, rows = (
        run_multi_seed(
            seed_start=8100,
            seed_end=8102,
            task_count=10,
        )
    )

    # 3 seeds × 4 methods
    assert len(
        rows
    ) == 12

    methods = {
        row["method"]
        for row in rows
    }

    assert methods == {
        "random_feasible",
        "projected_nearest",
        "weighted_heuristic",
        "dynamic_weighted_heuristic",
    }

    seeds = {
        row["seed"]
        for row in rows
    }

    assert seeds == {
        8100,
        8101,
        8102,
    }

    for method in methods:

        assert len(
            raw_results[
                method
            ][
                "waiting_time"
            ]
        ) == 3

        assert len(
            raw_results[
                method
            ][
                "completion_time"
            ]
        ) == 3


def test_static_methods_have_zero_reassignments():

    raw_results, _ = (
        run_multi_seed(
            seed_start=8100,
            seed_end=8101,
            task_count=10,
        )
    )

    for method in [
        "random_feasible",
        "projected_nearest",
        "weighted_heuristic",
    ]:

        assert all(
            value == 0.0
            for value
            in raw_results[
                method
            ][
                "reassignment_count"
            ]
        )

        assert all(
            value == 0.0
            for value
            in raw_results[
                method
            ][
                "max_cascade_depth"
            ]
        )