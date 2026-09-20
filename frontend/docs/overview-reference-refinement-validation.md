# Overview 局部調整

## 共用玻璃

原當日排程使用 `src/app.css` 的 `.overview-tool-panel`：

- background: `linear-gradient(145deg,rgba(250,251,250,.63),rgba(228,231,230,.40))`
- backdrop-filter: `blur(14px) saturate(108%)`
- border-radius: `var(--panel-radius)`，由 theme.css 解算為 `5px`
- border: `1px solid rgba(255,255,255,.58)`
- box-shadow: `0 10px 28px rgba(61,69,70,.055),inset 0 1px 0 rgba(255,255,255,.66)`

共用 token 位於 `src/app.css` 的 `.clinic-overview-dashboard`。移除完成率、任務進度及 Bottom 的獨立背景覆寫與完成率橘色裝飾框。Calendar 的 WebKit filter 原本引用未定義變數，現在與標準 filter 一致。

## 修改位置與資料

- `src/views/ClinicOverviewView.vue`：保留版位與面板尺寸，局部白灰背景、淡暖中央光；串接歷史及 rolling buffer、還原初始模型 layout。
- `src/components/overview/OverviewCalendar.vue`、`TaskProgressTimeline.vue`：使用共用材質；內容與 Timeline 不變。
- `src/components/overview/BuildingTrendPanel.vue`：只保留三色分組柱、置中群組、時間／電量軸與原生 hover tooltip，移除所有平均線／節點／區域／圖例／動畫。
- `src/components/overview/FloorRobotStatusPanel.vue`、`RobotBatteryTrend.vue`：三個等寬 Robot 區域、固定配色、10 格電量、平滑小折線、淡漸層、最新點 pulse、滑鼠與鍵盤 tooltip。
- `src/composables/useOverviewBatteryHistory.js`：優先接收 View 的 `data.batteryHistory`；不足部分使用目前 Robot 狀態更新，每樓層每 Robot 最多 30 點。Vue scope 自動停止 watcher，沒有額外 timer/listener。無歷史時只呈現目前值短線，不製造曲線。非該樓層的 Robot 不借用別層即時值。
- `src/components/scene/ClinicOverviewScene.vue`、`src/three/overviewOriginalState.js`：載入時保存全部 Object 初始 visible／transform，clone 材質快照並為每個 Mesh 建立獨立工作材質。回全棟完整 copy 原始材質，樓層 mapping 與選層透明效果保留。
- 移除 `enhanceGlassMaterials`：Glass 色彩、transmission、roughness、ior、thickness、envMapIntensity 強制設定，以及 MeshPhysicalMaterial 替換造成的 metalness／opacity／transparent／depthWrite／side 覆寫。移除額外 texture colorSpace 變更，保留 GLTFLoader 原始貼圖。未修改 GLB／Blender。
- `src/three/clinicOverviewLighting.js`：主光中性白、柔和冷灰補光；保留 SRGB、ACES、低強度 Hemisphere、soft shadow，沒有新增 PointLight 或 emissive。

## 驗證

- Build 通過，既有 bundle 超過 500 kB 提示仍存在。
- `tsc -p tsconfig.app.json --noEmit` 通過；此專案未配置 vue-tsc。
- `npm run lint` 無法執行：package.json 沒有 lint script。
- 6 個相關測試檔、14 個測試通過，包括共享材質隔離、反覆還原、隱藏 Group 還原、30 點上限、floor 隔離與 scope 清理。
- 完整 test：28 檔通過，7 檔失敗（新增兩個測試前執行）。失敗項涉及既有 task-logs 元件/store 缺檔、舊儀表斷言、未修改 sceneTheme 的既有配色斷言，以及缺少任務日誌導覽入口。本次不更動這些範圍。

- Chromium 實測 1440×900、1920×1080：四個面板 computed style 完全一致；全棟 45 根柱、0 平均線；Floor 1／2／3 各 3 個小圖表容器與 30 格電量；頁面與 Robot 區域沒有 overflow。多次回全棟後 alteredMaterials = 0，Runtime exception = 0。
- 最終靜態截圖關閉動畫以避免軟體 WebGL 繪圖截在過場中；正常模式另外測過反覆切換。截圖：`screenshots/overview-reference-{1440,1920}-{3,all}.png`。
