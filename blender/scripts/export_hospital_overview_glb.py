"""Export the visible hospital overview scene to a temporary GLB."""

import os
import tempfile

import bpy


scene = bpy.data.scenes.get("Scene")
if scene is None or not scene.objects:
    raise RuntimeError("The Blender file has no non-empty 'Scene' to export.")

bpy.context.window.scene = scene
output_dir = tempfile.mkdtemp(prefix="hospital-overview-export-")
output_path = os.path.join(output_dir, "hospital_overview.glb")
result = bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format="GLB",
    use_selection=False,
    use_visible=True,
    export_cameras=False,
    export_lights=False,
)
if "FINISHED" not in result:
    raise RuntimeError(f"GLB export failed: {result}")

print(f"OVERVIEW_GLB_PATH={output_path}")
