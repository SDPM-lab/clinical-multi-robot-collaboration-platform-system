#!/usr/bin/env python3

import math
from pathlib import Path

import yaml


REPO_ROOT = Path.home() / "clinical-multi-robot-collaboration-platform-system"
PKG_ROOT = REPO_ROOT / "ros2_ws/src/my_hospital_rmf"

NAV_GRAPH = PKG_ROOT / "nav_graphs/0.yaml"
MODEL_SDF = PKG_ROOT / "models/hospital_L1/model.sdf"


def load_nav_graph():
    with NAV_GRAPH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_vertices_and_lanes(data):
    level = data["levels"]["L1"]
    vertices = level["vertices"]
    lanes = level["lanes"]
    return vertices, lanes


def vertex_name(vertex):
    if len(vertex) >= 3 and isinstance(vertex[2], dict):
        return vertex[2].get("name", "")
    return ""


def box_link(name, pose, size, color, collision=False):
    collision_xml = ""
    if collision:
        collision_xml = f"""
      <collision name="collision">
        <geometry>
          <box>
            <size>{size}</size>
          </box>
        </geometry>
      </collision>"""

    return f"""
    <link name="{name}">
      <pose>{pose}</pose>{collision_xml}
      <visual name="visual">
        <geometry>
          <box>
            <size>{size}</size>
          </box>
        </geometry>
        <material>
          <ambient>{color}</ambient>
          <diffuse>{color}</diffuse>
        </material>
      </visual>
    </link>
"""


def cylinder_link(name, pose, radius, length, color):
    return f"""
    <link name="{name}">
      <pose>{pose}</pose>
      <visual name="visual">
        <geometry>
          <cylinder>
            <radius>{radius}</radius>
            <length>{length}</length>
          </cylinder>
        </geometry>
        <material>
          <ambient>{color}</ambient>
          <diffuse>{color}</diffuse>
        </material>
      </visual>
    </link>
"""


def lane_link(name, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return ""

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    yaw = math.atan2(dy, dx)

    return box_link(
        name=name,
        pose=f"{cx:.6f} {cy:.6f} 0.035 0 0 {yaw:.6f}",
        size=f"{length:.6f} 0.08 0.04",
        color="0.15 0.15 0.15 1",
        collision=False,
    )


def main():
    data = load_nav_graph()
    vertices, lanes = get_vertices_and_lanes(data)

    xs = [float(v[0]) for v in vertices]
    ys = [float(v[1]) for v in vertices]

    min_x = min(xs) - 2.0
    max_x = max(xs) + 2.0
    min_y = min(ys) - 2.0
    max_y = max(ys) + 2.0

    floor_cx = (min_x + max_x) / 2.0
    floor_cy = (min_y + max_y) / 2.0
    floor_w = max_x - min_x
    floor_h = max_y - min_y

    links = []

    links.append(box_link(
        name="floor",
        pose=f"{floor_cx:.6f} {floor_cy:.6f} -0.025 0 0 0",
        size=f"{floor_w:.6f} {floor_h:.6f} 0.05",
        color="0.88 0.88 0.88 1",
        collision=True,
    ))

    # 產生 nav lanes
    seen_edges = set()
    for i, lane in enumerate(lanes):
        a, b = int(lane[0]), int(lane[1])
        key = tuple(sorted((a, b)))
        if key in seen_edges:
            continue
        seen_edges.add(key)

        x1, y1 = float(vertices[a][0]), float(vertices[a][1])
        x2, y2 = float(vertices[b][0]), float(vertices[b][1])

        links.append(lane_link(f"lane_{a}_{b}", x1, y1, x2, y2))

    # 產生 waypoint markers
    for i, vertex in enumerate(vertices):
        x, y = float(vertex[0]), float(vertex[1])
        name = vertex_name(vertex)

        if not name:
            color = "0.55 0.55 0.55 1"
            radius = 0.12
            label = f"wp_{i}"
        elif name.endswith("_junction"):
            color = "0.2 0.55 1.0 1"
            radius = 0.16
            label = name
        elif name == "charging_station":
            color = "1.0 0.85 0.1 1"
            radius = 0.25
            label = name
        else:
            color = "0.2 0.9 0.35 1"
            radius = 0.22
            label = name

        safe_label = label.replace("-", "_").replace(" ", "_")
        links.append(cylinder_link(
            name=f"marker_{i}_{safe_label}",
            pose=f"{x:.6f} {y:.6f} 0.09 0 0 0",
            radius=radius,
            length=0.12,
            color=color,
        ))

    sdf = f"""<?xml version='1.0' encoding='utf-8'?>
<sdf version="1.7">
  <model name="hospital_L1">
    <static>true</static>
{''.join(links)}
  </model>
</sdf>
"""

    MODEL_SDF.write_text(sdf, encoding="utf-8")
    print(f"Generated: {MODEL_SDF}")
    print(f"Vertices: {len(vertices)}")
    print(f"Unique lanes: {len(seen_edges)}")
    print(f"Floor: center=({floor_cx:.2f}, {floor_cy:.2f}), size=({floor_w:.2f}, {floor_h:.2f})")


if __name__ == "__main__":
    main()
