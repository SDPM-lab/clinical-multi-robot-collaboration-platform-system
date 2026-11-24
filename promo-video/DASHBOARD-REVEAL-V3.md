# MediSync V6 | DashboardRevealV3

10 seconds, 1920 × 1080, 30 fps. Product labels, motion typography and the original brand treatment remain English. Voice and subtitles are Taiwan Mandarin and Traditional Chinese. The 90-second production remains at the planning stage. V5 and the two previous compositions remain available for comparison.

## Frames and Shotcraft mapping

| Frames | Picture |
|---|---|
| 0–73 | Two-line brand typography enters with a stagger and mask. The lockup shrinks across the stage as it hands off to the dashboard. |
| 74–160 | The six independent planes enter at different depths and angles. ExplodedView provides the shared perspective method, Depth Layer Moves the camera’s speed gradient, and DeckDealFlyin the stagger. ContactShadowLift places shadows below the planes as separate elements. |
| 121–240 | NeedleSweepSelftest informs the eased completion needle and numerical readout. The chart-live-moves data-writing idea is adapted to growing native-style grouped bars. The network arcs and packets travel outward before Online. |
| 240–299 | The interface resolves to a front-facing true-to-product layout behind the Simulated Data disclosure. The underlined Task Dispatch label anchors the handoff. |

## Voice session

Read with a bright, confident, controlled Taiwan Mandarin delivery. Treat MediSync as two naturally linked beats. Leave a short breath between sentences. Keep the last line energetic and land the final four syllables cleanly, before the last 1.7 seconds of the scene.

| Time | Subtitle and narration |
|---|---|
| 00.57–02.10 | 這是 MediSync。 |
| 02.10–05.23 | 整合智慧調度、任務管理與即時監控， |
| 05.23–08.23 | 讓多機器人協作，更有效率。 |

The Composition accepts a `voiceover` relative filepath under public. The preview uses Microsoft zh-TW-HsiaoChenNeural, synthesized at +15% rate and +3 Hz pitch. The 7.8-second take starts at frame 14. A replacement file uses that same start point. Music, UI movement and spatial effects remain on a separate stereo WAV.

## Sources and data boundaries

- The clinic model, controls, nav, tabs and original panel styling are the existing local Overview with WebGL, in its built-in English locale. The opening uses the original orange vector from MediSyncBrand.vue.
- The six layer textures are extracted from the original Vue panel DOM bounds in the isolated browser. Remotion adds depth, rotation, shadows and reveal masks, then returns to the full native frame. The isolated capture injects data into the original network and battery components and uses the existing task-type palette for schedule bullets. There are no production network or historical claims.
- The fixture generator reads the frontend's task definitions, English localization, task colors and seven robot series colors. It builds 24 tasks, 18 completed, 4 running and 2 pending. The schedule highlights the selected specimen delivery for the same robot and route shown in Task Progress. All seven robots contribute history on their allocated floor (five on Floor 1, one on Floor 2 and one on Floor 3). They have different battery levels, and one series rises while the others fall. Cleaning is outside the Create Task list.
- Nothing is written to the frontend, backend, production database, ROS, or telemetry. No third-party music or effects were used. The stereo mix is synthesized by scripts/dashboard-v3-audio.py using frame-indexed cue positions.

Capture with `node scripts/capture-dashboard-v3.mjs`, then split the six DOM rectangles with `python3 scripts/split-dashboard-v3.py`. Use the capture dependencies and local frontend startup described in QUICKSTART.md.
