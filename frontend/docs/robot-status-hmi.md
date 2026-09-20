# 機器人產品舞台與 Overview 進場

> Inspector 與結構功能的最新版本見 [本次修正紀錄](robot-structure-inspector.md)。以下保留前一版設計紀錄。

## 目前版本

機器人頁使用 20%／60%／20% 的儀表、Canvas、工具區。移除底部狀態／控制堆疊，把空間還給完整模型。以實際 GLB 頂點投影計算，預設視角占 Canvas 高度約 78%，aspect 1.1、.75、.55 均未裁切。模型絕對像素尺寸隨可用高度增加，不使用固定 CSS 放大倍率。1000px 以下切換模型在上、雙儀表在下，資訊面板展開於下方。

原有單一 Renderer 與 GLB 保留。GLB 放進 normalizationGroup，再放進 presentationGroup，原始場景 Transform 不再直接改寫。登場 1700ms，250ms 起旋轉一圈，以四次 ease-out 減速，1500ms 回到預設方向、1700ms 啟用 OrbitControls。切換機器人使用 420ms 淡出／0.2rad 微旋轉／淡入，不重新載入模型。雙擊及工具列可重設。

舞台使用暖色 SpotLight、DirectionalLight 主光／Rim Light、HemisphereLight，加上 ACES tone mapping。深淺色 light/rim 色值集中於 robotHmi.js。Contact Shadow 使用程序產生的徑向透明貼圖平面，非即時物理投影陰影；後方光暈與柔和光束由 CSS 呈現。背景遮罩單獨 backdrop-filter:blur(2px)，不模糊 Canvas 和文字，外圍保留原電路。

電量主色為 rgba(201,111,59,.94) → rgba(166,82,43,.92)，正常溫度為 rgba(79,159,145,.96) → rgba(53,115,105,.94)；低電量／溫度偏高使用低彩度赭黃，危急使用暗紅，充電為青綠。儀表用暖白文字及刻度。55°C 起 Warning、70°C 起 Critical，保留底盤局部 emissive、警告文字及緩慢呼吸。

主畫面只留機器人名稱、型號／編號、狀態。移除裝飾標題、Demo 標籤、孤立機器人／Info 圖示、底部重設／拖曳提示／Thermal View／索引／充電按鈕。右側窄工具列提供總覽、任務、能源、溫度、診斷、模型設定；280px 面板以 280ms 滑入，再次點擊收合。總覽內可選機器人，中央保留左右箭頭與鍵盤切換。

## 真實介面與導航限制

現有 POST /api/v1/task 的 CreateTaskRequest 沒有指定 R01／R02／R03 的欄位，也沒有充電／對接／BMS 確認鏈路。充電 Adapter 已移除模擬時鐘與模擬命令，available=false，呼叫 dispatch 會拒絕。UI 顯示「控制服務未連線」，停用「前往充電」，不出現確認模擬充電或派遣成功訊息。原先 chargingCommand 的模擬值不再被頁面採用。

能源工具可「預覽充電路線」：從共用 robot.currentWaypoint 出發，到 robot.chargingWaypoint（既有 charging_station），載入 Traffic Editor 產生的 Graph 0，沿既有 shortestVertexPath 尋找有向 Lane 路徑。SVG 每段延遲 130ms、350ms 描繪，發光虛線以 1.8 秒流動；顯示「預覽／尚未派遣」。沒有位置或無可達路徑就顯示不可用，絕不以直線代替。

**此路線是導航圖拓撲預覽，不是 RMF 回傳且已受理的行駛路線，也未考量即時交通預約。** 因控制服務尚未接通，本次沒有實作或假裝真實到站、完成與電池充電回報。

現有模型依然沒有已確認的電池 Mesh／實際位置；robotBatteryZoneRules 留空，局部電池發光未啟用。實查底盤 Mesh 為 Layer_03001／03002／03003（原始 Layer 03.001／002／003），外殼 Layer_01001 僅原始 y<6 的表面套用局部熱區。leftMotor／rightMotor 不做無依據的獨立分類。

原有開發用溫度由 Store 提供；頁面僅在 import.meta.env.DEV 顯示此來源的數值，正式建置缺少實際溫度時顯示尚無資料。沒有另外建立 Robot Store 或任務狀態。

## Overview

QuickTaskLog 移除優先級 UI，草稿與發布都明確寫入 priority:'normal'；資料欄位與任務日誌／編輯視窗的共用選擇器保留，送出仍進入 To do 並跳至對應卡片。

進場時間約 2.2 秒：

- 電路描繪 0–500ms；節點與一次訊號波 250–850ms。
- 輸入區 400–1000ms 向下淡入。
- 任務路線約 650–1300ms 描繪（資料晚到則依實際到達時間播放）。
- 四個面板自 900／1010／1120／1230ms 起，各播放 470ms。
- 數字／圓環透過 Overview 專用 provide/inject 延遲 1050ms 才開始，最晚約 2.2 秒完成。此設定不影響機器人 HMI 的 Count-up。

沒有延遲真實資料載入或增加全畫面 Spinner；進場各一次，原有背景訊號的持續流動仍保留。離開時清除 animation frames、計時器、Observer／事件與私有 GPU 資源。所有新增動畫尊重 prefers-reduced-motion。

## 本次檔案

- src/views/RobotFleetView.vue
- src/views/AppShellView.vue（只傳入背景進場狀態）
- src/components/robot-status/RobotViewport.vue
- src/components/robot-status/BatteryGauge.vue
- src/components/robot-status/TemperatureGauge.vue
- src/components/robot-status/ChargingRoutePlane.vue（新增）
- src/styles/robotHmi.css
- src/config/robotHmi.js
- src/services/chargingCommandAdapter.js
- src/data/demoActiveRoutes.js（匯出既有尋路函式，不改原演算法）
- src/components/overview/QuickTaskLog.vue
- src/components/overview/OverviewPanels.vue
- src/components/overview/OverviewRouteBackground.vue
- src/components/overview/TaskRouteProgressPanel.vue（僅動畫時間）
- src/components/overview/RobotStatusPanel.vue（僅 Count-up 時間）
- src/components/overview/FleetOverviewPanel.vue（僅刻度動畫 delay）
- src/composables/useCountUp.js
- test/robotFleetView.test.js
- test/robotHmi.test.js
- test/taskLogs.test.js
- docs/robot-status-hmi.md

## 驗證

Build 成功，仍有 bundle 超過 500kB 的既有提醒。20 個測試檔、77 項測試通過。測試核對導航路徑每段皆為真實有向 Lane、終點為 charging_station、離線控制不改變 Store，以及 Overview 發送仍為 normal／todo。

另以 GLTFLoader 載入 GLB，逐頂點投影驗證預設相機完整容納模型。尚未進行瀏覽器、WebGL shader 或全螢幕畫面實測。

## 排程歷史後續（本次不修改）

左側精簡任務代碼、名稱、機器人、狀態、建立／完成時間；點擊代碼展開當時路線、Waypoint／抵達時間、Total Time、異常／等待，右側顯示對應地圖路線。
