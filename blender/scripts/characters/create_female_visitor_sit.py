import math

import bpy


COLLECTION = "FemaleVisitorSit"
ROOT_NAME = "FemaleVisitorSit_Root"


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


def bevel(obj, width=0.01, segments=3):
    modifier = obj.modifiers.new("RoundedEdges", "BEVEL")
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


def cylinder(name, radius, depth, location, mat, collection, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.12, 0.008), 2)
    return obj


def sphere(name, location, scale, mat, collection):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to(obj, collection)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def build():
    collection = clean_collection()
    skin = material("MAT_FemaleVisitor_Skin", (0.72, 0.43, 0.29), 0.52)
    hair = material("MAT_FemaleVisitor_Hair", (0.09, 0.035, 0.018), 0.72)
    top = material("MAT_FemaleVisitor_Top", (0.76, 0.22, 0.18), 0.52)
    skirt = material("MAT_FemaleVisitor_Skirt", (0.12, 0.18, 0.28), 0.58)
    shoe = material("MAT_FemaleVisitor_Shoe", (0.06, 0.07, 0.08), 0.38)
    chair = material("MAT_FemaleVisitor_Chair", (0.26, 0.30, 0.31), 0.45, 0.18)
    bag = material("MAT_FemaleVisitor_Bag", (0.30, 0.10, 0.055), 0.38)

    parts = []

    # Simple waiting-room chair.
    parts.append(cube("FemaleVisitorSit_ChairSeat", (0, 0, 0.48), (0.48, 0.46, 0.08), chair, collection, 0.025))
    parts.append(cube("FemaleVisitorSit_ChairBack", (0, 0.18, 0.82), (0.48, 0.08, 0.62), chair, collection, 0.03))
    for x in (-0.18, 0.18):
        for y in (-0.15, 0.15):
            parts.append(cylinder("FemaleVisitorSit_ChairLeg", 0.025, 0.48, (x, y, 0.24), chair, collection))

    # Seated pose: thighs point forward and lower legs descend to the floor.
    parts.append(cylinder("FemaleVisitorSit_LeftThigh", 0.075, 0.32, (-0.085, -0.13, 0.40), skirt, collection, (math.pi / 2, 0, 0)))
    parts.append(cylinder("FemaleVisitorSit_RightThigh", 0.075, 0.32, (0.085, -0.13, 0.40), skirt, collection, (math.pi / 2, 0, 0)))
    parts.append(cylinder("FemaleVisitorSit_LeftLowerLeg", 0.05, 0.34, (-0.085, -0.29, 0.22), skin, collection))
    parts.append(cylinder("FemaleVisitorSit_RightLowerLeg", 0.05, 0.34, (0.085, -0.29, 0.22), skin, collection))
    parts.append(cylinder("FemaleVisitorSit_LeftShoe", 0.06, 0.18, (-0.085, -0.37, 0.06), shoe, collection, (math.pi / 2, 0, 0)))
    parts.append(cylinder("FemaleVisitorSit_RightShoe", 0.06, 0.18, (0.085, -0.37, 0.06), shoe, collection, (math.pi / 2, 0, 0)))
    parts.append(cube("FemaleVisitorSit_Torso", (0, 0.02, 0.91), (0.30, 0.22, 0.55), top, collection, 0.05))
    parts.append(sphere("FemaleVisitorSit_Head", (0, 0.01, 1.48), (0.135, 0.12, 0.16), skin, collection))
    parts.append(sphere("FemaleVisitorSit_Hair", (0, 0.05, 1.56), (0.14, 0.12, 0.16), hair, collection))

    for side in (-1, 1):
        parts.append(cylinder(f"FemaleVisitorSit_Arm_{side}", 0.045, 0.34, (side * 0.17, -0.06, 0.88), top, collection, (0, math.pi / 2, 0)))
        parts.append(sphere(f"FemaleVisitorSit_Hand_{side}", (side * 0.17, -0.23, 0.78), (0.055, 0.055, 0.065), skin, collection))

    parts.append(cube("FemaleVisitorSit_Handbag", (-0.22, -0.18, 0.59), (0.16, 0.07, 0.18), bag, collection, 0.025))
    parts.append(cylinder("FemaleVisitorSit_BagHandle", 0.012, 0.18, (-0.22, -0.18, 0.72), bag, collection, (0, math.pi / 2, 0)))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 0.65
    root["depth_m"] = 0.65
    root["height_m"] = 1.55
    root["model"] = "FemaleVisitorSit"
    root["description"] = "seated female hospital visitor with handbag"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：FemaleVisitorSit 坐姿女性訪客")


if __name__ == "__main__":
    build()