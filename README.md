# Clinical Multi-Robot Collaboration Platform System

醫療院所多機器人協作平台，讓護理人員可以透過網頁派遣機器人執行清潔、消毒、鍍膜殺菌等任務，底層由 Open-RMF 負責路徑規劃與機器人排程。

---

## 系統架構全貌

```
┌──────────────────────────────────────────────────────────────────┐
│  瀏覽器 (醫護人員)                                                │
│  frontend/  (Vue 3 + Vite)  :5174                                │
└────────────────┬─────────────────────────┬───────────────────────┘
                 │ HTTP REST               │ WebSocket :9090
                 ▼                         ▼
┌────────────────────────┐   ┌─────────────────────────────────────┐
│  backend/              │   │  hospital_rosbridge_ws_adapter.py   │
│  ASP.NET Core  :5000   │   │  (把 /fleet_states 推到瀏覽器)       │
└────────┬───────────────┘   └──────────────┬──────────────────────┘
         │ HTTP POST /api/hospital/tasks      │ 訂閱 ROS topic
         ▼                                   │
┌─────────────────────────────┐              │
│  hospital_ros_api_bridge.py │ ─────────────┘
│  FastAPI  :5050             │
│  ・接收 HTTP → 發 ROS topic  │
│  ・訂閱 fleet_states         │
└────────┬────────────────────┘
         │ pub /hospital_task_request (String)
         ▼
┌──────────────────────────────┐
│  hospital_rule_dispatcher.py │
│  ROS 2 Node                  │
│  ・聽任務請求                  │
│  ・依距離/電量/忙碌選最佳機器人  │
│  ・發 /task_api_requests      │
└────────┬─────────────────────┘
         │ pub /task_api_requests (ApiRequest)
         ▼
┌──────────────────────────────────────────────┐
│  Open-RMF 核心 + rmf_demos_fleet_adapter     │
│  ・路徑規劃                                   │
│  ・pub /robot_path_requests (PathRequest)    │
│  ・pub /fleet_states (FleetState)            │
└────────┬──────────────────────┬──────────────┘
         │                      │
         ▼                      ▼
┌──────────────────────┐  ┌────────────────────────────┐
│  hospital_fake_robot │  │  所有訂閱 /fleet_states 的人 │
│  _state_publisher.py │  │  (bridge / ws_adapter)      │
│  ・模擬 2 台機器人移動  │  └────────────────────────────┘
│  ・pub /robot_state  │
└──────────────────────┘
```

---

## 各資料夾說明

### `frontend/`

**Vue 3 + Vite** 前端儀表板，給醫護人員使用。

| 路徑 | 用途 |
|------|------|
| `src/components/views/` | 各個頁面：機器人狀態、任務派遣、地圖、警報、甘特圖 |
| `src/components/` | 共用元件：RobotCard、TaskModal、NotificationBell 等 |
| `src/js/composables/` | Vue composables：`useRobots`、`useTasks`、`useRosBridge`（WebSocket 連線） |
| `src/js/data/` | 靜態設定資料：地圖 topics、選單、任務類型 |
| `src/router/` | Vue Router 路由設定 |
| `vite.config.js` | Vite 開發伺服器設定，proxy 到後端 |

**輸入**：護理人員的操作  
**輸出**：HTTP 請求到 backend :5000；WebSocket 訂閱 :9090 取得機器人即時位置

---

### `backend/`

**ASP.NET Core 8** REST API，任務管理核心。

| 路徑 | 用途 |
|------|------|
| `Server/Controllers/TaskController.cs` | 任務 CRUD、SSE 事件串流 (`GET /api/v1/task/event/trace`) |
| `Server/Controllers/RobotController.cs` | 機器人狀態查詢 |
| `Server/Controllers/PlaceController.cs` | 地點資訊 |
| `Server/Services/TaskService.cs` | 任務邏輯：建立任務後 **轉發 HTTP POST** 到 Python ROS bridge (:5050)；地點名稱對應 RMF waypoint |
| `Server/Services/RobotStateStore.cs` | 從 WebSocket adapter 抓機器人狀態快照 |
| `Server/Models/RobotTask.cs` | 任務資料模型（id、title、place、items、status…） |
| `Server/appsettings.json` | 設定 `RosBridge:BaseUrl`（預設 http://localhost:5050） |
| `Server.Tests/` | 整合測試 + 單元測試 |
| `api.yml` | OpenAPI 規格文件 |
| `socket.yml` | WebSocket 介面文件 |

**地點對照表**（`TaskService.cs` 中）：

| 前端地點 | RMF Waypoint |
|---------|-------------|
| ward-3f | ward_a |
| ward-2f | ward_b |
| emergency | procedure_room |
| corridor-1f | nurse_station |

**輸入**：前端 HTTP 請求  
**輸出**：HTTP POST → `hospital_ros_api_bridge.py` :5050

---

### `ros2_ws/src/my_hospital_rmf/`

**ROS 2 / Open-RMF** 醫院整合套件，共四個 Python 節點。

#### `maps/`

| 檔案 | 來源 | 說明 |
|------|------|------|
| `hospital_floor.png` | **手動放入**（底圖） | 工程圖底圖，匯入 traffic-editor 時使用 |
| `hospital_floor_real.png` | **手動放入**（底圖） | 較精確的實際底圖 |
| `hospital.building.yaml` | **手動用 traffic-editor 編輯** | 定義所有 waypoints（護理站、病房、充電站…）、lane 連結、測量比例 → 這是整個地圖的「唯一真實來源」 |
| `hospital.world` | **由 hospital.building.yaml 生成** (`rmf_building_map_tools`) | Gazebo 模擬世界檔 |

#### `models/hospital_L1/`

| 檔案 | 來源 | 說明 |
|------|------|------|
| `model.config` | **由 hospital.building.yaml 生成** | Gazebo 模型 metadata |
| `model.sdf` | **由 hospital.building.yaml 生成** | Gazebo 模型幾何定義（牆壁、走道） |

#### `nav_graphs/`

| 檔案 | 來源 | 說明 |
|------|------|------|
| `0.yaml` | **由 hospital.building.yaml 生成** | Open-RMF 導航圖：waypoint 座標 + lane 連結。被 fleet adapter 和 Python 腳本讀取 |

> **生成流程**：`hospital.building.yaml` → `rmf_building_map_tools`（`building_map_generator`）→ `hospital.world` + `models/hospital_L1/` + `nav_graphs/0.yaml`

#### `config/fleet_config.yaml`

**手動設定**。定義機器人艦隊參數：速度上限、車體尺寸、電池系統、充電策略、兩台機器人的充電站位置（`charging_station`）。

**輸入**：`hospital.launch.xml` 啟動時讀取  
**輸出**：告訴 fleet adapter 如何管理 `hospital_robot_1`、`hospital_robot_2`

#### `launch/hospital.launch.xml`

**輸入**：`maps/hospital.building.yaml`、`nav_graphs/0.yaml`、`config/fleet_config.yaml`  
**輸出**：啟動 Open-RMF 共用節點（排程、交通管理、視覺化）+ 醫院艦隊 adapter

#### `scripts/` — 四個 Python 節點

---

### `scripts/hospital_fake_robot_state_publisher.py`

**模擬機器人**（無真實硬體時使用）。

| 機器人 | 起始位置 |
|--------|---------|
| hospital_robot_1 | charging_station_junction |
| hospital_robot_2 | storage_junction |

```
輸入  /robot_path_requests  ← Open-RMF fleet adapter 下發的路徑
輸出  /robot_state          → fleet adapter 接收位置回報
```

以 0.2 秒 timer 更新位置（速度 0.6 m/s），模擬機器人沿路徑點移動。到達目的地後清空 task_id 表示任務完成。

---

### `scripts/hospital_ros_api_bridge.py`

**HTTP ↔ ROS 橋接**（FastAPI :5050）。讓 .NET backend 透過 HTTP 發任務進 ROS。

```
輸入（HTTP）  POST /api/hospital/tasks  ← backend
輸出（ROS）   /hospital_task_request    → rule_dispatcher

輸入（ROS）   /fleet_states             ← fleet adapter
輸出（HTTP）  GET  /api/hospital/robots → frontend/backend 查詢用
```

---

### `scripts/hospital_rule_dispatcher.py`

**任務派遣決策節點**。收到任務後選最合適的機器人。

選擇邏輯（score 最小者獲選）：
```
score = 與目標的歐氏距離
      + 1000  (若機器人正在執行任務)
      + 500   (若電量 < 20%)
```

```
輸入  /hospital_task_request  ← ros_api_bridge（任務 JSON）
輸入  /fleet_states           ← fleet adapter（機器人即時狀態）
輸出  /task_api_requests      → Open-RMF 核心（標準 RMF 任務格式）
```

---

### `scripts/hospital_rosbridge_ws_adapter.py`

**WebSocket 推播伺服器**（:9090）。把 ROS 的 `/fleet_states` 即時推送到瀏覽器前端，格式相容 rosbridge protocol。

```
輸入  /fleet_states  ← fleet adapter（ROS topic）
輸出  ws://localhost:9090  → 前端 useRosBridge composable
```

---

## 預設 Port 對照

| 服務 | Port | 技術 |
|------|------|------|
| Vue 前端 | 5174 | Vite dev server |
| .NET 後端 | 5000 | ASP.NET Core |
| ROS API Bridge | 5050 | FastAPI / uvicorn |
| WebSocket Adapter | 9090 | websockets (Python) |
| RMF Web API Server | 8000 | rmf_api_server |
| RMF Dashboard | 5173 | rmf-web |

---

## 啟動順序

```bash
# 1. Open-RMF Web API Server（RMF 任務管理後台）
#    https://github.com/open-rmf/rmf_api_server

# 2. RMF Dashboard（選用，RMF 自己的監控 UI）

# 3. 模擬機器人（無實體時）
ros2 run my_hospital_rmf hospital_fake_robot_state_publisher

# 4. Open-RMF 主體（排程 + 艦隊 adapter）
ros2 launch my_hospital_rmf hospital.launch.xml

# 5. 規則派遣器
ros2 run my_hospital_rmf hospital_rule_dispatcher

# 6. ROS HTTP API Bridge（讓 .NET 可以呼叫 ROS）
ros2 run my_hospital_rmf hospital_ros_api_bridge
# 或直接執行：python3 hospital_ros_api_bridge.py

# 7. WebSocket Adapter（把機器人狀態推到瀏覽器）
ros2 run my_hospital_rmf hospital_rosbridge_ws_adapter

# 8. .NET 後端
cd backend && dotnet run --project Server

# 9. Vue 前端
cd frontend && npm run dev
```

---

## 完整任務流程（以派遣機器人去 ward_a 為例）

```
護理人員在前端填寫任務（地點: ward-3f, 事項: clean-object）
  ↓ HTTP POST /api/v1/task
.NET Backend 建立任務，映射地點 ward-3f → ward_a
  ↓ HTTP POST http://localhost:5050/api/hospital/tasks
hospital_ros_api_bridge.py 收到，發布到 ROS
  ↓ /hospital_task_request  {"target":"ward_a","task_type":"go_to_place"}
hospital_rule_dispatcher.py 收到，查當前 /fleet_states：
  - hospital_robot_1 在 charging_station_junction，距離 500，空閒
  - hospital_robot_2 在 storage_junction，距離 800，空閒
  → 選 hospital_robot_1（score 較低）
  ↓ /task_api_requests  (RMF ApiRequest JSON)
Open-RMF 核心 路徑規劃，計算 charging_station_junction → ward_a 路徑
  ↓ /robot_path_requests  (PathRequest with waypoints)
hospital_fake_robot_state_publisher.py 收到路徑，開始模擬移動
  ↓ /robot_state  (每 0.2 秒更新位置)
Open-RMF fleet adapter 彙整成 FleetState
  ↓ /fleet_states
hospital_rosbridge_ws_adapter.py 廣播
  ↓ WebSocket ws://localhost:9090
前端 useRosBridge.js 更新 RobotCard 顯示機器人位置
```

---

## 地圖 Waypoints（`nav_graphs/0.yaml` / `hospital.building.yaml`）

| Waypoint 名稱 | 對應位置 |
|--------------|---------|
| nurse_station | 護理站 |
| ward_a ~ ward_d | 各病房 |
| consult_1 ~ consult_3 | 診間 |
| charging_station | 充電站 |
| procedure_room | 處置室 |
| pharmacy | 藥房 |
| lab | 檢驗室 |
| blood_draw | 抽血室 |
| storage | 倉庫 |
| meeting_room | 會議室 |
| director_room | 主任室 |
| ultrasound / ecg / therapy_room | 各檢查室 |
| reception_back | 櫃台後方 |
| *_junction | 走道交叉點（不是目的地，是路徑中繼點） |
