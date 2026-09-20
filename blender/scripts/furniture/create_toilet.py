import bpy


COLLECTION = "Toilet"
ROOT_NAME = "Toilet_Root"


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


def warm_marble_material():
    """暖米白陶瓷，加入很淡的淺灰石紋。"""
    name = "MAT_Toilet_WarmIvoryMarble"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")

    texcoord.location = (-760, 40)
    mapping.location = (-570, 40)
    noise.location = (-360, 40)
    ramp.location = (-130, 80)
    bump.location = (-120, -150)
    shader.location = (140, 70)
    output.location = (400, 70)

    # 把紋路拉長，形成柔和石紋，不會像髒污斑點。
    mapping.inputs["Scale"].default_value = (0.75, 3.4, 1.15)
    noise.inputs["Scale"].default_value = 2.7
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.62
    noise.inputs["Distortion"].default_value = 0.32

    color_ramp = ramp.color_ramp
    color_ramp.elements.remove(color_ramp.elements[1])
    ivory = color_ramp.elements[0]
    ivory.position = 0.25
    ivory.color = (0.88, 0.84, 0.75, 1.0)

    gray_vein = color_ramp.elements.new(0.50)
    gray_vein.color = (0.60, 0.61, 0.59, 1.0)

    soft_ivory = color_ramp.elements.new(0.62)
    soft_ivory.color = (0.94, 0.91, 0.84, 1.0)

    highlight = color_ramp.elements.new(0.82)
    highlight.color = (0.98, 0.96, 0.91, 1.0)

    shader.inputs["Roughness"].default_value = 0.28
    shader.inputs["Metallic"].default_value = 0.0
    shader.inputs["IOR"].default_value = 1.46

    # 凹凸非常弱，只讓近看時略有材質感。
    bump.inputs["Strength"].default_value = 0.055
    bump.inputs["Distance"].default_value = 0.008

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    mat.diffuse_color = (0.92, 0.89, 0.82, 1.0)
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


def cylinder(name, radius, depth, location, mat, collection, vertices=48):
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
    bevel(obj, min(radius * 0.12, 0.012), 3)
    return obj


def torus(name, major_radius, minor_radius, location, mat, collection):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=48,
        minor_segments=12,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = 0.78
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

    # 主體：暖米白＋淡灰石紋。
    porcelain = warm_marble_material()

    # 座圈比主體稍深，仍屬同一組暖灰米色系。
    seat = basic_material(
        "MAT_Toilet_WarmGreigeSeat",
        (0.62, 0.59, 0.53),
        roughness=0.38,
    )

    # 水面／內部使用柔和霧藍灰，不使用原本接近黑色的顏色。
    interior = basic_material(
        "MAT_Toilet_SoftWater",
        (0.30, 0.43, 0.45),
        roughness=0.30,
    )

    # 按鈕採用香檳銀，配合米白與木色醫院環境。
    metal = basic_material(
        "MAT_Toilet_ChampagneMetal",
        (0.48, 0.45, 0.39),
        roughness=0.26,
        metallic=0.72,
    )

    parts = []

    parts.append(cylinder(
        "Toilet_Bowl", 0.29, 0.30, (0, 0.02, 0.20),
        porcelain, collection, 48,
    ))
    parts.append(cube(
        "Toilet_BowlFront", (0, -0.09, 0.14), (0.48, 0.34, 0.22),
        porcelain, collection, 0.10,
    ))
    parts.append(cylinder(
        "Toilet_WaterOpening", 0.205, 0.012, (0, 0.015, 0.355),
        interior, collection, 48,
    ))
    parts.append(torus(
        "Toilet_SeatRing", 0.235, 0.035, (0, 0.015, 0.375),
        seat, collection,
    ))
    parts.append(cube(
        "Toilet_SeatBack", (0, 0.18, 0.43), (0.42, 0.08, 0.045),
        seat, collection, 0.02,
    ))

    parts.append(cube(
        "Toilet_Tank", (0, 0.22, 0.64), (0.48, 0.22, 0.48),
        porcelain, collection, 0.06,
    ))
    parts.append(cube(
        "Toilet_TankLid", (0, 0.22, 0.895), (0.51, 0.25, 0.055),
        porcelain, collection, 0.025,
    ))
    parts.append(cylinder(
        "Toilet_FlushButton", 0.035, 0.018, (0.12, 0.22, 0.93),
        metal, collection, 24,
    ))
    parts.append(cube(
        "Toilet_Base", (0, 0.05, 0.035), (0.47, 0.42, 0.07),
        porcelain, collection, 0.025,
    ))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 0.70
    root["depth_m"] = 0.65
    root["height_m"] = 0.95
    root["model"] = "Toilet"
    root["description"] = "warm ivory hospital toilet with subtle gray marble texture"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：暖米白淡灰石紋 Toilet")


if __name__ == "__main__":
    build()
