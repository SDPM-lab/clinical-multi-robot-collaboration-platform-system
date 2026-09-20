# 排程歷史與 Overview 夕陽渲染驗收

2026-09-11；1536×768 Chromium 實際瀏覽器驗證。

## 新增頁面與修改檔案

- 新增 `src/views/ScheduleHistoryView.vue`：獨立排程歷史頁面，透過現有 Navbar「排程歷史」進入。
- 新增 `src/components/history/HistoryEvent.vue`：共用唯讀事件呈現。
- 新增 `src/data/scheduleHistory.js`：資料 adapter、集中展示 history、篩選、日期區間與重疊事件排版。
- 修改 `src/views/AppShellView.vue`：啟用原本無作用的 history 選项並接上新頁面；沿用 App Shell，不增加第二套導覽。
- 修改 `src/components/scene/ClinicOverviewScene.vue`、`src/three/clinicOverviewLighting.js`：場景專屬背景、PMREM 環境、PBR 材質與夕陽方向光。
- 新增 `test/scheduleHistory.test.js`、`test/scheduleHistoryView.test.js`。
- 承接先前本次要求的 `ClinicOverviewView.vue`、`BuildingTrendPanel.vue`、`OverviewCalendar.vue`、`clinicOverviewPresets.js` 與其 preset 測試修改。

## Calendar 與唯讀互動

專案沒有已安裝 Calendar 套件。本頁使用現有 Vue 3、CSS Grid、原生 Date 與 dialog，不新增外部日曆依賴。舊 TaskGantt 屬於可編輯任務派遣，不將其編輯控制搬到歷史頁。

| 檢視 | 對應方式 |
| --- | --- |
| Daily | 1 天 24 小時時間軸 |
| Weekly（預設） | 週一至週日 7 欄、24 小時時間軸 |
| Monthly | 6×7 日期格，最多兩筆事件，超出顯示「還有 N 筆」 |
| List | 選取月份內按日期分組的歷史表格 |

時間軸位置依 start/end；重疊事件分欄；跨午夜事件按日切片。今天所在日期欄顯示現在時間線，每分鐘更新，並於離開頁面清除 timer。時間軸初始捲到 07:00。
Mini Calendar、Previous／Today／Next、主要日期同步。點 Monthly 日期或「還有 N 筆」進 Daily。四種 view 切換保留 selectedDate、篩選及搜尋，220ms 淡入，外部高度不變。

事件皆為 button，點擊開啟原生模態 detail drawer，可用關閉按鈕或 Escape 關閉；沒有新增、拖曳改時、resize 或編輯動作。

## 資料與篩選

優先 adapter 讀取現有 `demoFleetStore.tasks` 中具有有效日期、起訖時間及 completed／cancelled／failed／running 對應狀態的紀錄。原始 store 目前只有無日期的展示派遣任務，不能將它們視為真實已完成歷史。
因此集中在 `scheduleHistory.js`，由現有任務／Robot／地點模板產生一次、無隨機值的示範歷史，頁面標示「展示資料 · 唯讀」。不寫回 store，不改寫任務狀態，不宣稱已接上歷史 API。未來提供有日期的有效 store 紀錄時，優先顯示實際 adapter 結果。

統一模型包含 id、taskId、title、robotId、robotName、start、end、startLocation、endLocation、priority、status、taskType。
Priority／Status options 集中定義；Robot 來自現有 fleet store；Location 合併 `demoActiveRoutes.locationDetails` 與事件起終點；Task Type 從紀錄建立。
五組篩選可多選、立即更新、支援全部／清除，顯示啟用數量。搜尋涵蓋任務 ID、名稱、Robot、起終點。

Priority 漸層：urgent #f06a50→#ff9a62；high #ed8b2c→#ffc061；normal #f2bd43→#f6dc79；low #70b99c→#a4d6b9。以 32%／22% 混白降低飽和度，3px 左邊線、4px 圓角。
頁面 glass panel 5px 圓角、14px blur、108% saturate，左側 clamp(210px,17vw,260px)。

## Blender／GLB 實際檢查

目前 `frontend/public/models/clinic_overview.glb`：

- generator 為 Khronos glTF Blender I/O v5.2.39。
- 沒有 `KHR_lights_punctual`，沒有 GLB light extension。
- 沒有 texture 資源（textures 數量 0），所以沒有可載入的 emissive／normal／base-color 貼圖；使用匯出材質參數。
- 有 UP_DoorGlass、UP_WindowGlass、UP_EntranceInterior、UP_WallLamp、UP_WarmInterior 等 emissive 材質。這些是 Mesh 材質，不是已匯出的燈光。
- 專案內沒有 HDR／EXR 資產，因此沒有從外部 URL 下載環境貼圖。

讀取倉庫現有 `blender/hospital_beautified.blend` 得到：AgX；Preview_Sun（SUN，energy 2）；沒有 Area Light；沒有啟用 compositor；world 沒有啟用節點；Material Preview 視窗使用 Blender 內建 forest.exr，use_scene_world／use_scene_lights 為 false。這說明該檔案預覽依賴 Studio 環境，不能期待自動包含在 GLB 中。此 blend 不保證就是目前 clinic_overview.glb 的直接來源；未臆測沒有提供的 clinic 原始 .blend。

現有 `blender/scripts/export_hospital_glb.py` 還明確設 `export_lights=False`（該腳本輸出 hospital.glb，不宣稱它是 clinic GLB 的匯出流程）。

網頁原先無 environment map、使用 ACES 而非 AgX，並有前端牆面／深灰與玻璃色彩覆寫，這些是已確認的顯示差異來源。現在移除廣泛 color 覆寫，保留匯出的 base color、roughness、metallic、normal、alpha、side。若日後包含 base-color／emissive texture，將其標為 SRGB。

## 最終 Three.js 設定

- `SRGBColorSpace`、`ACESFilmicToneMapping`、exposure **0.94**。
- Canvas alpha 0，pixelRatio 上限 2，PCFSoftShadowMap。
- Sunset key #ffa96b / **1.65**，基準方向 **(-14,10,12)**，唯一新增燈組中的投影主光。
- Sky hemisphere #cddce7 / #8c7567，**0.72**。
- Front fill #e8edf0 / **0.34**，(10,8,14)。
- Rim #ffc38d / **0.28**，(10,7,-12)。
- 沒有額外 AmbientLight／PointLight、沒有 Bloom。
- Shadow 2048²、bias -.00015、normalBias .025、radius 3、intensity .35，frustum 依模型 bounding box fit，fit 使用同一夕陽方向。
- 本地 Three.js `RoomEnvironment` → `PMREMGenerator` → `scene.environment`；建立完成後釋放 room／generator，頁面卸載時釋放 environment render target。
- envMapIntensity：玻璃／窗戶／金屬 .38；植物 .12；其他 .18，避免均勻環境反射蓋過夕陽方向。
- 保留 GLB 既有玻璃 emissive；只將確切 UP_EntranceInterior／UP_WarmInterior／UP_WallLamp 且無 emissiveMap 的室內發光 Mesh intensity 降至 .18，避免入口發光方塊。未對屋頂或植物添加 emissive。
- CSS 夕陽背景只在 Overview scene：冷灰藍天空 #dce4e9 → 灰暖色 #ebe7e3 → 桃橘地平線 #f1d8c4 → #ded8d1，加右側低濃度暖光暈。
- Canvas 使用放大的 95%×100% radial mask，中心 65% 保持不透明，不模糊 canvas；無 Fog，以免建築泛白。
- 本階段未改動模型 transform 或相機 preset。保留前一項明確指定 position (16.1229,10.138,27.1508)、target (.1357,5.4919,2.4446)。

## 承接完成的 Overview 空間與動畫

Bottom 上緣 y=510；Floor 1 按鈕下緣 y=490，間距20px。1536×768 時 Bottom 高240px；1536×690 時高162px，兩者均無整頁垂直捲動。小於650px高度使用140px的保底高度。
柱狀圖使用各 Robot 的淺→深垂直 SVG 漸層與唯一 ID；900ms 由下生長，650ms 起分層／Robot／小時錯開。平均線950ms後描繪1300ms，節點依序出現；動畫無循環。時間延後避免在父面板淡入前已播完。
排程任務名稱12.5px、Robot12px、時間11.5px、日期13px。大量任務使用52px最小列高、面板內 overflow-y:auto、暖橘細捲軸。
多任務瀏覽器 fixture：列表 clientHeight193、scrollHeight884、scrollTop130；整頁仍768px。

## 驗證

- `npm run build`：通過，既有超過500kB bundle提示仍存在。
- `npm run typecheck`：已執行；缺少 package.json script，未通過。
- `npm run lint`：已執行；缺少 package.json script，未通過。
- 本階段5組相關Vitest、12個測試通過：日期範圍、多選搜尋、重疊／跨日事件、唯讀資料 adapter、四種 view 保留篩選與日期、月檢視日期同步、陰影、presets及Bottom模式。
- 瀏覽器：Navbar開啟新頁面成功，Weekly15筆事件，原生detail dialog成功開啟；List11個日期組、33筆資料，選單篩選後8筆；切Daily仍保留1項篩選且只有1日欄。
- 無JavaScript執行例外，document.scrollHeight768。
- 所有資料互動為本機展示／store驗證，未建立真實ROS歷史API連線。

## 截圖

- [Weekly](screenshots/history-weekly-1536x768.png)
- [Monthly](screenshots/history-monthly-1536x768.png)
- [List](screenshots/history-list-1536x768.png)
- [Overview 夕陽](screenshots/overview-sunset-1536x768.png)
