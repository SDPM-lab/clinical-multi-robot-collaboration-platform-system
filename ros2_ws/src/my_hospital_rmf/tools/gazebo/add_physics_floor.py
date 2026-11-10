#!/usr/bin/env python3

from pathlib import Path
import re


PKG_ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = PKG_ROOT / "maps/L1.world"

text = WORLD_PATH.read_text(encoding="utf-8")

# 如果之前已經存在 physics_floor，先移除，避免重複加入
pattern = re.compile(
    r'\s*<model\s+name=["\']physics_floor["\']>.*?</model>',
    flags=re.DOTALL,
)

text = pattern.sub("", text)

physics_floor = """
    <!-- Invisible primitive collision floor for robot physics -->
    <model name="physics_floor">
      <static>true</static>
      <pose>0 0 0 0 0 0</pose>
      <link name="floor_link">
        <collision name="floor_collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
        </collision>
      </link>
    </model>
"""

if "  </world>" not in text:
    raise RuntimeError(
        f"No </world> closing tag found in {WORLD_PATH}"
    )

text = text.replace(
    "  </world>",
    physics_floor + "\n  </world>",
    1,
)

WORLD_PATH.write_text(
    text,
    encoding="utf-8",
)

print(f"Added physics_floor to {WORLD_PATH}")
