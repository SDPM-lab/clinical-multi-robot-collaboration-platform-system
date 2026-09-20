import math

import bpy


COLLECTION = "HospitalWardrobe"
ROOT_NAME = "HospitalWardrobe_Root"


def basic_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    mat.diffuse_color = (*color, 1.0)
    return mat


def wood_material(name, dark_color, light_color, grain_scale=7.0):
    """不規則直向木紋；色差刻意控制得柔和，避免像虎斑紋。"""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    wave = nodes.new("ShaderNodeTexWave")
    noise = nodes.new("ShaderNodeTexNoise")
    mix = nodes.new("ShaderNodeMixRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    texcoord.location = (-900, 70)
    mapping.location = (-720, 70)
    wave.location = (-520, 150)
    noise.location = (-520, -80)
    mix.location = (-290, 70)
    ramp.location = (-80, 100)
    bump.location = (-70, -130)
    shader.location = (180, 80)
    output.location = (430, 80)

    # 衣櫃正面朝 +X，Y 是門板橫向，因此沿 Y 變化會形成直向木紋。
    mapping.inputs["Scale"].default_value = (1.0, 1.15, 0.78)
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = grain_scale
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 4.0
    wave.inputs["Detail Scale"].default_value = 1.8

    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.68
    noise.inputs["Distortion"].default_value = 0.28

    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.68

    ramp.color_ramp.elements[0].position = 0.24
    ramp.color_ramp.elements[0].color = (*dark_color, 1.0)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (*light_color, 1.0)

    shader.inputs["Roughness"].default_value = 0.48
    shader.inputs["Metallic"].default_value = 0.0

    bump.inputs["Strength"].default_value = 0.085
    bump.inputs["Distance"].default_value = 0.012

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(wave.outputs["Color"], mix.inputs[1])
    links.new(noise.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(mix.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    mat.diffuse_color = (*light_color, 1.0)
    return mat


def clean_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to(obj, collection):
    if collection not in obj.users_collection:
        collection.objects.link(obj)

    for old_collection in list(obj.users_collection):
        if old_collection != collection:
            old_collection.objects.unlink(obj)


def bevel(obj, width=0.01, segments=4):
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
        vertices=32,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    move_to(obj, collection)
    bevel(obj, min(radius * 0.15, 0.006), 3)
    return obj


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def build():
    collection = clean_collection()

    # 櫃體較深、門板較亮，保持同一組暖咖啡木色。
    cabinet = wood_material(
        "MAT_Wardrobe_CoffeeWood",
        dark_color=(0.105, 0.036, 0.012),
        light_color=(0.35, 0.145, 0.047),
        grain_scale=6.0,
    )
    door = wood_material(
        "MAT_Wardrobe_WarmWalnutDoor",
        dark_color=(0.19, 0.065, 0.018),
        light_color=(0.62, 0.31, 0.105),
        grain_scale=8.5,
    )
    frame = basic_material(
        "MAT_Wardrobe_DarkCoffeeFrame",
        (0.12, 0.052, 0.025),
        roughness=0.44,
        metallic=0.0,
    )
    handle = basic_material(
        "MAT_Wardrobe_ChampagneHandle",
        (0.44, 0.36, 0.25),
        roughness=0.27,
        metallic=0.72,
    )

    parts = []

    # Gazebo 模型使用 +X 作為正面，Z=0 為地板。
    parts.append(cube(
        "Wardrobe_Cabinet",
        (0, 0, 1.0),
        (0.55, 1.40, 2.0),
        cabinet,
        collection,
        0.035,
    ))
    parts.append(cube(
        "Wardrobe_Top",
        (0, 0, 2.015),
        (0.62, 1.46, 0.05),
        frame,
        collection,
        0.018,
    ))
    parts.append(cube(
        "Wardrobe_Base",
        (0, 0, 0.025),
        (0.62, 1.46, 0.05),
        frame,
        collection,
        0.018,
    ))

    for index, y in enumerate((0.3525, -0.3525), start=1):
        parts.append(cube(
            f"Wardrobe_Door_{index}",
            (0.281, y, 1.0),
            (0.018, 0.685, 1.90),
            door,
            collection,
            0.012,
        ))
        parts.append(cylinder(
            f"Wardrobe_Handle_{index}",
            0.018,
            0.045,
            (0.311, y / 4.7, 1.0),
            handle,
            collection,
            rotation=(0, math.pi / 2, 0),
        ))

    parts.append(cube(
        "Wardrobe_CenterSeam",
        (0.295, 0, 1.0),
        (0.012, 0.018, 1.90),
        frame,
        collection,
        0.003,
    ))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 1.46
    root["depth_m"] = 0.62
    root["height_m"] = 2.04
    root["model"] = "hospital_wardrobe"
    root["description"] = "warm coffee and walnut two-door hospital wardrobe"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：暖咖啡胡桃木紋 HospitalWardrobe")


if __name__ == "__main__":
    build()
