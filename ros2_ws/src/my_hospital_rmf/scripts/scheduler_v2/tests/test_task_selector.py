#!/usr/bin/env python3

import pytest

from scheduler_v2.models import (
    Task,
)

from scheduler_v2.task_selector import (
    calculate_waiting_time,
    calculate_effective_priority,
    sort_tasks,
    select_next_task,
)


# ==========================================================
# Helper
# ==========================================================

def make_task(
    task_id: str,
    priority: int,
    created_at: float,
) -> Task:

    return Task(
        task_id=task_id,
        task_type="general_delivery",
        source="storage",
        destination="ward_a",
        priority=priority,
        required_capabilities={
            "navigation",
            "general_delivery",
        },
        created_at=created_at,
    )


# ==========================================================
# Waiting Time
# ==========================================================

def test_waiting_time():

    task = make_task(
        task_id="T001",
        priority=1,
        created_at=100.0,
    )

    waiting_time = (
        calculate_waiting_time(
            task=task,
            current_time=160.0,
        )
    )

    assert waiting_time == 60.0


def test_waiting_time_never_negative():

    task = make_task(
        task_id="T001",
        priority=1,
        created_at=100.0,
    )

    waiting_time = (
        calculate_waiting_time(
            task=task,
            current_time=90.0,
        )
    )

    assert waiting_time == 0.0


# ==========================================================
# Effective Priority
# ==========================================================

def test_effective_priority_without_waiting():

    task = make_task(
        task_id="T001",
        priority=2,
        created_at=100.0,
    )

    score = (
        calculate_effective_priority(
            task=task,
            current_time=100.0,
            aging_interval_seconds=120.0,
        )
    )

    assert score == 2.0


def test_effective_priority_with_aging():

    task = make_task(
        task_id="T001",
        priority=0,
        created_at=0.0,
    )

    score = (
        calculate_effective_priority(
            task=task,
            current_time=360.0,
            aging_interval_seconds=120.0,
        )
    )

    assert score == 3.0


def test_aging_does_not_modify_original_priority():

    task = make_task(
        task_id="T001",
        priority=0,
        created_at=0.0,
    )

    calculate_effective_priority(
        task=task,
        current_time=360.0,
        aging_interval_seconds=120.0,
    )

    assert task.priority == 0


def test_invalid_aging_interval():

    task = make_task(
        task_id="T001",
        priority=1,
        created_at=0.0,
    )

    with pytest.raises(
        ValueError
    ):

        calculate_effective_priority(
            task=task,
            current_time=100.0,
            aging_interval_seconds=0.0,
        )


# ==========================================================
# Priority Selection
# ==========================================================

def test_higher_priority_selected_first():

    low = make_task(
        "LOW",
        priority=0,
        created_at=0.0,
    )

    high = make_task(
        "HIGH",
        priority=2,
        created_at=0.0,
    )

    selected = (
        select_next_task(
            tasks=[
                low,
                high,
            ],
            current_time=0.0,
            aging_interval_seconds=120.0,
        )
    )

    assert selected is high


# ==========================================================
# Aging
# ==========================================================

def test_old_low_priority_can_overtake_newer_high_priority():

    old_low = make_task(
        "OLD_LOW",
        priority=0,
        created_at=0.0,
    )

    newer_high = make_task(
        "NEW_HIGH",
        priority=2,
        created_at=300.0,
    )

    # current_time = 360
    #
    # OLD_LOW:
    # 0 + 360 / 120 = 3.0
    #
    # NEW_HIGH:
    # 2 + 60 / 120 = 2.5
    #
    # 所以 OLD_LOW 應因 Aging 排到前面。
    selected = (
        select_next_task(
            tasks=[
                newer_high,
                old_low,
            ],
            current_time=360.0,
            aging_interval_seconds=120.0,
        )
    )

    assert selected is old_low


# ==========================================================
# Emergency Protection
# ==========================================================

def test_emergency_cannot_be_overtaken_by_aging():

    very_old_low = make_task(
        "VERY_OLD_LOW",
        priority=0,
        created_at=0.0,
    )

    new_emergency = make_task(
        "NEW_EMERGENCY",
        priority=3,
        created_at=1000.0,
    )

    # current_time = 1200
    #
    # VERY_OLD_LOW:
    #
    # waiting = 1200
    # effective_priority
    # = 0 + 1200 / 120
    # = 10
    #
    # NEW_EMERGENCY:
    #
    # waiting = 200
    # effective_priority
    # = 3 + 200 / 120
    # ≈ 4.67
    #
    # 如果只看 Effective Priority，
    # VERY_OLD_LOW 會排在前面。
    #
    # 但因為 Emergency 是保護層級，
    # NEW_EMERGENCY 必須永遠優先。

    selected = (
        select_next_task(
            tasks=[
                very_old_low,
                new_emergency,
            ],
            current_time=1200.0,
            aging_interval_seconds=120.0,
        )
    )

    assert selected is new_emergency


def test_older_emergency_selected_first():

    old_emergency = make_task(
        "OLD_EMERGENCY",
        priority=3,
        created_at=100.0,
    )

    new_emergency = make_task(
        "NEW_EMERGENCY",
        priority=3,
        created_at=200.0,
    )

    selected = (
        select_next_task(
            tasks=[
                new_emergency,
                old_emergency,
            ],
            current_time=300.0,
            aging_interval_seconds=120.0,
        )
    )

    assert selected is old_emergency


# ==========================================================
# FCFS Tie Break
# ==========================================================

def test_same_effective_priority_uses_fcfs():

    old_normal = make_task(
        "OLD_NORMAL",
        priority=1,
        created_at=0.0,
    )

    new_high = make_task(
        "NEW_HIGH",
        priority=2,
        created_at=120.0,
    )

    # current_time = 240
    #
    # OLD_NORMAL:
    # 1 + 240 / 120 = 3
    #
    # NEW_HIGH:
    # 2 + 120 / 120 = 3
    #
    # effective priority 相同，
    # OLD_NORMAL 較早建立，
    # 所以 FCFS 應先。
    selected = (
        select_next_task(
            tasks=[
                new_high,
                old_normal,
            ],
            current_time=240.0,
            aging_interval_seconds=120.0,
        )
    )

    assert selected is old_normal


# ==========================================================
# Deterministic Tie Break
# ==========================================================

def test_same_priority_and_arrival_uses_task_id():

    task_b = make_task(
        "T002",
        priority=1,
        created_at=0.0,
    )

    task_a = make_task(
        "T001",
        priority=1,
        created_at=0.0,
    )

    ordered = (
        sort_tasks(
            tasks=[
                task_b,
                task_a,
            ],
            current_time=0.0,
            aging_interval_seconds=120.0,
        )
    )

    assert [
        task.task_id
        for task in ordered
    ] == [
        "T001",
        "T002",
    ]


# ==========================================================
# Empty Queue
# ==========================================================

def test_empty_task_list_returns_none():

    selected = (
        select_next_task(
            tasks=[],
            current_time=0.0,
        )
    )

    assert selected is None