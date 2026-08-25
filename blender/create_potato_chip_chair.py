import bpy
import math
from mathutils import Vector


COLLECTION = "Potato_Chip_Chair"


def mat(name, color, roughness=0.45, metallic=0.0):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    return material


def clean_collection():
    old = bpy.data.collections.get(COLLECTION)

    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        bpy.data.collections.remove(old)

    new_collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(new_collection)

    return new_collection

def move_to(obj, collection):
    collection.objects.link(obj)
    for old in list(obj.users_collection):
        if old != collection:
            old.objects.unlink(obj)


def bevel(obj, width=0.025, segments=4):
    modifier = obj.modifiers.new("Soft_edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()


def seat(collection, wood, suffix=""):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, location=(0, 0, 0.48))
    obj = bpy.context.object
    obj.name = f"PotatoChip_Seat{suffix}"
    obj.scale = (0.34, 0.31, 0.075)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(wood)
    move_to(obj, collection)
    return obj


def back(collection, wood, suffix=""):
    # Curved shell: a shallow arc in plan and a gentle lean in elevation.
    vertices = []
    faces = []
    columns = 25
    rows = 9
    for row in range(rows):
        height = row / (rows - 1)
        z = 0.55 + height * 0.50
        half_width = 0.30 - 0.035 * height
        for column in range(columns):
            across = column / (columns - 1) * 2 - 1
            curve = math.sqrt(max(0.0, 1.0 - across * across))
            x = across * half_width
            y = 0.12 + 0.095 * curve + 0.045 * height
            vertices.append((x, y, z))
    for row in range(rows - 1):
        for column in range(columns - 1):
            a = row * columns + column
            faces.append((a, a + 1, a + columns + 1, a + columns))
    mesh = bpy.data.meshes.new("PotatoChip_Back_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"PotatoChip_Curved_Back{suffix}", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(wood)
    solidify = obj.modifiers.new("Back_thickness", "SOLIDIFY")
    solidify.thickness = 0.035
    bevel(obj, 0.018, 3)
    return obj


def cylinder(name, radius, depth, location, material, collection, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.18, 0.018), 3)
    return obj


def build_chair(collection, shell_material, base_material, index):
    suffix = f"_{index}"
    chair_parts = []

    chair_parts.append(seat(collection, shell_material, suffix))
    chair_parts.append(back(collection, shell_material, suffix))
    chair_parts.append(
        cylinder(
            f"PotatoChip_Central_Pillar{suffix}",
            0.055,
            0.36,
            (0, 0, 0.27),
            base_material,
            collection
        )
    )
    chair_parts.append(
        cylinder(
            f"PotatoChip_Round_Base{suffix}",
            0.24,
            0.035,
            (0, 0, 0.075),
            base_material,
            collection
        )
    )

    root = bpy.data.objects.new(f"PotatoChipChair_Root{suffix}", None)
    root["width_m"] = 0.68
    root["depth_m"] = 0.52
    root["height_m"] = 1.05
    root["seat_height_m"] = 0.48
    root["back_curve_radius_m"] = 0.095
    root["design"] = "warm sand curved shell chair"
    collection.objects.link(root)

    for obj in chair_parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    return root


def build():
    collection = clean_collection()

    # 暖米沙色椅面，搭配櫃台與牆壁
    shell_material = mat(
        "MAT_PotatoChair_WarmSand",
        (0.72, 0.62, 0.49),
        roughness=0.58,
        metallic=0.0
    )

    # 低彩度香檳金屬底座
    base_material = mat(
        "MAT_PotatoChair_ChampagneBase",
        (0.26, 0.20, 0.15),
        roughness=0.38,
        metallic=0.55
    )

    chair_roots = []
    for index, location in enumerate(((-0.78, 0, 0), (0, 0, 0), (0.78, 0, 0)), 1):
        root = build_chair(collection, shell_material, base_material, index)
        root.location = location
        chair_roots.append(root)

    group_root = bpy.data.objects.new("PotatoChipChair_Triple_Root", None)
    collection.objects.link(group_root)
    for root in chair_roots:
        root.parent = group_root

    bpy.ops.object.select_all(action="DESELECT")
    group_root.select_set(True)
    bpy.context.view_layer.objects.active = group_root

    print("完成：三張暖米沙色 Potato Chip Chair 組合")


if __name__ == "__main__":
    build()