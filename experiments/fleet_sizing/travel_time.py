from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Tuple

from config import BATCH_ROUTE_SUMMARY_PATH
from nav_graph import NavGraph


@dataclass(frozen=True)
class RouteTravelStats:
    task_type: str
    source: str
    destination: str
    n: int
    mean_s: float
    sd_s: float
    median_s: float
    p95_s: float
    min_s: float
    max_s: float
    mean_actual_distance_m: float
    mean_average_speed_mps: float


class TravelTimeModel:
    def __init__(
        self,
        summary_csv_path: Path = BATCH_ROUTE_SUMMARY_PATH,
        nav_graph: NavGraph | None = None,
    ):
        self.summary_csv_path = Path(summary_csv_path)
        self.nav_graph = nav_graph or NavGraph()

        # key = (source, destination)
        self.route_stats: Dict[
            Tuple[str, str],
            RouteTravelStats
        ] = {}

        self.effective_speed_mps: float | None = None

        self._load_summary()
        self._calculate_effective_speed()

    def _load_summary(self) -> None:
        if not self.summary_csv_path.exists():
            raise FileNotFoundError(
                f"Route summary CSV not found: "
                f"{self.summary_csv_path}"
            )

        with self.summary_csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise ValueError(
                    "Route summary CSV has no header."
                )

            for row in reader:
                stats = RouteTravelStats(
                    task_type=row["task_type"],
                    source=row["source"],
                    destination=row["destination"],
                    n=int(row["n"]),
                    mean_s=float(row["mean_travel_time_s"]),
                    sd_s=float(row["sd_travel_time_s"]),
                    median_s=float(row["median_travel_time_s"]),
                    p95_s=float(row["p95_travel_time_s"]),
                    min_s=float(row["min_travel_time_s"]),
                    max_s=float(row["max_travel_time_s"]),
                    mean_actual_distance_m=float(
                        row["mean_actual_distance_m"]
                    ),
                    mean_average_speed_mps=float(
                        row["mean_average_speed_mps"]
                    ),
                )

                key = (
                    stats.source,
                    stats.destination,
                )

                self.route_stats[key] = stats

    def _calculate_effective_speed(self) -> None:
        speeds = [
            stats.mean_average_speed_mps
            for stats in self.route_stats.values()
            if stats.mean_average_speed_mps > 0
        ]

        if not speeds:
            raise ValueError(
                "No valid average speed found "
                "in route summary."
            )

        self.effective_speed_mps = mean(speeds)

    def has_empirical_route(
        self,
        source: str,
        destination: str,
    ) -> bool:
        return (source, destination) in self.route_stats

    def get_empirical_stats(
        self,
        source: str,
        destination: str,
    ) -> RouteTravelStats:
        key = (source, destination)

        if key not in self.route_stats:
            raise KeyError(
                f"No empirical route data for "
                f"{source} -> {destination}"
            )

        return self.route_stats[key]

    def get_travel_time_mean(
        self,
        source: str,
        destination: str,
    ) -> float:
        # Case 1:
        # 已有實測 route，直接使用 mean travel time。
        if self.has_empirical_route(
            source,
            destination,
        ):
            return self.route_stats[
                (source, destination)
            ].mean_s

        # Case 2:
        # 沒有實測 route，使用 shortest-path distance
        # / calibrated effective speed。
        return self._estimate_from_nav_graph(
            source,
            destination,
        )

    def _estimate_from_nav_graph(
        self,
        source: str,
        destination: str,
    ) -> float:
        if source == destination:
            return 0.0

        if self.effective_speed_mps is None:
            raise RuntimeError(
                "Effective speed is not initialized."
            )

        distance_m = (
            self.nav_graph.shortest_path_distance(
                source,
                destination,
            )
        )

        return distance_m / self.effective_speed_mps

    def get_route_source(
        self,
        source: str,
        destination: str,
    ) -> str:
        if self.has_empirical_route(
            source,
            destination,
        ):
            return "empirical"

        return "nav_graph_fallback"


if __name__ == "__main__":
    model = TravelTimeModel()

    print(
        "Loaded empirical routes:",
        len(model.route_stats),
    )

    print(
        "Effective speed:",
        round(model.effective_speed_mps, 4),
        "m/s",
    )

    examples = [
        ("pharmacy", "ward_a_2"),
        ("ward_a_2", "pharmacy"),
        ("charging_station_2", "pharmacy"),
    ]

    for source, destination in examples:
        travel_time = model.get_travel_time_mean(
            source,
            destination,
        )

        method = model.get_route_source(
            source,
            destination,
        )

        print(
            f"{source} -> {destination}: "
            f"{travel_time:.2f} s "
            f"[{method}]"
        )