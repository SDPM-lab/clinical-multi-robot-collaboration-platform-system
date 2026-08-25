#!/usr/bin/env python3
"""Build a lightweight Blender replacement scene from hospital.world.

Imported geometry policy:
  * hospital_L1: visual meshes only, imported at their full Gazebo transforms.
  * furniture/medical equipment: one named Empty plus a box proxy.
  * doors: one named Empty plus per-joint pivot Empties and exact visual boxes.
  * simple_robot_real: three independent named Empty plus box proxies.
  * collision elements are never traversed or imported.

No network requests are made. Proxy bounds may be measured from an existing
local Gazebo model/cache mesh, but those detailed meshes and their textures are
never loaded into Blender or copied.

Run with Blender:
  blender --background --python tools/blender_import_hospital_proxy.py

Run a read-only parse check without Blender:
  python3 tools/blender_import_hospital_proxy.py --audit
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys
import urllib.parse
import xml.etree.ElementTree as ET


SCRIPT = Path(__file__).resolve()

def _project_root():
    for path in SCRIPT.parents:
        if (path / "ros2_ws" / "src" / "my_hospital_rmf").exists():
            return path
    raise RuntimeError("Cannot find project root from script location")

PROJECT = _project_root()
DEFAULT_WORLD = PROJECT / "ros2_ws/src/my_hospital_rmf/maps/hospital.world"
DEFAULT_MODELS = PROJECT / "ros2_ws/src/my_hospital_rmf/models"
DEFAULT_OUTPUT = PROJECT / "hospital_raw.blend"
DEFAULT_PREVIEW = PROJECT / "hospital_raw_preview.png"


def values(text, count, default):
    if not text or not text.strip():
        return tuple(default)
    parsed = tuple(float(item) for item in text.split())
    return (parsed + tuple(default[len(parsed):]))[:count]


def pose(element):
    return values(element.findtext("pose"), 6, (0, 0, 0, 0, 0, 0))


def scale_matrix_xyz(x, y, z):
    return ((x, 0, 0, 0), (0, y, 0, 0), (0, 0, z, 0), (0, 0, 0, 1))


def pose_matrix_raw(p):
    x, y, z, roll, pitch, yaw = p
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    # SDFormat fixed-axis RPY: Rz(yaw) * Ry(pitch) * Rx(roll).
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr, x),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr, y),
        (-sp, cp * sr, cp * cr, z),
        (0, 0, 0, 1),
    )


def matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)) for i in range(4))


def transform(matrix, point):
    x, y, z = point
    return tuple(sum(matrix[i][k] * (x, y, z, 1)[k] for k in range(4)) for i in range(3))


def corners(bounds):
    low, high = bounds
    return [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]


def transformed_bounds(bounds, matrix):
    points = [transform(matrix, point) for point in corners(bounds)]
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def union_bounds(all_bounds):
    all_bounds = list(all_bounds)
    if not all_bounds:
        return None
    return (
        tuple(min(bound[0][i] for bound in all_bounds) for i in range(3)),
        tuple(max(bound[1][i] for bound in all_bounds) for i in range(3)),
    )


class LocalResolver:
    """Resolve project models and existing Gazebo caches; never download."""

    def __init__(self, model_root):
        self.model_root = Path(model_root).resolve()
        self.cache_roots = [Path.home() / ".gz/fuel", Path.home() / ".ignition/fuel"]

    def model_sdf(self, uri):
        name = uri.removeprefix("model://").strip("/").split("/", 1)[0]
        path = self.model_root / name / "model.sdf"
        if not path.exists():
            raise FileNotFoundError(f"Missing local model SDF: {path}")
        return path.resolve()

    def asset(self, uri, source_dir):
        uri = (uri or "").strip()
        if uri.startswith("model://"):
            path = self.model_root / urllib.parse.unquote(uri.removeprefix("model://"))
            return path.resolve() if path.exists() else None
        if uri.startswith("file://"):
            path = Path(urllib.parse.unquote(urllib.parse.urlparse(uri).path))
            if path.exists():
                return path.resolve()
            parts = list(path.parts)
            if "models" in parts:
                index = len(parts) - 1 - parts[::-1].index("models")
                fallback = self.model_root / Path(*parts[index + 1:])
                return fallback.resolve() if fallback.exists() else None
            return None
        if uri.startswith(("http://", "https://")):
            parsed = urllib.parse.urlparse(uri)
            parts = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
            # /1.0/<owner>/models/<name>/<version>/files/<relative path>
            try:
                model_index = parts.index("models")
                owner = parts[model_index - 1]
                name = parts[model_index + 1]
                version = parts[model_index + 2]
                files_index = parts.index("files", model_index + 3)
                relative = Path(*parts[files_index + 1:])
            except (ValueError, IndexError):
                return None
            host = parsed.netloc
            for root in self.cache_roots:
                candidate = root / host / owner / "models" / name / version / relative
                if candidate.exists():
                    return candidate.resolve()
            return None
        path = Path(source_dir) / urllib.parse.unquote(uri)
        return path.resolve() if path.exists() else None


def model_element(path):
    root = ET.parse(path).getroot()
    model = root if root.tag == "model" else root.find("model")
    if model is None:
        raise ValueError(f"No model in {path}")
    return model


def world_element(path):
    root = ET.parse(path).getroot()
    world = root if root.tag == "world" else root.find("world")
    if world is None:
        raise ValueError(f"No world in {path}")
    return world


def obj_bounds(path):
    points = []
    with Path(path).open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            if line.startswith("v "):
                fields = line.split()
                if len(fields) >= 4:
                    points.append(tuple(float(value) for value in fields[1:4]))
    return point_bounds(points)


def stl_bounds(path):
    path = Path(path)
    data = path.read_bytes()
    points = []
    if len(data) >= 84:
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        if 84 + triangle_count * 50 == len(data):
            for index in range(triangle_count):
                offset = 84 + index * 50 + 12
                for vertex in range(3):
                    points.append(struct.unpack_from("<fff", data, offset + vertex * 12))
            return point_bounds(points)
    for line in data.decode("utf-8", errors="ignore").splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0].lower() == "vertex":
            points.append(tuple(float(value) for value in fields[1:4]))
    return point_bounds(points)


def point_bounds(points):
    points = list(points)
    if not points:
        return None
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def mesh_bounds(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".obj":
        return obj_bounds(path)
    if suffix == ".stl":
        return stl_bounds(path)
    return None


def visual_local_bounds(model, source_path, resolver):
    results = []
    measured_meshes = 0
    unresolved_meshes = 0
    for link in model.findall("link"):
        link_matrix = pose_matrix_raw(pose(link))
        for visual in link.findall("visual"):  # Deliberately never visits <collision>.
            geometry = visual.find("geometry")
            if geometry is None or not list(geometry):
                continue
            shape = list(geometry)[0]
            shape_matrix = matmul(link_matrix, pose_matrix_raw(pose(visual)))
            bounds = None
            if shape.tag == "box":
                size = values(shape.findtext("size"), 3, (1, 1, 1))
                bounds = tuple(-item / 2 for item in size), tuple(item / 2 for item in size)
            elif shape.tag == "cylinder":
                radius = float(shape.findtext("radius", "0.5"))
                length = float(shape.findtext("length", "1"))
                bounds = (-radius, -radius, -length / 2), (radius, radius, length / 2)
            elif shape.tag == "sphere":
                radius = float(shape.findtext("radius", "0.5"))
                bounds = (-radius, -radius, -radius), (radius, radius, radius)
            elif shape.tag == "mesh":
                asset = resolver.asset(shape.findtext("uri", ""), source_path.parent)
                bounds = mesh_bounds(asset) if asset else None
                if bounds:
                    mesh_scale = values(shape.findtext("scale"), 3, (1, 1, 1))
                    shape_matrix = matmul(shape_matrix, scale_matrix_xyz(*mesh_scale))
                    measured_meshes += 1
                else:
                    unresolved_meshes += 1
            if bounds:
                results.append(transformed_bounds(bounds, shape_matrix))
    return union_bounds(results), measured_meshes, unresolved_meshes


def fallback_size(name):
    key = name.lower()
    rules = (
        (("robot",), (0.55, 0.42, 0.32)),
        (("standing", "nurse", "visitor"), (0.55, 0.55, 1.75)),
        (("extinguisher",), (0.25, 0.25, 0.65)),
        (("trolleybed",), (2.1, 0.9, 1.15)),
        (("sofa",), (1.8, 0.85, 0.85)),
        (("table", "desk", "station", "reception"), (1.4, 0.8, 0.9)),
        (("chair",), (0.65, 0.65, 1.0)),
        (("wardrobe", "cabinet", "rack", "bookshelf", "fridge"), (1.0, 0.65, 1.8)),
        (("toilet", "sink"), (0.75, 0.65, 0.85)),
        (("monitor",), (0.7, 0.35, 0.55)),
        (("ivstand",), (0.6, 0.6, 1.8)),
        (("trash", "bin"), (0.45, 0.45, 0.75)),
        (("xray", "cgm", "pressure"), (0.9, 0.8, 1.5)),
    )
    for words, size in rules:
        if any(word in key for word in words):
            return size
    return (0.8, 0.8, 1.0)


def proxy_spec(name, model, source_path, resolver):
    bounds, measured, unresolved = visual_local_bounds(model, source_path, resolver)
    if bounds:
        low, high = bounds
        size = tuple(max(high[i] - low[i], 0.05) for i in range(3))
        center = tuple((high[i] + low[i]) / 2 for i in range(3))
        source = "visual_bounds"
    else:
        # Use the SDF model name, avoiding instance prefixes such as
        # "OpenRobotics/" accidentally matching the word "robot".
        size = fallback_size(model.get("name", name))
        center = (0, 0, size[2] / 2)
        source = "fallback"
    return {"size": size, "center": center, "source": source, "measured_meshes": measured, "unresolved_meshes": unresolved}


def collect_scene(world_path, model_root):
    resolver = LocalResolver(model_root)
    world = world_element(world_path)
    building = None
    furniture = []
    robots = []
    for include in world.findall("include"):
        uri = include.findtext("uri", "").strip()
        name = include.findtext("name", uri.removeprefix("model://"))
        if uri == "model://hospital_nav_overlay":
            continue
        source = resolver.model_sdf(uri)
        model = model_element(source)
        item = {"name": name, "uri": uri, "pose": pose(include), "source": source, "model": model}
        if uri == "model://hospital_L1":
            building = item
        elif uri == "model://simple_robot_real":
            item["proxy"] = proxy_spec(name, model, source, resolver)
            robots.append(item)
        else:
            item["proxy"] = proxy_spec(name, model, source, resolver)
            furniture.append(item)
    doors = [{"name": model.get("name", "door"), "pose": pose(model), "model": model} for model in world.findall("model")]
    if building is None:
        raise RuntimeError("hospital_L1 was not found in the world SDF")
    return resolver, building, furniture, doors, robots


def audit(args):
    _, building, furniture, doors, robots = collect_scene(args.world, args.model_root)
    report = {
        "world": str(args.world),
        "building": {"name": building["name"], "uri": building["uri"], "pose": building["pose"], "visuals": len(list(building["model"].iterfind(".//visual")))},
        "collections": {"Building": 1, "Furniture_Proxy": len(furniture), "Doors_Proxy": len(doors), "Robots_Proxy": len(robots)},
        "robots": [{"name": item["name"], "pose": item["pose"], "size": item["proxy"]["size"]} for item in robots],
        "proxy_bounds": {
            "from_local_visuals_or_cache": sum(item["proxy"]["source"] == "visual_bounds" for item in furniture + robots),
            "fallback": sum(item["proxy"]["source"] == "fallback" for item in furniture + robots),
        },
        "network_downloads": 0,
        "collision_imports": 0,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def blender_build(args):
    try:
        import bpy
        from mathutils import Euler, Matrix, Vector
    except ImportError as exc:
        raise SystemExit("Run this mode inside Blender, or use --audit with Python.") from exc

    resolver, building, furniture, doors, robots = collect_scene(args.world, args.model_root)

    def bmatrix(p):
        x, y, z, roll, pitch, yaw = p
        return Matrix.Translation((x, y, z)) @ Euler((roll, pitch, yaw), "XYZ").to_matrix().to_4x4()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene["source_world"] = str(args.world)
    scene["geometry_policy"] = "hospital_L1 visuals + lightweight proxies; collision excluded"

    collections = {}
    for name in ("Building", "Furniture_Proxy", "Doors_Proxy", "Robots_Proxy"):
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        collections[name] = collection

    def move_to(obj, collection):
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)

    def import_mesh(path, collection, base_name):
        before = set(bpy.data.objects)
        suffix = path.suffix.lower()
        if suffix == ".obj":
            if hasattr(bpy.ops.wm, "obj_import"):
                bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
            else:
                bpy.ops.import_scene.obj(filepath=str(path), axis_forward="Y", axis_up="Z")
        elif suffix == ".stl":
            if hasattr(bpy.ops.wm, "stl_import"):
                bpy.ops.wm.stl_import(filepath=str(path))
            else:
                bpy.ops.import_mesh.stl(filepath=str(path))
        elif suffix == ".dae":
            bpy.ops.wm.collada_import(filepath=str(path))
        else:
            raise RuntimeError(f"Unsupported building visual mesh: {path}")
        new = [obj for obj in bpy.data.objects if obj not in before]
        meshes = [obj for obj in new if obj.type == "MESH"]
        for index, obj in enumerate(meshes, 1):
            matrix = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = matrix
            obj.name = base_name if len(meshes) == 1 else f"{base_name}_{index}"
            move_to(obj, collection)
        for obj in new:
            if obj not in meshes:
                bpy.data.objects.remove(obj, do_unlink=True)
        return meshes

    # Full hospital_L1 visual import. No collision nodes are visited.
    building_root = bpy.data.objects.new(building["name"], None)
    building_root.empty_display_type = "PLAIN_AXES"
    building_root.matrix_world = bmatrix(building["pose"])
    building_root["sdf_uri"] = building["uri"]
    collections["Building"].objects.link(building_root)
    for link in building["model"].findall("link"):
        for visual in link.findall("visual"):
            mesh = visual.find("geometry/mesh")
            if mesh is None:
                continue
            path = resolver.asset(mesh.findtext("uri", ""), building["source"].parent)
            if path is None:
                raise RuntimeError(f"Missing hospital_L1 visual: {mesh.findtext('uri')}")
            objects = import_mesh(path, collections["Building"], f"hospital_L1__{link.get('name')}__{visual.get('name')}")
            mesh_scale = values(mesh.findtext("scale"), 3, (1, 1, 1))
            local = bmatrix(pose(link)) @ bmatrix(pose(visual)) @ Matrix.Diagonal((*mesh_scale, 1.0))
            for obj in objects:
                obj.matrix_world = building_root.matrix_world @ local @ obj.matrix_world
                obj["sdf_link"] = link.get("name", "")
                obj["sdf_visual"] = visual.get("name", "")

    def make_proxy(item, collection_name):
        root = bpy.data.objects.new(item["name"], None)
        root.empty_display_type = "CUBE"
        root.empty_display_size = 0.22
        root.matrix_world = bmatrix(item["pose"])
        root["sdf_uri"] = item["uri"]
        root["sdf_pose"] = list(item["pose"])
        root["proxy_size"] = list(item["proxy"]["size"])
        root["bounds_source"] = item["proxy"]["source"]
        collections[collection_name].objects.link(root)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cube = bpy.context.object
        cube.name = item["name"] + "__proxy"
        move_to(cube, collections[collection_name])
        cube.dimensions = item["proxy"]["size"]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        cube.parent = root
        cube.matrix_parent_inverse = Matrix.Identity(4)
        cube.matrix_basis = Matrix.Translation(item["proxy"]["center"])
        cube.display_type = "WIRE"
        cube.color = (0.35, 0.55, 0.8, 1.0) if collection_name == "Furniture_Proxy" else (0.85, 0.35, 0.15, 1.0)
        return root

    for item in furniture:
        make_proxy(item, "Furniture_Proxy")
    for item in robots:
        make_proxy(item, "Robots_Proxy")

    # Each door root stays at the original world model pose. Joint child Empties
    # are the exact rotation centers; leaves are positioned relative to them.
    for item in doors:
        model = item["model"]
        root = bpy.data.objects.new(item["name"], None)
        root.empty_display_type = "ARROWS"
        root.empty_display_size = 0.28
        root.matrix_world = bmatrix(item["pose"])
        root["sdf_pose"] = list(item["pose"])
        collections["Doors_Proxy"].objects.link(root)
        joints_by_child = {joint.findtext("child", ""): joint for joint in model.findall("joint")}
        for link in model.findall("link"):
            joint = joints_by_child.get(link.get("name", ""))
            pivot_local = bmatrix(pose(joint)) if joint is not None else Matrix.Identity(4)
            pivot_name = joint.get("name", "pivot") if joint is not None else link.get("name", "pivot") + "_pivot"
            pivot = bpy.data.objects.new(f"{item['name']}__{pivot_name}", None)
            pivot.empty_display_type = "SINGLE_ARROW"
            pivot.empty_display_size = 0.18
            collections["Doors_Proxy"].objects.link(pivot)
            pivot.parent = root
            pivot.matrix_parent_inverse = Matrix.Identity(4)
            pivot.matrix_basis = pivot_local
            pivot["rotation_center"] = True
            for visual in link.findall("visual"):
                box = visual.find("geometry/box")
                if box is None:
                    continue
                size = values(box.findtext("size"), 3, (1, 0.03, 2.2))
                bpy.ops.mesh.primitive_cube_add(size=1.0)
                leaf = bpy.context.object
                leaf.name = f"{item['name']}__{link.get('name')}__proxy"
                move_to(leaf, collections["Doors_Proxy"])
                leaf.dimensions = size
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                leaf.parent = pivot
                leaf.matrix_parent_inverse = Matrix.Identity(4)
                leaf.matrix_basis = pivot_local.inverted() @ bmatrix(pose(link)) @ bmatrix(pose(visual))
                leaf.display_type = "WIRE"
                leaf.color = (0.8, 0.6, 0.2, 1.0)

    # Strict top-down preview framing based on source model positions.
    all_poses = [item["pose"] for item in furniture + robots + doors]
    xs = [item[0] for item in all_poses]
    ys = [item[1] for item in all_poses]
    center = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0))
    span = max(max(xs) - min(xs), max(ys) - min(ys)) + 5.0
    camera_data = bpy.data.cameras.new("Top_Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span
    camera = bpy.data.objects.new("Top_Camera", camera_data)
    camera.location = (center.x, center.y, max(35.0, span))
    camera.rotation_euler = (0, 0, 0)
    scene.collection.objects.link(camera)
    scene.camera = camera
    sun_data = bpy.data.lights.new("Preview_Sun", "SUN")
    sun_data.energy = 2.0
    sun = bpy.data.objects.new("Preview_Sun", sun_data)
    sun.rotation_euler = (math.radians(25), math.radians(-20), math.radians(-25))
    scene.collection.objects.link(sun)
    scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.08, 0.08, 0.08)

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(DEFAULT_OUTPUT))
    scene.render.filepath = str(DEFAULT_PREVIEW)
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {DEFAULT_OUTPUT}")
    print(f"Preview: {DEFAULT_PREVIEW}")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--audit", action="store_true")
    return parser.parse_args(argv)


def main():
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        try:
            import bpy  # noqa: F401
            argv = []   # inside Blender with no extra args — use defaults
        except ImportError:
            argv = sys.argv[1:]  # plain python3
    args = parse_args(argv)
    for key in ("world", "model_root"):
        setattr(args, key, getattr(args, key).resolve())
    if args.audit:
        audit(args)
    else:
        blender_build(args)


if __name__ == "__main__":
    main()
