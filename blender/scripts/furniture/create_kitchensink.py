import math
import bpy


SOURCE_KEY = "openrobotics/kitchensink"
TARGET_COLLECTION = "KitchenSink_Replacement"

WIDTH_M = 1.20
DEPTH_M = 0.65
HEIGHT_M = 0.90


def simple_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, 1.0)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


def stone_material():
    name = "MAT_KitchenSink_DarkStone"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    noise.inputs["Scale"].default_value = 7.0
    noise.inputs["Detail"].default_value = 3.2
    noise.inputs["Roughness"].default_value = 0.72
    # 中淺灰石材紋理，與灰白醫院空間協調但仍可辨識輪廓。
    ramp.color_ramp.elements[0].color = (0.18, 0.21, 0.22, 1.0)
    ramp.color_ramp.elements[1].color = (0.40, 0.44, 0.45, 1.0)
    shader.inputs["Roughness"].default_value = 0.52
    shader.inputs["Metallic"].default_value = 0.025
    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.0025

    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    mat.diffuse_color = (0.30, 0.33, 0.34, 1.0)
    return mat


def source_roots():
    matches = [
        obj for obj in bpy.context.scene.objects
        if SOURCE_KEY in obj.name.casefold()
        and "replacement" not in obj.name.casefold()
    ]
    roots = []
    for obj in matches:
        parent = obj.parent
        has_matching_parent = False
        while parent:
            if SOURCE_KEY in parent.name.casefold():
                has_matching_parent = True
                break
            parent = parent.parent
        if not has_matching_parent:
            roots.append(obj)
    if not roots:
        raise RuntimeError(
            "找不到 OpenRobotics/KitchenSink；請確認 Outliner 名稱。"
        )
    return sorted(roots, key=lambda obj: obj.name.casefold())


def hierarchy(root):
    result = [root]
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(obj.children)
    return result


def hide_original(roots):
    for root in roots:
        for obj in hierarchy(root):
            obj.hide_set(True)
            obj.hide_viewport = True
            obj.hide_render = True


def clean_target():
    old = bpy.data.collections.get(TARGET_COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    result = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(result)
    return result


def move_to(obj, collection):
    collection.objects.link(obj)
    for old in list(obj.users_collection):
        if old != collection:
            old.objects.unlink(obj)


def bevel(obj, width=0.02, segments=4, smooth=True):
    modifier = obj.modifiers.new(name="RoundedEdges", type="BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    if smooth and obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def cube(name, location, dimensions, mat, collection, bevel_width=0.02):
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
    name, radius, depth, location, mat, collection, rotation=(0.0, 0.0, 0.0)
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.16, 0.009), 3)
    return obj


def torus(name, location, major_radius, minor_radius, mat, collection):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=32,
        minor_segments=12,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    return obj


def build_one(index, source_matrix, collection, mats):
    stone, cabinet, basin, metal, dark = mats
    prefix = f"KitchenSinkReplacement_{index:02d}"
    parts = []

    cabinet_height = HEIGHT_M - 0.14
    counter_z = HEIGHT_M - 0.055
    counter_thickness = 0.11
    basin_width = 0.56
    basin_depth = 0.40
    side_width = (WIDTH_M - basin_width) * 0.5
    front_rail = 0.105
    back_rail = DEPTH_M - basin_depth - front_rail

    # 深咖啡櫃體與底部陰影層。
    parts.append(cube(
        prefix + "_Cabinet",
        (0.0, 0.0, cabinet_height * 0.5),
        (WIDTH_M, DEPTH_M, cabinet_height),
        cabinet, collection, 0.026,
    ))
    parts.append(cube(
        prefix + "_ToeKick",
        (0.0, -DEPTH_M * 0.5 - 0.012, 0.065),
        (WIDTH_M * 0.86, 0.035, 0.13),
        dark, collection, 0.008,
    ))

    # 四片深色石材檯面包圍真正凹下的水槽。
    for side in (-1, 1):
        parts.append(cube(
            prefix + f"_CounterSide_{side}",
            (side * (basin_width * 0.5 + side_width * 0.5), 0.0, counter_z),
            (side_width, DEPTH_M, counter_thickness),
            stone, collection, 0.018,
        ))
    parts.append(cube(
        prefix + "_CounterFront",
        (0.0, -DEPTH_M * 0.5 + front_rail * 0.5, counter_z),
        (basin_width, front_rail, counter_thickness),
        stone, collection, 0.018,
    ))
    parts.append(cube(
        prefix + "_CounterBack",
        (0.0, DEPTH_M * 0.5 - back_rail * 0.5, counter_z),
        (basin_width, back_rail, counter_thickness),
        stone, collection, 0.018,
    ))

    # 水槽盆底與內側四壁。
    basin_bottom_z = HEIGHT_M - 0.20
    parts.append(cube(
        prefix + "_BasinBottom",
        (0.0, 0.0, basin_bottom_z),
        (basin_width - 0.08, basin_depth - 0.08, 0.055),
        basin, collection, 0.035,
    ))
    wall_height = 0.12
    for side in (-1, 1):
        parts.append(cube(
            prefix + f"_BasinSide_{side}",
            (side * (basin_width * 0.5 - 0.022), 0.0, basin_bottom_z + 0.055),
            (0.044, basin_depth, wall_height),
            basin, collection, 0.018,
        ))
    for side in (-1, 1):
        parts.append(cube(
            prefix + f"_BasinWall_{side}",
            (0.0, side * (basin_depth * 0.5 - 0.022), basin_bottom_z + 0.055),
            (basin_width, 0.044, wall_height),
            basin, collection, 0.018,
        ))

    drain_z = basin_bottom_z + 0.032
    parts.append(cylinder(
        prefix + "_Drain", 0.052, 0.014,
        (0.0, 0.0, drain_z), metal, collection,
    ))
    parts.append(torus(
        prefix + "_DrainRing", (0.0, 0.0, drain_z + 0.009),
        0.052, 0.007, metal, collection,
    ))

    # 後擋水板。
    parts.append(cube(
        prefix + "_Backsplash",
        (0.0, DEPTH_M * 0.5 - 0.025, HEIGHT_M + 0.08),
        (WIDTH_M, 0.05, 0.22),
        stone, collection, 0.015,
    ))

    # 置中的霧銀水龍頭，出水口朝向前方（-Y）。
    faucet_y = 0.21
    parts.append(cylinder(
        prefix + "_FaucetBase", 0.052, 0.035,
        (0.0, faucet_y, HEIGHT_M + 0.025), metal, collection,
    ))
    parts.append(cylinder(
        prefix + "_FaucetStem", 0.024, 0.32,
        (0.0, faucet_y, HEIGHT_M + 0.19), metal, collection,
    ))
    parts.append(cylinder(
        prefix + "_FaucetSpout", 0.022, 0.23,
        (0.0, faucet_y - 0.105, HEIGHT_M + 0.325),
        metal, collection, rotation=(math.radians(90.0), 0.0, 0.0),
    ))
    parts.append(cylinder(
        prefix + "_FaucetNozzle", 0.024, 0.075,
        (0.0, faucet_y - 0.22, HEIGHT_M + 0.29), metal, collection,
    ))

    # 櫃門與霧銀把手。
    for side in (-1, 1):
        x = side * 0.29
        parts.append(cube(
            prefix + f"_CabinetDoor_{side}",
            (x, -DEPTH_M * 0.5 - 0.009, 0.41),
            (0.55, 0.018, 0.62),
            cabinet, collection, 0.012,
        ))
        parts.append(cube(
            prefix + f"_Handle_{side}",
            (side * 0.085, -DEPTH_M * 0.5 - 0.035, 0.52),
            (0.035, 0.025, 0.18),
            metal, collection, 0.009,
        ))

    root = bpy.data.objects.new(prefix + "_Root", None)
    root["width_m"] = WIDTH_M
    root["depth_m"] = DEPTH_M
    root["height_m"] = HEIGHT_M
    root["design"] = "warm beige and textured gray hospital kitchen sink"
    collection.objects.link(root)

    for obj in parts:
        world = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world

    root.matrix_world = source_matrix
    return root


def main():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    originals = source_roots()
    source_matrices = [obj.matrix_world.copy() for obj in originals]
    target = clean_target()

    stone = stone_material()
    cabinet = simple_material(
        "MAT_KitchenSink_WarmGreigeCabinet", (0.52, 0.36, 0.22), 0.68
    )
    basin = simple_material(
        "MAT_KitchenSink_WarmGrayBasin", (0.52, 0.57, 0.58), 0.42, 0.08
    )
    metal = simple_material(
        "MAT_KitchenSink_BrushedMetal", (0.46, 0.50, 0.51), 0.28, 0.70
    )
    dark = simple_material(
        "MAT_KitchenSink_MediumGrayBase", (0.18, 0.20, 0.21), 0.58, 0.05
    )

    created = [
        build_one(index, matrix, target, (stone, cabinet, basin, metal, dark))
        for index, matrix in enumerate(source_matrices, 1)
    ]
    hide_original(originals)

    bpy.ops.object.select_all(action="DESELECT")
    for root in created:
        root.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    print(
        f"完成：隱藏 {len(originals)} 座原始 KitchenSink，"
        f"並在相同位置建立 {len(created)} 座深色替代洗手台。"
    )


if __name__ == "__main__":
    main()
