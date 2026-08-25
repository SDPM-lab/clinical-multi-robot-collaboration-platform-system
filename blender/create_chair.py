import bpy


COLLECTION = "Chair"


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


def material_orange_fabric():
    """飽和橘色沙發布料"""

    name = "MAT_Chair_SaturatedOrange"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    bump = nodes.new("ShaderNodeBump")

    # 飽和橘色
    shader.inputs["Base Color"].default_value = (
        0.95,
        0.17,
        0.025,
        1
    )

    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Metallic"].default_value = 0.0

    # 細微布料表面
    noise.inputs["Scale"].default_value = 95.0
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.70

    bump.inputs["Strength"].default_value = 0.065
    bump.inputs["Distance"].default_value = 0.0035

    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    material.diffuse_color = (0.95, 0.17, 0.025, 1)

    return material


def material_black_legs():
    """霧面深色椅腳"""

    name = "MAT_Chair_MatteBlack"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.025, 0.022, 0.020, 1)
    bsdf.inputs["Roughness"].default_value = 0.42
    bsdf.inputs["Metallic"].default_value = 0.18

    material.diffuse_color = (0.025, 0.022, 0.020, 1)

    return material


def add_bevel(obj, width, segments=8):
    modifier = obj.modifiers.new("Soft_Rounded_Edges", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()


def cube(
    name,
    location,
    scale,
    material,
    collection,
    bevel_width
):
    bpy.ops.mesh.primitive_cube_add(location=location)

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    obj.data.materials.append(material)
    move_to(obj, collection)
    add_bevel(obj, bevel_width, 8)

    return obj


def build():
    collection = clean_collection()

    orange = material_orange_fabric()
    black = material_black_legs()

    parts = []

    # 下方包覆式椅身
    parts.append(
        cube(
            "TubChair_LowerBody",
            (0, 0.00, 0.35),
            (0.42, 0.34, 0.29),
            orange,
            collection,
            0.14
        )
    )

    # 圓潤高椅背
    parts.append(
        cube(
            "TubChair_RoundedBack",
            (0, 0.23, 0.69),
            (0.41, 0.12, 0.34),
            orange,
            collection,
            0.18
        )
    )

    # 左右包覆扶手
    for side in (-1, 1):
        arm = cube(
            f"TubChair_Arm_{side}",
            (side * 0.355, -0.015, 0.59),
            (0.095, 0.33, 0.29),
            orange,
            collection,
            0.085
        )

        # 讓扶手稍微向內包覆
        arm.rotation_euler.z = side * 0.035
        parts.append(arm)

    # 內側靠背軟墊
    parts.append(
        cube(
            "TubChair_InnerBackCushion",
            (0, 0.105, 0.69),
            (0.305, 0.075, 0.225),
            orange,
            collection,
            0.11
        )
    )

    # 獨立坐墊
    parts.append(
        cube(
            "TubChair_SeatCushion",
            (0, -0.105, 0.49),
            (0.305, 0.265, 0.075),
            orange,
            collection,
            0.07
        )
    )

    # 四支短黑色椅腳
    for side in (-1, 1):
        for front_back in (-1, 1):
            leg = cube(
                f"TubChair_Leg_{side}_{front_back}",
                (
                    side * 0.30,
                    front_back * 0.225,
                    0.10
                ),
                (0.042, 0.042, 0.10),
                black,
                collection,
                0.012
            )

            # 前後腳稍微向外張
            leg.rotation_euler.y = side * 0.045
            parts.append(leg)

    # 整張椅子的控制 Root
    root = bpy.data.objects.new("Chair_Root", None)

    root["width_m"] = 0.84
    root["depth_m"] = 0.76
    root["height_m"] = 1.03
    root["seat_height_m"] = 0.49
    root["design"] = "saturated orange upholstered tub chair"

    collection.objects.link(root)

    # 全部零件成為 Root 子物件
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root

    print("完成：飽和橘色包覆式單人沙發椅")


if __name__ == "__main__":
    build()