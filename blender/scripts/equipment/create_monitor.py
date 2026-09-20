import bpy


COLLECTION = "MedicalMonitor"


def material(name, color, roughness=0.5, metallic=0.0, emission=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission, 1.0)
        shader.inputs["Emission Strength"].default_value = 0.35
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


def bevel(obj, width=0.02, segments=4):
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


def cylinder(name, radius, depth, location, mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.2, 0.012), 3)
    return obj


def build():
    collection = clean_collection()
    white = material("MAT_Monitor_White", (0.78, 0.82, 0.84), 0.35)
    dark = material("MAT_Monitor_Frame", (0.025, 0.035, 0.045), 0.28, 0.25)
    screen = material(
        "MAT_Monitor_Screen",
        (0.035, 0.16, 0.20),
        0.22,
        emission=(0.02, 0.20, 0.24),
    )
    accent = material("MAT_Monitor_Accent", (0.04, 0.62, 0.58), 0.3)
    button = material("MAT_Monitor_Button", (0.85, 0.18, 0.10), 0.4)

    parts = []
    # Front faces toward negative Y, with the base resting on Z=0.
    parts.append(cube("Monitor_Body", (0, 0, 1.18), (0.82, 0.16, 0.62), dark, collection, 0.045))
    parts.append(cube("Monitor_Screen", (0, -0.087, 1.20), (0.67, 0.018, 0.43), screen, collection, 0.018))
    parts.append(cube("Monitor_ScreenTop", (0, -0.101, 1.405), (0.58, 0.008, 0.012), accent, collection, 0.004))

    for index, x in enumerate((-0.24, -0.08, 0.08, 0.24), 1):
        parts.append(cube(
            f"Monitor_Button_{index}",
            (x, -0.101, 0.91),
            (0.08, 0.025, 0.035),
            button if index == 4 else white,
            collection,
            0.008,
        ))

    parts.append(cylinder("Monitor_Neck", 0.055, 0.28, (0, 0, 0.71), white, collection))
    parts.append(cube("Monitor_Base", (0, 0.01, 0.54), (0.52, 0.34, 0.08), white, collection, 0.035))
    parts.append(cube("Monitor_BaseTrim", (0, -0.17, 0.585), (0.28, 0.025, 0.025), accent, collection, 0.008))

    root = bpy.data.objects.new("Monitor_Root", None)
    root["width_m"] = 0.82
    root["depth_m"] = 0.34
    root["height_m"] = 1.52
    root["design"] = "hospital patient vital signs monitor"
    collection.objects.link(root)

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：MedicalMonitor 醫療監視器")


if __name__ == "__main__":
    build()