import bpy


COLLECTION = "AdjTable"
ROOT_NAME = "AdjTable_Root"


def material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


def clean_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    collection.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def bevel(obj, width=0.02, segments=3):
    modifier = obj.modifiers.new("RoundedEdges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"


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


def cylinder(name, radius, depth, location, mat, collection, vertices=20):
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
    bevel(obj, min(radius * 0.18, 0.012), 2)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def build():
    collection = clean_collection()
    top = material("MAT_AdjTable_Top", (0.78, 0.82, 0.81), 0.36, 0.12)
    edge = material("MAT_AdjTable_Edge", (0.16, 0.20, 0.21), 0.32, 0.48)
    column = material("MAT_AdjTable_Column", (0.46, 0.52, 0.53), 0.25, 0.78)
    wheel = material("MAT_AdjTable_Wheel", (0.025, 0.03, 0.032), 0.68)
    accent = material("MAT_AdjTable_Accent", (0.90, 0.28, 0.08), 0.38, 0.1)

    parts = []

    # Adjustable over-bed table top with a raised safety rim.
    parts.append(cube("AdjTable_Top", (0, 0, 0.91), (0.62, 0.46, 0.07), top, collection, 0.025))
    parts.append(cube("AdjTable_FrontRim", (0, -0.225, 0.96), (0.62, 0.025, 0.06), edge, collection, 0.008))
    parts.append(cube("AdjTable_BackRim", (0, 0.225, 0.96), (0.62, 0.025, 0.06), edge, collection, 0.008))
    parts.append(cube("AdjTable_LeftRim", (-0.30, 0, 0.96), (0.025, 0.43, 0.06), edge, collection, 0.008))
    parts.append(cube("AdjTable_RightRim", (0.30, 0, 0.96), (0.025, 0.43, 0.06), edge, collection, 0.008))

    # Two-piece telescoping column and height adjustment handle.
    parts.append(cylinder("AdjTable_OuterColumn", 0.075, 0.72, (0, 0.08, 0.50), column, collection))
    parts.append(cylinder("AdjTable_InnerColumn", 0.052, 0.30, (0, 0.08, 0.84), edge, collection))
    parts.append(cylinder("AdjTable_AdjustmentKnob", 0.035, 0.07, (0, -0.005, 0.68), accent, collection, 16))

    # Wide weighted base with four casters.
    parts.append(cube("AdjTable_Base", (0, 0.08, 0.12), (0.62, 0.42, 0.14), edge, collection, 0.035))
    for x in (-0.24, 0.24):
        for y in (-0.08, 0.24):
            parts.append(cylinder("AdjTable_Caster", 0.06, 0.045, (x, y, 0.045), wheel, collection))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 0.62
    root["depth_m"] = 0.46
    root["height_m"] = 0.99
    root["model"] = "AdjTable"
    root["description"] = "height-adjustable over-bed table"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：AdjTable 可調式床邊桌")


if __name__ == "__main__":
    build()
