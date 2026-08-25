import bpy
import math
from mathutils import Vector


COLLECTION_NAME = "Reception_Design"
TOTAL_LENGTH = 9.8
TOTAL_DEPTH = 5.908
TOTAL_HEIGHT = 0.126
PANEL_DEPTH = 0.7
CORNER_RADIUS = 0.35
BEVEL = 0.045


def material_wood():
    material = bpy.data.materials.get("Reception_Wood") or bpy.data.materials.new("Reception_Wood")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 18.0
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 4.0
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.08, 0.025, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.62, 0.24, 0.055, 1)
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.38
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.025
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(wave.outputs["Color"], mix.inputs[1])
    links.new(ramp.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    shader.inputs["Roughness"].default_value = 0.48
    return material


def material_stripe(name, color):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*color, 1)
    material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.42
    return material


def collection():
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        bpy.data.collections.remove(old)
    result = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(result)
    return result


def cube(name, location, dimensions, material, target):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Soft_Curved_Edges", "BEVEL")
    bevel.width = BEVEL
    bevel.segments = 5
    bevel.limit_method = "ANGLE"
    obj.data.materials.append(material)
    target.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != target:
            old_collection.objects.unlink(obj)
    return obj


def cylinder(name, location, radius, depth, material, target):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    target.objects.link(obj)
    for old_collection in list(obj.users_collection):
        if old_collection != target:
            old_collection.objects.unlink(obj)
    return obj


def stripe(name, x, material, target):
    return cube(
        name,
        (x, -PANEL_DEPTH / 2 - 0.008, TOTAL_HEIGHT / 2),
        (0.12, 0.016, TOTAL_HEIGHT * 0.76),
        material,
        target,
    )


def build():
    target = collection()
    wood = material_wood()
    light = material_stripe("Reception_Wood_Light", (0.72, 0.34, 0.09))
    dark = material_stripe("Reception_Wood_Dark", (0.18, 0.045, 0.012))

    cube("Reception_Front_Curved_Fascia", (0, 0, TOTAL_HEIGHT / 2), (TOTAL_LENGTH - 0.7, PANEL_DEPTH, TOTAL_HEIGHT), wood, target)
    cube("Reception_Left_Return", (-(TOTAL_LENGTH - 0.7) / 2, TOTAL_DEPTH / 2 - PANEL_DEPTH / 2, TOTAL_HEIGHT / 2), (PANEL_DEPTH, TOTAL_DEPTH - PANEL_DEPTH, TOTAL_HEIGHT), wood, target)
    cube("Reception_Right_Return", ((TOTAL_LENGTH - 0.7) / 2, TOTAL_DEPTH / 2 - PANEL_DEPTH / 2, TOTAL_HEIGHT / 2), (PANEL_DEPTH, TOTAL_DEPTH - PANEL_DEPTH, TOTAL_HEIGHT), wood, target)

    for x in (-4.55, 4.55):
        for y in (0, TOTAL_DEPTH - PANEL_DEPTH):
            cylinder("Reception_Rounded_Corner", (x, y, TOTAL_HEIGHT / 2), CORNER_RADIUS, TOTAL_HEIGHT, wood, target)

    for index, x in enumerate([-(TOTAL_LENGTH - 1.0) / 2 + i * 0.42 for i in range(22)]):
        stripe(f"Reception_Wood_Stripe_{index:02d}", x, light if index % 4 else dark, target)

    root = bpy.data.objects.new("hospital_reception_curved_wood", None)
    root["overall_length_m"] = TOTAL_LENGTH
    root["overall_depth_m"] = TOTAL_DEPTH
    root["overall_height_m"] = TOTAL_HEIGHT
    root["corner_radius_m"] = CORNER_RADIUS
    root["design"] = "curved wood with stripes and mottled procedural grain"
    target.objects.link(root)

    bpy.context.scene["reception_dimensions_m"] = (TOTAL_LENGTH, TOTAL_DEPTH, TOTAL_HEIGHT)
    bpy.context.scene["reception_corner_radius_m"] = CORNER_RADIUS
    bpy.context.view_layer.objects.active = root
    root.select_set(True)


if __name__ == "__main__":
    build()