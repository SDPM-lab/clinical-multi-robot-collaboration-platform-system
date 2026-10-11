# 任務派遣地圖：第 1 階段資料契約

本階段僅建立資料與工具，尚未接入畫面。沒有修改任務 store、導航圖、building YAML、Navbar 或後端。本文件中的「驗證」指與目前工作目錄來源資料一致。使用者已確認採用修改後的名稱；不以舊底圖標示判斷房間用途。

## 資料來源與座標

- `ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml`：reference-image 座標；212 個頂點、63 段牆、25 扇門，一項 10 公尺量測。沒有 `floors` 或已命名房間多邊形。
- 不使用舊 `L1.png` 作為畫面底圖、命名依據或房間用途驗證依據。
- `frontend/public/generated/rmf-navigation.json`：Graph 0，51 個頂點、104 條有向路段，供既有導航與任務地圖使用。
- `frontend/src/data/hospitalRoomLayout.js`：獨立顯示配置，以目前修改後的 building 頂點索引列出候選邊界；不是 nav graph 的節點索引。房間用途採用現行導航 JSON、`RoomLabelLayer.js` 與 `demoActiveRoutes.js` 的命名，並列出房間類別及導航站點映射。
- `frontend/public/generated/hospital-floorplan.json`：產生的 RMF 公尺座標、牆／門／外框、房間驗證結果與來源 SHA-256。**不修改、不取代導航圖。**

此單層 reference-image 的比例為 `10 / 360.283` 公尺／像素，轉換為 `rmf.x = image.x * scale`、`rmf.y = -image.y * scale`。與目前 Graph 0 全部 51 個命名節點逐一比對，誤差必須小於 `1e-6` 公尺，否則產生程序停止。不可套用 occupancy map `L1.yaml` 的 `0.02775` 或 `[0, -30.142, 0]` 原點。

SVG 使用 `dispatchMapGeometry.js` 的 `rmfToMapPoint()`：先沿用 `rmfToThree()`，再沿用原有 `(world.x + 20) * 22`、`(world.z + 14) * 22`。房間、導航節點、路線及日後有效的 RMF 機器人定位均須經此投影。歷史頁既有 `routeCoordinates` 已是 SVG 座標，不可重複投影。

## 邊界驗證與缺口

房間頂點全部取自 building 原始頂點，未新增示範座標。沿候選多邊形每條邊以至多 1cm 間隔取樣，檢查是否有原始牆／門線段支持，容許 12cm 的描圖落點差異；不移動原始頂點。門段僅用於房間區域閉合，不是新增不可通行障礙。所有映射站點必須存在於同層 Graph 0 且落在多邊形內。

這項檢查是有明列容差的來源幾何核對，不是精確拓撲重建。`boundaryEvidence` 保留各邊最大偏差。若來源變動造成偏差或站點在外，該房間標為 `unresolved`，`polygon` 為空，候選點只放在 `candidatePolygon`，不得繪製成正式房間。

目前 18 筆區域中，14 筆通過上述幾何核對：病房 A／B、診間 1／2／3、檢驗室、X 光檢查區、超音波室、心電圖室、治療室、充電區、廢棄物回收區、茶水間、衣物回收區。

未通過、暫不繪製色塊的 4 區：

| 區域 | 原因 | 需要補充 |
| --- | --- | --- |
| 抽血區 | 候選下邊界入口有未被牆／門段支持的缺口 | 確認入口邊界或門線資料 |
| 護理站 | 96–106 附近有頂點外形，但沒有對應完整 walls | 核准的多邊形或完整牆線 |
| 接待櫃檯 | 開放式區域，無房間閉合邊界 | 可視化区域的核准範圍；不必假裝為封閉房間 |
| 藥局 | 現行 pharmacy 節點缺少對應的可確認閉合邊界 | 包含現行 pharmacy 節點的房間邊界 |

房間正式用途以使用者修改後的導航／前端命名為準，包括診間 1／2／3、X 光檢查區、茶水間、衣物回收區與廢棄物回收區。舊圖片文字與歷史門名不覆蓋現行節點命名；不因改名而顯示「用途待核對」。`nameAuthority` 明列名稱來源，`sourceNote` 僅記錄幾何缺口。

三個診間可用相同色系，但不調整位置或比例。所有資料 `isDemo: false` 表示不是捏造示範；幾何完整性另由 `verificationStatus` 判定。若未來加入示範，須使用獨立資料集、`isDemo: true` 與明顯示範標示。

## 接入畫面時的規則

- 只繪製 `renderable: true` 的 `polygon`，不使用 `candidatePolygon`。
- 同一 SVG group 統一套用平移與縮放；陰影／薄側邊僅為裝飾，不改導航平面。
- `fitMapToViewport()` 接收 SVG viewport 單位與面板遮擋 inset，將全圖放入未被遮擋的區域。桌面左 inset 為面板寬度加間隔，底 inset 為排程實際高度；手機上下排列時左 inset 為 0。
- 拖曳必須先以 SVG `getScreenCTM().inverse()` 將 client 座標轉為 SVG 單位，再改 pan；不能混用 CSS 像素。
- `getRoomSelectableWaypoints()` 僅回傳房間明確映射、同樓層、存在於目前導航圖及任務允許清單的節點。零個則不可派遣，多個須另選站點。不得使用房間中心。
- 幾何有對應節點不等於目前任務可接受所有節點。現行 store 的 reachableLocations 僅允許八個地點，且排除 Charging Station B；接入時保持該限制。
- 路線沿既有有向 lanes 搜尋；不可畫起終點直線或增補 lanes。房間顯示層不參與路網規劃。
- 目前機器人依 store 的 currentLocation 放置，沒有已接上的真實定位串流。保留響應式更新，驗證時區分模擬 prop/store 更新與真實 ROS/API 更新。
- 任務建立仍為 demoFleetStore；後端 POST `/api/v1/task` 並未接入此頁。第 1 階段不變更這項行為。

## 產生與檢查

在專案根目錄執行（Python 需 PyYAML，與既有導航轉換腳本相同）：

```sh
python3 frontend/scripts/generate-hospital-floorplan.py
python3 frontend/scripts/generate-hospital-floorplan.py --check
cd frontend
npm test -- test/dispatchMapGeometry.test.js
```

產生腳本讀取同一份 JSON-compatible JS 配置；不得在 `export const hospitalRoomLayout =` 宣告後加入非 JSON 語法。產物可重現，無執行時間戳。`--check` 比對來源與產物，不寫入任何檔案。未解決區域會列出而不強行補圖；building 與 graph 座標不一致則直接失敗。

第 2 階段才接入 SVG 房間層、浮動表單、排程收合與地圖互動。桌面截圖與完整任務／排程操作驗證於畫面完成後提供。

## 第 1 階段驗證結果

- `generate-hospital-floorplan.py --check`：通過；14/18 區域可繪製，51 個導航節點對齊。
- `dispatchMapGeometry.test.js`：9 項通過，涵蓋來源雜湊、比例、缺口隔離、修改後的正式名稱、站點允許清單、SVG 投影、桌面／窄螢幕安全視角與隱藏 viewport。
- `git diff --check`：通過。新增內容尚未接入應用程式，未執行 UI、後端或真實即時定位驗證；不能將這些測試視為已完成全頁驗收。
