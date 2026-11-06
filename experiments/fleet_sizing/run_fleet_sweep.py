from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from config import (
    INITIAL_REPLICATIONS,
    RESULTS_DIR,
)

from run_replications import (
    ReplicationSummary,
    run_replications,
)


FLEET_CONFIGURATIONS = [
    (1, 1, 1),

    (2, 1, 1),
    (1, 2, 1),
    (1, 1, 2),

    (2, 2, 1),
    (2, 1, 2),
    (1, 2, 2),

    (2, 2, 2),
]


def run_fleet_sweep(
    replications: int = INITIAL_REPLICATIONS,
) -> List[ReplicationSummary]:

    summaries = []

    for index, configuration in enumerate(
        FLEET_CONFIGURATIONS,
        start=1,
    ):

        print()
        print("=" * 70)

        print(
            f"Fleet {index}/{len(FLEET_CONFIGURATIONS)}:",
            configuration,
        )

        print("=" * 70)

        summary = run_replications(
            fleet_configuration=configuration,
            replications=replications,
        )

        summaries.append(summary)

    return summaries


def print_comparison(
    summaries: List[ReplicationSummary],
) -> None:

    print()
    print("=" * 120)
    print("FLEET SIZING COMPARISON")
    print("=" * 120)

    header = (
        f"{'Fleet':<12}"
        f"{'N':>4}"
        f"{'Completion':>14}"
        f"{'Min Comp.':>12}"
        f"{'Avg Wait':>12}"
        f"{'P95 Wait':>12}"
        f"{'Avg Resp':>12}"
        f"{'P95 Resp':>12}"
        f"{'Max Util':>12}"
    )

    print(header)
    print("-" * 120)

    for summary in summaries:

        total_robots = sum(
            summary.fleet_configuration
        )

        print(
            f"{str(summary.fleet_configuration):<12}"
            f"{total_robots:>4}"
            f"{summary.mean_completion_rate * 100:>13.2f}%"
            f"{summary.min_completion_rate * 100:>11.2f}%"
            f"{summary.mean_waiting_time_s:>11.1f}s"
            f"{summary.mean_p95_waiting_time_s:>11.1f}s"
            f"{summary.mean_source_arrival_time_s:>11.1f}s"
            f"{summary.mean_p95_source_arrival_time_s:>11.1f}s"
            f"{summary.mean_max_robot_utilization * 100:>11.2f}%"
        )


def save_csv(
    summaries: List[ReplicationSummary],
) -> Path:

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        RESULTS_DIR
        / "fleet_sizing_sweep.csv"
    )

    fieldnames = [
        "clean_count",
        "medical_count",
        "ward_count",
        "total_robots",

        "replications",

        "mean_completion_rate",
        "min_completion_rate",

        "mean_waiting_time_s",
        "mean_p95_waiting_time_s",

        "mean_source_arrival_time_s",
        "mean_p95_source_arrival_time_s",

        "mean_total_time_s",
        "mean_p95_total_time_s",

        "mean_robot_utilization",
        "mean_max_robot_utilization",

        "completion_rate_ci95_half_width",
        "source_arrival_ci95_half_width_s",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for summary in summaries:

            clean_count, medical_count, ward_count = (
                summary.fleet_configuration
            )

            writer.writerow({
                "clean_count":
                    clean_count,

                "medical_count":
                    medical_count,

                "ward_count":
                    ward_count,

                "total_robots":
                    sum(
                        summary.fleet_configuration
                    ),

                "replications":
                    summary.replications,

                "mean_completion_rate":
                    summary.mean_completion_rate,

                "min_completion_rate":
                    summary.min_completion_rate,

                "mean_waiting_time_s":
                    summary.mean_waiting_time_s,

                "mean_p95_waiting_time_s":
                    summary.mean_p95_waiting_time_s,

                "mean_source_arrival_time_s":
                    summary.mean_source_arrival_time_s,

                "mean_p95_source_arrival_time_s":
                    summary.mean_p95_source_arrival_time_s,

                "mean_total_time_s":
                    summary.mean_total_time_s,

                "mean_p95_total_time_s":
                    summary.mean_p95_total_time_s,

                "mean_robot_utilization":
                    summary.mean_robot_utilization,

                "mean_max_robot_utilization":
                    summary.mean_max_robot_utilization,

                "completion_rate_ci95_half_width":
                    summary.completion_rate_ci95_half_width,

                "source_arrival_ci95_half_width_s":
                    summary.source_arrival_ci95_half_width_s,
            })

    return output_path


if __name__ == "__main__":

    summaries = run_fleet_sweep(
        replications=INITIAL_REPLICATIONS,
    )

    print_comparison(
        summaries
    )

    output_path = save_csv(
        summaries
    )

    print()
    print(
        "Saved:",
        output_path,
    )