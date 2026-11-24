# MediSync Live Map V3.2

1920 × 1080, 30 fps, 600 frames. Studio composition `LiveMapPhaseV3-2`.

| Frames, inclusive | Time | Picture |
|---|---|---|
| 0–59 | 00–02 s | T0002 and M01 assignment handoff |
| 60–149 | 02–05 s | Live task and route progress |
| 150–239 | 05–08 s | Follow M01 |
| 240–299 | 08–10 s | Third Person |
| 300–359 | 10–12 s | First Person |
| 360–419 | 12–14 s | Local Follow |
| 420–444 | 14–14.83 s | Captured camera returns to the fleet overview |
| 445–539 | 14.83–18 s | Reveal the three routes in sequence and show all seven robots |
| 540–599 | 18–20 s | Hold the final map, labels and route legend |

The camera mode cuts retain the V3.1 source indices, allowing six seconds across all three views. Selector travel begins at frames 288 and 348, the outgoing and incoming moving shots meet at frames 300 and 360, and the short focus brackets clear by frames 312 and 372. Identical light cues begin at frames 289 and 349. An existing fleet camera take handles the pullback. At frame 540 the final captured fleet image and data are held through the end. The finale narration was shortened to “一張地圖，掌握整個車隊的多項作業。” to fit the read at its recorded speed.

V3.1 temporarily covered live capture with an outgoing JPEG at each mode change. That left part of the picture motionless as the wipe moved across it. V3.2 keeps both native shots playing up to their shared cut and uses M01’s tracked position and heading to carry the viewer between angles. The switch itself uses the captured camera states, avoiding interpolating through the building. The selector sits in the header above the map, with equal-width, single-line segments.

## Shotcraft

- `segmented-thumb-hero` informs the selection and landing beat. The orange thumb travels for 11 frames and the next view takes over on the following frame.
- `shot-transitions` informs the focus handoff at each cut. Short inset corner marks align the viewer’s attention over the moving capture.
- `space-camera-moves` informs the spatial pullback and settling beat in the existing 3D overview footage.
- `line-carry-transition` informs the sequential reveal of the existing route paths, with each line tied to its fleet label.

## Fleet data

The same isolated capture and route data underpin the map, route overlays and vehicle states.

| ID | Final state | Route |
|---|---|---|
| M01 | Arrived | Pharmacy → Ward A, medication delivery (T0002) |
| M02 | En route | Blood Draw → Laboratory, specimen delivery |
| C01 | En route | Ward B → Waste Return, waste transport |
| C02 | Idle | — |
| W01 | Charging | — |
| W02 | Charging | — |
| W03 | Charging | — |
