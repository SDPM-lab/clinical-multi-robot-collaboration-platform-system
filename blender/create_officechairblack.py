import math

import bpy


COLLECTION = "OfficeChairBlack"


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


def smooth_bevel(obj, width, segments=4):
    bevel = obj.modifiers.new("RoundedEdges", "BEVEL")
    bevel.width = width
    bevel.segments = segments
    bevel.limit_method = "ANGLE"

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
        smooth_bevel(obj, bevel_width)
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
    smooth_bevel(obj, min(radius * 0.2, 0.015), 3)
    return obj


def torus(name, location, major_radius, minor_radius, rotation, mat, collection):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=32,
        minor_segments=12,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    return obj


def build():
    collection = clean_collection()
    black = material("MAT_OfficeChair_Black", (0.012, 0.014, 0.016), 0.62)
    frame = material("MAT_OfficeChair_BlackMetal", (0.018, 0.022, 0.025), 0.3, 0.65)
    wheel_mat = material("MAT_OfficeChair_Wheels", (0.008, 0.009, 0.010), 0.78)

    parts = []

    # Padded seat and a tall, slightly reclined backrest.
    parts.append(cube("OfficeChairBlack_Seat", (0, 0, 0.53), (0.62, 0.56, 0.13), black, collection, 0.06))
    back = cube("OfficeChairBlack_Backrest", (0, 0.19, 0.91), (0.59, 0.12, 0.68), black, collection, 0.055)
    back.rotation_euler.x = math.radians(-8)
    parts.append(back)

    # Open arm supports and padded arm caps.
    for side in (-1, 1):
        x = side * 0.39
        support = cylinder(
            f"OfficeChairBlack_ArmSupport_{side}",
            0.018,
            0.27,
            (x, 0.02, 0.69),
            frame,
            collection,
        )
        parts.append(support)
        parts.append(cube(
            f"OfficeChairBlack_ArmPad_{side}",
            (x, 0.00, 0.84),
            (0.13, 0.29, 0.055),
            black,
            collection,
            0.025,
        ))

    # Gas lift, height adjustment collar, and five-star base.
    parts.append(cylinder("OfficeChairBlack_GasLift", 0.055, 0.39, (0, 0, 0.29), frame, collection))
    parts.append(cylinder("OfficeChairBlack_HeightCollar", 0.085, 0.045, (0, 0, 0.49), frame, collection))

    for index in range(5):
        angle = index * 2 * math.pi / 5
        x = math.cos(angle) * 0.42
        y = math.sin(angle) * 0.42
        spoke = cube(
            f"OfficeChairBlack_BaseSpoke_{index + 1}",
            (x / 2, y / 2, 0.10),
            (0.84, 0.065, 0.055),
            frame,
            collection,
            0.02,
        )
        spoke.rotation_euler.z = angle
        parts.append(spoke)

        stem = cylinder(
            f"OfficeChairBlack_CasterStem_{index + 1}",
            0.018,
            0.12,
            (x, y, 0.045),
            frame,
            collection,
        )
        parts.append(stem)
        wheel_x = x - math.cos(angle) * 0.025
        wheel_y = y - math.sin(angle) * 0.025
        parts.append(torus(
            f"OfficeChairBlack_Wheel_{index + 1}",
            (wheel_x, wheel_y, 0.015),
            0.065,
            0.022,
            (math.radians(90), angle, 0),
            wheel_mat,
            collection,
        ))

    root = bpy.data.objects.new("OfficeChairBlack_Root", None)
    root["width_m"] = 0.90
    root["depth_m"] = 0.95
    root["height_m"] = 1.28
    root["seat_height_m"] = 0.53
    root["design"] = "black ergonomic office chair"
    collection.objects.link(root)

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：OfficeChairBlack 黑色辦公椅")


if __name__ == "__main__":
    build()