#!/usr/bin/env python3

from experiment_v2.run_multi_seed_static import (
    run_multi_seed_static,
    summarize_values,
)


def test_summarize_values():

    summary = (
        summarize_values(
            [
                1.0,
                2.0,
                3.0,
            ]
        )
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


def test_multi_seed_runs_paired_scenarios():

    raw_results, rows = (
        run_multi_seed_static(
            seed_start=8100,
            seed_end=8102,
            task_count=10,
        )
    )

    # 3 seeds × 3 methods
    assert len(
        rows
    ) == 9

    methods = {
        row["method"]
        for row in rows
    }

    assert methods == {
        "random_feasible",
        "projected_nearest",
        "weighted_heuristic",
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