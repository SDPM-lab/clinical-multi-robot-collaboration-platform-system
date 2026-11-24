# MediSync｜Live Map Phase V2

`LiveMapPhaseV2` · 1920 × 1080 · 30 fps · 450 幀 · 15 秒

| 幀 | 畫面 | Shotcraft 實作 |
|---|---|---|
| 0–89 | REAL-TIME VISIBILITY. 左側主標，右側較大 F1 地圖。M01、Pharmacy、Ward A 依序定位。 | `crane-rise-reveal` 的低幅高角度揭露，配合標題遮罩與地圖分層。 |
| 90–179 | ACTIVE TASKS, CLEARLY CONNECTED. 左側參考路線與右側 T0002 / M01 / 位置 / 進度。 | `canvas-materialize-moves` 的資訊落位改為固定資訊軌與裁切揭露，避免卡片漂浮。 |
| 180–269 | FOLLOW THE ROBOT. 先出現 Follow Robot，保留 M01 的位置開窗，再接第三視角。 | `circle-match-iris` 的共用位置，借 `line-carry-transition` 的交接概念保留定位錨點。 |
| 270–359 | THREE VIEW MODES. 清楚列出 Third-person、First-person、Local Follow。三個畫面同時對照，再收束至 Local Follow。 | `panel-grid-moves / comic-panel-split` 的格線展開與局部遮罩；高對比切換列指出敘事焦點。 |
| 360–449 | MONITOR. TRACK. RESPOND. 左側完整任務與進度，右側與 M01 位置對齊的全域地圖。 | 共用機器人位置接回監控構圖；相機帶回全域後穩定落位。 |

## 舊版診斷與修正

- Phase 4 V1 全頁捕捉為 1280×720，放大至 1920×1080，已烘焙的小字和房間標籤會模糊；稀疏擷取的光流也可能在運鏡時產生拖影。最近一版 `LiveMapTrackingPrototypeV2` 已是原生 1080p 底片和清楚文字，但三維模型在多個構圖只佔小區域，地圖縮放排版後，房間特徵與路徑仍難一眼辨認。
- 最近一版來源與成片均為 30 fps。時間戳沒查到遺漏。跟隨切換有固定切點及遮罩；但有些切點同時開始調整畫框大小、裁切和標題，容易讀成畫面中途跳位。新版主底片全程由同一個 OffthreadVideo 依絕對幀索引播放，視角比較的兩條補充底片只在 270–321 幀按對應全域時間讀取。外框在切點前後以同一插值收尾，遮罩以 M01 位置為錨點。
- 第三人稱與局部跟隨沿用逐幀的 1920×1080 硬體 WebGL 擷取；第一視角用正式 `getRobotCameraPose('firstPerson')` 補抓同一隔離時間軸，隱藏本體幾何以清楚觀察視線前方。三個視角皆為虛擬場景相機。Global 鳥瞰保留在任務與片尾鏡頭。
- Task Progress 使用三段狀態軌。當前步驟高亮橘色，已通過用深色，未達成用淺中性色。資料來自同一 T0002，動畫在第 198 幀後才開始沿路移動，第 397 幀抵達 Ward A 才切換 Destination reached。不呈現虛構完成率。地圖上原生房間名移除，關鍵端點以高解析標籤重建。
- 繁中旁白及字幕沿用同長度的上一版原速音軌，字幕保持於底部安全區。正式網站、其他 Phase 和既有 Composition 保持原狀。
