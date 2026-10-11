#!/usr/bin/env python3
"""Derive display geometry without changing the RMF navigation graph.

Requires PyYAML, already used by convert-rmf-navigation.py. --check verifies the
committed artifact without writing. Geometry validation is deliberately strict:
unknown room edges remain unresolved rather than being invented.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "frontend/src/data/hospitalRoomLayout.js"
GRAPH = ROOT / "frontend/public/generated/rmf-navigation.json"
OUTPUT = ROOT / "frontend/public/generated/hospital-floorplan.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance_to_segment(point, a, b):
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    length_squared = dx * dx + dy * dy
    t = max(0, min(1, ((point["x"] - a["x"]) * dx + (point["y"] - a["y"]) * dy) / length_squared)) if length_squared else 0
    return math.hypot(point["x"] - a["x"] - t * dx, point["y"] - a["y"] - t * dy)


def contains(point, polygon):
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if distance_to_segment(point, a, b) < 1e-8:
            return True
        if (a["y"] > point["y"]) != (b["y"] > point["y"]):
            x = a["x"] + (point["y"] - a["y"]) * (b["x"] - a["x"]) / (b["y"] - a["y"])
            if point["x"] < x:
                inside = not inside
    return inside


def generate():
    config = json.loads(CONFIG.read_text().split("export const hospitalRoomLayout =", 1)[1])
    building_path = ROOT / config["source"]
    building = yaml.safe_load(building_path.read_text())
    # This generator supports this one reference-image level only. Other frames
    # need an explicit transform, never silently applying occupancy-map origin.
    if building.get("coordinate_system") != "reference_image" or len(building["levels"]) != 1:
        raise ValueError("Expected a single reference-image level")
    level = building["levels"][config["level"]]
    vertices = level["vertices"]
    scales = [measurement[2]["distance"][1] / math.dist(vertices[measurement[0]][:2], vertices[measurement[1]][:2]) for measurement in level["measurements"]]
    scale = sum(scales) / len(scales)

    def point(index):
        return {"x": vertices[index][0] * scale, "y": -vertices[index][1] * scale}

    graph = json.loads(GRAPH.read_text())
    if graph["graphIndex"] != 0 or graph["sourceBuilding"] != config["source"]:
        raise ValueError("Navigation source does not match room configuration")
    named = {v[3]: point(i) for i, v in enumerate(vertices) if v[3]}
    graph_named = {v["name"]: v for v in graph["namedWaypoints"] if v["level"] == config["level"]}
    errors = []
    for name, vertex in graph_named.items():
        if name not in named:
            raise ValueError(f"Missing building waypoint: {name}")
        errors.append(math.hypot(vertex["x"] - named[name]["x"], vertex["y"] - named[name]["y"]))
    max_error = max(errors, default=0)
    if not errors or max_error > 1e-6:
        raise ValueError(f"Building/navigation coordinates disagree: {max_error} metres; regenerate/review sources first")

    walls = [{"sourceWallIndex": i, "vertexIndices": edge[:2], "endpoints": [point(edge[0]), point(edge[1])]} for i, edge in enumerate(level["walls"])]
    doors = [{"sourceDoorIndex": i, "name": edge[2]["name"][1], "vertexIndices": edge[:2], "endpoints": [point(edge[0]), point(edge[1])]} for i, edge in enumerate(level["doors"])]
    support = walls + doors
    tolerance = config["boundaryToleranceMeters"]
    rooms = []
    for definition in config["rooms"]:
        polygon = [point(i) for i in definition["boundaryVertexIndices"]]
        issues, edge_evidence = [], []
        if len(polygon) < 3:
            issues.append("missing-room-boundary")
        for index, (a, b) in enumerate(zip(polygon, polygon[1:] + polygon[:1])):
            # Dense samples establish agreement with source wall/door segments;
            # tolerance accounts for independently clicked image vertices only.
            steps = max(1, math.ceil(math.hypot(b["x"] - a["x"], b["y"] - a["y"]) / 0.01))
            samples = [{"x": a["x"] + (b["x"] - a["x"]) * t / steps, "y": a["y"] + (b["y"] - a["y"]) * t / steps} for t in range(steps + 1)]
            residual = max(min(distance_to_segment(sample, *edge["endpoints"]) for edge in support) for sample in samples)
            edge_evidence.append({"edgeIndex": index, "maxDistanceToSourceMeters": residual})
            if residual > tolerance:
                issues.append(f"unsupported-boundary-edge:{index}")
        for name in definition["waypointNames"]:
            if name not in graph_named:
                issues.append(f"missing-graph-waypoint:{name}")
            elif polygon and not contains(graph_named[name], polygon):
                issues.append(f"waypoint-outside-boundary:{name}")
        rooms.append({
            **definition, "level": config["level"], "source": config["source"], "isDemo": False,
            "verificationStatus": "source-geometry-verified" if not issues else "unresolved",
            "nameAuthority": "current-navigation-and-frontend-names",
            "renderable": not issues, "polygon": polygon if not issues else [],
            "candidatePolygon": polygon if issues else [], "issues": issues, "boundaryEvidence": edge_evidence,
        })
    return {
        "schemaVersion": 1, "level": config["level"], "coordinateFrame": "rmf", "units": "metres", "isDemo": False,
        "source": config["source"], "nameSources": config["nameSources"], "labelPolicy": config["labelPolicy"],
        "sourceHashes": {str(path.relative_to(ROOT)): digest(path) for path in [building_path, CONFIG, GRAPH]},
        "transform": {"imageScale": scale, "invertImageY": True, "offsetX": 0, "offsetY": 0},
        "validation": {"matchedWaypoints": len(errors), "maxWaypointErrorMeters": max_error, "boundaryToleranceMeters": tolerance, "boundarySampleStepMeters": 0.01},
        "footprint": [point(i) for i in config["footprintVertexIndices"]],
        "walls": walls, "doors": doors, "rooms": rooms,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = generate()
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != content:
            raise SystemExit("Floorplan artifact is stale; inspect source changes and regenerate")
    else:
        OUTPUT.write_text(content)
    valid = sum(room["renderable"] for room in result["rooms"])
    print(f"{valid}/{len(result['rooms'])} room regions verified; {result['validation']['matchedWaypoints']} waypoints aligned")
    for room in result["rooms"]:
        if room["issues"]:
            print(f"  {room['id']}: {', '.join(room['issues'])}")


if __name__ == "__main__":
    main()
