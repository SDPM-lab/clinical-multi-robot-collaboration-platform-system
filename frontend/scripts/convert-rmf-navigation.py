#!/usr/bin/env python3
"""Convert freshly generated RMF nav graphs into browser-friendly JSON."""

from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[2]
BUILDING = ROOT / "ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml"
GENERATED = ROOT / "ros2_ws/src/my_hospital_rmf/nav_graphs_generated"
OUTPUT = ROOT / "frontend/public/generated"


def convert(source_path, graph_index):
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    levels, vertices, lanes = [], [], []
    vertex_offset = 0
    lane_offset = 0
    for level_name, level in source.get("levels", {}).items():
        level_vertices = level.get("vertices", [])
        level_lanes = level.get("lanes", [])
        vertex_ids = [f"v{vertex_offset + index}" for index in range(len(level_vertices))]
        lane_ids = [f"l{lane_offset + index}" for index in range(len(level_lanes))]
        levels.append({"id": level_name, "vertexIds": vertex_ids, "laneIds": lane_ids})
        for index, vertex in enumerate(level_vertices):
            params = vertex[2] if len(vertex) > 2 else {}
            vertices.append({
                "id": vertex_ids[index], "sourceVertexIndex": index, "level": level_name,
                "x": vertex[0], "y": vertex[1], "name": params.get("name", ""),
                "isCharger": bool(params.get("is_charger", False)), "params": params,
            })
        for index, lane in enumerate(level_lanes):
            params = lane[2] if len(lane) > 2 else {}
            lanes.append({
                "id": lane_ids[index], "level": level_name,
                "from": vertex_ids[lane[0]], "to": vertex_ids[lane[1]],
                "doorName": params.get("door_name"), "params": params,
            })
        vertex_offset += len(level_vertices)
        lane_offset += len(level_lanes)

    adjacency = {vertex["id"]: [] for vertex in vertices}
    for lane in lanes:
        adjacency[lane["from"]].append({"laneId": lane["id"], "neighborVertexId": lane["to"]})
    doors = [{"name": name, "level": door.get("map"), "endpoints": door.get("endpoints", [])} for name, door in source.get("doors", {}).items()]
    return {
        "sourceBuilding": str(BUILDING.relative_to(ROOT)),
        "sourceNavigationGraph": str(source_path.relative_to(ROOT)),
        "buildingName": source.get("building_name"), "graphIndex": graph_index,
        "levels": levels, "vertices": vertices, "lanes": lanes, "adjacency": adjacency,
        "namedWaypoints": [vertex for vertex in vertices if vertex["name"]],
        "chargingWaypoints": [vertex for vertex in vertices if vertex["isCharger"]],
        "doors": doors, "lifts": source.get("lifts", {}),
    }


def main():
    graph_zero = convert(GENERATED / "0.yaml", 0)
    graph_one = convert(GENERATED / "1.yaml", 1)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "rmf-navigation.json").write_text(json.dumps(graph_zero, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "rmf-navigation-graph-1.json").write_text(json.dumps(graph_one, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Graph 0: {len(graph_zero['vertices'])} vertices, {len(graph_zero['lanes'])} lanes")
    print(f"Graph 1: {len(graph_one['vertices'])} vertices, {len(graph_one['lanes'])} lanes")


if __name__ == "__main__":
    main()
