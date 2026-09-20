# 任務日誌與機器人 Inspector 修正紀錄

## 任務卡

移除每張卡的「移至」與狀態 select、兩條專用 CSS。原本 moveLog 同時服務拖放，因此保留；dragstart／drop／updateStatus／儲存／回滾流程未變。任務代碼、優先級、內容、時間、作者、操作選單／編輯／刪除保留。

## 舞台與 Inspector

- 完全刪除 stage-spotlight 元素與 clip-path 梯形樣式。保留真正的 SpotLight、DirectionalLight 主光、DirectionalLight Rim、HemisphereLight。
- 只使用以機器人為中心的橢圓 Radial Glow，blur 28px，淺色降低強度。
- Inspector 為相連的 Icon Bar＋內容，整體寬 340px；內容高度自適應，過長則內部捲動。每次 mount 預設 overview「機器人總覽」，可收合，不持久儲存。
- 機器人登場 1700ms 後，Inspector 以 280ms 淡入。分類內容切換 240ms、cubic-bezier(.22,1,.36,1)。結構操作／Raycaster 等登場完畢才啟用。
- 分類為總覽、目前任務、能源、溫度、結構、診斷。重設視角留在 Inspector。
- 標題字體堆疊為 Inter、SF Pro Display、Noto Sans TC、sans-serif；font-weight:800；clamp(2.5rem,3.8vw,4.25rem)，1536 寬約 58.37px、1920 寬 68px；line-height:.95，letter-spacing:-.045em。
- 左側儀表改為舞台頂端對齊，再向上偏移 50–70px（768 高為 50px、1080 高為 54px）。實測第一張卡 top 為 140.45px／145.59px，兩卡間距18px，寬248px。
- Contact Shadow 平面由2.9×2.9縮為2.4×2.4；材質opacity淺色.12、深色.19，貼圖外緣快速衰減，不疊加 CSS 陰影。
- 實測修正 Canvas 固有寬度撐開窄螢幕 Grid：使用 minmax(0,1fr) 與 min-width:0。
- 深色實測發現 OverviewRouteBackground 的 :global([data-theme='dark']) 後接選擇器被編譯成裸 [data-theme='dark']，把整頁 opacity 設為 .3。修正為正確 scoped 後代選擇器；保留所有電路動畫，頁面opacity恢復1。

## GLB 真實結構

GLTFLoader traverse 確認8個Mesh，不是單一合併Mesh。原始GLB未更動。

| Runtime Object | Parent | Material | 分類 |
| --- | --- | --- | --- |
| Default002 | Default001 | Default:0:0:0 | 功能未辨識，不可選取 |
| Default003 | Default001 | Default:0:0:0.001 | 功能未辨識，不可選取 |
| Layer_01001 | Layer_01 | Layer 01:0:0:0 | 外殼 |
| Layer_02001 | Layer_02 | Layer 02:0:0:0 | 前側上方面板 |
| Layer_02002 | Layer_02 | Layer 02:0:0:0.001 | 前側下方面板 |
| Layer_03001 | Layer_03 | Layer 03:0:0:0 | 底盤構件 |
| Layer_03002 | Layer_03 | Layer 03:0:0:0.001 | 底盤構件 |
| Layer_03003 | Layer_03 | Layer 03:0:0:0.002 | 底盤構件 |

robotComponentRules.js 使用以上完整Object名稱。controller／battery／leftMotor／rightMotor／lidar 保留空陣列，沒有把不明Mesh假裝成馬達或電池。display分類UI稱為「前側面板」，不推定其內部電子功能。

## 結構功能

- 只有規則內6個Mesh可Raycast；未辨識Mesh仍參與遮擋判定。Hover使用淡橘emissive .12；點擊透過選取事件讓Inspector切到結構。
- 拖曳超過5px、多指觸控、取消事件不觸發選取，登場／切換期間不Raycast。
- 聚焦依構件合併Box3計算中心、視野角與距離，Camera／Orbit Target在750ms平順移動，沒有為馬達硬寫座標。
- 選取構件使用 #C96F3B、emissiveIntensity .45；一般選取模式其他構件opacity .27並去飽和。X-Ray只讓外殼透明，其他構件保持正常不透明。
- Exploded是真實Mesh位移：外殼往外，前側面板向上／前，底盤向下，持續850ms；沒有新增或虛構內部幾何。這是現有可分離構件的展示，不是完整維修拆解圖。
- 每個Mesh儲存originalPosition／originalQuaternion／originalScale。所有展開目標由原始Transform計算，不累加。整機模式與Robot切換會安全復原；離開結構分類保留模式。
- 沒有獨立構件感測資料，因此不借用總溫度冒充零件溫度／轉速／負載／錯誤碼。無法提供「點擊左馬達聚焦或過熱」這種未確認零件的功能。
- 若要真正拆解內部硬體，需要在Blender確認並分離電池、左右驅動馬達、控制器與LiDAR，保留正確局部座標與零件原點、使用明確名稱再重新匯出；還需要對應零件的感測資料。

## 保留的介面限制

充電服務仍未連線，按鈕維持停用；既有真實Lane路徑預覽保留。電池位置仍未確認，局部電池發光仍未啟用。此次沒有把這些尚未接通的功能改成假成功。

## 驗證

- Build通過，仍有bundle超過500kB提醒。
- 21個測試檔、81項測試通過；最後X-Ray不透明度調整另重跑3項結構測試通過。
- 真實GLB測試：8 Mesh／6可選Mesh、3次分解復原無位移累積、Bounding Box聚焦、材質隔離、登場禁止選取、拖曳不誤選、事件解除。
- Kanban元件測試：拖放經四個欄位再返回，DOM／Store／localStorage狀態皆正確。
- Chromium＋SwiftShader實測1536×768、1920×1080，深色與淺色均截圖檢查；Inspector寬340px、高368px（總覽）。
- 3D實際點擊選中外殼，Inspector自動切結構；X-Ray／Exploded可操作，切Robot後回整機，過程GLB僅請求1次。
- 390px窄螢幕無水平溢位。
- 瀏覽器實際拖卡到In progress，localStorage為in_progress；卡片沒有select；重新進入頁面顯示機器人總覽。
- 最終瀏覽器JavaScript／WebGL錯誤0筆，深色overview-page opacity為1。
- 截圖位於 /tmp/robot-hmi-check/：1536-light.png、1536-dark.png、1920-light.png、1920-dark.png、xray.png、exploded.png。

## 資源生命週期

仍使用原本一個Renderer與私有Runtime材質。卸載移除5個pointer listeners、鍵盤監聽、ResizeObserver、MutationObserver、OrbitControls與RAF；停止Camera／Exploded tween，dispose私有Material、Geometry、Texture與Renderer。沒有改寫GLB共用材質或即時地圖資源。

## 本次修改檔案

- src/views/TaskLogsView.vue
- src/views/RobotFleetView.vue
- src/components/robot-status/RobotViewport.vue
- src/styles/robotHmi.css
- src/config/robotComponentRules.js（新增）
- src/three/robot/RobotStructureController.js（新增）
- src/components/overview/OverviewRouteBackground.vue（深色選擇器修正）
- test/robotFleetView.test.js
- test/robotStructure.test.js（新增）
- test/taskLogs.test.js
- docs/robot-structure-inspector.md（新增）
- docs/robot-status-hmi.md（連結至本次更新）
