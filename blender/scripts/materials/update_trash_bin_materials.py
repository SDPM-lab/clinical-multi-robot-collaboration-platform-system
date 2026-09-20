"""Update materials on the existing TrashBin models in the open scene."""

import bpy


def set_color(material_name, color, roughness):
    changed = 0

    for material in bpy.data.materials:
        if not material.name.startswith(material_name):
            continue

        material.diffuse_color = (*color, 1.0)

        if material.use_nodes:
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (*color, 1.0)
                bsdf.inputs["Roughness"].default_value = roughness
                bsdf.inputs["Metallic"].default_value = 0.0

        changed += 1

    print(f"{material_name}：修改 {changed} 個材質")


def main():
    # 主體：淺木質灰
    set_color("MAT_TrashBin_VeryLightWoodGray", (0.46, 0.42, 0.36), 0.62)

    # 前面板：稍微淺一點，和主體有層次
    set_color("MAT_TrashBin_LightFront", (0.58, 0.54, 0.47), 0.58)

    # 掀蓋：中度灰褐色
    set_color("MAT_TrashBin_LightLid", (0.30, 0.27, 0.23), 0.55)

    # 內部維持深灰，但不要純黑
    set_color("MAT_TrashBin_SoftDarkInterior", (0.075, 0.070, 0.065), 0.68)

    # 踏板與轉軸：深咖啡灰
    set_color("MAT_TrashBin_WarmGrayMetal", (0.16, 0.14, 0.12), 0.42)
    print("完成：垃圾桶已改成淺木質灰色系")


if __name__ == "__main__":
    main()
