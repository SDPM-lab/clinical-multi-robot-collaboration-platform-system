import math
import re

import bpy
from mathutils import Matrix


COLLECTION_NAME = "LitterBin"
ROOT_PREFIX = "LitterBin_Replacement_"

# 若整批方向不正確，可改成 90、-90 或 180。
ROTATION_OFFSET_DEG = 0.0
MODEL_SCALE = 1.0


def material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)

    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, 1.0)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic

    return mat


def find_originals():
    """辨識 LitterBin、LitterBin2、LitterBin_2 等 Gazebo 根物件。"""
    pattern = re.compile(r"^litterbin(?:_?\d+)?$", re.IGNORECASE)
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
    rotation=(0.0, 0.0, 0.0),
    vertices=32,
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
    bevel(obj, min(radius * 0.18, 0.008), 3)
    return obj


def text_mesh(name, body, location, size, mat, collection):
    """建立可隨 glTF 匯出的簡單英文字標。"""
    bpy.ops.object.text_add(
        location=location,
        rotation=(math.radians(90), 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.002
    obj.data.bevel_depth = 0.001
    obj.data.materials.append(mat)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    move_to(obj, collection)
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
    body_mat, trim_mat, opening_mat, recycle_mat, other_mat, text_mat, rubber_mat = mats
    suffix = f"{index:02d}"
    parts = []

    total_width = 1.08
    total_depth = 0.46
    total_height = 1.12

    # 下半部雙門箱體
    parts.append(cube(
        f"LitterBin_{suffix}_LowerBody",
        (0, 0, 0.43),
        (1.02, 0.43, 0.78),
        body_mat,
        collection,
        0.045,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_CenterSeam",
        (0, -0.224, 0.43),
        (0.018, 0.012, 0.68),
        trim_mat,
        collection,
        0.004,
    ))

    # 兩扇前門
    for side, label in ((-1, "Recycle"), (1, "Other")):
        x = side * 0.255
        parts.append(cube(
            f"LitterBin_{suffix}_{label}Door",
            (x, -0.228, 0.42),
            (0.47, 0.025, 0.64),
            body_mat,
            collection,
            0.022,
        ))

        # 金屬門把
        parts.append(cube(
            f"LitterBin_{suffix}_{label}Handle",
            (x, -0.258, 0.67),
            (0.15, 0.045, 0.055),
            trim_mat,
            collection,
            0.014,
        ))
        parts.append(cube(
            f"LitterBin_{suffix}_{label}HandleInset",
            (x, -0.284, 0.67),
            (0.095, 0.012, 0.018),
            opening_mat,
            collection,
            0.005,
        ))

    # 上方投入口外殼：用框架組成，兩個洞不是畫在平面上的假黑框。
    hood_bottom = 0.79
    hood_top = total_height
    hood_center_z = (hood_bottom + hood_top) / 2
    hood_height = hood_top - hood_bottom

    parts.append(cube(
        f"LitterBin_{suffix}_HoodTop",
        (0, 0, hood_top - 0.035),
        (total_width, total_depth, 0.07),
        body_mat,
        collection,
        0.05,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_HoodLeftSide",
        (-0.515, 0, hood_center_z),
        (0.05, total_depth, hood_height),
        body_mat,
        collection,
        0.025,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_HoodRightSide",
        (0.515, 0, hood_center_z),
        (0.05, total_depth, hood_height),
        body_mat,
        collection,
        0.025,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_HoodCenterDivider",
        (0, 0, hood_center_z),
        (0.055, total_depth, hood_height),
        body_mat,
        collection,
        0.018,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_HoodBottomSill",
        (0, 0, hood_bottom + 0.035),
        (total_width, total_depth, 0.07),
        trim_mat,
        collection,
        0.018,
    ))

    # 投入口後方的深色內壁，放在較深的位置，形成真正凹入感。
    for side, label in ((-1, "Recycle"), (1, "Other")):
        x = side * 0.265
        parts.append(cube(
            f"LitterBin_{suffix}_{label}OpeningBack",
            (x, 0.16, 0.945),
            (0.43, 0.025, 0.16),
            opening_mat,
            collection,
            0.018,
        ))
        parts.append(cube(
            f"LitterBin_{suffix}_{label}OpeningFloor",
            (x, 0.02, 0.855),
            (0.43, 0.30, 0.035),
            opening_mat,
            collection,
            0.012,
        ))

    # 低飽和分類標籤，符合目前暖白醫院色系。
    parts.append(cube(
        f"LitterBin_{suffix}_RecycleLabelPlate",
        (-0.255, -0.258, 0.39),
        (0.31, 0.028, 0.22),
        recycle_mat,
        collection,
        0.018,
    ))
    parts.append(cube(
        f"LitterBin_{suffix}_OtherLabelPlate",
        (0.255, -0.258, 0.39),
        (0.31, 0.028, 0.22),
        other_mat,
        collection,
        0.018,
    ))
    parts.append(text_mesh(
        f"LitterBin_{suffix}_RecycleText",
        "RECYCLE",
        (-0.255, -0.277, 0.39),
        0.055,
        text_mat,
        collection,
    ))
    parts.append(text_mesh(
        f"LitterBin_{suffix}_OtherText",
        "OTHER",
        (0.255, -0.277, 0.39),
        0.055,
        text_mat,
        collection,
    ))

    # 底座及四個防滑腳
    parts.append(cube(
        f"LitterBin_{suffix}_BasePlinth",
        (0, 0, 0.055),
        (1.06, 0.45, 0.09),
        trim_mat,
        collection,
        0.025,
    ))
    for x in (-0.47, 0.47):
        for y in (-0.17, 0.17):
            parts.append(cylinder(
                f"LitterBin_{suffix}_Foot",
                0.025,
                0.035,
                (x, y, 0.010),
                rubber_mat,
                collection,
                vertices=20,
            ))

    root = bpy.data.objects.new(f"{ROOT_PREFIX}{suffix}", None)
    root["source_object"] = original.name
    root["width_m"] = total_width
    root["depth_m"] = total_depth
    root["height_m"] = total_height
    root["model"] = "LitterBin"
    root["description"] = "rounded dual-compartment indoor hospital recycling bin"
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
        print("找不到 LitterBin 原始物件。")
        print("請確認 Outliner 名稱是否為 LitterBin、LitterBin2 或 LitterBin_2。")
        return

    collection = clean_collection()

    # 暖銀灰主體，避免過度冰冷，也能配合米白牆面與木色門。
    body_mat = material("MAT_LitterBin_WarmSilver", (0.54, 0.52, 0.47), 0.32, 0.68)
    trim_mat = material("MAT_LitterBin_ChampagneTrim", (0.30, 0.285, 0.26), 0.28, 0.76)
    opening_mat = material("MAT_LitterBin_OpeningDark", (0.035, 0.040, 0.042), 0.72, 0.08)
    recycle_mat = material("MAT_LitterBin_MutedBlue", (0.12, 0.26, 0.32), 0.58, 0.05)
    other_mat = material("MAT_LitterBin_MutedCaramel", (0.48, 0.18, 0.065), 0.58, 0.03)
    text_mat = material("MAT_LitterBin_LabelText", (0.88, 0.86, 0.80), 0.62)
    rubber_mat = material("MAT_LitterBin_RubberFoot", (0.025, 0.026, 0.025), 0.72)
    mats = (
        body_mat,
        trim_mat,
        opening_mat,
        recycle_mat,
        other_mat,
        text_mat,
        rubber_mat,
    )

    replacements = []
    for index, original in enumerate(originals, 1):
        replacements.append(build_one(index, original, collection, mats))

    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    replacements[0].select_set(True)
    bpy.context.view_layer.objects.active = replacements[0]

    print(f"完成：已建立並替換 {len(replacements)} 個大型雙分類 LitterBin")
    for replacement in replacements:
        print(" -", replacement.name, "來源：", replacement["source_object"])


if __name__ == "__main__":
    build()
