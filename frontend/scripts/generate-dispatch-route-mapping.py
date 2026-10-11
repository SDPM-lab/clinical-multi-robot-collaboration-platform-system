#!/usr/bin/env python3
"""Audit the L1 GLB route graph against RMF Graph 0 without using Blender.

The semantic anchors below are reviewed correspondences, not a proximity match.
An edge is emitted only when its endpoints have a GLB anchor and the GLB route
graph has a continuous path between them. Unresolved edges are reported rather
than silently invented.
"""

from collections import defaultdict, deque
from hashlib import sha256
from pathlib import Path
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
GLB = ROOT / "frontend/public/models/L1__flat.glb"
GRAPH = ROOT / "frontend/public/generated/rmf-navigation.json"
BUILDING = ROOT / "ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml"
NAV_YAML = ROOT / "ros2_ws/src/my_hospital_rmf/nav_graphs_generated/0.yaml"
OUTPUT = ROOT / "frontend/public/generated/dispatch-route-mapping.json"

# Source vertex index -> existing, named display node. These are semantic
# candidates checked against route connectivity below, not ROS calibration.
ANCHORS = {
    0: "left_mid", 1: "center_mid", 2: "reception_door",
    3: "right_mid", 4: "right_waste", 5: "right_therapy",
    6: "right_ecg", 7: "right_charge", 8: "right_ultrasound",
    9: "right_top", 10: "center_top", 11: "blood_door",
    12: "lab_door", 13: "left_top", 14: "ward_b_junction",
    15: "consult_2_door", 16: "consult_1_door",
    17: "consult_1_edge", 18: "consult_2_edge", 19: "consult_3_edge",
    20: "consult_3_door", 21: "ward_b_edge", 22: "ward_a_edge",
    23: "ward_a_door", 24: "laboratory_dock", 25: "blood_draw_dock",
    26: "xray_dock", 27: "xray_door", 28: "charging_edge",
    29: "ultrasound_edge", 30: "ecg_edge", 31: "therapy_dock",
    32: "waste_return_edge", 33: "right_bottom", 34: "pharmacy_dock",
    35: "support_bottom", 36: "clothes_return_edge", 37: "support_top",
    38: "pantry_dock", 39: "clothes_return_dock", 40: "charging_dock",
    41: "waste_return_dock", 42: "ultrasound_dock", 43: "ecg_dock",
    44: "ward_a_dock", 45: "ward_b_dock", 46: "consult_3_dock",
    47: "consult_2_dock", 48: "consult_1_dock", 49: "left_nurse",
    50: "nurse_station_dock",
}

# Explicit display corrections approved for the two GLB/TE topology conflicts.
# These are artistic bends, not new Traffic Editor/ROS navigation vertices.
DISPLAY_CORRECTIONS = {
    "ward_b_junction": [-10.725, 0.095, -5.85],
    "ward_b_door": [-11.2, 0.095, -6.942],
    "ward_b_elbow": [-11.2, 0.095, -5.85],
    "right_waste": [11.076, 0.095, 1.521],
    "right_therapy": [11.076, 0.095, 0.78],
    "waste_elbow": [10.35, 0.095, 1.521],
    "waste_drop": [10.35, 0.095, 0.78],
    "therapy_elbow": [11.45, 0.095, 0.78],
    "therapy_rise": [11.45, 0.095, 1.521],
    "reception_elbow": [0.936, 0.095, 4.641],
}
SUPPRESSED_GLB_ROUTES = {
    "Route_left_top__consult_3_door",
    "Route_right_therapy__right_mid", "Route_right_waste__right_therapy",
    "Route_right_ecg__right_waste", "Route_right_waste__waste_door",
    "Route_right_therapy__therapy_door",
    "Route_center_reception__reception_door",
}
CORRECTED_ROUTES = [
    ("left_top", "ward_b_junction"), ("ward_b_junction", "consult_3_door"),
    ("ward_b_junction", "ward_b_elbow"), ("ward_b_elbow", "ward_b_door"),
    ("right_mid", "right_waste"), ("right_waste", "right_therapy"),
    ("right_therapy", "right_ecg"),
    ("right_waste", "waste_elbow"), ("waste_elbow", "waste_drop"),
    ("waste_drop", "waste_door"),
    ("right_therapy", "therapy_elbow"), ("therapy_elbow", "therapy_rise"),
    ("therapy_rise", "therapy_door"),
    ("center_mid", "reception_elbow"), ("reception_elbow", "reception_door"),
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_glb(path):
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12 or struct.unpack("<I", header[:4])[0] != 0x46546C67:
            raise ValueError("Not a GLB file")
        length, kind = struct.unpack("<II", stream.read(8))
        if kind != 0x4E4F534A:
            raise ValueError("GLB has no JSON chunk")
        return json.loads(stream.read(length))


def active_objects(document):
    scene = document["scenes"][document.get("scene", 0)]
    seen = set()
    pending = list(scene["nodes"])
    while pending:
        index = pending.pop()
        if index in seen:
            continue
        seen.add(index)
        pending.extend(document["nodes"][index].get("children", []))
    return [document["nodes"][index] for index in sorted(seen)]


def clean_name(name):
    return re.sub(r"\.\d+$", "", name)


def shortest_display_path(adjacency, start, end):
    if start == end:
        return [start]
    queue = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        for neighbor in sorted(adjacency[path[-1]]):
            if neighbor in visited:
                continue
            result = path + [neighbor]
            if neighbor == end:
                return result
            visited.add(neighbor)
            queue.append(result)
    return None


def build():
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    glb = read_glb(GLB)
    objects = active_objects(glb)
    display_nodes = {}
    for item in objects:
        name = clean_name(item.get("name", ""))
        if name.startswith("RouteNode_"):
            display_nodes[name[10:]] = {"object": name, "position": item.get("translation", [0, 0, 0])}
    display_edges = {}
    adjacency = defaultdict(set)
    for item in objects:
        name = clean_name(item.get("name", ""))
        if not name.startswith("Route_") or name.startswith("RouteNode_"):
            continue
        endpoints = name[6:].split("__")
        if len(endpoints) != 2 or any(point not in display_nodes for point in endpoints):
            raise ValueError(f"GLB route has missing endpoints: {name}")
        if "mesh" not in item or item.get("translation") or item.get("rotation") or item.get("scale"):
            raise ValueError(f"GLB route is not a simple named segment: {name}")
        primitives = glb["meshes"][item["mesh"]]["primitives"]
        if len(primitives) != 1:
            raise ValueError(f"GLB route has multiple mesh primitives: {name}")
        accessor = glb["accessors"][primitives[0]["attributes"]["POSITION"]]
        low, high = accessor.get("min"), accessor.get("max")
        if not low or not high:
            raise ValueError(f"GLB route has no geometry bounds: {name}")
        for endpoint in endpoints:
            point = display_nodes[endpoint]["position"]
            if any(point[axis] < low[axis] - .08 or point[axis] > high[axis] + .08 for axis in range(3)):
                raise ValueError(f"GLB route geometry misses endpoint {endpoint}: {name}")
        display_edges[name] = {"object": name, "nodes": endpoints, "kind": "glb"}
    for name, position in DISPLAY_CORRECTIONS.items():
        display_nodes[name] = {
            "object": display_nodes.get(name, {}).get("object"),
            "position": position, "correction": "TE topology display correction",
        }
    if len(objects) < 400 or len([name for name in display_edges if name not in SUPPRESSED_GLB_ROUTES]) != 96:
        raise ValueError("Active GLB scene changed; review anchor mapping")
    for name in SUPPRESSED_GLB_ROUTES:
        if name not in display_edges:
            raise ValueError(f"Expected GLB route missing: {name}")
        del display_edges[name]
    for a, b in CORRECTED_ROUTES:
        display_edges[f"Correction_{a}__{b}"] = {
            "object": None, "nodes": [a, b], "kind": "corrected",
        }
    for edge in display_edges.values():
        a, b = edge["nodes"]
        adjacency[a].add(b)
        adjacency[b].add(a)
    vertices = {}
    for vertex in graph["vertices"]:
        source_index = vertex["sourceVertexIndex"]
        anchor = ANCHORS.get(source_index)
        if anchor and anchor not in display_nodes:
            raise ValueError(f"Missing GLB anchor for {vertex['id']}: {anchor}")
        vertices[vertex["id"]] = {
            "name": vertex["name"], "sourceVertexIndex": source_index,
            "sourcePosition": [vertex["x"], vertex["y"]],
            "displayNode": anchor, "status": "candidate" if anchor else "unmapped",
        }
    mapped_edges = {}
    issues = []
    for lane in graph["lanes"]:
        a, b = lane["from"], lane["to"]
        start, end = vertices[a]["displayNode"], vertices[b]["displayNode"]
        path = shortest_display_path(adjacency, start, end) if start and end else None
        if not path or len(path) < 2:
            issues.append({"laneId": lane["id"], "from": a, "to": b, "reason": "No distinct connected GLB route path"})
            continue
        mapped_edges[lane["id"]] = {"from": a, "to": b, "displayNodes": path}
    edge_users = defaultdict(set)
    for lane in mapped_edges.values():
        source_pair = tuple(sorted((lane["from"], lane["to"])))
        for a, b in zip(lane["displayNodes"], lane["displayNodes"][1:]):
            edge_users[tuple(sorted((a, b)))].add(source_pair)
    display_pairs = {tuple(sorted(edge["nodes"])): name for name, edge in display_edges.items()}
    anchor_users = defaultdict(list)
    for vertex_id, vertex in vertices.items():
        anchor_users[vertex["displayNode"]].append(vertex_id)
    audit = {
        "glbRouteMeshesVerified": len([item for item in objects if clean_name(item.get("name", "")).startswith("Route_") and not clean_name(item.get("name", "")).startswith("RouteNode_")]),
        "unmappedVertexIds": [vertex_id for vertex_id, vertex in vertices.items() if not vertex["displayNode"]],
        "duplicateVertexAnchors": {key: value for key, value in anchor_users.items() if key and len(value) > 1},
        "sharedDisplaySegments": [
            {"nodes": list(key), "sourcePairs": [list(pair) for pair in sorted(users)]}
            for key, users in sorted(edge_users.items()) if len(users) > 1
        ],
        "visualOnlyEdges": sorted(name for pair, name in display_pairs.items() if pair not in edge_users),
        "isolatedDisplayNodes": sorted(name for name in display_nodes if not adjacency[name]),
        "nonDestinationRooms": ["Room_director", "Room_men_restroom", "Room_women_restroom", "Room_lift_1", "Room_lift_2"],
    }
    if audit["duplicateVertexAnchors"] or audit["sharedDisplaySegments"]:
        raise ValueError("Ambiguous TE/GLB correspondence; inspect audit before exporting")
    return {
        "schemaVersion": 1, "level": "L1", "graphIndex": 0,
        "source": {str(p.relative_to(ROOT)): digest(p) for p in (BUILDING, NAV_YAML, GRAPH, GLB)},
        "glbScene": glb["scenes"][glb.get("scene", 0)].get("name"),
        "suppressedGlbRoutes": sorted(SUPPRESSED_GLB_ROUTES),
        "correctionNote": "Approved schematic display changes preserve TE topology; corrected bends are not ROS nodes.",
        "displayNodes": display_nodes, "displayEdges": display_edges,
        "vertices": vertices, "lanes": mapped_edges,
        "unmappedLanes": issues, "audit": audit,
    }


def main():
    data = build()
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("Dispatch route mapping is stale; regenerate it")
    else:
        OUTPUT.write_text(content, encoding="utf-8")
    print(f"{len(data['vertices'])} vertices; {len(data['lanes'])} mapped directed lanes; {len(data['unmappedLanes'])} unresolved lanes")
    print(f"  {len(data['audit']['visualOnlyEdges'])} visual-only segments; {len(data['audit']['isolatedDisplayNodes'])} isolated GLB nodes")
    for issue in data["unmappedLanes"]:
        print(f"  {issue['laneId']}: {issue['from']} -> {issue['to']}: {issue['reason']}")


if __name__ == "__main__":
    main()
