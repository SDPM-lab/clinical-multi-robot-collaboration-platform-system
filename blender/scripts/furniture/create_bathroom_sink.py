import math
import re

import bpy
from mathutils import Matrix, Vector


COLLECTION = "BathroomSink_Replacement"
ROOT_PREFIX = "BathroomSink_Replacement_"

# 如果整批洗手台朝向相反，只需改成 90.0 或 -90.0。
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
    shader.inputs["IOR"].default_value = 1.46
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    mat.diffuse_color = (*color, 1.0)
    return mat


def find_originals():
    """尋找 OpenRobotics/BathroomSink、BathroomSink_2……等原始根物件。"""
    pattern = re.compile(r"^bathroomsink(?:_\d+)?$", re.IGNORECASE)
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


def bevel(obj, width=0.01, segments=5):
    modifier = obj.modifiers.new("Soft_Rounded_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


def cylinder(name, radius, depth, location, mat, collection, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.15, 0.012), 4)
    return obj


def sphere(name, location, scale, mat, collection):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to(obj, collection)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def superellipse_point(angle, radius_x, radius_y, exponent=3.6):
    cosine = math.cos(angle)
    sine = math.sin(angle)
    power = 2.0 / exponent
    x = radius_x * math.copysign(abs(cosine) ** power, cosine)
    y = radius_y * math.copysign(abs(sine) ** power, sine)
    return x, y


def create_basin(name, mat, collection):
    """建立有真實凹槽的圓角方形洗手盆，不使用深色平面假裝洞口。"""
    segments = 64

    # +X 是洗手台正面；Y 是左右寬度。
    rings = (
        (0.285, 0.385, 0.815),  # 外側下緣
        (0.305, 0.405, 0.905),  # 外側上緣
        (0.238, 0.325, 0.925),  # 內側盆口
        (0.178, 0.250, 0.835),  # 內盆斜面
        (0.092, 0.140, 0.775),  # 排水口周圍
    )

    vertices = []
    for radius_x, radius_y, z in rings:
        for index in range(segments):
            angle = math.tau * index / segments
            x, y = superellipse_point(angle, radius_x, radius_y)
            vertices.append((x, y, z))

    underside_center = len(vertices)
    vertices.append((0, 0, 0.805))
    bowl_center = len(vertices)
    vertices.append((0, 0, 0.765))

    faces = []
    for ring_index in range(len(rings) - 1):
        start_a = ring_index * segments
        start_b = (ring_index + 1) * segments
        for index in range(segments):
            next_index = (index + 1) % segments
            faces.append((
                start_a + index,
                start_a + next_index,
                start_b + next_index,
                start_b + index,
            ))

    # 封住底面以及內盆最低處，模型仍保持中間凹入。
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((underside_center, next_index, index))
        last_ring = (len(rings) - 1) * segments
        faces.append((bowl_center, last_ring + index, last_ring + next_index))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

    bevel(obj, 0.012, 4)
    return obj


def create_pipe(name, points, radius, mat, collection):
    curve_data = bpy.data.curves.new(f"{name}_Curve", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 16
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 5
    curve_data.resolution_u = 24

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


def hide_original_tree(root):
    root.hide_set(True)
    root.hide_viewport = True
    root.hide_render = True
    for child in root.children_recursive:
        child.hide_set(True)
        child.hide_viewport = True
        child.hide_render = True


def build_one(index, original, collection, porcelain, metal, drain_mat):
    suffix = f"{index:02d}"
    parts = []

    parts.append(create_basin(
        f"BathroomSink_SmoothBasin_{suffix}",
        porcelain,
        collection,
    ))

    # 盆底排水孔與後側溢水孔。
    parts.append(cylinder(
        f"BathroomSink_Drain_{suffix}",
        0.038,
        0.010,
        (0.035, 0, 0.772),
        drain_mat,
        collection,
        32,
    ))
    overflow = sphere(
        f"BathroomSink_Overflow_{suffix}",
        (-0.145, 0, 0.850),
        (0.027, 0.010, 0.018),
        drain_mat,
        collection,
    )
    parts.append(overflow)

    # 光滑銀色圓弧水龍頭。
    parts.append(cylinder(
        f"BathroomSink_FaucetBase_{suffix}",
        0.055,
        0.035,
        (-0.205, 0, 0.955),
        metal,
        collection,
        48,
    ))
    parts.append(create_pipe(
        f"BathroomSink_FaucetArch_{suffix}",
        (
            (-0.205, 0, 0.960),
            (-0.205, 0, 1.155),
            (-0.115, 0, 1.245),
            (0.000, 0, 1.205),
            (0.045, 0, 1.080),
        ),
        0.024,
        metal,
        collection,
    ))
    parts.append(cylinder(
        f"BathroomSink_FaucetNozzle_{suffix}",
        0.028,
        0.050,
        (0.045, 0, 1.060),
        metal,
        collection,
        40,
    ))

    # 小型單把手，保持畫面簡潔。
    handle = cylinder(
        f"BathroomSink_FaucetHandle_{suffix}",
        0.016,
        0.105,
        (-0.205, 0.080, 1.005),
        metal,
        collection,
        32,
    )
    handle.rotation_euler.x = math.radians(65)
    parts.append(handle)

    root = bpy.data.objects.new(f"{ROOT_PREFIX}{suffix}", None)
    root["source_object"] = original.name
    root["width_m"] = 0.81
    root["depth_m"] = 0.61
    root["height_m"] = 1.27
    root["model"] = "BathroomSink"
    root["description"] = "smooth wall-mounted upper basin without cabinet"
    collection.objects.link(root)
    parent_parts(root, parts)

    location, rotation, _source_scale = original.matrix_world.decompose()
    root.matrix_world = (
        Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Rotation(math.radians(ROTATION_OFFSET_DEG), 4, "Z")
        @ Matrix.Scale(MODEL_SCALE, 4)
    )

    hide_original_tree(original)
    return root


def build():
    originals = find_originals()
    if not originals:
        raise RuntimeError(
            "找不到 OpenRobotics/BathroomSink；請確認原始洗手台根物件仍存在。"
        )

    collection = clean_generated_collection()

    # 暖灰白陶瓷：亮而不會像純白塑膠；金屬則使用柔和銀灰。
    porcelain = material(
        "MAT_BathroomSink_SmoothWarmPorcelain",
        (0.78, 0.79, 0.76),
        roughness=0.16,
        metallic=0.0,
    )
    metal = material(
        "MAT_BathroomSink_SatinSilver",
        (0.48, 0.52, 0.53),
        roughness=0.20,
        metallic=0.88,
    )
    drain_mat = material(
        "MAT_BathroomSink_Drain",
        (0.12, 0.14, 0.14),
        roughness=0.26,
        metallic=0.72,
    )

    roots = [
        build_one(index, original, collection, porcelain, metal, drain_mat)
        for index, original in enumerate(originals, start=1)
    ]

    bpy.ops.object.select_all(action="DESELECT")
    roots[0].select_set(True)
    bpy.context.view_layer.objects.active = roots[0]

    print(f"完成：建立 {len(roots)} 個光滑壁掛式 BathroomSink")
    for root in roots:
        print(f"  {root['source_object']} -> {root.name}")


if __name__ == "__main__":
    build()
