import bpy


COLLECTION = "BedsideTable"
ROOT_NAME = "BedsideTable_Root"


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


def cylinder(name, radius, depth, location, mat, collection, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
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
    cabinet = material("MAT_Bedside_Cabinet", (0.70, 0.76, 0.77), 0.42, 0.12)
    front = material("MAT_Bedside_Front", (0.82, 0.86, 0.85), 0.38, 0.08)
    dark = material("MAT_Bedside_Handle", (0.06, 0.08, 0.085), 0.28, 0.55)
    metal = material("MAT_Bedside_Metal", (0.42, 0.48, 0.49), 0.24, 0.78)
    rubber = material("MAT_Bedside_Rubber", (0.025, 0.03, 0.032), 0.68)

    parts = []

    # Main cabinet: 0.55 m wide, 0.48 m deep, 0.72 m tall.
    parts.append(cube("BedsideTable_Cabinet", (0, 0, 0.43), (0.55, 0.48, 0.72), cabinet, collection, 0.035))
    parts.append(cube("BedsideTable_Top", (0, 0, 0.82), (0.59, 0.52, 0.08), front, collection, 0.025))
    parts.append(cube("BedsideTable_Base", (0, 0, 0.065), (0.57, 0.50, 0.09), dark, collection, 0.02))

    # Upper drawer and lower cabinet door.
    parts.append(cube("BedsideTable_Drawer", (0, -0.252, 0.64), (0.46, 0.035, 0.16), front, collection, 0.012))
    parts.append(cube("BedsideTable_Door", (0, -0.253, 0.33), (0.46, 0.035, 0.36), front, collection, 0.012))
    parts.append(cylinder("BedsideTable_DrawerHandle", 0.014, 0.16, (0, -0.285, 0.64), dark, collection, (0, 1.5708, 0)))
    parts.append(cylinder("BedsideTable_DoorHandle", 0.014, 0.16, (0.15, -0.286, 0.34), dark, collection, (0, 1.5708, 0)))

    # Thin side bumper strips and four small feet.
    for x in (-0.285, 0.285):
        parts.append(cube("BedsideTable_SideBumper", (x, 0, 0.84), (0.025, 0.50, 0.07), dark, collection, 0.008))
    for x in (-0.22, 0.22):
        for y in (-0.18, 0.18):
            parts.append(cylinder("BedsideTable_Foot", 0.035, 0.07, (x, y, 0.0), rubber, collection))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 0.59
    root["depth_m"] = 0.52
    root["height_m"] = 0.90
    root["model"] = "BedsideTable"
    root["description"] = "hospital bedside cabinet with drawer and door"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：BedsideTable 醫院床邊櫃")


if __name__ == "__main__":
    build()
