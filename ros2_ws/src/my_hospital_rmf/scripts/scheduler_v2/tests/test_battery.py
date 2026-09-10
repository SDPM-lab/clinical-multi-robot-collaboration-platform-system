#!/usr/bin/env python3

import pytest

from scheduler_v2.battery import (
    calculate_battery_consumption,
    calculate_remaining_battery,
    has_enough_battery_for_task,
)


# ==========================================================
# Consumption
# ==========================================================

def test_battery_consumption():

    consumption = (
        calculate_battery_consumption(
            travel_distance=100.0,
            drain_per_meter=0.0005,
        )
    )

    assert (
        consumption
        ==
        pytest.approx(
            0.05
        )
    )


def test_zero_distance_has_zero_consumption():

    assert (
        calculate_battery_consumption(
            travel_distance=0.0,
            drain_per_meter=0.0005,
        )
        ==
        0.0
    )


def test_negative_distance_rejected():

    with pytest.raises(
        ValueError
    ):

        calculate_battery_consumption(
            travel_distance=-1.0,
            drain_per_meter=0.0005,
        )


# ==========================================================
# Remaining Battery
# ==========================================================

def test_remaining_battery():

    remaining = (
        calculate_remaining_battery(
            battery=0.80,
            consumption=0.15,
        )
    )

    assert (
        remaining
        ==
        pytest.approx(
            0.65
        )
    )


def test_remaining_battery_never_negative():

    remaining = (
        calculate_remaining_battery(
            battery=0.10,
            consumption=0.50,
        )
    )

    assert remaining == 0.0


# ==========================================================
# Safety
# ==========================================================

def test_task_is_safe_when_remaining_above_threshold():

    assert (
        has_enough_battery_for_task(
            battery=0.50,
            expected_consumption=0.10,
            safety_threshold=0.20,
        )
        is True
    )


def test_task_is_safe_exactly_at_threshold():

    assert (
        has_enough_battery_for_task(
            battery=0.30,
            expected_consumption=0.10,
            safety_threshold=0.20,
        )
        is True
    )


def test_task_is_unsafe_below_threshold():

    assert (
        has_enough_battery_for_task(
            battery=0.25,
            expected_consumption=0.10,
            safety_threshold=0.20,
        )
        is False
    )