import bpy
import math
import re
from mathutils import Matrix


COLLECTION_NAME = "CGMVanguard"
ROTATION_OFFSET_DEG = 0.0
BACK_ANGLE_DEG = 27.0


# =========================================================
# 材質
# =========================================================

def make_material(
    name,
    color,
    roughness=0.5,
    metallic=0.0
):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1.0)

    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic

    return mat


# =========================================================
# Collection
# =========================================================

def clean_collection():
    old = bpy.data.collections.get(COLLECTION_NAME)

    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    return collection


def move_to_collection(obj, collection):
    if collection not in obj.users_collection:
        collection.objects.link(obj)

    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


# =========================================================
# 建模工具
# =========================================================

def add_bevel(obj, width=0.02, segments=5):
    modifier = obj.modifiers.new("Soft_Rounded_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def create_cube(
    name,
    location,
    dimensions,
    material,
    collection,
    bevel_width=0.02,
    rotation=(0, 0, 0)
):
    bpy.ops.mesh.primitive_cube_add(location=location)

    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    obj.rotation_euler = rotation
    obj.data.materials.append(material)

    move_to_collection(obj, collection)

    if bevel_width > 0:
        add_bevel(obj, bevel_width)

    return obj


def create_cylinder(
    name,
    radius,
    depth,
    location,
    material,
    collection,
    rotation=(0, 0, 0),
    vertices=32
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)

    move_to_collection(obj, collection)
    add_bevel(obj, min(radius * 0.18, 0.012), 3)

    return obj


def create_wheel(
    name,
    location,
    material,
    collection
):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.065,
        minor_radius=0.022,
        major_segments=28,
        minor_segments=10,
        location=location,
        rotation=(math.radians(90), 0, 0)
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)

    move_to_collection(obj, collection)

    return obj


def parent_keep_transform(obj, parent):
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix


def all_children(obj):
    result = []

    for child in obj.children:
        result.append(child)
        result.extend(all_children(child))

    return result


# =========================================================
# 尋找原始 CGMVanguard
# =========================================================

def find_original_targets():
    targets = []

    for obj in bpy.data.objects:
        short_name = obj.name.split("/")[-1]

        if re.fullmatch(
            r"cgmvanguard(?:_\d+)?",
            short_name,
            flags=re.IGNORECASE
        ):
            targets.append(obj)

    targets.sort(key=lambda obj: obj.name.casefold())

    return targets


def hide_original(obj):
    obj.hide_set(True)
    obj.hide_render = True

    for child in all_children(obj):
        child.hide_set(True)
        child.hide_render = True


# =========================================================
# 建立電動病床原型
# =========================================================

def create_bed_prototype(collection):
    # 暖灰金屬床架
    frame_mat = make_material(
        "MAT_CGM_BedFrame",
        (0.25, 0.235, 0.215),
        roughness=0.34,
        metallic=0.48
    )

    # 較淺床頭、床尾板
    panel_mat = make_material(
        "MAT_CGM_BedPanel",
        (0.38, 0.36, 0.33),
        roughness=0.42,
        metallic=0.22
    )

    # 酒紅棕床墊
    mattress_mat = make_material(
        "MAT_CGM_BurgundyMattress",
        (0.285, 0.070, 0.058),
        roughness=0.72
    )

    # 床墊縫線
    seam_mat = make_material(
        "MAT_CGM_MattressSeam",
        (0.135, 0.030, 0.025),
        roughness=0.70
    )

    # 深色底盤
    chassis_mat = make_material(
        "MAT_CGM_DarkChassis",
        (0.055, 0.050, 0.047),
        roughness=0.42,
        metallic=0.32
    )

    # 藍灰色控制面板
    control_mat = make_material(
        "MAT_CGM_ControlPanel",
        (0.025, 0.105, 0.135),
        roughness=0.32
    )

    # 輪胎
    wheel_mat = make_material(
        "MAT_CGM_Wheel",
        (0.018, 0.018, 0.017),
        roughness=0.70
    )

    parts = []

    # -----------------------------------------------------
    # 底盤
    # -----------------------------------------------------

    parts.append(
        create_cube(
            "CGMBed_MainFrame",
            (0, 0, 0.43),
            (2.08, 0.92, 0.16),
            frame_mat,
            collection,
            0.035
        )
    )

    parts.append(
        create_cube(
            "CGMBed_LowerChassis",
            (0, 0, 0.25),
            (1.65, 0.56, 0.13),
            chassis_mat,
            collection,
            0.030
        )
    )

    # 底部橫向支撐
    for index, x in enumerate((-0.72, 0.72), 1):
        parts.append(
            create_cube(
                f"CGMBed_ChassisSupport_{index}",
                (x, 0, 0.25),
                (0.14, 0.78, 0.10),
                frame_mat,
                collection,
                0.020
            )
        )

    # -----------------------------------------------------
    # 分段式床墊
    # -----------------------------------------------------

    angle = math.radians(BACK_ANGLE_DEG)

    # 靠背與平面床墊交接位置
    pivot_x = -0.12
    pivot_z = 0.66

    back_length = 0.96

    back_center_x = (
        pivot_x
        - (back_length / 2) * math.cos(angle)
    )

    back_center_z = (
        pivot_z
        + (back_length / 2) * math.sin(angle)
    )

    # 抬高靠背下方支撐板
    parts.append(
        create_cube(
            "CGMBed_BackPlatform",
            (back_center_x, 0, back_center_z - 0.08),
            (back_length, 0.84, 0.09),
            frame_mat,
            collection,
            0.025,
            rotation=(0, angle, 0)
        )
    )

    # 抬高靠背床墊
    parts.append(
        create_cube(
            "CGMBed_BackMattress",
            (back_center_x, 0, back_center_z + 0.04),
            (back_length, 0.80, 0.17),
            mattress_mat,
            collection,
            0.070,
            rotation=(0, angle, 0)
        )
    )

    # 中間坐墊
    parts.append(
        create_cube(
            "CGMBed_CenterMattress",
            (0.12, 0, 0.68),
            (0.52, 0.80, 0.18),
            mattress_mat,
            collection,
            0.065
        )
    )

    # 腿部床墊
    parts.append(
        create_cube(
            "CGMBed_LegMattress",
            (0.68, 0, 0.665),
            (0.68, 0.80, 0.17),
            mattress_mat,
            collection,
            0.065
        )
    )

    # 床墊分段縫線
    parts.append(
        create_cube(
            "CGMBed_CenterSeam",
            (0.39, 0, 0.776),
            (0.025, 0.76, 0.012),
            seam_mat,
            collection,
            0.005
        )
    )

    # 枕頭，跟隨靠背角度
    parts.append(
        create_cube(
            "CGMBed_Pillow",
            (-0.72, 0, 1.00),
            (0.38, 0.62, 0.13),
            mattress_mat,
            collection,
            0.060,
            rotation=(0, angle, 0)
        )
    )

    # -----------------------------------------------------
    # 床頭板與床尾板
    # -----------------------------------------------------

    parts.append(
        create_cube(
            "CGMBed_HeadBoard",
            (-1.05, 0, 0.84),
            (0.14, 1.00, 0.76),
            panel_mat,
            collection,
            0.055
        )
    )

    parts.append(
        create_cube(
            "CGMBed_FootBoard",
            (1.05, 0, 0.78),
            (0.14, 1.00, 0.64),
            panel_mat,
            collection,
            0.055
        )
    )

    # 床頭板上方把手造型
    parts.append(
        create_cube(
            "CGMBed_HeadHandle",
            (-1.12, 0, 1.12),
            (0.055, 0.52, 0.10),
            chassis_mat,
            collection,
            0.025
        )
    )

    # 床尾板上方把手
    parts.append(
        create_cube(
            "CGMBed_FootHandle",
            (1.12, 0, 1.00),
            (0.055, 0.52, 0.10),
            chassis_mat,
            collection,
            0.025
        )
    )

    # 床尾控制面板
    parts.append(
        create_cube(
            "CGMBed_ControlScreen",
            (1.126, -0.17, 0.83),
            (0.018, 0.25, 0.12),
            control_mat,
            collection,
            0.012
        )
    )

    # -----------------------------------------------------
    # 左右側護欄
    # -----------------------------------------------------

    for side in (-1, 1):
        y = side * 0.49

        parts.append(
            create_cube(
                f"CGMBed_SideRail_{side}",
                (0.05, y, 0.73),
                (0.88, 0.075, 0.30),
                panel_mat,
                collection,
                0.055
            )
        )

        # 護欄內側深色裝飾
        parts.append(
            create_cube(
                f"CGMBed_SideRailInset_{side}",
                (0.05, side * 0.532, 0.73),
                (0.52, 0.015, 0.10),
                chassis_mat,
                collection,
                0.015
            )
        )

        # 護欄轉軸
        parts.append(
            create_cylinder(
                f"CGMBed_RailPivot_{side}",
                0.075,
                0.10,
                (-0.36, y, 0.58),
                frame_mat,
                collection,
                rotation=(math.radians(90), 0, 0)
            )
        )

    # -----------------------------------------------------
    # 床腳與輪子
    # -----------------------------------------------------

    for x_index, x in enumerate((-0.80, 0.80), 1):
        for side in (-1, 1):
            y = side * 0.35

            parts.append(
                create_cylinder(
                    f"CGMBed_Leg_{x_index}_{side}",
                    0.045,
                    0.30,
                    (x, y, 0.25),
                    frame_mat,
                    collection
                )
            )

            parts.append(
                create_cube(
                    f"CGMBed_CasterJoint_{x_index}_{side}",
                    (x, y, 0.105),
                    (0.12, 0.08, 0.07),
                    frame_mat,
                    collection,
                    0.015
                )
            )

            parts.append(
                create_wheel(
                    f"CGMBed_Wheel_{x_index}_{side}",
                    (x, y, 0.065),
                    wheel_mat,
                    collection
                )
            )

    # -----------------------------------------------------
    # Root
    # -----------------------------------------------------

    root = bpy.data.objects.new(
        "CGMVanguard_BedPrototype",
        None
    )

    root.empty_display_type = "CUBE"
    root.empty_display_size = 0.18

    root["width_m"] = 1.00
    root["length_m"] = 2.18
    root["height_m"] = 1.30
    root["back_angle_deg"] = BACK_ANGLE_DEG
    root["model"] = "CGMVanguard"
    root["description"] = "adjustable electric hospital bed"

    collection.objects.link(root)

    for obj in parts:
        parent_keep_transform(obj, root)

    return root


# =========================================================
# 複製整張病床
# =========================================================

def duplicate_hierarchy(
    source_root,
    collection,
    suffix
):
    sources = [source_root, *all_children(source_root)]
    copied = {}

    for source in sources:
        new_obj = source.copy()

        # 共用 Mesh 資料，減少檔案大小
        if source.data:
            new_obj.data = source.data

        new_obj.name = f"{source.name}_{suffix}"
        collection.objects.link(new_obj)
        copied[source] = new_obj

    for source, new_obj in copied.items():
        if source.parent in copied:
            new_obj.parent = copied[source.parent]
        else:
            new_obj.parent = None

        new_obj.matrix_basis = source.matrix_basis.copy()

    return copied[source_root]


# =========================================================
# 一次替換所有 CGMVanguard
# =========================================================

def build_all_replacements():
    targets = find_original_targets()

    if not targets:
        raise RuntimeError(
            "找不到 OpenRobotics/CGMVanguard、"
            "CGMVanguard_2 或 CGMVanguard_3。"
        )

    collection = clean_collection()
    prototype = create_bed_prototype(collection)

    replacements = []

    for index, target in enumerate(targets, 1):
        replacement = duplicate_hierarchy(
            prototype,
            collection,
            f"{index:02d}"
        )

        replacement.name = (
            f"CGMVanguard_BedReplacement_{index:02d}"
        )

        location = target.matrix_world.to_translation()
        rotation = target.matrix_world.to_quaternion()

        rotation_offset = Matrix.Rotation(
            math.radians(ROTATION_OFFSET_DEG),
            4,
            "Z"
        )

        # 保留位置和方向，但不繼承原本錯誤縮放
        replacement.matrix_world = (
            Matrix.Translation(location)
            @ rotation.to_matrix().to_4x4()
            @ rotation_offset
        )

        replacement.scale = (1, 1, 1)
        replacement["replacement_for"] = target.name

        hide_original(target)
        replacements.append(replacement)

    # 移除只用來複製的原型
    prototype_objects = [
        prototype,
        *all_children(prototype)
    ]

    for obj in reversed(prototype_objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    bpy.ops.object.select_all(action="DESELECT")

    if replacements:
        replacements[0].select_set(True)
        bpy.context.view_layer.objects.active = replacements[0]

    bpy.context.view_layer.update()

    print(f"完成：建立 {len(replacements)} 張 CGMVanguard 電動病床")

    for replacement in replacements:
        print(
            replacement.name,
            "→",
            replacement.get("replacement_for")
        )


if __name__ == "__main__":
    build_all_replacements()