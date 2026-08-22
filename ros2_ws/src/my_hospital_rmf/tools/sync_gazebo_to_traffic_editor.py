#!/usr/bin/env python3
"""Synchronize model poses from a Gazebo saved world to Traffic Editor."""

import argparse
from datetime import datetime
import math
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

import yaml


# ANSI colour helpers — disabled when stdout is not a TTY (e.g. piped to a file).
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text

def _green(t):  return _c("32", t)
def _yellow(t): return _c("33", t)
def _cyan(t):   return _c("36", t)
def _dim(t):    return _c("2",  t)
def _bold(t):   return _c("1",  t)


def _find_src_pkg() -> Path:
    """Return the source-tree package root, even when running from install/."""
    try:
        from ament_index_python.packages import get_package_share_directory
        # share = <ws>/install/my_hospital_rmf/share/my_hospital_rmf
        # parents[3] = <ws>
        share = Path(get_package_share_directory("my_hospital_rmf"))
        candidate = share.parents[3] / "src" / "my_hospital_rmf"
        if candidate.is_dir():
            return candidate
    except (ImportError, LookupError):
        pass
    return Path(__file__).resolve().parents[1]


_SRC_PKG = _find_src_pkg()

DEFAULT_SDF      = _SRC_PKG / "maps/hospital_real.sdf"
DEFAULT_BUILDING = _SRC_PKG / "maps/hospital.building.yaml"
DEFAULT_PROPS    = _SRC_PKG / "config/props.yaml"
DEFAULT_BACKUPS  = _SRC_PKG / "backups"
MAX_BACKUPS      = 5
LEVEL            = "L1"
BACKUP_NAME_RE   = re.compile(r"^\d{8}_\d{6}(?:_\d{6})?$")
EXCLUDED_NAMES   = {
    "hospital_L1",
    "hospital_nav_overlay",
    "hospital_robot_1",
    "hospital_robot_2",
    "hospital_robot_3",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Write Gazebo model poses back to hospital.building.yaml"
    )
    parser.add_argument(
        "sdf",
        type=Path,
        nargs="?",
        default=DEFAULT_SDF,
        help=f"SDF saved from Gazebo Sim (default: {DEFAULT_SDF})",
    )
    return parser.parse_args()


def read_saved_poses(sdf_path):
    root = ET.parse(sdf_path).getroot()
    world = root.find("world") if root.tag == "sdf" else None
    if world is None:
        raise ValueError(f"No <world> found in {sdf_path}")

    poses = {}
    for model in world.findall("model"):
        name = model.get("name")
        pose = model.find("pose")
        if name and pose is not None and pose.text:
            poses[name] = parse_pose(pose.text, name)
    for include in world.findall("include"):
        name = include.findtext("name")
        pose_text = include.findtext("pose")
        if name and pose_text:
            poses[name] = parse_pose(pose_text, name)
    return poses


def parse_pose(text, name):
    values = [float(v) for v in text.split()]
    if len(values) != 6:
        raise ValueError(
            f"Entity {name!r} has {len(values)} pose values; expected x y z roll pitch yaw"
        )
    return values


def level_scale(building):
    level = building["levels"][LEVEL]
    vertices = level.get("vertices", [])
    measurements = level.get("measurements", [])
    if not measurements:
        raise ValueError(f"Level {LEVEL!r} has no scale measurement")
    start_index, end_index, params = measurements[0]
    distance_param = params.get("distance")
    if not isinstance(distance_param, list) or len(distance_param) < 2:
        raise ValueError("Invalid Traffic Editor measurement distance")
    distance_metres = float(distance_param[1])
    start = vertices[start_index]
    end = vertices[end_index]
    pixel_distance = math.hypot(float(end[0]) - float(start[0]), float(end[1]) - float(start[1]))
    if pixel_distance <= 0:
        raise ValueError("Traffic Editor scale measurement has zero pixel length")
    return distance_metres / pixel_distance


def unique_model_names(models):
    """Reproduce building_map_generator's suffixes: name, name_2, name_3, ..."""
    counts = {}
    names = []
    for model in models:
        base = str(model["name"])
        counts[base] = counts.get(base, 0) + 1
        names.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return names


def model_line_indices(lines):
    level_pattern = re.compile(rf"^  {re.escape(LEVEL)}:\s*$")
    level_start = next(
        (i for i, line in enumerate(lines) if level_pattern.match(line.rstrip("\n"))),
        None,
    )
    if level_start is None:
        raise ValueError(f"Level {LEVEL!r} not found in YAML text")

    models_start = next(
        (
            i for i in range(level_start + 1, len(lines))
            if re.match(r"^    models:\s*$", lines[i].rstrip("\n"))
        ),
        None,
    )
    if models_start is None:
        raise ValueError(f"models section for level {LEVEL!r} not found")

    indices = []
    for i in range(models_start + 1, len(lines)):
        line = lines[i]
        if re.match(r"^    \S", line) and not line.startswith("      "):
            break
        if re.match(r"^      - \{.*\}\s*$", line.rstrip("\n")):
            indices.append(i)
    return indices


def replace_number(line, key, value):
    pattern = re.compile(rf"({re.escape(key)}:\s*)[-+0-9.eE]+")
    updated, count = pattern.subn(rf"\g<1>{value:.15g}", line, count=1)
    if count != 1:
        raise ValueError(f"Could not update {key!r} in model line: {line.rstrip()}")
    return updated


def reconcile_props_text(original_text, poses, deleted_names, renamed_names):
    """Update, delete, and rename complete prop entries while preserving YAML style."""
    lines = original_text.splitlines(keepends=True)
    name_pattern = re.compile(r"^(\s*- name:\s*)(.+?)(\s*\n?)$")
    pose_pattern = re.compile(r"^(\s*pose:\s*)\[([^]]+)\](\s*(?:#.*)?\n?)$")

    starts = [
        (i, m.group(2).strip().strip("'\""))
        for i, line in enumerate(lines)
        if (m := name_pattern.match(line))
    ]

    changes, deleted, renamed = [], [], []
    output = lines[: starts[0][0]] if starts else list(lines)
    for position, (start, name) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        block = lines[start:end]
        if name in deleted_names:
            deleted.append(name)
            continue
        new_name = renamed_names.get(name, name)
        if new_name != name:
            match = name_pattern.match(block[0])
            block[0] = f"{match.group(1)}{new_name}{match.group(3)}"
            renamed.append((name, new_name))
        pose = poses.get(name)
        if pose is not None:
            for bi, line in enumerate(block):
                pose_match = pose_pattern.match(line)
                if not pose_match:
                    continue
                old = [float(v.strip()) for v in pose_match.group(2).split(",")]
                if len(old) != 6:
                    raise ValueError(f"Prop {name!r} does not have a six-value pose")
                if not all(abs(a - b) <= 1e-8 for a, b in zip(old, pose)):
                    pose_text = ", ".join(f"{v:.15g}" for v in pose)
                    block[bi] = f"{pose_match.group(1)}[{pose_text}]{pose_match.group(3)}"
                    changes.append((name, old, pose))
                break
        output.extend(block)
    return "".join(output), changes, deleted, renamed


def prune_old_backups(backup_root):
    backup_dirs = sorted(
        p for p in backup_root.iterdir()
        if p.is_dir() and BACKUP_NAME_RE.fullmatch(p.name)
    )
    removed = []
    for old in backup_dirs[:-MAX_BACKUPS]:
        shutil.rmtree(old)
        removed.append(old)
    return removed


def main():
    args = parse_args()
    sdf_path      = args.sdf.resolve()
    building_path = DEFAULT_BUILDING.resolve()
    props_path    = DEFAULT_PROPS.resolve()
    backup_root   = DEFAULT_BACKUPS.resolve()

    if not sdf_path.is_file():
        raise FileNotFoundError(f"Saved SDF not found: {sdf_path}")
    if not building_path.is_file():
        raise FileNotFoundError(f"Building YAML not found: {building_path}")
    if not props_path.is_file():
        raise FileNotFoundError(f"Props YAML not found: {props_path}")

    original_text = building_path.read_text(encoding="utf-8")
    building = yaml.safe_load(original_text)
    if building.get("coordinate_system") != "reference_image":
        raise ValueError("This importer currently requires coordinate_system: reference_image")
    if LEVEL not in building.get("levels", {}):
        raise ValueError(f"Level {LEVEL!r} not found in {building_path}")

    poses = read_saved_poses(sdf_path)
    models = building["levels"][LEVEL].get("models", [])
    entity_names = unique_model_names(models)
    lines = original_text.splitlines(keepends=True)
    line_indices = model_line_indices(lines)
    if len(line_indices) != len(models):
        raise ValueError(
            f"Parsed {len(models)} YAML models but found {len(line_indices)} editable model lines"
        )

    metres_per_pixel = level_scale(building)
    changes, missing = [], []
    for model, entity_name, line_index in zip(models, entity_names, line_indices):
        if entity_name in EXCLUDED_NAMES:
            continue
        pose = poses.get(entity_name)
        if pose is None:
            missing.append(entity_name)
            continue
        world_x, world_y, world_z, _roll, _pitch, world_yaw = pose
        pixel_x = world_x / metres_per_pixel
        pixel_y = -world_y / metres_per_pixel
        old = (
            float(model.get("x", 0)),
            float(model.get("y", 0)),
            float(model.get("z", 0)),
            float(model.get("yaw", 0)),
        )
        new = (pixel_x, pixel_y, world_z, world_yaw)
        if all(abs(a - b) <= 1e-8 for a, b in zip(old, new)):
            continue
        line = lines[line_index]
        line = replace_number(line, "x", pixel_x)
        line = replace_number(line, "y", pixel_y)
        line = replace_number(line, "z", world_z)
        line = replace_number(line, "yaw", world_yaw)
        lines[line_index] = line
        changes.append((entity_name, old, new))

    # Always delete models absent from the SDF.
    deleted_names = set(missing)
    surviving_models    = [m for m, n in zip(models, entity_names) if n not in deleted_names]
    surviving_old_names = [n for n in entity_names if n not in deleted_names]
    surviving_new_names = unique_model_names(surviving_models)
    renamed_names = {o: n for o, n in zip(surviving_old_names, surviving_new_names) if o != n}

    if deleted_names:
        deleted_line_indices = [
            li for n, li in zip(entity_names, line_indices) if n in deleted_names
        ]
        for li in sorted(deleted_line_indices, reverse=True):
            del lines[li]

    props_original_text = props_path.read_text(encoding="utf-8")
    props_document = yaml.safe_load(props_original_text) or {}
    prop_names = {
        str(prop.get("name"))
        for prop in props_document.get("props", [])
        if prop.get("name") is not None
    }
    deleted_prop_names = set(deleted_names)
    deleted_prop_names.update(
        n for n in prop_names if n not in poses and n not in EXCLUDED_NAMES
    )
    props_updated_text, props_changes, props_deleted, props_renamed = reconcile_props_text(
        props_original_text, poses, deleted_prop_names, renamed_names
    )

    print(_dim(f"Scale: {metres_per_pixel:.15g} metre/pixel"))
    for name, old, new in changes:
        print(
            _green(name) + ": "
            f"({old[0]:.3f}, {old[1]:.3f}, z={old[2]:.3f}, yaw={old[3]:.4f}) -> "
            + _cyan(f"({new[0]:.3f}, {new[1]:.3f}, z={new[2]:.3f}, yaw={new[3]:.4f})")
        )
    print(_bold(f"Matched {len(models) - len(missing)} of {len(models)} Traffic Editor models"))
    print(_green(f"Changed {len(changes)} model pose(s)"))
    print(_green(f"Changed {len(props_changes)} props override pose(s)"))
    for name in missing:
        print(_yellow(f"Delete missing model: {name}"))
    if props_deleted:
        print(_yellow(f"Deleted {len(props_deleted)} matching prop override(s)"))
    for old_name, new_name in props_renamed:
        print(_cyan(f"Renamed prop override: {old_name} -> {new_name}"))

    building_changed = bool(changes or deleted_names)
    props_changed    = bool(props_changes or props_deleted or props_renamed)
    if not building_changed and not props_changed:
        print(_dim("No changes to write"))
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = backup_root / timestamp
    backup_dir.mkdir(parents=True)
    if building_changed:
        shutil.copy2(building_path, backup_dir / building_path.name)
        building_path.write_text("".join(lines), encoding="utf-8")
        print(_dim(f"Backup: {backup_dir / building_path.name}"))
        print(_green(f"Updated: {building_path}"))
    if props_changed:
        shutil.copy2(props_path, backup_dir / props_path.name)
        props_path.write_text(props_updated_text, encoding="utf-8")
        print(_dim(f"Backup: {backup_dir / props_path.name}"))
        print(_green(f"Updated: {props_path}"))
    for removed in prune_old_backups(backup_root):
        print(_dim(f"Removed old backup: {removed}"))
    print(_bold(_green("Run rebuild-hospital to regenerate Gazebo and navigation outputs")))


if __name__ == "__main__":
    main()
