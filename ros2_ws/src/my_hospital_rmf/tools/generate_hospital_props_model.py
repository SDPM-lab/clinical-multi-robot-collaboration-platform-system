#!/usr/bin/env python3

from pathlib import Path


REPO_ROOT = Path.home() / "clinical-multi-robot-collaboration-platform-system"
PKG_ROOT = REPO_ROOT / "ros2_ws/src/my_hospital_rmf"

MODEL_DIR = PKG_ROOT / "models/hospital_props"
MODEL_SDF = MODEL_DIR / "model.sdf"
MODEL_CONFIG = MODEL_DIR / "model.config"


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
      <collision name="collision">
        <geometry>
          <box>
            <size>{size}</size>
          </box>
        </geometry>
      </collision>
    </link>
"""


def make_bed(name, x, y, yaw=0.0):
    links = []

    links.append(box_link(
        f"{name}_base",
        f"{x} {y} 0.25 0 0 {yaw}",
        "1.6 0.75 0.25",
        "0.85 0.85 0.9 1"
    ))

    links.append(box_link(
        f"{name}_pillow",
        f"{x - 0.5} {y} 0.45 0 0 {yaw}",
        "0.35 0.65 0.12",
        "0.95 0.95 1.0 1"
    ))

    return "".join(links)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    links = []

    # 左側病房
    links.append(make_bed("ward_a_bed", 7.7, -3.4, 1.57))
    links.append(make_bed("ward_b_bed", 7.7, -7.3, 1.57))
    links.append(make_bed("ward_c_bed", 7.7, -11.0, 1.57))
    links.append(make_bed("ward_d_bed", 7.7, -14.8, 1.57))

    # 護理站櫃台
    links.append(box_link(
        "nurse_station_counter",
        "9.8 -10.5 0.45 0 0 0",
        "1.6 0.45 0.9",
        "0.2 0.5 1.0 1"
    ))

    # 藥局藥櫃
    links.append(box_link(
        "pharmacy_shelf_1",
        "30.9 -5.2 0.8 0 0 0",
        "1.4 0.3 1.6",
        "1.0 0.8 0.25 1"
    ))

    links.append(box_link(
        "pharmacy_shelf_2",
        "30.9 -4.4 0.8 0 0 0",
        "1.4 0.3 1.6",
        "1.0 0.8 0.25 1"
    ))

    # 檢驗室桌
    links.append(box_link(
        "lab_table",
        "13.1 -5.3 0.4 0 0 0",
        "1.4 0.7 0.8",
        "0.6 0.6 0.6 1"
    ))

    # 抽血區椅子
    links.append(box_link(
        "blood_draw_chair",
        "17.3 -5.3 0.3 0 0 0",
        "0.55 0.55 0.6",
        "0.3 0.7 0.9 1"
    ))

    # 處置室診療床
    links.append(box_link(
        "procedure_room_bed",
        "23.4 -5.2 0.35 0 0 0",
        "1.6 0.7 0.35",
        "0.9 0.9 0.95 1"
    ))

    # 倉儲架
    links.append(box_link(
        "storage_shelf",
        "28.3 -15.1 0.9 0 0 0",
        "1.6 0.35 1.8",
        "0.55 0.35 0.2 1"
    ))

    # 會議桌
    links.append(box_link(
        "meeting_table",
        "30.2 -21.8 0.4 0 0 0",
        "1.8 0.9 0.8",
        "0.45 0.28 0.15 1"
    ))

    MODEL_SDF.write_text(f"""<?xml version="1.0" ?>
<sdf version="1.7">
  <model name="hospital_props">
    <static>true</static>
{''.join(links)}
  </model>
</sdf>
""", encoding="utf-8")

    MODEL_CONFIG.write_text("""<?xml version="1.0" ?>
<model>
  <name>hospital_props</name>
  <version>1.0</version>
  <sdf version="1.7">model.sdf</sdf>
  <author>
    <name>hospital_rmf</name>
  </author>
  <description>Simple hospital props for Gazebo visualization.</description>
</model>
""", encoding="utf-8")

    print(f"Generated hospital props model: {MODEL_DIR}")


if __name__ == "__main__":
    main()
