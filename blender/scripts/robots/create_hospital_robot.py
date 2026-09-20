import math

import bpy


COLLECTION = "HospitalRobot"


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


def bevel(obj, width, segments=3):
    modifier = obj.modifiers.new("RoundedEdges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"

    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def cube(name, location, dimensions, mat, collection, bevel_width=0.0):
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


def cylinder(name, radius, depth, location, mat, collection, vertices=32, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation or (0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.12, 0.006), 3)
    return obj


def torus(name, location, major_radius, minor_radius, mat, collection, rotation=None):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=32,
        minor_segments=12,
        location=location,
        rotation=rotation or (0, 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    return obj


def build():
    collection = clean_collection()
    blue = material("MAT_HospitalRobot_Blue", (0.015, 0.12, 0.72), 0.34, 0.12)
    dark_blue = material("MAT_HospitalRobot_DarkBlue", (0.008, 0.025, 0.12), 0.28, 0.2)
    red = material("MAT_HospitalRobot_Wheels", (0.72, 0.025, 0.02), 0.48, 0.05)
    black = material("MAT_HospitalRobot_Sensor", (0.008, 0.01, 0.014), 0.2, 0.35)
    white = material("MAT_HospitalRobot_Light", (0.8, 0.92, 1.0), 0.2, 0.0)

    parts = []
    parts.append(cube("HospitalRobot_Body", (0, 0, 0.13), (0.34, 0.28, 0.18), blue, collection, 0.045))
    parts.append(cube("HospitalRobot_Top", (0, 0, 0.245), (0.28, 0.23, 0.055), dark_blue, collection, 0.018))
    parts.append(cube("HospitalRobot_FrontPanel", (0.176, 0, 0.15), (0.012, 0.20, 0.09), blue, collection, 0.004))

    for side in (-1, 1):
        y = side * 0.145
        parts.append(cylinder(
            f"HospitalRobot_Wheel_{'Left' if side < 0 else 'Right'}",
            0.06,
            0.025,
            (0, y, 0.065),
            red,
            collection,
            rotation=(math.radians(90), 0, 0),
        ))
        parts.append(cylinder(
            f"HospitalRobot_WheelHub_{'Left' if side < 0 else 'Right'}",
            0.022,
            0.028,
            (0, y + side * 0.014, 0.065),
            black,
            collection,
            rotation=(math.radians(90), 0, 0),
        ))

    parts.append(cylinder("HospitalRobot_LidarMount", 0.025, 0.045, (0, 0, 0.30), black, collection))
    parts.append(torus("HospitalRobot_Lidar", (0, 0, 0.335), 0.045, 0.012, black, collection))
    parts.append(cylinder("HospitalRobot_LidarCap", 0.034, 0.018, (0, 0, 0.345), black, collection))

    for side in (-1, 1):
        x = 0.181
        y = side * 0.075
        parts.append(cylinder(
            f"HospitalRobot_FrontLight_{side}",
            0.014,
            0.006,
            (x, y, 0.16),
            white,
            collection,
            rotation=(0, math.radians(90), 0),
        ))

    root = bpy.data.objects.new("HospitalRobot_Root", None)
    root["width_m"] = 0.39
    root["length_m"] = 0.39
    root["height_m"] = 0.36
    root["drive_type"] = "differential drive"
    root["sensors"] = "LiDAR, IMU"
    root["design"] = "blue hospital delivery robot"
    collection.objects.link(root)

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：HospitalRobot 藍色醫院配送機器人")


if __name__ == "__main__":
    build()
