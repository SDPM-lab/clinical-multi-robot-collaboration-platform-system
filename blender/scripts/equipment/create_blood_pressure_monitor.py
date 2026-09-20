import math
import re

import bpy
from mathutils import Matrix


COLLECTION = "BloodPressureMonitor_Replacement"
ROOT_PREFIX = "BloodPressureMonitor_Replacement_"
ROTATION_OFFSET_DEG = 0.0
MODEL_SCALE = 1.0


def material(name, color, roughness=0.5, metallic=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission, 1.0)
        shader.inputs["Emission Strength"].default_value = 0.25
    mat.diffuse_color = (*color, 1.0)
    return mat


def find_originals():
    pattern = re.compile(r"^blood[_]?pressure[_]?monitor(?:[_]?\d+)?$", re.IGNORECASE)
    result = []
    for obj in bpy.data.objects:
        short_name = obj.name.split("/")[-1]
        lowered = short_name.casefold()
        if "replacement" in lowered or "__proxy" in lowered:
            continue
        if pattern.fullmatch(short_name):
            result.append(obj)
    result.sort(key=lambda obj: obj.name.casefold())
    return result


def clean_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    if collection not in obj.users_collection:
        collection.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def bevel(obj, width=0.01, segments=4):
    modifier = obj.modifiers.new("Soft_Rounded_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def cube(name, location, dimensions, mat, collection, bevel_width=0.01, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to(obj, collection)
    if bevel_width:
        bevel(obj, bevel_width)
    return obj


def cylinder(name, radius, depth, location, mat, collection, rotation=(0, 0, 0), vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.18, 0.012), 3)
    return obj


def tube_curve(name, points, radius, mat, collection):
    data = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 12
    data.bevel_depth = radius
    data.bevel_resolution = 4
    data.use_fill_caps = True
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = matrix


def hide_tree(root):
    root.hide_set(True)
    root.hide_viewport = True
    root.hide_render = True
    for child in root.children_recursive:
        child.hide_set(True)
        child.hide_viewport = True
        child.hide_render = True


def build_one(index, original, collection, mats):
    silver, dark_silver, black, screen_mat, blue, cuff_mat, hose_mat, accent = mats
    suffix = f"{index:02d}"
    parts = []

    # 五腳移動底座。
    parts.append(cylinder(f"BPM_BaseHub_{suffix}", 0.115, 0.10, (0, 0, 0.105), dark_silver, collection))
    for leg_index in range(5):
        angle = math.radians(leg_index * 72)
        dx, dy = math.cos(angle), math.sin(angle)
        parts.append(cube(
            f"BPM_BaseLeg_{leg_index + 1}_{suffix}",
            (0.19 * dx, 0.19 * dy, 0.075),
            (0.42, 0.065, 0.055),
            dark_silver,
            collection,
            0.018,
            rotation=(0, 0, angle),
        ))
        wx, wy = 0.39 * dx, 0.39 * dy
        parts.append(cube(f"BPM_CasterFork_{leg_index + 1}_{suffix}", (wx, wy, 0.06), (0.05, 0.05, 0.075), dark_silver, collection, 0.008))
        parts.append(cylinder(
            f"BPM_Caster_{leg_index + 1}_{suffix}",
            0.045,
            0.035,
            (wx, wy, 0.028),
            black,
            collection,
            rotation=(math.radians(90), 0, angle),
            vertices=24,
        ))

    # 立式伸縮金屬柱。
    parts.append(cylinder(f"BPM_OuterColumn_{suffix}", 0.036, 1.02, (0, 0, 0.66), dark_silver, collection))
    parts.append(cylinder(f"BPM_InnerColumn_{suffix}", 0.024, 0.68, (0, 0, 1.43), silver, collection))
    parts.append(cylinder(f"BPM_AdjustmentCollar_{suffix}", 0.050, 0.075, (0, 0, 1.12), dark_silver, collection))

    # 監測器外殼、螢幕與控制按鈕。
    parts.append(cube(f"BPM_MonitorBody_{suffix}", (0, 0, 1.78), (0.54, 0.23, 0.52), silver, collection, 0.055))
    parts.append(cube(f"BPM_MonitorFrame_{suffix}", (0, -0.122, 1.80), (0.44, 0.018, 0.34), dark_silver, collection, 0.018))
    parts.append(cube(f"BPM_Display_{suffix}", (0, -0.135, 1.80), (0.385, 0.010, 0.275), screen_mat, collection, 0.010))
    parts.append(cube(f"BPM_DisplayAccent_{suffix}", (0, -0.143, 1.925), (0.28, 0.008, 0.012), blue, collection, 0.004))
    for button_index, x in enumerate((-0.17, -0.055, 0.055, 0.17), start=1):
        parts.append(cylinder(f"BPM_Button_{button_index}_{suffix}", 0.018, 0.012, (x, -0.145, 1.55), accent if button_index == 4 else dark_silver, collection, rotation=(math.radians(90), 0, 0), vertices=24))

    # 下方托盤，用來放袖帶或小物件。
    parts.append(cube(f"BPM_Tray_{suffix}", (0, 0.16, 1.24), (0.50, 0.34, 0.065), silver, collection, 0.025))
    parts.append(cube(f"BPM_TrayLip_{suffix}", (0, -0.015, 1.285), (0.42, 0.025, 0.035), dark_silver, collection, 0.008))

    # 袖帶收在側邊，軟管以彎曲曲線連接到主機。
    parts.append(cube(f"BPM_Cuff_{suffix}", (0.28, 0.03, 1.43), (0.20, 0.13, 0.075), cuff_mat, collection, 0.028))
    parts.append(tube_curve(
        f"BPM_CuffHose_{suffix}",
        [(0.20, 0.01, 1.52), (0.37, -0.02, 1.35), (0.36, -0.08, 1.11), (0.25, -0.10, 0.98)],
        0.009,
        hose_mat,
        collection,
    ))
    parts.append(cylinder(f"BPM_HoseConnector_{suffix}", 0.015, 0.05, (0.19, 0, 1.52), hose_mat, collection, rotation=(0, math.radians(90), 0), vertices=20))

    root = bpy.data.objects.new(f"{ROOT_PREFIX}{suffix}", None)
    root["source_object"] = original.name
    root["width_m"] = 0.82
    root["depth_m"] = 0.72
    root["height_m"] = 2.08
    root["model"] = "BloodPressureMonitor"
    root["description"] = "silver-gray mobile blood pressure monitoring station"
    collection.objects.link(root)
    parent_parts(root, parts)

    location, rotation, _scale = original.matrix_world.decompose()
    root.matrix_world = (
        Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Rotation(math.radians(ROTATION_OFFSET_DEG), 4, "Z")
        @ Matrix.Scale(MODEL_SCALE, 4)
    )
    hide_tree(original)
    return root


def build():
    originals = find_originals()
    if not originals:
        raise RuntimeError("找不到原始 BloodPressureMonitor；請確認名稱或原始模型仍存在。")

    collection = clean_collection()
    silver = material("MAT_BPM_SilverMetal", (0.48, 0.54, 0.56), 0.26, 0.78)
    dark_silver = material("MAT_BPM_DarkSilver", (0.17, 0.21, 0.22), 0.31, 0.68)
    black = material("MAT_BPM_WheelRubber", (0.025, 0.030, 0.032), 0.65)
    screen = material("MAT_BPM_Screen", (0.035, 0.12, 0.14), 0.24, 0.05, emission=(0.02, 0.16, 0.17))
    blue = material("MAT_BPM_ScreenAccent", (0.15, 0.48, 0.56), 0.32, 0.12)
    cuff = material("MAT_BPM_Cuff", (0.12, 0.22, 0.28), 0.68)
    hose = material("MAT_BPM_Hose", (0.055, 0.065, 0.065), 0.72)
    accent = material("MAT_BPM_Accent", (0.70, 0.28, 0.10), 0.40, 0.15)
    mats = (silver, dark_silver, black, screen, blue, cuff, hose, accent)

    roots = [build_one(i, original, collection, mats) for i, original in enumerate(originals, 1)]
    bpy.ops.object.select_all(action="DESELECT")
    roots[0].select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    print(f"完成：建立 {len(roots)} 個立式血壓監測站替代模型")
    for root in roots:
        print(f"  {root['source_object']} -> {root.name}")


if __name__ == "__main__":
    build()
