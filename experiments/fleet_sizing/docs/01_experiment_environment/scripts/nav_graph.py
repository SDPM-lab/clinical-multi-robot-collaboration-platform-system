from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import hypot, inf
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from config import NAV_GRAPH_PATH


@dataclass(frozen=True)
class Waypoint:
    index: int
    name: str
    x: float
    y: float
    is_charger: bool = False


class NavGraph:
    def __init__(self, yaml_path: Path = NAV_GRAPH_PATH):
        self.yaml_path = Path(yaml_path)

        self.waypoints_by_name: Dict[str, Waypoint] = {}
        self.waypoints_by_index: Dict[int, Waypoint] = {}

        # adjacency[src] = [(dst, distance), ...]
        self.adjacency: Dict[int, List[Tuple[int, float]]] = {}

        self._load()

    def _load(self) -> None:
        if not self.yaml_path.exists():
            raise FileNotFoundError(
                f"Nav graph file not found: {self.yaml_path}"
            )

        with self.yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        levels = data.get("levels", {})

        if not levels:
            raise ValueError("No levels found in nav graph.")

        # 目前正式 robot graph 只有 L1
        if "L1" not in levels:
            raise ValueError(
                f"Expected level 'L1', got: {list(levels.keys())}"
            )

        graph = levels["L1"]

        vertices = graph.get("vertices", [])
        lanes = graph.get("lanes", [])

        self._load_vertices(vertices)
        self._load_lanes(lanes)

    def _load_vertices(self, vertices: list) -> None:
        for index, vertex in enumerate(vertices):
            if len(vertex) < 3:
                raise ValueError(
                    f"Invalid vertex format at index {index}: {vertex}"
                )

            x = float(vertex[0])
            y = float(vertex[1])
            params = vertex[2]

            if not isinstance(params, dict):
                raise ValueError(
                    f"Vertex params must be a dict at index {index}: {params}"
                )

            name = params.get("name")

            # Fleet sizing 只需要 named waypoint。
            if not name:
                continue

            waypoint = Waypoint(
                index=index,
                name=name,
                x=x,
                y=y,
                is_charger=bool(params.get("is_charger", False)),
            )

            if name in self.waypoints_by_name:
                raise ValueError(
                    f"Duplicate waypoint name: {name}"
                )

            self.waypoints_by_name[name] = waypoint
            self.waypoints_by_index[index] = waypoint

    def _load_lanes(self, lanes: list) -> None:
        for lane in lanes:
            if len(lane) < 2:
                raise ValueError(f"Invalid lane format: {lane}")

            source_index = int(lane[0])
            destination_index = int(lane[1])

            if source_index not in self.waypoints_by_index:
                raise ValueError(
                    f"Lane source vertex {source_index} has no named waypoint."
                )

            if destination_index not in self.waypoints_by_index:
                raise ValueError(
                    f"Lane destination vertex {destination_index} "
                    "has no named waypoint."
                )

            source = self.waypoints_by_index[source_index]
            destination = self.waypoints_by_index[destination_index]

            distance = hypot(
                destination.x - source.x,
                destination.y - source.y,
            )

            self.adjacency.setdefault(source_index, []).append(
                (destination_index, distance)
            )

    def get_waypoint_position(self, name: str) -> Tuple[float, float]:
        waypoint = self._get_waypoint(name)
        return waypoint.x, waypoint.y

    def shortest_path(
        self,
        source_name: str,
        destination_name: str,
    ) -> List[str]:
        source = self._get_waypoint(source_name)
        destination = self._get_waypoint(destination_name)

        if source.index == destination.index:
            return [source.name]

        distances = {
            index: inf
            for index in self.waypoints_by_index
        }

        previous: Dict[int, int] = {}

        distances[source.index] = 0.0

        queue = [(0.0, source.index)]

        while queue:
            current_distance, current_index = heappop(queue)

            if current_distance > distances[current_index]:
                continue

            if current_index == destination.index:
                break

            for neighbor_index, edge_distance in self.adjacency.get(
                current_index, []
            ):
                new_distance = current_distance + edge_distance

                if new_distance < distances[neighbor_index]:
                    distances[neighbor_index] = new_distance
                    previous[neighbor_index] = current_index

                    heappush(
                        queue,
                        (new_distance, neighbor_index),
                    )

        if distances[destination.index] == inf:
            raise ValueError(
                f"No path from {source_name} to {destination_name}"
            )

        path_indices = []
        current = destination.index

        while current != source.index:
            path_indices.append(current)
            current = previous[current]

        path_indices.append(source.index)
        path_indices.reverse()

        return [
            self.waypoints_by_index[index].name
            for index in path_indices
        ]

    def shortest_path_distance(
        self,
        source_name: str,
        destination_name: str,
    ) -> float:
        path = self.shortest_path(
            source_name,
            destination_name,
        )

        if len(path) <= 1:
            return 0.0

        total_distance = 0.0

        for source_name, destination_name in zip(
            path[:-1],
            path[1:],
        ):
            source = self._get_waypoint(source_name)
            destination = self._get_waypoint(destination_name)

            total_distance += hypot(
                destination.x - source.x,
                destination.y - source.y,
            )

        return total_distance

    def get_chargers(self) -> List[str]:
        return [
            waypoint.name
            for waypoint in self.waypoints_by_name.values()
            if waypoint.is_charger
        ]

    def has_waypoint(self, name: str) -> bool:
        return name in self.waypoints_by_name

    def _get_waypoint(self, name: str) -> Waypoint:
        try:
            return self.waypoints_by_name[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown waypoint: {name}"
            ) from exc


if __name__ == "__main__":
    graph = NavGraph()

    print(
        f"Loaded {len(graph.waypoints_by_name)} named waypoints."
    )

    print("Chargers:", graph.get_chargers())

    source = "pharmacy"
    destination = "ward_a_2"

    print(
        f"{source} -> {destination}:",
        graph.shortest_path(source, destination),
    )

    print(
        "Distance:",
        round(
            graph.shortest_path_distance(
                source,
                destination,
            ),
            3,
        ),
        "m",
    )