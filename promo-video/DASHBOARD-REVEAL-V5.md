# MediSync V8 | DashboardRevealV5

A 10-second dashboard prototype, 1920 × 1080 at 30 fps. The review MP4 is 960 × 540. V4 remains a separate Composition and preview. The wider native clinic capture, English UI, brand mark, titles, and Taiwan Mandarin narration are reused.

## One capture-only fleet

`src/dashboard-v5-demo.json` provides the same rows, membership, colors and connection state for the mock fleet list, battery snapshots, legend and count. The fleet contains 15 rather than the conflicting total of 13 in the brief. The display reads 13 / 15 connected. F2-03 and F3-04 are offline in the connection snapshot and retain their earlier history.

| Floor | Robot IDs | 07:00 | 08:00 | 09:00 | 10:00 | 11:00 |
|---|---|---:|---:|---:|---:|---:|
| Floor 1 | C01, C02, M01, M02, W01, W02, W03 | 7 | 7 | 7 | 7 | 7 |
| Floor 2 | F2-01, F2-02, F2-03 | 3 | 3 | 3 | 3 | 3 |
| Floor 3 | F3-01, F3-02, F3-03, F3-04, F3-05 | 5 | 5 | 5 | 5 | 5 |

Capture reads matching fixtures through the local browser request interceptor. The original component provides the chart axes and layout, and the capture-only module transformation expands the chart legend. No frontend or backend files are edited. The prototype retains the Overview layout, so the fleet list is supplied in the shared demo data and documented here.

## Timing and recipes

| Frames | Change from V4 |
|---|---|
| 0–91 | Reuse the logo, masked typography, and camera entrance. |
| 92–170 | Stagger six 2.5D planes individually. Release contact shadows as spring motion lands. |
| 172–262 | Start data only after landing. Keep a static native chart background and overlay the native bar texture with clips. Each clip uses a fixed measured width, a fixed baseline, 22 frames of cubic-out height interpolation, and a 2-frame per-floor stagger. No grid wipe or decorative overlay. |
| 189–241 | Count the whole demo fleet from 0 to 13 connected out of 15. |
| 205–245 | One monotonic value drives both the gauge number and needle to 75. The flat screenshot replacement that could reset the data is removed. |
| 225–251 | Replace the V4 Network effect overlay with only the native orange center and three original arcs, illuminated outwards in order. |
| 254 / 267 / 284 | Location, Source, Destination light in order, with connectors driven by the simulated arrival frames. |

Shotcraft recipes adapted for the prototype are Space Camera Moves / Exploded View, Depth Layer Moves, Contact Shadow Lift, Deck Deal Fly-in, Gauge Readout Moves, and Chart Live Moves. Chart Live Moves informs the data cadence, with static axes and no effect overlays.

Chinese subtitles and narration keep their existing word timebase. The matching stereo bed is generated with `scripts/dashboard-v4-audio.py --v5`. UI accents use frames 20, 92, 99, 121, 172, 231 and 284.

## Render verification

The exported MP4 decoded into 300 nonblack frames and two AAC audio channels. Maximum adjacent-frame mean luma change was 5.03/255 at the 64 × 36 analysis scale. The audio decoded without full-scale clipping. Eleven exported frame samples verify the logo, camera, landing, bar growth, gauge, connection, Wi‑Fi, and three task states. Studio playback was checked through the final connected count. See previews/DashboardRevealV5-Review.png.
