#!/usr/bin/env python3
"""Replace the generated robot with robots declared in fleet_config.yaml."""

from pathlib import Path
import re

import yaml


PKG_ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = PKG_ROOT / "maps/L1.world"
FLEET_CONFIG = PKG_ROOT / "config/fleet_config.yaml"

text = WORLD_PATH.read_text(encoding="utf-8")
config = yaml.safe_load(FLEET_CONFIG.read_text(encoding="utf-8"))
robots = config["rmf_fleet"]["robots"]
if not robots:
    raise ValueError(f"No robots declared in {FLEET_CONFIG}")


def remove_include(world_text: str, name: str) -> str:
    pattern = re.compile(
        rf"\s*<include>\s*<name>{re.escape(name)}</name>.*?</include>",
        flags=re.DOTALL,
    )
    return pattern.sub("", world_text)


text = remove_include(text, "hospital_slam_robot")
for robot_name in robots:
    text = remove_include(text, robot_name)

robot_lines = ["    <!-- robots from fleet_config.yaml — do not edit manually -->"]
for name, info in robots.items():
    pose = info.get("start_pose", [0, 0, 0.05, 0, 0, 0])
    if not isinstance(pose, list) or len(pose) != 6:
        raise ValueError(f"Robot {name!r} requires a six-value start_pose")
    pose_text = " ".join(str(value) for value in pose)
    robot_lines.append(
        f"""    <include>
      <name>{name}</name>
      <uri>model://simple_robot</uri>
      <pose>{pose_text}</pose>
    </include>"""
    )

if "  </world>" not in text:
    raise ValueError(f"No world closing tag found in {WORLD_PATH}")
robot_block = "\n".join(robot_lines) + "\n"
text = text.replace("  </world>", robot_block + "  </world>", 1)
WORLD_PATH.write_text(text, encoding="utf-8")
print(f"Added {len(robots)} robot(s): {', '.join(robots)}")
