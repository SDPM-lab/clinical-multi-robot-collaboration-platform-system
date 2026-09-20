#!/usr/bin/env python3
"""Synchronize Gazebo L1 instances into the existing beautified Blender scene.

Run with Blender, opening the destination scene first:

  blender --background blender/scenes/floor_L1.blend \
    --python ros2_ws/src/my_hospital_rmf/tools/blender/sync_l1_world_to_blender.py \
    -- --apply

Without ``--apply`` the script only prints the planned changes. The synchronizer
updates the source proxy roots and any beautified replacement roots that declare
``source_object``, ``replacement_for``, or ``source_gazebo_object``. Blender-only
building, camera, light, material, and decoration objects are left untouched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Euler, Matrix


SCRIPT = Path(__file__).resolve()


def project_root() -> Path:
    for parent in SCRIPT.parents:
        if (parent / "ros2_ws/src/my_hospital_rmf").exists():
            return parent
    raise RuntimeError("Cannot find project root")


ROOT = project_root()
PKG = ROOT / "ros2_ws/src/my_hospital_rmf"
DEFAULT_WORLD = PKG / "maps/L1.world"
DEFAULT_MODELS = PKG / "models"
IMPORTER_PATH = SCRIPT.with_name("blender_import_hospital_proxy.py")
BLENDER_WALL_Z_SCALE = 0.45


def load_importer():
    spec = importlib.util.spec_from_file_location("hospital_proxy_importer", IMPORTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bmatrix(pose):
    x, y, z, roll, pitch, yaw = pose
    return Matrix.Translation((x, y, z)) @ Euler((roll, pitch, yaw), "XYZ").to_matrix().to_4x4()


def natural_instance_key(name):
    tail = name.rsplit("_", 1)
    if len(tail) == 2 and tail[1].isdigit():
        return tail[0], int(tail[1])
    return name, 1


def get_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        floor = bpy.data.collections.get("Floor_1")
        (floor or bpy.context.scene.collection).children.link(collection)
    return collection


def collection_roots(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        return []
    return [obj for obj in collection.objects if obj.parent is None]


def source_name(obj):
    for key in ("source_object", "replacement_for", "source_gazebo_object"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def replacement_map():
    result = {}
    proxy_collections = {"Furniture_Proxy", "Robots_Proxy", "Doors_Proxy", "Building"}
    for obj in bpy.data.objects:
        if obj.parent is not None:
            continue
        if any(collection.name in proxy_collections for collection in obj.users_collection):
            continue
        source = source_name(obj)
        if source:
            result.setdefault(source, []).append(obj)

    # Older PotatoChipChair replacements predate source metadata. Their numeric
    # suffixes still match the Gazebo instance suffixes, so record that relation.
    collection = bpy.data.collections.get("Potato_Chip_Chair")
    if collection:
        roots = sorted(
            (obj for obj in collection.objects if obj.parent is None),
            key=lambda obj: natural_instance_key(obj.name),
        )
        for index, obj in enumerate(roots, 1):
            source = "OpenRobotics/PotatoChipChair" + (f"_{index}" if index > 1 else "")
            obj["source_object"] = source
            result.setdefault(source, []).append(obj)

    # The custom chair roots use the Gazebo suffix in their own name.
    collection = bpy.data.collections.get("Chair")
    if collection:
        for obj in (item for item in collection.objects if item.parent is None):
            suffix = obj.name.removeprefix("Chair_Root")
            source = "OpenRobotics/Chair" + suffix
            obj["source_object"] = source
            result.setdefault(source, []).append(obj)

    # The hand-built warm reception desks were created before replacement
    # metadata was introduced. Their suffixes match the NurseTable instances.
    collection = bpy.data.collections.get("Reception_Design")
    if collection:
        for obj in (item for item in collection.objects if item.parent is None):
            if not obj.name.startswith("nurse_table_warm_modern"):
                continue
            suffix = obj.name.removeprefix("nurse_table_warm_modern")
            source = "OpenRobotics/NurseTable" + suffix
            obj["source_object"] = source
            result.setdefault(source, []).append(obj)
    return result


def nurse_tables_missing_appearance(items, proxies, relations):
    return sorted(
        name for name in items
        if name.startswith("OpenRobotics/NurseTable")
        and name in proxies
        and not relations.get(name)
    )


def add_nurse_table_appearance(name, proxy, proxies, relations):
    prototype_name = "OpenRobotics/NurseTable"
    prototype_proxy = proxies.get(prototype_name)
    prototype_replacements = relations.get(prototype_name, [])
    if prototype_proxy is None or not prototype_replacements:
        raise RuntimeError("Cannot find nurse_table_warm_modern appearance prototype")
    source = prototype_replacements[0]
    offset = prototype_proxy.matrix_world.inverted_safe() @ source.matrix_world.copy()
    suffix = name.removeprefix(prototype_name)
    replacement = clone_tree(
        source,
        "nurse_table_warm_modern" + suffix,
        source.users_collection[0],
    )
    replacement.matrix_world = proxy.matrix_world @ offset
    replacement["source_object"] = name
    set_hidden_tree(proxy, True)
    relations.setdefault(name, []).append(replacement)
    return replacement


def descendants(root):
    found = []
    stack = list(root.children)
    while stack:
        item = stack.pop()
        found.append(item)
        stack.extend(item.children)
    return found


def remove_tree(root):
    for obj in reversed(descendants(root)):
        bpy.data.objects.remove(obj, do_unlink=True)
    if root.name in bpy.data.objects:
        bpy.data.objects.remove(root, do_unlink=True)


def clone_tree(source_root, root_name, target_collection=None):
    mapping = {}

    def clone(source, parent=None):
        copied = source.copy()
        if source.data is not None:
            copied.data = source.data.copy()
        mapping[source] = copied
        collections = [target_collection] if parent is None and target_collection else list(source.users_collection)
        for collection in collections:
            collection.objects.link(copied)
        copied.parent = parent
        copied.matrix_parent_inverse = source.matrix_parent_inverse.copy()
        copied.matrix_basis = source.matrix_basis.copy()
        for child in source.children:
            clone(child, copied)
        return copied

    result = clone(source_root)
    result.name = root_name
    return result


def set_hidden_tree(root, hidden):
    for obj in [root, *descendants(root)]:
        obj.hide_set(hidden)
        obj.hide_viewport = hidden
        obj.hide_render = hidden


def rename_proxy_child(root):
    children = list(root.children)
    if len(children) == 1:
        children[0].name = root.name + "__proxy"


def make_box_proxy(item, collection_name, visible=True):
    collection = get_collection(collection_name)
    root = bpy.data.objects.new(item["name"], None)
    root.empty_display_type = "CUBE"
    root.empty_display_size = 0.22
    root.matrix_world = bmatrix(item["pose"])
    root["sdf_uri"] = item["uri"]
    root["sdf_pose"] = list(item["pose"])
    root["proxy_size"] = list(item["proxy"]["size"])
    root["bounds_source"] = item["proxy"]["source"]
    collection.objects.link(root)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    cube = bpy.context.object
    for old in list(cube.users_collection):
        old.objects.unlink(cube)
    collection.objects.link(cube)
    cube.name = item["name"] + "__proxy"
    cube.dimensions = item["proxy"]["size"]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cube.parent = root
    cube.matrix_parent_inverse = Matrix.Identity(4)
    cube.matrix_basis = Matrix.Translation(item["proxy"]["center"])
    cube.display_type = "WIRE"
    cube.color = (0.35, 0.55, 0.8, 1.0) if collection_name == "Furniture_Proxy" else (0.85, 0.35, 0.15, 1.0)
    if not visible:
        set_hidden_tree(root, True)
    return root


def model_material(visual, cache):
    diffuse = visual.findtext("material/diffuse") or visual.findtext("material/ambient")
    values = tuple(float(value) for value in diffuse.split()) if diffuse else (0.55, 0.58, 0.60, 1.0)
    rgba = (values + (1.0, 1.0, 1.0, 1.0))[:4]
    key = tuple(round(value, 4) for value in rgba)
    if key not in cache:
        material = bpy.data.materials.new("MAT_SyncedElevator_" + "_".join(f"{value:.2f}" for value in key[:3]))
        material.diffuse_color = key
        material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = key
        shader.inputs["Roughness"].default_value = 0.42
        shader.inputs["Metallic"].default_value = 0.12
        cache[key] = material
    return cache[key]


def import_mesh(path, collection, base_name):
    before = set(bpy.data.objects)
    suffix = path.suffix.lower()
    if suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    elif suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
    elif suffix == ".dae":
        bpy.ops.wm.collada_import(filepath=str(path))
    else:
        raise RuntimeError(f"Unsupported building mesh: {path}")
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    for index, obj in enumerate(meshes, 1):
        matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = matrix
        obj.name = base_name if len(meshes) == 1 else f"{base_name}_{index}"
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
    for obj in imported:
        if obj not in meshes:
            bpy.data.objects.remove(obj, do_unlink=True)
    return meshes


def sync_building(resolver, building):
    """Replace generated wall meshes while keeping the custom Blender floor."""
    collection = get_collection("Building")
    old_walls = [obj for obj in list(collection.objects) if obj.name.startswith("hospital_L1__wall_")]
    for obj in old_walls:
        bpy.data.objects.remove(obj, do_unlink=True)

    wall_material = bpy.data.materials.get("MAT_Wall_WarmWhite")
    imported_count = 0
    building_matrix = bmatrix(building["pose"])
    for link in building["model"].findall("link"):
        for visual in link.findall("visual"):
            mesh = visual.find("geometry/mesh")
            if mesh is None:
                continue
            path = resolver.asset(mesh.findtext("uri", ""), building["source"].parent)
            if path is None:
                raise RuntimeError(f"Missing building visual: {mesh.findtext('uri')}")
            base_name = f"hospital_L1__{link.get('name')}__{visual.get('name')}"
            imported = import_mesh(path, collection, base_name)
            scale = tuple(float(value) for value in (mesh.findtext("scale") or "1 1 1").split())
            local = (
                bmatrix(tuple(float(x) for x in (link.findtext("pose") or "0 0 0 0 0 0").split()))
                @ bmatrix(tuple(float(x) for x in (visual.findtext("pose") or "0 0 0 0 0 0").split()))
                @ Matrix.Diagonal((*scale, 1.0))
            )
            for obj in imported:
                obj.matrix_world = building_matrix @ local @ obj.matrix_world
                obj.scale.z *= BLENDER_WALL_Z_SCALE
                obj["sdf_link"] = link.get("name", "")
                obj["sdf_visual"] = visual.get("name", "")
                obj["blender_wall_z_scale"] = BLENDER_WALL_Z_SCALE
                if wall_material:
                    obj.data.materials.clear()
                    obj.data.materials.append(wall_material)
                imported_count += 1
    return len(old_walls), imported_count


def make_elevator(item, proxy_root, material_cache):
    collection = get_collection("Elevators")
    root = bpy.data.objects.new("Elevator_" + item["name"].rsplit("_", 1)[-1], None)
    root.matrix_world = bmatrix(item["pose"])
    root["source_object"] = item["name"]
    root["model"] = "hospital_elevator_static_real"
    collection.objects.link(root)
    model = item["model"]
    for link in model.findall("link"):
        link_matrix = bmatrix(tuple(float(x) for x in (link.findtext("pose") or "0 0 0 0 0 0").split()))
        for visual in link.findall("visual"):
            visual_pose = tuple(float(x) for x in (visual.findtext("pose") or "0 0 0 0 0 0").split())
            geometry = visual.find("geometry")
            if geometry is None:
                continue
            obj = None
            box = geometry.find("box")
            cylinder = geometry.find("cylinder")
            if box is not None:
                size = tuple(float(x) for x in box.findtext("size").split())
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                obj = bpy.context.object
                obj.dimensions = size
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            elif cylinder is not None:
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=48,
                    radius=float(cylinder.findtext("radius")),
                    depth=float(cylinder.findtext("length")),
                )
                obj = bpy.context.object
            if obj is None:
                continue
            for old in list(obj.users_collection):
                old.objects.unlink(obj)
            collection.objects.link(obj)
            obj.name = f"{root.name}__{link.get('name')}__{visual.get('name')}"
            obj.parent = root
            obj.matrix_parent_inverse = Matrix.Identity(4)
            obj.matrix_basis = link_matrix @ bmatrix(visual_pose)
            obj.data.materials.append(model_material(visual, material_cache))
    set_hidden_tree(proxy_root, True)
    return root


def make_door(item):
    collection = get_collection("Doors_Proxy")
    model = item["model"]
    root = bpy.data.objects.new(item["name"], None)
    root.empty_display_type = "ARROWS"
    root.empty_display_size = 0.28
    root.matrix_world = bmatrix(item["pose"])
    root["sdf_pose"] = list(item["pose"])
    collection.objects.link(root)
    joints = {joint.findtext("child", ""): joint for joint in model.findall("joint")}
    for link in model.findall("link"):
        joint = joints.get(link.get("name", ""))
        pivot_pose = tuple(float(x) for x in (joint.findtext("pose") if joint is not None else "0 0 0 0 0 0").split())
        pivot_local = bmatrix(pivot_pose)
        pivot_name = joint.get("name", "pivot") if joint is not None else link.get("name", "pivot") + "_pivot"
        pivot = bpy.data.objects.new(f"{item['name']}__{pivot_name}", None)
        collection.objects.link(pivot)
        pivot.parent = root
        pivot.matrix_parent_inverse = Matrix.Identity(4)
        pivot.matrix_basis = pivot_local
        pivot["rotation_center"] = True
        for visual in link.findall("visual"):
            box = visual.find("geometry/box")
            if box is None:
                continue
            size = tuple(float(x) for x in box.findtext("size").split())
            link_pose = tuple(float(x) for x in (link.findtext("pose") or "0 0 0 0 0 0").split())
            visual_pose = tuple(float(x) for x in (visual.findtext("pose") or "0 0 0 0 0 0").split())
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            leaf = bpy.context.object
            for old in list(leaf.users_collection):
                old.objects.unlink(leaf)
            collection.objects.link(leaf)
            leaf.name = f"{item['name']}__{link.get('name')}__proxy"
            leaf.dimensions = size
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            leaf.parent = pivot
            leaf.matrix_parent_inverse = Matrix.Identity(4)
            leaf.matrix_basis = pivot_local.inverted() @ bmatrix(link_pose) @ bmatrix(visual_pose)
            leaf.display_type = "WIRE"
            leaf.color = (0.8, 0.6, 0.2, 1.0)
    return root


def child_meshes(root):
    return [obj for obj in descendants(root) if obj.type == "MESH"]


def find_door_leaf(pivot, suffix):
    return next((obj for obj in pivot.children if obj.type == "MESH" and obj.name.endswith(suffix)), None)


def style_door_panel(leaf, source_leaf):
    leaf.data.materials.clear()
    for material in source_leaf.data.materials:
        leaf.data.materials.append(material)
    leaf.display_type = "TEXTURED"
    leaf.hide_render = False
    leaf.hide_set(False)
    leaf.hide_viewport = False
    leaf["finished_door_panel"] = True


def add_door_appearance(target_root, source_root):
    """Copy one finished door panel and handle onto a generated door proxy.

    Traffic Editor provides the door transform and size. The existing ward door
    supplies the Blender material and handle mesh. Panel width/height and handle
    placement are adjusted to the target proxy while preserving the source
    thickness and handle geometry.
    """
    source_pivot = next((obj for obj in source_root.children if obj.get("rotation_center")), None)
    target_pivot = next((obj for obj in target_root.children if obj.get("rotation_center")), None)
    if source_pivot is None or target_pivot is None:
        raise RuntimeError(f"Door pivot missing for {target_root.name}")

    source_leaf = find_door_leaf(source_pivot, "__proxy")
    target_leaf = find_door_leaf(target_pivot, "__proxy")
    source_panel = next(
        (
            obj for obj in source_pivot.children
            if obj.type == "MESH" and obj is not source_leaf and not obj.name.endswith("__proxy")
        ),
        None,
    )
    if source_leaf is None or target_leaf is None or source_panel is None:
        raise RuntimeError(f"Door panel prototype incomplete for {target_root.name}")

    relative_panel = source_leaf.matrix_world.inverted_safe() @ source_panel.matrix_world
    panel = source_panel.copy()
    panel.data = source_panel.data.copy()
    get_collection("Doors_Proxy").objects.link(panel)
    panel.name = target_root.name + "_frame"
    panel["door_visual_for"] = target_root.name
    panel.parent = target_pivot
    panel.matrix_world = target_leaf.matrix_world @ relative_panel

    source_panel_dims = source_panel.dimensions.copy()
    source_leaf_dims = source_leaf.dimensions.copy()
    panel.dimensions = (
        target_leaf.dimensions.x * source_panel_dims.x / source_leaf_dims.x,
        source_panel_dims.y,
        target_leaf.dimensions.z * source_panel_dims.z / source_leaf_dims.z,
    )

    source_handle = next(
        (obj for obj in source_pivot.children if obj.get("door_handle_visual")),
        None,
    )
    if source_handle is None:
        source_handle = next(
            (
                obj for obj in bpy.data.objects
                if obj.parent is source_pivot and "Door_handle" in obj.name
            ),
            None,
        )
    if source_handle is None:
        raise RuntimeError(f"Door handle prototype missing for {target_root.name}")

    for index, source_mesh in enumerate(child_meshes(source_handle), 1):
        relative_handle = source_leaf.matrix_world.inverted_safe() @ source_mesh.matrix_world
        copied = source_mesh.copy()
        copied.data = source_mesh.data.copy()
        for collection in source_mesh.users_collection:
            collection.objects.link(copied)
        copied.name = f"{target_root.name}_handle_{index}"
        copied["door_visual_for"] = target_root.name
        copied["door_handle_visual"] = True
        copied.parent = target_pivot
        copied.matrix_world = target_leaf.matrix_world @ relative_handle

    # The generated inner leaf and the slightly larger frame form the same
    # two-layer door construction used by the existing finished room doors.
    style_door_panel(target_leaf, source_leaf)


def doors_missing_appearance(door_roots):
    result = []
    for name, root in door_roots.items():
        # The main entrance is a double entrance with its own design; do not turn
        # it into two copies of the single interior-door prototype.
        if name == "main_entrance":
            continue
        pivots = [obj for obj in root.children if obj.get("rotation_center")]
        for pivot in pivots:
            panel = next(
                (
                    obj for obj in pivot.children
                    if obj.type == "MESH" and not obj.name.endswith("__proxy")
                ),
                None,
            )
            if panel is None:
                result.append(name)
                break
    return sorted(set(result))


def door_panels_missing_style(door_roots):
    result = []
    for name, root in door_roots.items():
        if name == "main_entrance":
            continue
        for pivot in (obj for obj in root.children if obj.get("rotation_center")):
            leaf = find_door_leaf(pivot, "__proxy")
            finished_frame = next(
                (
                    obj for obj in pivot.children
                    if obj.type == "MESH" and obj.get("door_visual_for") == name
                ),
                None,
            )
            if finished_frame is None or leaf is None:
                continue
            if (
                leaf.hide_render
                or leaf.hide_viewport
                or leaf.display_type != "TEXTURED"
                or not leaf.data.materials
            ):
                result.append(name)
                break
    return sorted(set(result))


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    importer = load_importer()
    resolver, building, furniture, doors, robots = importer.collect_scene(args.world.resolve(), args.model_root.resolve())
    items = {item["name"]: item for item in furniture + robots}
    world_names = set(items)
    proxies = {
        obj.name: obj
        for collection in ("Furniture_Proxy", "Robots_Proxy")
        for obj in collection_roots(collection)
    }
    relations = replacement_map()
    stale = sorted(set(proxies) - world_names)
    missing = sorted(world_names - set(proxies))
    missing_nurse_appearances = nurse_tables_missing_appearance(items, proxies, relations)

    moved = []
    for name in sorted(world_names & set(proxies)):
        old = proxies[name].matrix_world.copy()
        new = bmatrix(items[name]["pose"])
        position_delta = (old.translation - new.translation).length
        rotation_delta = old.to_quaternion().rotation_difference(new.to_quaternion()).angle
        if position_delta > 0.001 or rotation_delta > 0.001:
            moved.append(name)

    door_items = {item["name"]: item for item in doors}
    door_roots = {obj.name: obj for obj in collection_roots("Doors_Proxy")}
    stale_doors = sorted(set(door_roots) - set(door_items))
    missing_doors = sorted(set(door_items) - set(door_roots))
    appearance_targets = doors_missing_appearance(door_roots)
    panel_style_targets = door_panels_missing_style(door_roots)

    report = {
        "world": str(args.world.resolve()),
        "blend": bpy.data.filepath,
        "move_instances": moved,
        "add_instances": missing,
        "remove_instances": stale,
        "add_nurse_table_appearances": missing_nurse_appearances,
        "add_doors": missing_doors,
        "remove_doors": stale_doors,
        "add_door_appearances": appearance_targets,
        "style_door_panels": panel_style_targets,
        "replace_building_walls": True,
        "apply": args.apply,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.apply:
        return

    old_wall_count, new_wall_count = sync_building(resolver, building)

    # Preserve each beautified model's local adjustment relative to its source
    # proxy, then place both at the current Gazebo transform.
    for name in sorted(world_names & set(proxies)):
        proxy = proxies[name]
        old = proxy.matrix_world.copy()
        offsets = [(replacement, old.inverted_safe() @ replacement.matrix_world.copy()) for replacement in relations.get(name, [])]
        proxy.matrix_world = bmatrix(items[name]["pose"])
        proxy["sdf_pose"] = list(items[name]["pose"])
        for replacement, offset in offsets:
            replacement.matrix_world = proxy.matrix_world @ offset

    # Add new instances by cloning an existing instance with the same SDF URI.
    material_cache = {}
    for name in missing:
        item = items[name]
        target_collection = "Robots_Proxy" if item in robots else "Furniture_Proxy"
        prototype = next(
            (
                root for root in proxies.values()
                if root.get("sdf_uri") == item["uri"]
            ),
            None,
        )
        if prototype is not None:
            proxy = clone_tree(prototype, name, get_collection(target_collection))
            proxy.matrix_world = bmatrix(item["pose"])
            proxy["sdf_uri"] = item["uri"]
            proxy["sdf_pose"] = list(item["pose"])
            rename_proxy_child(proxy)
        else:
            proxy = make_box_proxy(item, target_collection, visible=True)
        proxies[name] = proxy

        if "PotatoChipChair" in name:
            prototype_source = "OpenRobotics/PotatoChipChair_8"
            prototype_proxy = proxies.get(prototype_source)
            prototype_replacements = relations.get(prototype_source, [])
            if prototype_proxy and prototype_replacements:
                source_replacement = prototype_replacements[0]
                offset = prototype_proxy.matrix_world.inverted_safe() @ source_replacement.matrix_world.copy()
                replacement = clone_tree(
                    source_replacement,
                    "PotatoChipChair_Triple_Root" + name.removeprefix("OpenRobotics/PotatoChipChair"),
                    source_replacement.users_collection[0],
                )
                replacement.matrix_world = proxy.matrix_world @ offset
                replacement["source_object"] = name
                set_hidden_tree(proxy, True)
        elif "hospital_elevator" in name:
            make_elevator(item, proxy, material_cache)

    for name in missing_nurse_appearances:
        add_nurse_table_appearance(name, proxies[name], proxies, relations)

    # Remove source proxies absent from the current world and all beautified
    # replacements that explicitly map to those proxies.
    removed_replacements = set()
    for name in stale:
        for replacement in relations.get(name, []):
            if replacement.name in bpy.data.objects and replacement not in removed_replacements:
                removed_replacements.add(replacement)
                remove_tree(replacement)
        if name in bpy.data.objects:
            remove_tree(bpy.data.objects[name])

    # Door proxy roots are generated directly from the inline SDF door models.
    for name in sorted(set(door_items) & set(door_roots)):
        door_roots[name].matrix_world = bmatrix(door_items[name]["pose"])
        door_roots[name]["sdf_pose"] = list(door_items[name]["pose"])
    for name in stale_doors:
        if name in bpy.data.objects:
            remove_tree(bpy.data.objects[name])
    for name in missing_doors:
        door_roots[name] = make_door(door_items[name])

    # Copy the finished interior-door panel and handle to new Traffic Editor
    # doors. Existing hand-finished doors are preserved.
    prototype_door = door_roots.get("ward_b_door")
    if appearance_targets and prototype_door is None:
        raise RuntimeError("Cannot find ward_b_door appearance prototype")
    for name in appearance_targets:
        add_door_appearance(door_roots[name], prototype_door)

    prototype_pivot = next(obj for obj in prototype_door.children if obj.get("rotation_center"))
    prototype_leaf = find_door_leaf(prototype_pivot, "__proxy")
    for name in panel_style_targets:
        target_pivot = next(obj for obj in door_roots[name].children if obj.get("rotation_center"))
        style_door_panel(find_door_leaf(target_pivot, "__proxy"), prototype_leaf)

    bpy.context.scene["gazebo_sync_world"] = str(args.world.resolve())
    bpy.context.scene["gazebo_sync_counts"] = json.dumps({
        "moved": len(moved),
        "added": len(missing),
        "removed": len(stale),
        "nurse_table_appearances_added": len(missing_nurse_appearances),
        "doors_added": len(missing_doors),
        "doors_removed": len(stale_doors),
        "door_appearances_added": len(appearance_targets),
        "door_panels_styled": len(panel_style_targets),
        "walls_removed": old_wall_count,
        "walls_added": new_wall_count,
    })
    output = (args.output or Path(bpy.data.filepath)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    print(f"Saved synchronized Blender scene: {output}")


if __name__ == "__main__":
    main()
