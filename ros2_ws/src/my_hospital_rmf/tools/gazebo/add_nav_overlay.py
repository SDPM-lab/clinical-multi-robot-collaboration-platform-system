#!/usr/bin/env python3
"""Add the generated navigation overlay model to L1.world."""

from pathlib import Path


PKG_ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = PKG_ROOT / "maps/L1.world"

text = WORLD_PATH.read_text(encoding="utf-8")
if "model://hospital_nav_overlay" in text:
    print("Navigation overlay already present")
    raise SystemExit(0)

overlay_include = """    <include>
      <name>hospital_nav_overlay</name>
      <uri>model://hospital_nav_overlay</uri>
    </include>
"""
marker = "    <rmf_charger_waypoints"
if marker in text:
    text = text.replace(marker, overlay_include + marker, 1)
elif "  </world>" in text:
    text = text.replace("  </world>", overlay_include + "  </world>", 1)
else:
    raise ValueError(f"No world closing tag found in {WORLD_PATH}")

WORLD_PATH.write_text(text, encoding="utf-8")
print("Added hospital_nav_overlay")
