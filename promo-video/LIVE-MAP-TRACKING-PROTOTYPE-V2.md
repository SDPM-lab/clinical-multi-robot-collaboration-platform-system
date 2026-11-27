# MediSync｜Cinematic Live Map Product Explainer V2

`LiveMapTrackingPrototypeV2` · 15 秒 · 1920 × 1080 · 30 fps · 450 幀

| 幀 | 鏡頭與畫面 | Shotcraft 應用 |
|---|---|---|
| 0–89 | REAL-TIME VISIBILITY. 左側標題，右側 F1 室內地圖，低幅推進後停穩。 | `lead-word-zoom-assemble` 借用先主標後副標的視線層次，`crane-rise-reveal` 借用單次高角度落位。 |
| 90–179 | EVERY TASK. IN SIGHT. 從 M01 到 T0002、路線與進度。定位標籤連到正式路網端點。 | `canvas-materialize-moves` 把原本小型任務資料依序落在大幅獨立版面；選擇、詳細資料與進度分段揭露。 |
| 180–269 | FOLLOW EVERY MOVE. M01 標記變成 Follow Robot，204–221 幀以共用標記開窗，接第三人稱跟隨。 | `circle-match-iris` 將地圖上 M01 作為開窗中心，鏡頭在遮罩後換位。 |
| 270–359 | MULTIPLE PERSPECTIVES. 同時展示 Third-person 與 Local Follow，後者遮罩擴張至滿幅。 | `panel-grid-moves / comic-panel-split` 同步分屏，`shot-transitions` 以遮罩帶入滿幅。 |
| 360–449 | MONITOR. TRACK. RESPOND. 從 Local Follow 收回同一 M01，回到可閱讀的任務監控構圖。 | 共用元素回接地圖標記，重組任務面板；M01 在抵達 Ward A 才亮起終點。 |

## V1 診斷與 V2 改法

V1 的來源為 1280×720 全頁 WebGL 截圖，在 1920×1080 文字也隨網站畫面放大 1.5 倍。V1 用 77 張擷取影格光流補間為 30 fps，在大幅視差變化的跟隨過場容易出現局部融化或卡頓感。來源與成片的時間戳均為連續 30 fps，當時 Composition 使用一條持續的 OffthreadVideo。逐幀鏡頭資料在轉場窗口為連續插值，未發現改掛載或幀時間戳掉失造成的重播。V1 轉場窗口的最大單幀相機位移約為 0.949 與 0.855 場景單位。

V2 的 3D 素材直接從正式 Three.js 的 1920×1080 drawing buffer 取像，DPR 1，JPEG 0.98，隱藏 DOM 避免網站文字烘焙進素材。關鍵 UI 用 Remotion 原生文字重建，沿用 MediSync 字標、橘白黑設計、任務與跟隨語意。主要 WebGL 鏡頭變動期間皆逐幀擷取，只有鏡頭與資料刻意停穩期間使用同一畫面。無光流、幀混合或加速原聲。底片 H.264 CRF 14，預覽 CRF 16，正式交付 1080p。

## 相機與資料來源

使用原始 `hospital_L1_environment.glb`、M01 `AGIBOT_A2D.glb`，以及正式 `rmf-navigation.json`。T0002 是隔離的 Medication Delivery，Pharmacy → Ward A，由 M01 模擬執行。Route 為參考線。執行進度自第 198 幀後平滑前進，到第 397 幀與 Ward A 端點一致。

全部相機以全域幀索引驅動。在擷取瀏覽器中，取樣控制接管相機後，正式 RAF 繼續排程但不再更新 OrbitControls、相機或畫面。全域角度 0–24 幀小幅推近，第三人稱沿正式姿勢函式的跟隨偏移（後方 2.4、上方 1.75，再加 0.5 高度）做單一阻尼，目標同樣阻尼。Local Follow 使用正式 `getRobotCameraPose('localFollow')` 的上方 6.4、Z 方向 4.8。由同一幀擷取兩個畫面，確保分割畫面中是同一時刻。兩個模式皆為模擬相機。大幅鳥瞰與近景切換只在遮罩內進行，避免把相機沿直線推過牆面。

重新擷取用 `scripts/capture-live-map-tracking-v2.mjs`，鎖定時間軸合成用 `scripts/assemble-live-map-tracking-v2.py`。正式網站原始檔沒有變更。旁白使用繁中合成原速，逐句幀範圍在 `src/live-map-tracking-v2-captions.json`。

初次瀏覽器合成畫面擷取在雙視角快切時可能拿到前一張表面。本版以硬體 WebGL 讀回每次繪製的 drawing buffer，並比對兩種相機同一時刻的原始影格。共擷取 282 張主影格與 52 張同幀的局部跟隨影格；跟拍區間量測最大相機／目標逐幀位移約 0.454／0.477 場景單位。
