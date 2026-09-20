# 單一樓層 Bottom 三欄電量趨勢

## 元件結構

- `FloorRobotStatusPanel.vue` 保持一個 Bottom Liquid Glass 外框，內部使用三個等寬 `robot-trend-column`。
- 每欄各自包含 Robot 名稱、`Day / Weekly / Monthly`、目前電量、10 格 indicator、最新狀態、展開按鈕與一個 `RobotBatteryTrend`。
- 沒有 Robot 圖片或大型 Icon。三欄時間範圍各自保存，預設皆為 `Day`。
- 展開按鈕透過 Teleport 顯示頁內 Dialog；沿用該欄時間範圍，關閉後不改樓層或其他欄位狀態。

## 資料與圖表

- 優先讀取 `data.batteryHistory[floor]` 和實際 telemetry rolling buffer。
- Day 取最新資料日期內的觀測；Weekly 取截至最新資料的 7 日資料；Monthly 取最新資料月份內的每日最後一筆觀測。
- 資料不足兩筆時使用 `robotBatteryTrend.js` 的固定 Demo 序列，沒有 `Math.random()`。若已有一筆真實資料，Demo 序列會以它為最後一筆，保留其時間、電量、任務與任務代號。
- Robot 01／02／03 分別使用橘紅、金黃、青綠；折線後方只有淡面積填色。沒有 Forecast series、未來點或預測虛線。
- 圖表初始 active point 是最後一筆。Tooltip 預設展開並顯示完整 `YYYY-MM-DD HH:mm:ss` 和「任務 · 任務代號 · 電量」；Hover 使用 nearest point，離開後回到最後一筆。
- SVG 由 ResizeObserver 配合容器尺寸，Y 軸固定 0–100%，保留低對比水平與垂直 Grid Line。

## Liquid Glass 與不變範圍

Bottom 延用 `.overview-tool-panel`，瀏覽器 computed style 與當日排程一致：

- background: `linear-gradient(145deg, rgba(250,251,250,.63), rgba(228,231,230,.40))`
- backdrop-filter: `blur(14px) saturate(108%)`
- border-radius: `5px`
- border: `1px solid rgba(255,255,255,.58)`
- box-shadow: `0 10px 28px rgba(61,69,70,.055), inset 0 1px 0 rgba(255,255,255,.66)`

本次沒有修改全棟柱狀圖、模型、模型材質、相機、Navbar、儀表、樓層按鈕、右側面板或其他頁面。

## 驗證

- 5 個相關測試檔、14 tests 通過；新增覆蓋三欄、30 格電量、預設 Tooltip、獨立時間範圍、固定 Demo、nearest-point hover、離開還原與 Dialog 狀態。
- `tsc -p tsconfig.app.json --noEmit` 通過。
- `npm run build` 通過；既有 bundle size 警告仍存在。
- `npm run lint` 無法執行，因為 package.json 沒有 lint script。
- 完整測試為 32 檔通過、7 檔既有失敗；本次相關測試均通過。既有失敗來自缺少 task-log 元件/store、Gauge 舊斷言、sceneTheme 舊配色斷言與缺少任務日誌導覽。
- Chromium 1440×900 與 1920×1080：3 欄、3 張圖、3 個預設 Tooltip、30 格、0 圖片，頁面／Header／圖表皆無 overflow；Dialog 無 overflow，Runtime exception 為 0。
