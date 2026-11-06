# Task Dispatch GLB integration

> This records the earlier integration state. For the current page layout and route presentation, see `task-dispatch-revision.md`.

The page loads `/models/L1__flat.glb` (two underscores) with GLTFLoader. The original GLB is unchanged. SHA-256: `6c726e833c6f8e65e40ab625fb427e84837c0ccb5ca744aed4f9ffcdb3af534a`.

The default scene is `L1_Solid_Block_Map_v5`. Original materials, room labels, colored sides and static green lines are retained. Other scenes are previous exports, not additional floors. `Preview_Ground_NOT_FOR_EXPORT.003` is excluded at runtime. Cameras/lights are also filtered defensively; none are present in this export. All parsed scenes, including detached objects and shared resources, are included in disposal.

## Layout

Dashboard's existing stage gradient is shared through `overviewThemeVars['--overview-stage-background']` and applied at AppShell level. Inner stages are transparent, so the Navbar and content have a continuous background. The dispatch renderer uses alpha, transparent clear color and null scene background.

Desktop form width: 368px. Schedule width: 380–420px (about 415px at 1536px). Canvas covers the entire workspace below the 64px Navbar and extends behind both glass panels. Below 1180px, panels and map stack in a scroller below the Navbar. Long panel contents scroll internally. Dispatch reuses FloorSelector with only F1; Dashboard keeps its existing defaults.

## Navigation and calibration

The existing source chain is:

1. Traffic Editor: `ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml`.
2. `scripts/generate-rmf-navigation.sh`: RMF building map generator → `nav_graphs_generated/0.yaml`.
3. `scripts/convert-rmf-navigation.py` → `public/generated/rmf-navigation.json`.
4. Dispatch loads `NAVIGATION_ASSETS.graph0` and retains existing station IDs, directed lanes and `shortestVertexPath`.

No additional navigation JSON is created. Blender green meshes never define navigation topology. Top-surface connectors remain visual geometry; dynamic routes use navigation floor height.

The initial transform reuses `rmfMapTransform`: X offset -19.860754013061523, Z offset -13.426342964172363, scale 1, rotation 0, inverted ROS Y. This is explicitly an **uncalibrated preview**, not a verified match to the redrawn model.

The 校正 panel exposes X/Z translation, uniform scale and rotation, plus blue overlays of existing graph vertices and lanes. Stations, task routes and robot positions share this transform. 儲存校正設定 persists it locally under `hospital-rmf-dispatch-alignment-v1`; 還原初值 restores the old map transform. Saving does not certify alignment or change Traffic Editor/ROS data.

Robot markers use explicit `rmfPosition` when supplied, otherwise the existing named waypoint/current location. Room selection uses explicit room-to-waypoint aliases and requires the waypoint to exist in the graph and be allowed by the form.

## Verification

The existing form payload and `demoFleetStore.createTask`/`moveTasks` calls are preserved. A backend TaskController exists, but this page currently uses the demo store; this change does not establish or claim a live dispatch API connection.

`npm run build` and 8 targeted Vitest tests passed. Tests cover the actual GLB, preview filtering, selectable room/material availability, coordinate conversion/invalid inputs, form payloads, schedule editing state and shared FloorSelector behavior.

Actual screenshots and browser results: `docs/screenshots/dispatch-glb-*`. Browser verification covers zoom buttons, wheel, pan, reset, map selection, calibration/persistence, schedule editing, responsive layout and page remount. Instrumentation confirms that page exit disconnects the Canvas, loses its WebGL context and leaves zero dispatch animation frames.
