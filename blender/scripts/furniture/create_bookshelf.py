import bpy


COLLECTION = "Bookshelf"
ROOT_NAME = "Bookshelf_Root"


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


def parent_parts(root, parts):
    for obj in parts:
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix


def build():
    collection = clean_collection()
    wood = material("MAT_Bookshelf_Wood", (0.30, 0.16, 0.075), 0.46)
    shelf = material("MAT_Bookshelf_Shelf", (0.42, 0.24, 0.11), 0.42)
    book_colors = (
        (0.12, 0.35, 0.52),
        (0.68, 0.20, 0.10),
        (0.22, 0.48, 0.26),
        (0.70, 0.53, 0.12),
    )
    books = [material(f"MAT_Bookshelf_Book_{i}", color, 0.58) for i, color in enumerate(book_colors, 1)]

    parts = []
    parts.append(cube("Bookshelf_Back", (0, 0.01, 0.86), (1.26, 0.014, 1.68), wood, collection, 0.012))
    parts.append(cube("Bookshelf_LeftSide", (0.63, -0.27, 0.86), (0.028, 0.56, 1.68), wood, collection, 0.012))
    parts.append(cube("Bookshelf_RightSide", (-0.63, -0.27, 0.86), (0.028, 0.56, 1.68), wood, collection, 0.012))
    parts.append(cube("Bookshelf_Bottom", (0, -0.27, 0.042), (1.232, 0.56, 0.084), shelf, collection, 0.014))
    parts.append(cube("Bookshelf_Top", (0, -0.27, 1.666), (1.232, 0.56, 0.028), shelf, collection, 0.008))

    shelf_heights = (0.32, 0.60, 0.88, 1.16, 1.44)
    for index, z in enumerate(shelf_heights, 1):
        parts.append(cube(f"Bookshelf_Shelf_{index}", (0, -0.27, z), (1.232, 0.56, 0.028), shelf, collection, 0.008))

    # A few upright books make the shelf readable without overcrowding it.
    for shelf_index, z in enumerate((0.18, 0.46, 0.74, 1.02, 1.30)):
        for book_index in range(5):
            width = 0.055 + (book_index % 2) * 0.012
            x = -0.48 + book_index * 0.075
            parts.append(cube(
                f"Bookshelf_Book_{shelf_index + 1}_{book_index + 1}",
                (x, -0.305, z),
                (width, 0.13, 0.20),
                books[(shelf_index + book_index) % len(books)],
                collection,
                0.006,
            ))

    root = bpy.data.objects.new(ROOT_NAME, None)
    root["width_m"] = 1.26
    root["depth_m"] = 0.58
    root["height_m"] = 1.70
    root["model"] = "Bookshelf"
    root["description"] = "five-shelf wooden hospital bookshelf"
    collection.objects.link(root)
    parent_parts(root, parts)

    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    print("完成：Bookshelf 五層書架")


if __name__ == "__main__":
    build()