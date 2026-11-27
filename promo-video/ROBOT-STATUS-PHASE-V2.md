# MediSync Phase 5 V2

`RobotStatusPhaseV2` · 20 秒 · 1920 × 1080 · 30 fps。

## 原站對照

| 產品元素 | V1 | V2 |
|---|---|---|
| Navbar | 影片自製單列 | 原 Vue Navbar 與完整圖示列 |
| Fleet、選中狀態 | 重建的窄欄 | 原始寬度、搜尋、樓層篩選、列表與原生按下樣式 |
| 中央模型區 | 另外放置有邊框的卡片 | 開場與收尾使用網站 viewport，模型特寫沿用相同真實 Agibot GLB，以 Three.js 相機渲染 |
| Batteries／Temperature | 重建儀表 | 實際 BatteryGauge 和 TemperatureGauge 擷取 |
| Robot information | 米白色重建卡片 | 原黃色面板、資訊格、Structure 按鈕與原生選中狀態 |

原版頁面由本機 Vue 伺服器開啟。在擷取瀏覽器中，以七台 Demo 車隊和任務紀錄攔截讀取請求，WebSocket 停用。溫度在正式頁面是空值，擷取瀏覽器只為影片讓原生元件讀取示例值。網站畫面上方保留 Demo Telemetry。M01 在 Ward A、Idle、82%、36°C，T0002 維持上一幕已抵達的狀態，因此沒有活動任務。每台資產均為專案的 Agibot 模型。

## 時序與動效

| 時間 | 動作 | Shotcraft 應用 |
|---|---|---|
| 0–3 秒 | Phase 4 最後一幀接 M01；拉回真實 Robot Status Workspace | `crane-rise-reveal` 的由近及遠、`mosaic-reframe` 的共享座標交棒 |
| 3–6 秒 | 原生清單進入特寫、捲動減速、M01 Hover 與點選；第 154 幀同步更新選中列和設備資料 | `scroll-brake-moves / changelog-scroll-brake` 的速度衰減 |
| 6–10 秒 | 中央 viewport 接到 Agibot 主體，固定目標作緩慢三維環繞 | `space-camera-moves` 的 subject-locked orbit |
| 10–14 秒 | 模型陪伴原生儀表，構圖由電量、溫度帶到原生 Robot information | `gauge-readout-moves` 的讀數焦點、`scanline-annotate-focus` 的先局部後重點閱讀、`element-body-moves` 的元件局部取景 |
| 14–18 秒 | Head 429、Left arm 466、Whole robot 509；游標、原生控制與模型相機同步 | `space-camera-moves` 的三維目標移動、`graze-face-tour` 的局部輪廓視角、`segmented-thumb-hero` 的選中時序 |
| 18–20 秒 | 模型回到原網頁的中央 viewport，定格原生頁面 | `crane-rise-reveal` 的回到全景 |

數值在切換設備時更新，在 M01 確認後維持 82%／36°C，並沿用原生儀表的液面與指示點位置。繁中旁白依實際鏡頭段落精簡，保留原語速。點擊與輕量提示音以影格對齊。
