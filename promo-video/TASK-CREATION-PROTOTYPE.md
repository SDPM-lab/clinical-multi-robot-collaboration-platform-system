# MediSync Phase B | TaskCreationPrototype

The standalone scene runs 18 seconds at 1920 × 1080, 30 fps and 540 frames. Product surfaces are native English captures from the actual Task Dispatch screen. The Mandarin trial read and Traditional Chinese captions use the requested script.

## Verified workflow

| Operation | Playback and verification |
|---|---|
| Task type | Open the real Task Type list and select Medication delivery. The selected task type constrains the native form and location controls. |
| Pharmacy | The medication configuration only permits Pharmacy as Source. The original selector is disabled; the cursor confirms the existing map pin. |
| Ward A and route | Use the native zoom-out control to keep the Ward A marker fully clickable. The captured marker is `ward_a_2`. The orange line is computed by the application's shortest-lane route preview through the original mapping. The capture suppresses the previously drawn route during the introductory shot so the film can reveal the real route after selection. |
| Creation | High is asserted active before submit. The POST payload was checked against medication delivery, Pharmacy, Ward A, High, and 14:20 Taipei time. The mock reply was held while the native button was disabled; no success toast was visible in that interval. |
| Notification | The success toast and notification center are original UI. The toast becomes visible at frame 353, with a short chime and a small transformed bounce. The camera and cursor move toward the native bell and notification record. |
| Schedule | The native date navigation was verified by moving to the next date and back. The demo uses Edit, the task's inline time field, Re-add task, and the native confirmation dialog. It verifies the same task's 15:05 entry and the success toast after the intercepted PATCH. |

## Shared demo scenario

`scripts/task-creation-demo.mjs` defines display ID **T0002**, record ID **film-task-t0002**, the two time values, and the intended lifecycle for later scenes. This scene creates and reschedules the same pending, unassigned task. Assignment, execution and completion are reserved for their corresponding scenes.

`scripts/capture-task-creation.mjs` intercepts the local browser requests for auth, CSRF, places, robots, tasks and the two mutations. The mock writes only to an in-memory task. All other requests to APIs and all WebSockets are blocked during capture. The original map model and route geometry are rendered by the frontend; no frontend or backend source is edited. Capture event and pointer coordinate evidence is in `src/task-creation-capture.json`.

## Motion and sound

- **Depth Layer Moves / MultiplaneReal** informs the independent entrance plane and camera parallax. **Contact Shadow Lift** informs the light separation shadow.
- **Cursor Flyover** informs the independently timed pointer arc, hover, press and camera focus. **Line Carry Transition** informs the route-first handoff. The route layer comes from the WebGL before/after pixels rather than a drawn approximation.
- **Spotlight Hero Card** informs the localized notification focus, settled camera and readable pause. The native notification appearance is retained in the source pixels.
- Taiwan Mandarin trial read uses Microsoft HsiaoYu Neural with +12% rate and +4 Hz pitch. Captions use the captured phrase boundaries, aligned to the five-frame voice start. The low stereo bed, control ticks and short creation chime are original and generated in `scripts/task-creation-audio.py`.

## Product limitations

Medication delivery does not permit manually selecting a different source. The original Ward A default may already be displayed before confirmation; the scene delays the route trace to make the confirmation legible. Schedule time edits are for eligible tasks without an actual start, with explicit re-add confirmation. The screen does not expose draggable schedule rows. 
