"""Export the visible Hospital L1 Blender scene for the frontend pipeline."""

from pathlib import Path

import bpy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "public" / "models" / "hospital_L1.glb"


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    result = bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_PATH),
        export_format="GLB",
        use_selection=False,
        use_visible=True,
        export_cameras=False,
        export_lights=False,
    )

    if "FINISHED" not in result:
        raise RuntimeError(f"Blender GLB export failed: {result}")

    print(f"Exported visible Hospital L1 scene to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
