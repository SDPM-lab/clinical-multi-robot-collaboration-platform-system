import math
import re

import bpy
from mathutils import Vector


SOURCE_PATTERN = re.compile(r"^rectable(?:[_\.]\d+)?$", re.IGNORECASE)
TARGET_COLLECTION = "RectangularTable_Replacement"
DEFAULT_WIDTH_M = 1.40
DEFAULT_DEPTH_M = 0.80
DEFAULT_HEIGHT_M = 0.76


def material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, 1.0)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


def brushed_silver_material():
    name = "MAT_MeetingTable_BrushedSilver"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    mapping.inputs["Scale"].default_value = (2.0, 2.0, 85.0)
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.55
    ramp.color_ramp.elements[0].color = (0.34, 0.37, 0.39, 1.0)
    ramp.color_ramp.elements[1].color = (0.62, 0.66, 0.68, 1.0)
    shader.inputs["Metallic"].default_value = 0.72
    shader.inputs["Roughness"].default_value = 0.31
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.002

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    mat.diffuse_color = (0.48, 0.52, 0.54, 1.0)
    return mat


def clear_replacements():
    old = bpy.data.collections.get(TARGET_COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    collection.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def add_bevel(obj, width, segments=4):
    modifier = obj.modifiers.new("RoundedEdges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
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
        add_bevel(obj, bevel_width)
    return obj


def cylinder(name, radius, depth, location, mat, collection, vertices=32):
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
    add_bevel(obj, min(radius * 0.18, 0.008), 3)
    return obj


def is_source(obj):
    if obj.name.startswith("MeetingTable_Replacement_"):
        return False
    leaf_name = obj.name.rsplit("/", 1)[-1]
    return bool(SOURCE_PATTERN.fullmatch(leaf_name))


def find_sources():
    candidates = [obj for obj in bpy.data.objects if is_source(obj)]
    candidate_set = set(candidates)
    roots = []
    for obj in candidates:
        parent = obj.parent
        nested = False
        while parent:
            if parent in candidate_set:
                nested = True
                break
            parent = parent.parent
        if not nested:
            roots.append(obj)
    return sorted(roots, key=lambda obj: obj.name.casefold())


def hide_hierarchy(root):
    stack = [root]
    while stack:
        obj = stack.pop()
        obj.hide_set(True)
        obj.hide_render = True
        stack.extend(obj.children)


def source_placement(source):
    if source.type == "MESH" and source.bound_box:
        minimum = Vector((
            min(corner[0] for corner in source.bound_box),
            min(corner[1] for corner in source.bound_box),
            min(corner[2] for corner in source.bound_box),
        ))
        maximum = Vector((
            max(corner[0] for corner in source.bound_box),
            max(corner[1] for corner in source.bound_box),
            max(corner[2] for corner in source.bound_box),
        ))
        local_size = maximum - minimum
        location, rotation, scale = source.matrix_world.decompose()
        size = Vector((
            abs(local_size.x * scale.x),
            abs(local_size.y * scale.y),
            abs(local_size.z * scale.z),
        ))
        floor_center_local = Vector((
            (minimum.x + maximum.x) * 0.5,
            (minimum.y + maximum.y) * 0.5,
            minimum.z,
        ))
        floor_center_world = source.matrix_world @ floor_center_local
    else:
        floor_center_world, rotation, scale = source.matrix_world.decompose()
        size = Vector((DEFAULT_WIDTH_M, DEFAULT_DEPTH_M, DEFAULT_HEIGHT_M))

    width = size.x if 0.65 <= size.x <= 4.0 else DEFAULT_WIDTH_M
    depth = size.y if 0.45 <= size.y <= 2.0 else DEFAULT_DEPTH_M
    height = size.z if 0.55 <= size.z <= 1.20 else DEFAULT_HEIGHT_M
    return floor_center_world, rotation, width, depth, height


def build_table(index, source, collection, top_mat, silver_mat, dark_mat):
    anchor, rotation, width, depth, height = source_placement(source)
    prefix = f"MeetingTable_Replacement_{index:02d}"
    root = bpy.data.objects.new(f"{prefix}_Root", None)
    root.location = anchor
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = rotation
    root["source_object"] = source.name
    root["width_m"] = width
    root["depth_m"] = depth
    root["height_m"] = height
    root["design"] = "light gray and brushed silver meeting table"
    collection.objects.link(root)

    top_thickness = max(0.055, min(height * 0.10, 0.085))
    leg_height = height - top_thickness
    leg_radius = max(0.027, min(width, depth) * 0.043)
    inset_x = width * 0.40
    inset_y = depth * 0.36
    parts = []

    parts.append(cube(
        f"{prefix}_Top",
        (0.0, 0.0, height - top_thickness * 0.5),
        (width, depth, top_thickness),
        top_mat,
        collection,
        min(0.045, depth * 0.055),
    ))

    # Slim silver apron gives the table a clean conference-room profile.
    parts.append(cube(
        f"{prefix}_Frame_Long",
        (0.0, 0.0, height - top_thickness - 0.045),
        (width * 0.80, 0.055, 0.075),
        silver_mat,
        collection,
        0.012,
    ))
    for side in (-1, 1):
        parts.append(cube(
            f"{prefix}_Frame_Side_{side}",
            (side * inset_x, 0.0, height - top_thickness - 0.045),
            (0.055, depth * 0.72, 0.075),
            silver_mat,
            collection,
            0.012,
        ))

    for side_x in (-1, 1):
        for side_y in (-1, 1):
            parts.append(cylinder(
                f"{prefix}_Leg_{side_x}_{side_y}",
                leg_radius,
                leg_height,
                (side_x * inset_x, side_y * inset_y, leg_height * 0.5),
                silver_mat,
                collection,
            ))
            parts.append(cylinder(
                f"{prefix}_Foot_{side_x}_{side_y}",
                leg_radius * 1.20,
                0.022,
                (side_x * inset_x, side_y * inset_y, 0.011),
                dark_mat,
                collection,
            ))

    # A subtle central cable cover makes it read as a meeting table.
    cable_width = min(width * 0.18, 0.30)
    parts.append(cube(
        f"{prefix}_CableCover",
        (0.0, 0.0, height + 0.004),
        (cable_width, min(depth * 0.10, 0.075), 0.012),
        silver_mat,
        collection,
        0.006,
    ))

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    hide_hierarchy(source)
    return root


def build():
    sources = find_sources()
    if not sources:
        raise RuntimeError(
            "找不到原始桌子；請確認 Outliner 名稱是 OpenRobotics/RecTable、RecTable_2 等。"
        )

    collection = clear_replacements()
    top_mat = material(
        "MAT_MeetingTable_LightGrayTop",
        (0.56, 0.59, 0.60),
        roughness=0.46,
        metallic=0.08,
    )
    silver_mat = brushed_silver_material()
    dark_mat = material(
        "MAT_MeetingTable_GrayFeet",
        (0.11, 0.13, 0.14),
        roughness=0.62,
        metallic=0.15,
    )

    created = [
        build_table(index, source, collection, top_mat, silver_mat, dark_mat)
        for index, source in enumerate(sources, 1)
    ]

    bpy.ops.object.select_all(action="DESELECT")
    for root in created:
        root.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    print(
        f"完成：隱藏 {len(sources)} 張原始 RecTable，建立 "
        f"{len(created)} 張銀灰色會議桌。"
    )


if __name__ == "__main__":
    build()
