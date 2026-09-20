import math
import re

import bpy
from mathutils import Matrix


COLLECTION = "Drawer_Replacement"
ROOT_PREFIX = "Drawer_Replacement_"

# 如果執行後全部方向不對，只改這一行：90.0 或 -90.0
ROTATION_OFFSET_DEG = 0.0
MODEL_SCALE = 1.0


def material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    mat.diffuse_color = (*color, 1.0)
    return mat


def find_originals():
    """尋找 OpenRobotics/Drawer、Drawer_2、Drawer_3……的根物件。"""
    pattern = re.compile(r"^drawer(?:_\d+)?$", re.IGNORECASE)
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


def clean_generated_collection():
    """只刪除上次由本腳本建立的替代品，不碰 Gazebo 原模型。"""
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


def cube(name, location, dimensions, mat, collection, bevel_width=0.01):
    bpy.ops.mesh.primitive_cube_add(location=location)
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
    rotation=(0, 0, 0),
    vertices=24,
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
    bevel(obj, min(radius * 0.15, 0.006), 3)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def hide_original_tree(root):
    """隱藏原始 Drawer 與全部 Proxy 子物件，但不刪除。"""
    root.hide_set(True)
    root.hide_viewport = True
    root.hide_render = True

    for child in root.children_recursive:
        child.hide_set(True)
        child.hide_viewport = True
        child.hide_render = True


def build_one(index, original, collection, materials):
    suffix = f"{index:02d}"
    body, drawer_front, trim, handle_well, handle_inner, rubber = materials
    parts = []

    # 霧砂銀灰色櫃身
    parts.append(cube(
        f"Drawer_Cabinet_{suffix}",
        (0, 0, 0.43),
        (0.45, 0.50, 0.76),
        body,
        collection,
        0.035,
    ))
    parts.append(cube(
        f"Drawer_Top_{suffix}",
        (0, 0, 0.84),
        (0.49, 0.54, 0.08),
        trim,
        collection,
        0.028,
    ))
    parts.append(cube(
        f"Drawer_Base_{suffix}",
        (0, 0, 0.055),
        (0.48, 0.53, 0.08),
        trim,
        collection,
        0.020,
    ))

    # 參考圖配置：上面兩個小抽屜，下面一個較大的抽屜。
    drawer_specs = (
        (1, 0.705, 0.15),
        (2, 0.515, 0.15),
        (3, 0.285, 0.27),
    )

    for drawer_index, z, height in drawer_specs:
        parts.append(cube(
            f"Drawer_Front_{drawer_index}_{suffix}",
            (0, -0.262, z),
            (0.39, 0.035, height),
            drawer_front,
            collection,
            0.018,
        ))

        # 以深色凹槽＋銀灰內片表現參考圖的嵌入式把手。
        parts.append(cube(
            f"Drawer_HandleWell_{drawer_index}_{suffix}",
            (0, -0.285, z + height * 0.10),
            (0.17, 0.018, 0.052),
            handle_well,
            collection,
            0.022,
        ))
        parts.append(cube(
            f"Drawer_HandleInner_{drawer_index}_{suffix}",
            (0, -0.297, z + height * 0.10),
            (0.125, 0.009, 0.026),
            handle_inner,
            collection,
            0.010,
        ))

    # 四個小腳輪，正面朝 -Y。
    for caster_index, (x, y) in enumerate(
        ((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18)),
        start=1,
    ):
        parts.append(cylinder(
            f"Drawer_Caster_{caster_index}_{suffix}",
            0.035,
            0.055,
            (x, y, 0.018),
            rubber,
            collection,
            rotation=(math.pi / 2, 0, 0),
        ))

    root = bpy.data.objects.new(f"{ROOT_PREFIX}{suffix}", None)
    root["source_object"] = original.name
    root["width_m"] = 0.49
    root["depth_m"] = 0.54
    root["height_m"] = 0.88
    root["model"] = "Drawer"
    root["description"] = "mist silver-gray mobile three-drawer cabinet"
    collection.objects.link(root)
    parent_parts(root, parts)

    location, rotation, _original_scale = original.matrix_world.decompose()
    root.matrix_world = (
        Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Rotation(math.radians(ROTATION_OFFSET_DEG), 4, "Z")
        @ Matrix.Scale(MODEL_SCALE, 4)
    )

    hide_original_tree(original)
    return root


def build():
    # 必須先尋找原物件，再清除上一輪替代品。
    originals = find_originals()
    if not originals:
        raise RuntimeError(
            "找不到 OpenRobotics/Drawer 或 Drawer_2～Drawer_5；"
            "請確認原始 Furniture_Proxy 仍存在於場景中。"
        )

    collection = clean_generated_collection()

    # 暖調霧砂銀灰：與白／米色醫院背景有層次，但不會太深。
    body = material(
        "MAT_Drawer_MistSilverBody",
        (0.50, 0.52, 0.51),
        roughness=0.52,
        metallic=0.30,
    )
    drawer_front = material(
        "MAT_Drawer_WarmSilverFront",
        (0.68, 0.68, 0.64),
        roughness=0.48,
        metallic=0.22,
    )
    trim = material(
        "MAT_Drawer_SoftSilverTrim",
        (0.58, 0.59, 0.56),
        roughness=0.40,
        metallic=0.42,
    )
    handle_well = material(
        "MAT_Drawer_HandleWell",
        (0.20, 0.22, 0.21),
        roughness=0.54,
        metallic=0.18,
    )
    handle_inner = material(
        "MAT_Drawer_HandleInner",
        (0.76, 0.76, 0.71),
        roughness=0.34,
        metallic=0.48,
    )
    rubber = material(
        "MAT_Drawer_CasterRubber",
        (0.035, 0.040, 0.038),
        roughness=0.72,
        metallic=0.0,
    )

    materials = (body, drawer_front, trim, handle_well, handle_inner, rubber)
    roots = [
        build_one(index, original, collection, materials)
        for index, original in enumerate(originals, start=1)
    ]

    bpy.ops.object.select_all(action="DESELECT")
    roots[0].select_set(True)
    bpy.context.view_layer.objects.active = roots[0]

    print(f"完成：建立 {len(roots)} 個霧砂銀灰色 Drawer 替代品")
    for root in roots:
        print(f"  {root['source_object']} -> {root.name}")


if __name__ == "__main__":
    build()
