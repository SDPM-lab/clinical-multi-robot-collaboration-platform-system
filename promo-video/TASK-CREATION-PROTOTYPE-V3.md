# MediSync Scene 02 V3｜Component-driven Product Cinematography

TaskCreationPrototypeV3 · 1920 × 1080 · 30 fps · 480 幀 · 16 秒

| 鏡頭 | 幀（不含右端） | 擷取與構圖 | 實作配方與轉場 |
|---|---|---|---|
| 01 Form Extraction | 0–60 | 從原版 Task Dispatch 浮起實際 Create Task 表單，置中停穩 | element-body-moves / contact-shadow-lift。用 ui-strip-away-outro 的周邊退場，表單在同一位置交給下一鏡 |
| 02 Task Type | 60–135 | 右側原版表單對左側 Create. Simply.。只拍開啟與選 Medication Delivery | segmented-thumb-hero 的停留、按壓、原生狀態切換 |
| 03 Visual Map | 135–255 | 獨立原版 WebGL 樓層擷取，從輕微透視落到正俯視，兩個標記各一次彈跳 | shot-transitions / mask-wipe 從中央裁幅揭露，overhead-camera-moves / tilt-reveal 收平，icon-performance-moves / attention-bounce 用於標記 |
| 04 Priority & Create | 255–315 | 原生 High 選項與 Create Task 按鈕各自有裁幅。點擊後顯示隔離 API 等待畫面 | segmented-thumb-hero。按鈕用同方向的切點進入，維持表單原有樣式 |
| 05 Notification | 315–390 | 模擬 POST 成功後，原生綠色 toast 從右上出現並從影片層提到中央。無游標 | spotlight-hero-card 取焦點移交與停留。通知只回彈一次，T0002 交給下一鏡 |
| 06 Schedule | 390–480 | 原版排程、編輯欄位與確認對話框；儲存後抽出原生任務列 | row-embed 以共享 ID 和局部收平交接，最後持續保留任務卡 |

另研究 mosaic-reframe、comic-panel-split、overhead-tabletop-drop、invisible-cut、circle-match-iris 與 line-carry-transition。查閱 Gallery、配方及其鏡頭 Demo。鏡頭固定或只移動局部素材，單一全域相機未進入合成。

## 產品規則與資料

- Capture 與 Demo API 沿用 `scripts/capture-task-creation.mjs`、`scripts/task-creation-demo.mjs` 和 `src/task-creation-capture.json`。資料由一次建立及一次排程更新的事件紀錄提供。
- Medication Delivery 的 Pharmacy 是鎖定起點，影片用標記上提提示位置。Ward A 點選後顯示路線。資料內部鍵為 `film-task-t0002`，顯示為 T0002，全程只用同一筆 High、尚未指派的任務。
- 原生橘色路線中心取自 `route-23.png` 的連續像素，座標見 `src/task-creation-v3-route.json`。固定 6 px 描邊，使用單一 SVG 路徑和累積筆畫長度呈現，轉角保持連續。
- 初始 14:20，更新為 15:05。以 Edit、時間欄、Save、原生確認對話框完成。獨立大卡與畫面角落的任務編號是影片重構，產品通知仍維持原版 toast 行為。

## 聲音與字幕

旁白使用新合成的 zh-TW-HsiaoYuNeural 試音，+8% 語速、+6 Hz 音高，四句在 6、96、243、350 幀放入。旁白可用 Composition 的 voiceover 屬性替換。字幕依量測的實際可聽區間排在約 0.27–2.63、3.27–7.47、8.17–10.97、11.73–14.80 秒。底樂與操作音由影片工程合成，使用獨立立體聲音軌。

| 類型 | 幀 |
|---|---|
| 表單抽出、地圖轉場 | 9、136 |
| 下拉與 Medication 選取 | 89、112 |
| 固定起點、目的地、路線 | 165、197、202 |
| High、Create Task、成功通知 | 270、297、315 |
| Edit、時間欄、Save、確認、已儲存 | 410、422、438、454、457 |

V2 與既有網頁工程維持原樣。V3 的 Composition、素材與渲染皆在 `video/medisync-launch` 專用工作區。
