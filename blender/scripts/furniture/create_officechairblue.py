import bpy


BLUE_KEY = "officechairblue"
BLACK_KEY = "officechairblack"
TARGET_COLLECTION = "OfficeChairBlue_Replacement"


def material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    mat.diffuse_color = (*color, 1.0)
    return mat


def find_objects(key):
    result = []
    for obj in bpy.data.objects:
        name = obj.name.casefold()
        if key in name and "proxy" not in name and "replacement" not in name:
            result.append(obj)
    return sorted(result, key=lambda obj: obj.name.casefold())


def clear_replacements():
    old = bpy.data.collections.get(TARGET_COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)


def main():
    blue_chairs = find_objects(BLUE_KEY)
    black_chairs = [obj for obj in find_objects(BLACK_KEY) if obj.type == "MESH"]
    if not blue_chairs:
        raise RuntimeError("找不到 OfficeChairBlue；請確認 Outliner 名稱包含 OfficeChairBlue。")
    if not black_chairs:
        raise RuntimeError("找不到 OfficeChairBlack；請確認原型椅仍存在。")

    clear_replacements()
    target = bpy.data.collections.new(TARGET_COLLECTION)
    bpy.context.scene.collection.children.link(target)

    navy = material("MAT_OfficeChairBlue_Replacement_Navy", (0.035, 0.085, 0.15), 0.68)
    coffee = material("MAT_OfficeChairBlue_Replacement_Coffee", (0.16, 0.075, 0.035), 0.48, 0.12)
    black = material("MAT_OfficeChairBlue_Replacement_Black", (0.018, 0.020, 0.022), 0.58, 0.12)

    template = black_chairs[0]
    created = []
    for index, blue in enumerate(blue_chairs, 1):
        copy = template.copy()
        copy.data = template.data.copy()
        copy.name = f"OfficeChairBlue_Replacement_{index:02d}"
        target.objects.link(copy)
        # 完全使用 OfficeChairBlue 原本的世界座標、旋轉與縮放。
        copy.matrix_world = blue.matrix_world.copy()
        copy.data.materials.clear()
        lower = copy.name.casefold()
        # Black 原型通常是單一網格，因此預設椅面使用藏青。
        copy.data.materials.append(navy)
        created.append(copy)

        # 保留原始模型但在視窗與算繪中隱藏。
        blue.hide_set(True)
        blue.hide_viewport = True
        blue.hide_render = True

    bpy.ops.object.select_all(action="DESELECT")
    for obj in created:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = created[0]
    print(f"完成：隱藏 {len(blue_chairs)} 個 OfficeChairBlue，建立 {len(created)} 個替代模型")


if __name__ == "__main__":
    main()
