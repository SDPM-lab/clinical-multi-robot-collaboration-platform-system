"""
Step 4: Patch hospital.world with:
  1. hospital_nav_overlay include
  2. Robots from fleet_config.yaml (replaces the single hospital_slam_robot)
"""
import re
import yaml
from pathlib import Path

REPO      = Path(__file__).resolve().parents[4]
world_path = REPO / "ros2_ws/src/my_hospital_rmf/maps/hospital.world"
cfg_path   = REPO / "ros2_ws/src/my_hospital_rmf/config/fleet_config.yaml"

text = world_path.read_text(encoding="utf-8")

# ── 1. nav overlay ───────────────────────────────────────────────
overlay_include = """    <include>
      <name>hospital_nav_overlay</name>
      <uri>model://hospital_nav_overlay</uri>
    </include>
"""
if "model://hospital_nav_overlay" in text:
    print("hospital_nav_overlay already in world")
else:
    marker = "    <rmf_charger_waypoints"
    if marker in text:
        text = text.replace(marker, overlay_include + marker)
    else:
        text = text.replace("  </world>", overlay_include + "  </world>")
    print("Added hospital_nav_overlay")

# ── 2. 移除 building_map_generator 生成的單台 hospital_slam_robot ──
text = re.sub(
    r'\s*<include>\s*<name>hospital_slam_robot</name>.*?</include>',
    '',
    text,
    flags=re.DOTALL,
)

# ── 3. 從 fleet_config.yaml 讀取所有機器人 ──
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

robots = cfg["rmf_fleet"]["robots"]

if any(f'<name>{n}</name>' in text for n in robots):
    print("Robot includes already in world")
else:
    robot_lines = ["    <!-- robots from fleet_config.yaml — do not edit manually -->"]
    for name, info in robots.items():
        pose = info.get("start_pose", [0, 0, 0.05, 0, 0, 0])
        pose_str = " ".join(str(v) for v in pose)
        robot_lines.append(f"""    <include>
      <name>{name}</name>
      <uri>model://simple_robot</uri>
      <pose>{pose_str}</pose>
    </include>""")
    robot_block = "\n".join(robot_lines) + "\n"
    text = text.replace("  </world>", robot_block + "  </world>")
    print(f"Added {len(robots)} robot(s): {', '.join(robots)}")

world_path.write_text(text, encoding="utf-8")
print("Done patching hospital.world")
