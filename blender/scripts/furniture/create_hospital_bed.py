import math

import bpy


COLLECTION = "HospitalBed"


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
        vertices=24,
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


def torus(name, location, major_radius, minor_radius, mat, collection):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=24,
        minor_segments=10,
        location=location,
        rotation=(math.radians(90), 0, 0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    return obj


def build():
    collection = clean_collection()
    frame = material("MAT_Bed_Frame", (0.72, 0.77, 0.80), 0.32, 0.35)
    mattress = material("MAT_Bed_Mattress", (0.82, 0.88, 0.90), 0.78)
    sheet = material("MAT_Bed_Sheet", (0.22, 0.52, 0.60), 0.70)
    rail = material("MAT_Bed_Rail", (0.12, 0.17, 0.19), 0.34, 0.45)
    wheel = material("MAT_Bed_Wheel", (0.025, 0.03, 0.035), 0.6)

    parts = []
    parts.append(cube("HospitalBed_Frame", (0, 0, 0.43), (2.10, 0.88, 0.18), frame, collection, 0.035))
    parts.append(cube("HospitalBed_Mattress", (0, 0, 0.61), (1.98, 0.78, 0.22), mattress, collection, 0.07))
    parts.append(cube("HospitalBed_Sheet", (0.30, 0, 0.735), (1.30, 0.74, 0.035), sheet, collection, 0.012))
    parts.append(cube("HospitalBed_Pillow", (-0.72, 0, 0.77), (0.34, 0.62, 0.13), mattress, collection, 0.045))

    for end, x in (("Head", -1.03), ("Foot", 1.03)):
        parts.append(cube(f"HospitalBed_{end}Board", (x, 0, 0.86), (0.12, 1.02, 0.72), frame, collection, 0.045))
        for side in (-1, 1):
            parts.append(cylinder(
                f"HospitalBed_{end}Post_{side}",
                0.035,
                0.82,
                (x, side * 0.43, 0.83),
                rail,
                collection,
            ))

    for side in (-1, 1):
        parts.append(cube(
            f"HospitalBed_SideRail_{side}",
            (0.18, side * 0.47, 0.91),
            (1.25, 0.055, 0.12),
            rail,
            collection,
            0.02,
        ))

    for index, x in enumerate((-0.82, 0.82), 1):
        for side in (-1, 1):
            parts.append(cylinder(
                f"HospitalBed_Leg_{index}_{side}",
                0.035,
                0.38,
                (x, side * 0.34, 0.23),
                frame,
                collection,
            ))
            parts.append(torus(
                f"HospitalBed_Caster_{index}_{side}",
                (x, side * 0.34, 0.055),
                0.065,
                0.022,
                wheel,
                collection,
            ))

    root = bpy.data.objects.new("HospitalBed_Root", None)
    root["width_m"] = 1.02
    root["depth_m"] = 2.22
    root["height_m"] = 1.22
    root["design"] = "hospital trolley bed with side rails"
    collection.objects.link(root)

    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：HospitalBed 醫院病床")


if __name__ == "__main__":
    build()