# Robot Status 前後端欄位對照

| 畫面 | 資料來源 | 目前處理 |
| --- | --- | --- |
| 機器人清單與樓層數量 | `GET /api/robots` 的 `robots[].id`、`levelName`、`robotType` | 已連接。名冊固定七台，均為 F1；F2/F3 沒有機器人時不顯示空的篩選頁籤。畫面短編號只供顯示，任務關聯仍用後端 `id`。 |
| 工作狀態與當前任務 | `robots[].status`、`GET /api/v1/task` 的 `assignedRobot`、`status`、`taskCode` | 已連接，每五秒更新。 |
| 目前位置與電量 | `robots[].location`、`battery`、`hasTelemetry` | 已連接；尚未收到 ROS2 遙測時顯示缺值，不把預設 `0` 當成電量或座標。 |
| 連線與溫度 | `hasTelemetry`；後端尚無獨立溫度欄位和心跳期限 | 無遙測時顯示未連線，溫度顯示缺值。日後需定義心跳逾時及溫度欄位後才能顯示即時值。 |
| 機器人類型 | 後端 `robotType` | clean：1–2；medical：3–4；ward：5–7。 |

機器人名冊由後端管理，因此狀態頁已移除僅修改瀏覽器示範名冊的新增和刪除操作。

目前前端短碼設定為 `C01/C02/M01/M02/W01/W02/W03`，原始後端 ID 沒改；7 台機器人類型分布為 2 Clean／2 Medical／3 Ward。`R01`～`R07` 是對應 ROS 機器人序號，不作為 UI 顯示短碼。

`robot_descriptions` 已確認型號為 Agibot Genie G1，套件為 `agibot_g1_description`；後端 API 與狀態頁現會顯示這些名冊資料，清單縮圖也讀取該描述庫的 G1 圖。ROS 套件提供的是由 Xacro 組裝的分件 GLB，不是瀏覽器可直接替換的單一整機 GLB，因此互動 3D 暫時保留現有 A2D 預覽；後續需額外匯出 G1 整機 GLB。

## 任務路線與欄位

- 建立任務 API 和畫面使用 `source`、`destination`；任務記錄原本已有 `source`。`origin` 不再作為建立任務 API 欄位。
- Dashboard 任務進度順序為「機器人目前位置 → source → destination」，中間可列 Traffic Editor 的參考途經點。若後端沒有定位，第一項顯示缺值；參考途經點不表示機器人已到達。
- 即時地圖目前的開發模擬路線仍由 `source` 開始。待收到機器人實際目前位置及正式派工路線後，才可把「目前位置 → source」這一段與真實行走動畫對齊。
- ROS2 尚未回報路點進度、到站確認與溫度；這些資料不能由前端的路線動畫推定為真實執行結果。

## 驗證

- `dotnet test backend/Server.Tests --no-restore`：49 通過。
- `npm run build`：通過。
- `npm test -- --run`：249 通過。
