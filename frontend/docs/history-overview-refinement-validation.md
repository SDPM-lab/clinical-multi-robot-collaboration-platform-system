# 排程歷史與 Overview 圖表調整驗證

## 實作範圍

- `ScheduleHistoryView.vue` 使用同一份 `inRange` 結果供統計列、Daily、Weekly、Monthly 與 List 顯示；日期、搜尋、Priority、Robot、Location、Status、Task Name 都先作用在同一條篩選管線。
- `historyPresentation.js` 集中管理任務名稱漸層、Priority／Status 表現與統計計算。Calendar 任務卡與 List 任務名稱標記均呼叫同一個 `historyTaskStyle()`。
- `HistorySummary.vue` 與 `HistoryMetric.vue` 提供五項橫向統計及 count-up／stagger 動畫。
- `HistoryEvent.vue` 使用完整淡色漸層背景、固定任務名稱配色、輕量 hover 與 stagger 進場，沒有左側彩色 border。
- `SharedLoading.vue` 從即時地圖原有 loading 視覺抽出；`HospitalScene.vue` 與排程歷史共用同一元件。排程歷史以資料來源初始化 Promise 控制 loading，沒有使用假 `setTimeout`。
- `BuildingTrendPanel.vue` 只調整全棟模式：縮窄說明區、減少內距，依實際容器尺寸放大三個樓層的 SVG plotting area，並保留 tooltip、柱狀與折線更新 transition。
- Overview shell 使用全站原有的珍珠白灰背景 token；Navbar 維持透明，背景延伸到頁面頂部。已移除後來加入的日落橘色覆蓋，3D 模型、相機、燈光、右側面板和 Bottom Panel 高度未改動。

## 狀態處理

- loading：共用即時地圖的 `SharedLoading`。
- empty：同一份篩選結果為空時顯示空狀態。
- error：資料來源初始化錯誤時顯示共用錯誤樣式並可重試。
- success：統計與目前 Calendar／List view 同時使用相同結果。

## 自動驗證

- TypeScript：`tsc -p tsconfig.app.json --noEmit` 通過。
- Build：`vite build` 通過；保留既有的大 chunk 警告。
- Tests：完整 Vitest suite 34 files、111 tests 通過。
- Lint：`package.json` 沒有 `lint` script，因此沒有可執行的現有 lint command。

## 瀏覽器驗證

以 Chromium 檢查 1440×900 與 1920×1080：

- Daily、Weekly、Monthly、List 均成功載入統計列。
- 搜尋與 Priority、Robot、Location、Status、Task Name Filter 都會即時改變統計與內容。
- Calendar 與 List 的任務名稱色值一致；Event 左側 border 計算值為 `0px`。
- List 的 Status 具有 icon 與文字。
- 1440×900：頁面寬度 1440／viewport 1440；History 主內容 scrollWidth 與 clientWidth 均為 1137。
- 1920×1080：頁面寬度 1920／viewport 1920；History 主內容 scrollWidth 與 clientWidth 均為 1602。
- List 在兩個尺寸下的 scrollWidth 與 clientWidth 相同，沒有橫向 overflow。
- Overview Bottom Panel 高度維持原設定：1440×900 為 372px、1920×1080 為 552px；全棟圖表 viewBox 分別擴展至 304×334 與 453×514。
- Navbar 背景計算值為透明，Overview 的珍珠白灰背景延伸至頁面頂部。
- 瀏覽器 runtime exceptions：0。

## 截圖

- `screenshots/overview-plot-1440x900.png`
- `screenshots/history-refined-daily-1440x900.png`
- `screenshots/history-refined-weekly-1440x900.png`
- `screenshots/history-refined-monthly-1440x900.png`
- `screenshots/history-refined-list-1440x900.png`
- 同名的 1920×1080 版本。
