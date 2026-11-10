# Clinical Multi-Robot Platform API

這份文件依據目前 `backend/Server/Controllers` 的實作整理。HTTP API 主服務使用 **ASP.NET Core Web API**（C#）；本專案另有 Python/FastAPI ROS bridge 的舊版程式，兩者不是同一個 API 服務。詳細比較見「技術選型」。

> **文件提醒：**目前開發環境提供的 Swagger 規格 `backend/api.yml` 有部分路徑和資料模型尚未跟上 Controller。本文列出的路徑以實際後端程式碼為準。

## 連線資訊

- 本機開發網址：`http://localhost:5100`（見 `Server/Properties/launchSettings.json`）。
- API 使用 JSON；JSON 屬性採 camelCase。任務類型採 snake_case，例如 `medication_delivery`；狀態等其他列舉維持 camelCase。
- 除健康檢查、CSRF 權杖和受限的開發登入外，API 預設要求登入。
- 登入使用 Cookie，不是把 access token 放在 `Authorization: Bearer` 標頭。
- 所有 `POST`、`PATCH`、`DELETE` 請求都要帶 `X-CSRF-TOKEN`。先呼叫 `GET /api/auth/csrf`，並在後續請求保留 Cookie。
- Cookie 驗證失敗回應 HTTP `401`；授權失敗回應 `403`。

### 登入 / CSRF 呼叫流程

1. `GET /api/auth/csrf`，保存回傳的 `token` 和伺服器設定的 Cookie。
2. 註冊或登入時，在標頭加上 `X-CSRF-TOKEN: <token>`，並使用同一個 Cookie jar。
3. 登入成功後重新呼叫 `GET /api/auth/csrf`，再以新權杖呼叫其他寫入 API。
4. 瀏覽器端需允許 credentials；Cookie 在正式環境要求 HTTPS。

## API 清單

### 健康檢查

| Method | Path | 登入 | 說明 |
|---|---|---:|---|
| `GET` | `/api/health` | 否 | 回傳 `{ "status": "healthy" }`。 |

### 帳號與登入

| Method | Path | 登入 | 說明 |
|---|---|---:|---|
| `GET` | `/api/auth/csrf` | 否 | 取得寫入請求用的 CSRF 權杖，並設定防偽 Cookie。 |
| `POST` | `/api/auth/register` | 否 | 建立帳號並登入，成功回 `201`。 |
| `POST` | `/api/auth/login` | 否 | 登入；`rememberMe: true` 的 Cookie 最長 14 天，否則 8 小時。 |
| `POST` | `/api/auth/dev-login` | 否（限開發本機） | 只在 Development 且來源 IP 為 loopback 時可用；其他情況回 `404`。 |
| `GET` | `/api/auth/me` | 是 | 取得目前登入者；失效時回 `401`。 |
| `POST` | `/api/auth/logout` | 是 | 清除登入 Cookie，成功回 `204`。 |
| `PATCH` | `/api/auth/profile` | 是 | 更新顯示名稱及可選頭像。 |

#### 註冊請求

```http
POST /api/auth/register
Content-Type: application/json
X-CSRF-TOKEN: <token>
```

```json
{
  "name": "王小明",
  "email": "user@example.com",
  "password": "至少 6 個字元"
}
```

`name` 長度 2–40；`email` 必須為有效 Email，最多 254 字元；`password` 長度 6–128。

#### 登入請求

```json
{
  "email": "user@example.com",
  "password": "your-password",
  "rememberMe": false
}
```

#### 個人資料更新

```json
{
  "name": "王小明",
  "avatarUrl": "data:image/png;base64,..."
}
```

`avatarUrl` 可為 `null` 以移除頭像，也可使用 PNG、JPEG 或 WebP 的 Base64 data URL；解碼後上限為 3 MiB。回應中的使用者資料為 `{ id, email, name, avatarUrl }`，不含密碼。

#### 帳號 API 常見錯誤

| HTTP | 說明 |
|---:|---|
| `400` | 欄位或 CSRF 驗證失敗；名稱或頭像不符合規則時也會回此狀態。 |
| `401` | 登入資料錯誤 (`invalid_credentials`)、登入過期 (`session_expired`) 或未登入。 |
| `409` | Email 已註冊 (`email_exists`)。 |
| `429` | 註冊/登入超過速率限制 (`rate_limited`)；限制為每個來源 IP 每分鐘 10 次。 |

### 任務

任務 API 前綴為 `/api/v1/task`。

| Method | Path | 說明 | 成功回應 |
|---|---|---|---|
| `GET` | `/api/v1/task` | 取得所有任務。 | `200`，任務陣列 |
| `GET` | `/api/v1/task/{task_id}` | 取得單一任務。 | `200`，任務物件 |
| `POST` | `/api/v1/task` | 建立任務。 | `201`，任務物件及 `Location` 標頭 |
| `PATCH` | `/api/v1/task/{task_id}/schedule` | 修改任務預定時間；服務可能以替代任務取代原任務。 | `201`，替代任務物件 |
| `PATCH` | `/api/v1/task/{task_id}/priority` | 修改尚未處理任務的優先級。 | `204` |
| `DELETE` | `/api/v1/task/{task_id}` | 刪除允許刪除的任務。 | `204` |
| `PATCH` | `/api/v1/task/{task_id}/abort` | 取消尚未送出/指派的任務。 | `200` |
| `GET` | `/api/v1/task/event/trace` | 透過 SSE 接收任務狀態變化。 | `200`, `text/event-stream` |
| `POST` | `/api/v1/task/{task_id}/simulation/arrive` | 模擬路線抵達回報；僅 Development 可用。 | `204` |

#### 建立任務

```json
{
  "taskType": "medication_delivery",
  "source": "nurse_station",
  "destination": "ward_a",
  "priority": "normal",
  "robotId": null,
  "scheduledAt": "2026-11-09T08:00:00+08:00",
  "note": "請交給護理站"
}
```

- 必填：`taskType`、`source`、`destination`、`priority`、`scheduledAt`。
- `taskType`：`waste_transport`、`clothes_collection`、`medication_delivery`、`specimen_delivery`、`ward_service`。
- `priority`：`low`、`normal`、`high`、`emergency`。
- `robotId`、`note` 可省略或為 `null`；時間使用含時區的 ISO 8601 格式。
- 建立成功表示任務資料已建立，不代表機器人已被分配或開始執行。預設設定 `TaskDispatch:Endpoint` 為 `null`，所以未設定外部分派端點時不會送出派工。

任務回應主要欄位：

```json
{
  "id": "task-id",
  "taskCode": "T0001",
  "taskType": "medication_delivery",
  "source": "nurse_station",
  "destination": "ward_a",
  "priority": "normal",
  "requiredCapabilities": ["medication_delivery"],
  "status": "pending",
  "requestedRobotId": null,
  "assignedRobot": null,
  "scheduledAt": "2026-11-09T00:00:00Z",
  "startedAt": null,
  "finishedAt": null,
  "note": "請交給護理站",
  "createdAt": "2026-11-09T00:00:00Z"
}
```

以上為欄位形狀示意，實際 ID、時間、能力需求及任務狀態由後端產生。`status` 可能值：`pending`、`assigned`、`running`、`completed`、`failed`、`cancelled`。

#### 修改排程 / 優先級

```json
PATCH /api/v1/task/{task_id}/schedule
{ "scheduledAt": "2026-11-10T09:30:00+08:00" }
```

```json
PATCH /api/v1/task/{task_id}/priority
{ "priority": "high" }
```

#### 任務狀態 SSE

連線 `GET /api/v1/task/event/trace` 後，伺服器每秒檢查狀態；狀態改變時送出 `data:` JSON 陣列：

```text
data: [{"id":"task-id","old":"pending","new":"assigned"}]
```

此串流只通知已存在任務的狀態變化，不是 WebSocket，也不會每秒送出完整任務快照。

#### 任務 API 常見錯誤

| HTTP | 說明 |
|---:|---|
| `400` | 請求欄位錯誤或時間/優先級不合法。 |
| `401` | 未登入或登入失效。 |
| `403` | 任務狀態不允許修改、刪除或重新排程。 |
| `404` | 任務不存在；Development 專用端點在非開發環境也回 `404`。 |
| `409` | 任務已送出或已指派，不能取消；或模擬抵達資料與任務不相符。 |
| `503` | 外部分派服務無法使用，或目前不支援重新排程所需的撤回操作。 |

### 機器人

| Method | Path | 說明 | 成功回應 |
|---|---|---|---|
| `GET` | `/api/robots` | 取得機器人、連線狀態及尚待確認的機器人。 | `200`，包含 `connection`、`robots`、`pendingRobots` |
| `POST` | `/api/robots/connect` | 要求連線到 ROS bridge。 | `200`，`{ success, url }` |
| `POST` | `/api/robots/disconnect` | 中斷 ROS bridge 連線。 | `200`，`{ success: true }` |
| `POST` | `/api/robots/confirm` | 更新已註冊機器人的顯示名稱。 | `200`，`{ success, rosName, displayName }` |
| `GET` | `/api/v1/robot` | 取得機器人 ID 與名稱清單。 | `200`，`[{ id, name }]` |

`POST /api/robots/connect` 請求：`{ "url": "ws://localhost:9090" }`。`url` 不可空白。

`POST /api/robots/confirm` 請求：`{ "rosName": "hospital_robot_1", "displayName": "機器人 A" }`。目前只允許更新已註冊的七台機器人，不接受新增機器人。

`GET /api/robots` 的 `connection` 包含 `url`、`status`、`failMessage`、`retryCount`；`robots` 為狀態清單，可能包括 `hasTelemetry`、`battery`、`location`、`x`、`y`、`yaw`、`currentTaskDetail` 等欄位。尚未收到遙測的註冊機器人仍會出現在清單並標為離線。

### 地點

| Method | Path | 登入 | 說明 |
|---|---|---:|---|
| `GET` | `/api/v1/place` | 是 | 取得固定地點清單，欄位為 `id`、`name`、`type`。 |

目前地點由後端固定提供，類型包含病房、護理站、部門、診間與倉儲區。

## 其他設定與限制

- CORS 允許來源由 `Server/appsettings.json` 的 `Cors:Origins` 設定；目前本機預設包含 `localhost:5173`、`5174`、`5175`。
- `GET /api.yml` 匿名提供 OpenAPI YAML；Development 環境啟用 Swagger UI。
- 目前任務查詢沒有分頁或篩選參數。
- 預設帳號資料及 Cookie 簽章金鑰儲存在後端本機 `App_Data`；這不是跨多個後端實例的共享資料庫。

## 技術選型：ASP.NET Core API 與 FastAPI

| 面向 | 本專案 ASP.NET Core Web API | FastAPI |
|---|---|---|
| 語言 / 執行環境 | C# / .NET | Python |
| 常見型別與驗證 | C# 型別、ASP.NET Core Model Binding、Data Annotations。 | Python 型別標註、Pydantic schema。 |
| 非同步處理 | `async`/`await`，整合 .NET HTTP、背景服務及中介軟體。 | `async`/`await`，常與 Python async 生態系搭配。 |
| API 文件 | 本專案以 `api.yml` 提供 OpenAPI，Development 啟用 Swagger UI。 | 常見設定可自動產生 OpenAPI 與互動式文件。 |
| 本專案用途 | 主要平台 API：登入、任務、機器人與地點。 | ROS 工作區有一份封存的舊版 `hospital_ros_api_bridge_legacy.py`，用 Python/FastAPI 接 HTTP 並連接 ROS；不等於目前主要 C# API。 |

簡單說，兩者都是建立 HTTP API 的框架；本專案主後端是 **ASP.NET Core（不是 FastAPI）**。選 ASP.NET Core 是因為主要平台服務以 C#/.NET 寫成；Python/FastAPI 適合貼近 Python/ROS 工具鏈的服務。是否更換框架要看團隊語言、部署與 ROS 整合需求，不能單憑框架名稱判定優劣。
