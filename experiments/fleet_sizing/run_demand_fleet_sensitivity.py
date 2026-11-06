from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import List, Tuple

from simulator import FleetSizingSimulator
from metrics import calculate_metrics


# ============================================================
# Experiment Configuration
# ============================================================

WORKLOAD_MULTIPLIERS = [
    1.0,
    2.0,
    3.0,
    4.0,
    5.0,
    6.0,
    8.0,
]

REPLICATIONS = 30


# ------------------------------------------------------------
# Candidate fleet configurations
#
# Tuple order:
#   (
#       clean_count,
#       medical_count,
#       ward_count,
#   )
#
# Every robot type starts from at least 1 because:
#
#   Clean:
#       required by waste / clothes
#
#   Medical:
#       required by specimen
#
#   Ward:
#       required by ward_service
#
# Therefore configurations containing 0 for any robot type
# are structurally infeasible for the current task model.
# ------------------------------------------------------------

FLEET_CONFIGURATIONS = [

    # Total = 3
    (1, 1, 1),

    # Total = 4
    (2, 1, 1),
    (1, 2, 1),
    (1, 1, 2),

    # Total = 5
    (3, 1, 1),
    (1, 3, 1),
    (1, 1, 3),
    (2, 2, 1),
    (2, 1, 2),
    (1, 2, 2),

    # Total = 6
    (4, 1, 1),
    (1, 4, 1),
    (1, 1, 4),

    (3, 2, 1),
    (3, 1, 2),
    (2, 3, 1),
    (1, 3, 2),
    (2, 1, 3),
    (1, 2, 3),

    (2, 2, 2),

    # Total = 7
    (5, 1, 1),
    (1, 5, 1),
    (1, 1, 5),

    (4, 2, 1),
    (4, 1, 2),
    (2, 4, 1),
    (1, 4, 2),
    (2, 1, 4),
    (1, 2, 4),

    (3, 3, 1),
    (3, 1, 3),
    (1, 3, 3),

    (3, 2, 2),
    (2, 3, 2),
    (2, 2, 3),

    # Total = 8
    (6, 1, 1),
    (1, 6, 1),
    (1, 1, 6),

    (5, 2, 1),
    (5, 1, 2),
    (2, 5, 1),
    (1, 5, 2),
    (2, 1, 5),
    (1, 2, 5),

    (4, 3, 1),
    (4, 1, 3),
    (3, 4, 1),
    (1, 4, 3),
    (3, 1, 4),
    (1, 3, 4),

    (4, 2, 2),
    (2, 4, 2),
    (2, 2, 4),

    (3, 3, 2),
    (3, 2, 3),
    (2, 3, 3),

    # Total = 9
    (3, 3, 3),

    (4, 3, 2),
    (4, 2, 3),
    (3, 4, 2),
    (2, 4, 3),
    (3, 2, 4),
    (2, 3, 4),

    # Total = 10
    (4, 3, 3),
    (3, 4, 3),
    (3, 3, 4),

    (4, 4, 2),
    (4, 2, 4),
    (2, 4, 4),
]


# ============================================================
# Feasibility Criteria
# ============================================================

# At least 99% of tasks should be completed.
MIN_MEAN_COMPLETION_RATE = 0.99

# Even the worst replication should maintain
# at least 99% completion.
MIN_SEED_COMPLETION_RATE = 0.99

# Avoid near-saturation operation.
MAX_MEAN_MAX_UTILIZATION = 0.90

# ------------------------------------------------------------
# Service-level constraint
#
# Reference:
# 1.0x workload with the minimum heterogeneous fleet
# (1 Clean, 1 Medical, 1 Ward) produced a mean
# P95 source-response time of approximately 297.6 s.
#
# Therefore 300 s is used as the reference service-level
# target when studying larger demand scales.
#
# IMPORTANT:
# This is an experimental reference service level,
# not a universal clinical standard.
# ------------------------------------------------------------

MAX_P95_RESPONSE_TIME_S = 300.0


# ============================================================
# Output
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent

RESULTS_DIR = (
    CURRENT_DIR
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

ALL_RESULTS_PATH = (
    RESULTS_DIR
    / "demand_fleet_sensitivity_all.csv"
)

SELECTED_RESULTS_PATH = (
    RESULTS_DIR
    / "demand_fleet_sensitivity_selected.csv"
)


# ============================================================
# Result Model
# ============================================================

@dataclass
class SensitivityResult:

    workload_multiplier: float

    clean_count: int
    medical_count: int
    ward_count: int

    total_robots: int

    replications: int

    average_tasks_per_day: float

    mean_completion_rate: float
    min_completion_rate: float

    mean_waiting_time_s: float
    mean_p95_waiting_time_s: float

    mean_response_time_s: float
    mean_p95_response_time_s: float

    mean_total_time_s: float
    mean_p95_total_time_s: float

    mean_average_utilization: float
    mean_max_utilization: float

    feasible: bool

    @property
    def fleet_configuration(
        self,
    ) -> Tuple[int, int, int]:

        return (
            self.clean_count,
            self.medical_count,
            self.ward_count,
        )


# ============================================================
# Utility Functions
# ============================================================

def sort_fleet_configurations(
    configurations: List[
        Tuple[int, int, int]
    ],
) -> List[
    Tuple[int, int, int]
]:

    return sorted(
        configurations,
        key=lambda fleet: (
            sum(fleet),

            fleet[0],
            fleet[1],
            fleet[2],
        ),
    )


def is_feasible(
    mean_completion_rate: float,
    min_completion_rate: float,
    mean_max_utilization: float,
    mean_p95_response_time_s: float,
) -> bool:

    return (
        mean_completion_rate
        >= MIN_MEAN_COMPLETION_RATE

        and min_completion_rate
        >= MIN_SEED_COMPLETION_RATE

        and mean_max_utilization
        < MAX_MEAN_MAX_UTILIZATION

        and mean_p95_response_time_s
        <= MAX_P95_RESPONSE_TIME_S
    )


# ============================================================
# Run One Fleet / One Workload
# ============================================================

def run_configuration(
    workload_multiplier: float,
    fleet_configuration: Tuple[
        int,
        int,
        int,
    ],
) -> SensitivityResult:

    completion_rates = []

    waiting_times = []
    p95_waiting_times = []

    response_times = []
    p95_response_times = []

    total_times = []
    p95_total_times = []

    average_utilizations = []
    max_utilizations = []

    tasks_per_day_values = []

    for seed in range(
        REPLICATIONS
    ):

        simulator = (
            FleetSizingSimulator(
                fleet_configuration=(
                    fleet_configuration
                ),
                seed=seed,
                workload_multiplier=(
                    workload_multiplier
                ),
            )
        )

        result = simulator.run()

        metrics = calculate_metrics(
            result
        )

        # ----------------------------------------------------
        # Demand
        # ----------------------------------------------------

        tasks_per_day_values.append(
            metrics.generated_tasks
            / 7.0
        )

        # ----------------------------------------------------
        # Completion
        # ----------------------------------------------------

        completion_rates.append(
            metrics.completion_rate
        )

        # ----------------------------------------------------
        # Waiting
        # ----------------------------------------------------

        waiting_times.append(
            metrics.average_waiting_time_s
        )

        p95_waiting_times.append(
            metrics.p95_waiting_time_s
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        response_times.append(
            metrics.average_source_arrival_time_s
        )

        p95_response_times.append(
            metrics.p95_source_arrival_time_s
        )

        # ----------------------------------------------------
        # Total Time
        # ----------------------------------------------------

        total_times.append(
            metrics.average_total_time_s
        )

        p95_total_times.append(
            metrics.p95_total_time_s
        )

        # ----------------------------------------------------
        # Utilization
        # ----------------------------------------------------

        average_utilizations.append(
            metrics.average_robot_utilization
        )

        max_utilizations.append(
            metrics.max_robot_utilization
        )

    clean_count = (
        fleet_configuration[0]
    )

    medical_count = (
        fleet_configuration[1]
    )

    ward_count = (
        fleet_configuration[2]
    )

    mean_completion = mean(
        completion_rates
    )

    min_completion = min(
        completion_rates
    )

    mean_max_util = mean(
        max_utilizations
    )

    mean_p95_response = mean(
        p95_response_times
    )

    feasible = is_feasible(
        mean_completion_rate=(
            mean_completion
        ),
        min_completion_rate=(
            min_completion
        ),
        mean_max_utilization=(
            mean_max_util
        ),
        mean_p95_response_time_s=(
            mean_p95_response
        ),
    )

    return SensitivityResult(

        workload_multiplier=(
            workload_multiplier
        ),

        clean_count=clean_count,
        medical_count=medical_count,
        ward_count=ward_count,

        total_robots=sum(
            fleet_configuration
        ),

        replications=REPLICATIONS,

        average_tasks_per_day=mean(
            tasks_per_day_values
        ),

        mean_completion_rate=(
            mean_completion
        ),

        min_completion_rate=(
            min_completion
        ),

        mean_waiting_time_s=mean(
            waiting_times
        ),

        mean_p95_waiting_time_s=mean(
            p95_waiting_times
        ),

        mean_response_time_s=mean(
            response_times
        ),

        mean_p95_response_time_s=(
            mean_p95_response
        ),

        mean_total_time_s=mean(
            total_times
        ),

        mean_p95_total_time_s=mean(
            p95_total_times
        ),

        mean_average_utilization=mean(
            average_utilizations
        ),

        mean_max_utilization=(
            mean_max_util
        ),

        feasible=feasible,
    )


# ============================================================
# Select Minimum Feasible Fleet
# ============================================================

def select_best_fleet(
    results: List[
        SensitivityResult
    ],
) -> SensitivityResult | None:

    feasible_results = [
        result
        for result in results
        if result.feasible
    ]

    if not feasible_results:
        return None

    # --------------------------------------------------------
    # Primary:
    #   Minimum total robot count
    #
    # Secondary:
    #   Lower P95 response time
    #
    # Tertiary:
    #   Lower maximum utilization
    #
    # Final deterministic tie-break:
    #   fleet tuple
    # --------------------------------------------------------

    feasible_results.sort(
        key=lambda result: (

            result.total_robots,

            result.mean_p95_response_time_s,

            result.mean_max_utilization,

            result.clean_count,
            result.medical_count,
            result.ward_count,
        )
    )

    return feasible_results[0]


# ============================================================
# CSV Writers
# ============================================================

def write_all_results(
    results: List[
        SensitivityResult
    ],
) -> None:

    fieldnames = [
        "workload_multiplier",

        "average_tasks_per_day",

        "clean_count",
        "medical_count",
        "ward_count",
        "total_robots",

        "replications",

        "mean_completion_rate",
        "min_completion_rate",

        "mean_waiting_time_s",
        "mean_p95_waiting_time_s",

        "mean_response_time_s",
        "mean_p95_response_time_s",

        "mean_total_time_s",
        "mean_p95_total_time_s",

        "mean_average_utilization",
        "mean_max_utilization",

        "feasible",
    ]

    with ALL_RESULTS_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:

            writer.writerow({

                "workload_multiplier":
                    result.workload_multiplier,

                "average_tasks_per_day":
                    result.average_tasks_per_day,

                "clean_count":
                    result.clean_count,

                "medical_count":
                    result.medical_count,

                "ward_count":
                    result.ward_count,

                "total_robots":
                    result.total_robots,

                "replications":
                    result.replications,

                "mean_completion_rate":
                    result.mean_completion_rate,

                "min_completion_rate":
                    result.min_completion_rate,

                "mean_waiting_time_s":
                    result.mean_waiting_time_s,

                "mean_p95_waiting_time_s":
                    result.mean_p95_waiting_time_s,

                "mean_response_time_s":
                    result.mean_response_time_s,

                "mean_p95_response_time_s":
                    result.mean_p95_response_time_s,

                "mean_total_time_s":
                    result.mean_total_time_s,

                "mean_p95_total_time_s":
                    result.mean_p95_total_time_s,

                "mean_average_utilization":
                    result.mean_average_utilization,

                "mean_max_utilization":
                    result.mean_max_utilization,

                "feasible":
                    result.feasible,
            })


def write_selected_results(
    selected_results: List[
        SensitivityResult
    ],
) -> None:

    fieldnames = [
        "workload_multiplier",

        "average_tasks_per_day",

        "clean_count",
        "medical_count",
        "ward_count",

        "total_robots",

        "mean_completion_rate",
        "min_completion_rate",

        "mean_waiting_time_s",
        "mean_p95_waiting_time_s",

        "mean_response_time_s",
        "mean_p95_response_time_s",

        "mean_average_utilization",
        "mean_max_utilization",
    ]

    with SELECTED_RESULTS_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in selected_results:

            writer.writerow({

                "workload_multiplier":
                    result.workload_multiplier,

                "average_tasks_per_day":
                    result.average_tasks_per_day,

                "clean_count":
                    result.clean_count,

                "medical_count":
                    result.medical_count,

                "ward_count":
                    result.ward_count,

                "total_robots":
                    result.total_robots,

                "mean_completion_rate":
                    result.mean_completion_rate,

                "min_completion_rate":
                    result.min_completion_rate,

                "mean_waiting_time_s":
                    result.mean_waiting_time_s,

                "mean_p95_waiting_time_s":
                    result.mean_p95_waiting_time_s,

                "mean_response_time_s":
                    result.mean_response_time_s,

                "mean_p95_response_time_s":
                    result.mean_p95_response_time_s,

                "mean_average_utilization":
                    result.mean_average_utilization,

                "mean_max_utilization":
                    result.mean_max_utilization,
            })


# ============================================================
# Console Output
# ============================================================

def print_configuration_result(
    result: SensitivityResult,
) -> None:

    status = (
        "PASS"
        if result.feasible
        else "FAIL"
    )

    fleet = (
        f"({result.clean_count},"
        f"{result.medical_count},"
        f"{result.ward_count})"
    )

    print(
        f"{fleet:<12}"
        f"N={result.total_robots:<2} "
        f"tasks/day="
        f"{result.average_tasks_per_day:>6.1f} "
        f"comp="
        f"{result.mean_completion_rate * 100:>6.2f}% "
        f"min="
        f"{result.min_completion_rate * 100:>6.2f}% "
        f"P95resp="
        f"{result.mean_p95_response_time_s:>8.1f}s "
        f"maxUtil="
        f"{result.mean_max_utilization * 100:>6.2f}% "
        f"[{status}]"
    )


def print_selected_summary(
    selected_results: List[
        SensitivityResult
    ],
) -> None:

    print()
    print("=" * 118)
    print(
        "DEMAND SCALE -> "
        "MINIMUM FEASIBLE FLEET"
    )
    print("=" * 118)

    print(
        f"{'Load':<8}"
        f"{'Tasks/day':>12}"
        f"{'Fleet':>16}"
        f"{'N':>5}"
        f"{'Mean Comp':>13}"
        f"{'Min Comp':>12}"
        f"{'P95 Wait':>13}"
        f"{'P95 Resp':>13}"
        f"{'Max Util':>12}"
    )

    print("-" * 118)

    for result in selected_results:

        fleet = (
            f"("
            f"{result.clean_count}, "
            f"{result.medical_count}, "
            f"{result.ward_count}"
            f")"
        )

        print(
            f"{result.workload_multiplier:<8.1f}"

            f"{result.average_tasks_per_day:>12.1f}"

            f"{fleet:>16}"

            f"{result.total_robots:>5}"

            f"{result.mean_completion_rate * 100:>12.2f}%"

            f"{result.min_completion_rate * 100:>11.2f}%"

            f"{result.mean_p95_waiting_time_s:>12.1f}s"

            f"{result.mean_p95_response_time_s:>12.1f}s"

            f"{result.mean_max_utilization * 100:>11.2f}%"
        )


# ============================================================
# Main
# ============================================================

def main() -> None:

    configurations = (
        sort_fleet_configurations(
            FLEET_CONFIGURATIONS
        )
    )

    all_results: List[
        SensitivityResult
    ] = []

    selected_results: List[
        SensitivityResult
    ] = []

    total_experiments = (
        len(WORKLOAD_MULTIPLIERS)
        * len(configurations)
    )

    experiment_index = 0

    print("=" * 118)
    print(
        "DEMAND-FLEET SENSITIVITY EXPERIMENT"
    )
    print("=" * 118)

    print(
        f"Workload multipliers: "
        f"{WORKLOAD_MULTIPLIERS}"
    )

    print(
        f"Fleet configurations: "
        f"{len(configurations)}"
    )

    print(
        f"Replications/configuration: "
        f"{REPLICATIONS}"
    )

    print(
        f"Total simulation runs: "
        f"{total_experiments * REPLICATIONS}"
    )

    print()

    for workload_multiplier in (
        WORKLOAD_MULTIPLIERS
    ):

        print()
        print("=" * 118)

        print(
            f"WORKLOAD "
            f"{workload_multiplier:.1f}x"
        )

        print("=" * 118)

        workload_results = []

        for fleet_configuration in (
            configurations
        ):

            experiment_index += 1

            print(
                f"[{experiment_index:03d}/"
                f"{total_experiments:03d}] ",
                end="",
            )

            result = run_configuration(
                workload_multiplier=(
                    workload_multiplier
                ),
                fleet_configuration=(
                    fleet_configuration
                ),
            )

            workload_results.append(
                result
            )

            all_results.append(
                result
            )

            print_configuration_result(
                result
            )

        # ----------------------------------------------------
        # Select minimum feasible fleet for this workload
        # ----------------------------------------------------

        selected = select_best_fleet(
            workload_results
        )

        print()

        if selected is None:

            print(
                "WARNING: "
                f"No feasible fleet found for "
                f"{workload_multiplier:.1f}x "
                "within the tested fleet search space."
            )

        else:

            selected_results.append(
                selected
            )

            print(
                "SELECTED: "
                f"{workload_multiplier:.1f}x "
                f"-> "
                f"("
                f"{selected.clean_count}, "
                f"{selected.medical_count}, "
                f"{selected.ward_count}"
                f") "
                f"N={selected.total_robots}, "
                f"P95 Response="
                f"{selected.mean_p95_response_time_s:.1f}s, "
                f"Max Util="
                f"{selected.mean_max_utilization * 100:.2f}%"
            )

    # ========================================================
    # Save CSV
    # ========================================================

    write_all_results(
        all_results
    )

    write_selected_results(
        selected_results
    )

    # ========================================================
    # Print Final Summary
    # ========================================================

    print_selected_summary(
        selected_results
    )

    print()
    print(
        f"All results saved to:"
    )

    print(
        ALL_RESULTS_PATH
    )

    print()

    print(
        f"Selected fleets saved to:"
    )

    print(
        SELECTED_RESULTS_PATH
    )


if __name__ == "__main__":
    main()