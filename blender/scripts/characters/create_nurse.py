import math

import bpy


COLLECTION = "Nurse"
ROOT_NAME = "Nurse_Root"


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


def cylinder(name, radius, depth, location, mat, collection, rotation=(0, 0, 0), vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.12, 0.008), 2)
    return obj


def sphere(name, location, scale, mat, collection):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
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
    skin = material("MAT_Nurse_Skin", (0.72, 0.43, 0.29), 0.52)
    hair = material("MAT_Nurse_Hair", (0.08, 0.045, 0.025), 0.72)
    uniform = material("MAT_Nurse_Uniform", (0.12, 0.52, 0.50), 0.52)
    white = material("MAT_Nurse_Cap", (0.93, 0.95, 0.92), 0.36)
    shoe = material("MAT_Nurse_Shoe", (0.08, 0.10, 0.10), 0.38)
    badge = material("MAT_Nurse_Badge", (0.88, 0.73, 0.25), 0.3, 0.25)

    parts = []

    parts.append(cylinder("Nurse_LeftShoe", 0.075, 0.20, (-0.045, -0.075, 0.065), shoe, collection, (math.pi / 2, 0, 0)))
    parts.append(cylinder("Nurse_RightShoe", 0.075, 0.20, (0.045, -0.075, 0.065), shoe, collection, (math.pi / 2, 0, 0)))
    parts.append(cylinder("Nurse_LeftLeg", 0.065, 0.48, (-0.045, 0, 0.34), uniform, collection))
    parts.append(cylinder("Nurse_RightLeg", 0.065, 0.48, (0.045, 0, 0.34), uniform, collection))
    parts.append(cube("Nurse_Torso", (0, 0, 0.86), (0.30, 0.20, 0.62), uniform, collection, 0.055))
    parts.append(sphere("Nurse_Head", (0, 0, 1.57), (0.14, 0.12, 0.17), skin, collection))
    parts.append(sphere("Nurse_Hair", (0, 0.025, 1.67), (0.135, 0.11, 0.09), hair, collection))
    parts.append(cube("Nurse_Cap", (0, 0, 1.76), (0.19, 0.16, 0.035), white, collection, 0.018))
    parts.append(cube("Nurse_CapCross", (0, -0.083, 1.765), (0.045, 0.008, 0.045), badge, collection, 0.004))

    for side in (-1, 1):
        y = side * 0.145
        parts.append(cylinder(f"Nurse_Arm_{'L' if side < 0 else 'R'}", 0.052, 0.48, (0, y, 0.90), uniform, collection, (math.pi / 2, 0, 0)))
        parts.append(sphere(f"Nurse_Hand_{'L' if side < 0 else 'R'}", (0, y * 1.55, 0.90), (0.06, 0.06, 0.07), skin, collection))

    parts.append(cube("Nurse_Collar", (0, -0.108, 1.13), (0.12, 0.012, 0.10), white, collection, 0.008))
    parts.append(cube("Nurse_Badge", (0, -0.118, 1.00), (0.075, 0.012, 0.055), badge, collection, 0.006))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 0.60
    root["depth_m"] = 0.45
    root["height_m"] = 1.80
    root["model"] = "Nurse"
    root["description"] = "standing hospital nurse in teal uniform"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：Nurse 醫院護理師")


if __name__ == "__main__":
    build()