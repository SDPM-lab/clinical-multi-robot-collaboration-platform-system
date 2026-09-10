#!/usr/bin/env python3

import pytest

from experiment_v2.paired_statistics import (
    calculate_median,
    compare_paired_metric,
)


# ==========================================================
# Median
# ==========================================================

def test_median_odd():

    assert (
        calculate_median(
            [
                3.0,
                1.0,
                2.0,
            ]
        )
        ==
        2.0
    )


def test_median_even():

    assert (
        calculate_median(
            [
                1.0,
                2.0,
                3.0,
                4.0,
            ]
        )
        ==
        2.5
    )


# ==========================================================
# Lower Is Better
# ==========================================================

def test_paired_lower_is_better():

    rows = [
        {
            "seed": 1,
            "method": "A",
            "waiting_time": 10.0,
        },
        {
            "seed": 1,
            "method": "B",
            "waiting_time": 20.0,
        },

        {
            "seed": 2,
            "method": "A",
            "waiting_time": 15.0,
        },
        {
            "seed": 2,
            "method": "B",
            "waiting_time": 25.0,
        },

        {
            "seed": 3,
            "method": "A",
            "waiting_time": 30.0,
        },
        {
            "seed": 3,
            "method": "B",
            "waiting_time": 20.0,
        },
    ]

    result = (
        compare_paired_metric(
            rows=rows,
            metric="waiting_time",
            method_a="A",
            method_b="B",
            lower_is_better=True,
        )
    )

    assert (
        result.sample_count
        ==
        3
    )

    assert (
        result.wins_a
        ==
        2
    )

    assert (
        result.wins_b
        ==
        1
    )

    assert (
        result.ties
        ==
        0
    )


# ==========================================================
# Higher Is Better
# ==========================================================

def test_paired_higher_is_better():

    rows = [
        {
            "seed": 1,
            "method": "A",
            "jain_fairness": 0.9,
        },
        {
            "seed": 1,
            "method": "B",
            "jain_fairness": 0.8,
        },

        {
            "seed": 2,
            "method": "A",
            "jain_fairness": 0.95,
        },
        {
            "seed": 2,
            "method": "B",
            "jain_fairness": 0.80,
        },
    ]

    result = (
        compare_paired_metric(
            rows=rows,
            metric="jain_fairness",
            method_a="A",
            method_b="B",
            lower_is_better=False,
        )
    )

    assert (
        result.wins_a
        ==
        2
    )

    assert (
        result.wins_b
        ==
        0
    )


# ==========================================================
# All Ties
# ==========================================================

def test_all_ties_have_no_p_value():

    rows = [
        {
            "seed": 1,
            "method": "A",
            "success_rate": 1.0,
        },
        {
            "seed": 1,
            "method": "B",
            "success_rate": 1.0,
        },

        {
            "seed": 2,
            "method": "A",
            "success_rate": 1.0,
        },
        {
            "seed": 2,
            "method": "B",
            "success_rate": 1.0,
        },
    ]

    result = (
        compare_paired_metric(
            rows=rows,
            metric="success_rate",
            method_a="A",
            method_b="B",
            lower_is_better=False,
        )
    )

    assert (
        result.ties
        ==
        2
    )

    assert (
        result.p_value
        is None
    )


# ==========================================================
# No Pair
# ==========================================================

def test_no_pair_rejected():

    with pytest.raises(
        ValueError
    ):

        compare_paired_metric(
            rows=[
                {
                    "seed": 1,
                    "method": "A",
                    "waiting_time": 10.0,
                },
            ],
            metric="waiting_time",
            method_a="A",
            method_b="B",
            lower_is_better=True,
        )