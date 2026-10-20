# Overview / Live Map visual revision

- Completion panel: top-to-bottom yellow alpha 0.08 → 0.22 → 0.38, blur 2px, radius 4px.
- Floor controls: row above panel, 12px gap. Expand control: 13px from right edge.
- Only CTX_Building_White / Light / Mid and CTX_Roof receive pale colors and neutral emissive fill. Global lights, exposure, hospital materials, and camera presets were not changed in this revision.
- Each floor chart has its own robot legend. Robot/network status remains unavailable: no verified live transport or health source exists in the current integration.
- Calendar scrollbar uses orange theme; date arrows have no default frame/background.
- Live Map task label underlines removed; route geometry unchanged.

Validation: 39 test files, 137 tests passed; production build passed (bundle-size advisory remains). Browser verified all three floor selections, completion fullscreen, three legends, unknown status copy, no horizontal overflow, no label underlines, and no page errors.

Screenshots: revision-overview-1536x864.png uses the existing default camera in a fresh browser, which is a close-up rather than the user's saved city view. revision-overview-city-inspection.png is a supplementary material inspection using existing debug camera controls in an isolated temporary browser; it does not change project presets. revision-live-map-1536x864.png shows the existing map camera.
