import math
import re

import bpy
from mathutils import Matrix


COLLECTION_NAME = "IVStand"
ROOT_PREFIX = "IVStand_Replacement_"

# 參考圖是沒有點滴袋的金屬架；需要點滴袋時改成 True。
ADD_FLUID_BAGS = False

# 如果全部方向需要修正，可填入 90、-90 或 180。
ROTATION_OFFSET_DEG = 0.0
MODEL_SCALE = 1.0


def material(name, color, roughness=0.5, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, alpha)

    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, alpha)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Alpha"].default_value = alpha

    if alpha < 1.0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
        elif hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"

    return mat


def find_originals():
    """辨識 IVStand、IVStand2、IVStand_2 等 Gazebo 根物件。"""
    pattern = re.compile(r"^ivstand(?:_?\d+)?$", re.IGNORECASE)
    originals = []

    for obj in bpy.data.objects:
        short_name = obj.name.split("/")[-1]
        lowered = short_name.casefold()

        if "replacement" in lowered or "__proxy" in lowered:
            continue

        if pattern.fullmatch(short_name):
            originals.append(obj)

    originals.sort(key=lambda item: item.name.casefold())
    return originals


def clean_collection():
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    if obj.name not in collection.objects:
        collection.objects.link(obj)

    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def bevel(obj, width=0.01, segments=3):
    modifier = obj.modifiers.new("Soft_Metal_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def cube(
    name,
    location,
    dimensions,
    mat,
    collection,
    bevel_width=0.01,
    rotation=(0.0, 0.0, 0.0),
):
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


def cylinder(
    name,
    radius,
    depth,
    location,
    mat,
    collection,
    vertices=32,
    rotation=(0.0, 0.0, 0.0),
):
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
    bevel(obj, min(radius * 0.18, 0.009), 3)
    return obj


def tube_curve(name, points, radius, mat, collection):
    """以曲線建立細金屬管，用於 J 形掛鉤及點滴軟管。"""
    curve_data = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 3
    curve_data.resolution_u = 3

    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)

    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"

    obj = bpy.data.objects.new(name, curve_data)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def hide_tree(obj):
    obj.hide_set(True)
    obj.hide_viewport = True
    obj.hide_render = True

    for child in obj.children:
        hide_tree(child)


def build_one(index, original, collection, mats):
    silver, dark_metal, black, accent, bag_mat, fluid_mat = mats
    suffix = f"{index:02d}"
    parts = []

    # 五爪星形底座與腳輪
    parts.append(cylinder(
        f"IVStand_{suffix}_BaseHub",
        0.105,
        0.095,
        (0, 0, 0.115),
        dark_metal,
        collection,
    ))

    for leg_index in range(5):
        angle = math.radians(leg_index * 72)
        direction_x = math.cos(angle)
        direction_y = math.sin(angle)

        parts.append(cube(
            f"IVStand_{suffix}_BaseLeg_{leg_index + 1}",
            (0.18 * direction_x, 0.18 * direction_y, 0.082),
            (0.39, 0.060, 0.052),
            dark_metal,
            collection,
            0.018,
            rotation=(0, 0, angle),
        ))

        wheel_x = 0.37 * direction_x
        wheel_y = 0.37 * direction_y

        parts.append(cube(
            f"IVStand_{suffix}_CasterFork_{leg_index + 1}",
            (wheel_x, wheel_y, 0.060),
            (0.045, 0.045, 0.075),
            dark_metal,
            collection,
            0.008,
        ))
        parts.append(cylinder(
            f"IVStand_{suffix}_Caster_{leg_index + 1}",
            0.043,
            0.032,
            (wheel_x, wheel_y, 0.030),
            black,
            collection,
            vertices=24,
            rotation=(math.radians(90), 0, angle),
        ))

    # 雙層伸縮金屬桿
    parts.append(cylinder(
        f"IVStand_{suffix}_OuterColumn",
        0.033,
        1.03,
        (0, 0, 0.67),
        dark_metal,
        collection,
    ))
    parts.append(cylinder(
        f"IVStand_{suffix}_InnerColumn",
        0.021,
        0.72,
        (0, 0, 1.46),
        silver,
        collection,
    ))
    parts.append(cylinder(
        f"IVStand_{suffix}_AdjustmentCollar",
        0.045,
        0.085,
        (0, 0, 1.13),
        dark_metal,
        collection,
    ))

    # 小型高度調節旋鈕，作為暖色細節但不搶畫面
    parts.append(cylinder(
        f"IVStand_{suffix}_AdjustmentKnob",
        0.024,
        0.050,
        (0.052, 0, 1.13),
        accent,
        collection,
        vertices=24,
        rotation=(0, math.radians(90), 0),
    ))

    # 頂部四個真正彎曲的 J 形金屬掛鉤
    hook_top_z = 1.84
    parts.append(cylinder(
        f"IVStand_{suffix}_TopCap",
        0.029,
        0.045,
        (0, 0, 1.815),
        dark_metal,
        collection,
    ))

    for hook_index, angle_deg in enumerate((45, 135, 225, 315), 1):
        angle = math.radians(angle_deg)
        dx = math.cos(angle)
        dy = math.sin(angle)

        points = [
            (0.00, 0.00, hook_top_z),
            (0.075 * dx, 0.075 * dy, hook_top_z),
            (0.145 * dx, 0.145 * dy, hook_top_z),
            (0.155 * dx, 0.155 * dy, hook_top_z - 0.055),
            (0.145 * dx, 0.145 * dy, hook_top_z - 0.115),
            (0.105 * dx, 0.105 * dy, hook_top_z - 0.125),
            (0.085 * dx, 0.085 * dy, hook_top_z - 0.095),
        ]

        parts.append(tube_curve(
            f"IVStand_{suffix}_JHook_{hook_index}",
            points,
            0.008,
            silver,
            collection,
        ))

    # 可選點滴袋；預設關閉以符合參考圖。
    if ADD_FLUID_BAGS:
        for bag_index, x in enumerate((-0.085, 0.085), 1):
            parts.append(cube(
                f"IVStand_{suffix}_FluidBag_{bag_index}",
                (x, -0.015, 1.62),
                (0.105, 0.040, 0.20),
                bag_mat,
                collection,
                0.025,
            ))
            parts.append(tube_curve(
                f"IVStand_{suffix}_InfusionTube_{bag_index}",
                [
                    (x, -0.015, 1.51),
                    (x + 0.015, -0.020, 1.35),
                    (x - 0.010, -0.025, 1.18),
                ],
                0.004,
                fluid_mat,
                collection,
            ))

    root = bpy.data.objects.new(f"{ROOT_PREFIX}{suffix}", None)
    root["source_object"] = original.name
    root["width_m"] = 0.80
    root["depth_m"] = 0.80
    root["height_m"] = 1.86
    root["model"] = "IVStand"
    root["description"] = "dark brushed-metal mobile IV stand with curved hooks"
    collection.objects.link(root)
    parent_parts(root, parts)

    location, rotation, _scale = original.matrix_world.decompose()
    rotation_offset = Matrix.Rotation(
        math.radians(ROTATION_OFFSET_DEG),
        4,
        "Z",
    )
    root.matrix_world = (
        Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ rotation_offset
        @ Matrix.Scale(MODEL_SCALE, 4)
    )

    hide_tree(original)
    return root


def build():
    originals = find_originals()

    if not originals:
        print("找不到 IVStand 原始物件。")
        print("請確認 Outliner 名稱是否為 IVStand、IVStand2 或 IVStand_2。")
        return

    collection = clean_collection()

    # 主體使用深銀灰金屬，和深灰椅子仍有明暗區別。
    silver = material("MAT_IVStand_BrushedSilver", (0.43, 0.47, 0.48), 0.24, 0.80)
    dark_metal = material("MAT_IVStand_GraphiteMetal", (0.12, 0.14, 0.145), 0.31, 0.68)
    black = material("MAT_IVStand_CasterRubber", (0.018, 0.022, 0.024), 0.72, 0.0)
    accent = material("MAT_IVStand_WarmAdjustment", (0.38, 0.12, 0.035), 0.48, 0.12)
    bag_mat = material("MAT_IVStand_FluidBag", (0.64, 0.80, 0.83), 0.24, 0.0, 0.52)
    fluid_mat = material("MAT_IVStand_ClearTube", (0.68, 0.74, 0.72), 0.38, 0.0, 0.72)
    mats = (silver, dark_metal, black, accent, bag_mat, fluid_mat)

    replacements = []
    for index, original in enumerate(originals, 1):
        replacements.append(build_one(index, original, collection, mats))

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    replacements[0].select_set(True)
    bpy.context.view_layer.objects.active = replacements[0]

    print(f"完成：已建立並替換 {len(replacements)} 個金屬 IVStand")
    for replacement in replacements:
        print(" -", replacement.name, "來源：", replacement["source_object"])


if __name__ == "__main__":
    build()
