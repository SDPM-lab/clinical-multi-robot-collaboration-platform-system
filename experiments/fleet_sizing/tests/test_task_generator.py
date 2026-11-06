from pathlib import Path
from collections import Counter, defaultdict
import sys

CURRENT_DIR = Path(__file__).resolve().parent
FLEET_SIZING_DIR = CURRENT_DIR.parent

if str(FLEET_SIZING_DIR) not in sys.path:
    sys.path.insert(0, str(FLEET_SIZING_DIR))

from config import (
    SIMULATION_DAYS,
    SECONDS_PER_DAY,
    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
    NORMAL_WORKLOAD_PER_DAY,
    WASTE_SOURCES,
    WASTE_DESTINATION,
    CLOTHES_SOURCES,
    CLOTHES_DESTINATION,
    MEDICATION_SOURCE,
    MEDICATION_DESTINATIONS,
    SPECIMEN_CLINICAL_LOCATIONS,
    SPECIMEN_LAB,
    WARD_SOURCE,
    WARD_DESTINATIONS,
    TASK_PRIORITY_DISTRIBUTIONS,
)

from task_generator import NormalTaskGenerator
from collections import Counter


def test_same_seed_is_reproducible():
    tasks1 = NormalTaskGenerator(seed=42).generate()
    tasks2 = NormalTaskGenerator(seed=42).generate()

    assert tasks1 == tasks2


def test_tasks_are_sorted_by_arrival_time():
    tasks = NormalTaskGenerator(seed=42).generate()

    arrival_times = [
        task.arrival_time_s
        for task in tasks
    ]

    assert arrival_times == sorted(arrival_times)


def test_all_arrivals_inside_simulation_horizon():
    tasks = NormalTaskGenerator(seed=42).generate()

    horizon = SIMULATION_DAYS * SECONDS_PER_DAY

    for task in tasks:
        assert 0 <= task.arrival_time_s < horizon


def test_source_and_destination_are_never_equal():
    tasks = NormalTaskGenerator(seed=42).generate()

    for task in tasks:
        assert task.source != task.destination


def test_waste_routes_are_valid():
    tasks = NormalTaskGenerator(seed=42).generate()

    waste_tasks = [
        task
        for task in tasks
        if task.task_type == TASK_WASTE
    ]

    for task in waste_tasks:
        assert task.source in WASTE_SOURCES
        assert task.destination == WASTE_DESTINATION


def test_clothes_routes_are_valid():
    tasks = NormalTaskGenerator(seed=42).generate()

    clothes_tasks = [
        task
        for task in tasks
        if task.task_type == TASK_CLOTHES
    ]

    for task in clothes_tasks:
        assert task.source in CLOTHES_SOURCES
        assert task.destination == CLOTHES_DESTINATION


def test_medication_routes_are_valid():
    tasks = NormalTaskGenerator(seed=42).generate()

    medication_tasks = [
        task
        for task in tasks
        if task.task_type == TASK_MEDICATION
    ]

    for task in medication_tasks:
        assert task.source == MEDICATION_SOURCE
        assert task.destination in MEDICATION_DESTINATIONS


def test_specimen_routes_are_bidirectional_lab_routes():
    tasks = NormalTaskGenerator(seed=42).generate()

    specimen_tasks = [
        task
        for task in tasks
        if task.task_type == TASK_SPECIMEN
    ]

    for task in specimen_tasks:

        clinical_to_lab = (
            task.source in SPECIMEN_CLINICAL_LOCATIONS
            and task.destination == SPECIMEN_LAB
        )

        lab_to_clinical = (
            task.source == SPECIMEN_LAB
            and task.destination
            in SPECIMEN_CLINICAL_LOCATIONS
        )

        assert clinical_to_lab or lab_to_clinical


def test_ward_routes_are_valid():
    tasks = NormalTaskGenerator(seed=42).generate()

    ward_tasks = [
        task
        for task in tasks
        if task.task_type == TASK_WARD
    ]

    for task in ward_tasks:
        assert task.source == WARD_SOURCE
        assert task.destination in WARD_DESTINATIONS


def test_ward_has_exactly_four_tasks_per_day():
    tasks = NormalTaskGenerator(seed=42).generate()

    daily_counts = defaultdict(int)

    for task in tasks:
        if task.task_type != TASK_WARD:
            continue

        day = int(
            task.arrival_time_s
            // SECONDS_PER_DAY
        )

        daily_counts[day] += 1

    for day in range(SIMULATION_DAYS):
        assert daily_counts[day] == 4


def test_long_run_average_matches_normal_workload():
    """
    Normal workload values are expected daily counts,
    not exact daily counts.

    Run many independent seeds and verify that
    long-run averages converge near the configured means.
    """

    number_of_seeds = 100

    totals = Counter()

    total_days = (
        number_of_seeds
        * SIMULATION_DAYS
    )

    for seed in range(number_of_seeds):

        tasks = NormalTaskGenerator(
            seed=seed
        ).generate()

        for task in tasks:
            totals[task.task_type] += 1

    averages = {
        task_type: count / total_days
        for task_type, count
        in totals.items()
    }

    # Tolerances are intentionally wider than the
    # expected sampling error, so the test checks
    # model correctness rather than one random fluctuation.

    assert abs(
        averages[TASK_WASTE]
        - NORMAL_WORKLOAD_PER_DAY[TASK_WASTE]
    ) < 0.5

    assert abs(
        averages[TASK_CLOTHES]
        - NORMAL_WORKLOAD_PER_DAY[TASK_CLOTHES]
    ) < 0.2

    assert abs(
        averages[TASK_MEDICATION]
        - NORMAL_WORKLOAD_PER_DAY[TASK_MEDICATION]
    ) < 0.7

    assert abs(
        averages[TASK_SPECIMEN]
        - NORMAL_WORKLOAD_PER_DAY[TASK_SPECIMEN]
    ) < 0.7

    assert abs(
        averages[TASK_WARD]
        - NORMAL_WORKLOAD_PER_DAY[TASK_WARD]
    ) < 0.01


def test_long_run_total_average_is_about_58_per_day():
    number_of_seeds = 100

    total_tasks = 0

    total_days = (
        number_of_seeds
        * SIMULATION_DAYS
    )

    for seed in range(number_of_seeds):

        tasks = NormalTaskGenerator(
            seed=seed
        ).generate()

        total_tasks += len(tasks)

    average_per_day = (
        total_tasks / total_days
    )

    expected_per_day = sum(
        NORMAL_WORKLOAD_PER_DAY.values()
    )

    assert abs(
        average_per_day
        - expected_per_day
    ) < 1.0

def test_all_priorities_are_valid():
    tasks = NormalTaskGenerator(
        seed=42
    ).generate()

    for task in tasks:
        assert task.priority in {
            0,
            1,
            2,
            3,
        }

def test_long_run_priority_distribution():
    number_of_seeds = 200

    counts_by_type = {}

    for seed in range(number_of_seeds):

        tasks = NormalTaskGenerator(
            seed=seed
        ).generate()

        for task in tasks:

            counts_by_type.setdefault(
                task.task_type,
                Counter(),
            )

            counts_by_type[
                task.task_type
            ][task.priority] += 1

    for (
        task_type,
        expected_distribution
    ) in (
        TASK_PRIORITY_DISTRIBUTIONS.items()
    ):

        counts = counts_by_type[
            task_type
        ]

        total = sum(
            counts.values()
        )

        for (
            priority,
            expected_probability
        ) in (
            expected_distribution.items()
        ):

            actual_probability = (
                counts[priority]
                / total
            )

            # 5 percentage point tolerance
            assert abs(
                actual_probability
                - expected_probability
            ) < 0.05, (
                f"{task_type}, "
                f"priority={priority}: "
                f"expected "
                f"{expected_probability:.3f}, "
                f"got "
                f"{actual_probability:.3f}"
            )