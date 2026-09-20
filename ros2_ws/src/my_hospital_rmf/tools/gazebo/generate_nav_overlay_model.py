#!/usr/bin/env python3

import math
from pathlib import Path

import yaml


PKG_ROOT = Path(__file__).resolve().parents[2]

NAV_GRAPH = PKG_ROOT / "nav_graphs/0.yaml"
OVERLAY_MODEL_DIR = PKG_ROOT / "models/hospital_nav_overlay"
MODEL_SDF = OVERLAY_MODEL_DIR / "model.sdf"
MODEL_CONFIG = OVERLAY_MODEL_DIR / "model.config"


def load_nav_graph():
    with NAV_GRAPH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def vertex_name(vertex):
    if len(vertex) >= 3 and isinstance(vertex[2], dict):
        return vertex[2].get("name", "")
    return ""


def box_link(name, pose, size, color):
    return f"""
    <link name="{name}">
      <pose>{pose}</pose>
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
        pose=f"{cx:.6f} {cy:.6f} 0.08 0 0 {yaw:.6f}",
        size=f"{length:.6f} 0.08 0.04",
        color="0.05 0.05 0.05 1",
    )


def main():
    data = load_nav_graph()
    level = data["levels"]["L1"]
    vertices = level["vertices"]
    lanes = level["lanes"]

    OVERLAY_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    links = []
    seen_edges = set()

    for lane in lanes:
        a = int(lane[0])
        b = int(lane[1])
        key = tuple(sorted((a, b)))

        if key in seen_edges:
            continue

        seen_edges.add(key)

        x1, y1 = float(vertices[a][0]), float(vertices[a][1])
        x2, y2 = float(vertices[b][0]), float(vertices[b][1])

        links.append(lane_link(f"lane_{a}_{b}", x1, y1, x2, y2))

    for i, vertex in enumerate(vertices):
        x = float(vertex[0])
        y = float(vertex[1])
        name = vertex_name(vertex)

        if not name:
            color = "0.55 0.55 0.55 1"
            radius = 0.12
            label = f"wp_{i}"
        elif name == "charging_station":
            color = "1.0 0.8 0.0 1"
            radius = 0.28
            label = name
        elif name.endswith("_junction"):
            color = "0.1 0.45 1.0 1"
            radius = 0.18
            label = name
        else:
            color = "0.1 0.85 0.25 1"
            radius = 0.24
            label = name

        safe_label = label.replace("-", "_").replace(" ", "_")

        links.append(cylinder_link(
            name=f"marker_{i}_{safe_label}",
            pose=f"{x:.6f} {y:.6f} 0.18 0 0 0",
            radius=radius,
            length=0.16,
            color=color,
        ))

    MODEL_SDF.write_text(f"""<?xml version="1.0" ?>
<sdf version="1.7">
  <model name="hospital_nav_overlay">
    <static>true</static>
{''.join(links)}
  </model>
</sdf>
""", encoding="utf-8")

    MODEL_CONFIG.write_text("""<?xml version="1.0" ?>
<model>
  <name>hospital_nav_overlay</name>
  <version>1.0</version>
  <sdf version="1.7">model.sdf</sdf>
  <author>
    <name>hospital_rmf</name>
  </author>
  <description>RMF nav graph overlay for Gazebo visualization.</description>
</model>
""", encoding="utf-8")

    print(f"Generated overlay model: {OVERLAY_MODEL_DIR}")
    print(f"Vertices: {len(vertices)}")
    print(f"Unique lanes: {len(seen_edges)}")


if __name__ == "__main__":
    main()
