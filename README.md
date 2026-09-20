# Clinical Multi-Robot Collaboration Platform System

醫療院所多機器人協作平台，讓護理人員可以透過網頁派遣機器人執行清潔、消毒、鍍膜殺菌等任務，底層由 Open-RMF 負責路徑規劃與機器人排程。

---

## 系統架構全貌

```
┌──────────────────────────────────────────────────────────────────┐
│  瀏覽器 (醫護人員)                                                │
│  frontend/  (Vue 3 + Vite + Three.js)  :5174                     │
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

**Vue 3 + Vite + Three.js** 醫院多機器人營運平台前端。目前正在重新設計 UI；第一階段首頁顯示可操作的靜態醫院 3D 環境，尚未接入即時機器人、人物、任務、路線或統計資料。

| 路徑 | 用途 |
|------|------|
| `src/views/AppShellView.vue` | 應用程式共用外殼，負責 Navbar 與頁面切換 |
| `src/views/ClinicOverviewView.vue` | Overview 首頁 Dashboard 與三層診所模型 |
| `src/components/scene/HospitalScene.vue` | Three.js 場景、GLB 載入、透視相機取景、OrbitControls、燈光、陰影與資源清理 |
| `src/config/sceneAssets.js` | 3D 資產路徑、場景分層與嵌入式動態物件的精確過濾設定 |
| `public/models/` | 瀏覽器直接讀取的 GLB 模型資產 |
| `src/js/composables/` | Vue composables：`useRobots`、`useTasks`、`useRosBridge`（WebSocket 連線） |
| `src/components/`、`src/components/views/` | 舊版任務、機器人、警報等元件暫時保留，但目前沒有掛到新版首頁路由 |
| `src/router/` | Vue Router 路由設定；目前 `/` 顯示新版 Overview |
| `vite.config.js` | Vite 開發伺服器設定，proxy 到後端 |

### Overview 第一階段

目前已完成：

- 以 `GLTFLoader` 載入醫院 GLB。
- 3D 場景填滿整個瀏覽器，不放在 Dashboard 卡片內。
- 保留 GLB 原始材質、貼圖與家具顏色，不修改模型內的材質資料。
- 使用 `PerspectiveCamera` 與 `OrbitControls`，支援滑鼠旋轉、滾輪縮放和拖曳平移。
- 使用 `Box3` 自動計算模型邊界、將模型置中，並依模型尺寸與相機 FOV 自動調整初始距離。
- Resize 時更新透視相機 aspect 與 renderer 尺寸。
- 使用 sRGB 色彩空間、ACES Filmic tone mapping、柔和環境光、方向光及陰影地面。
- 限制 device pixel ratio，並使用 `ResizeObserver` 更新畫面尺寸。
- 顯示中文載入進度及明確的模型載入錯誤。
- Vue 元件卸載時清除動畫、OrbitControls、geometry、material、texture、shadow map、renderer 和 WebGL context。

目前未實作：新版 Top Navbar、淺／深色切換、OpenRMF 即時位置、ROS 2 WebSocket、機器人路線、任務派遣 UI、人物動畫、統計卡片和警報資料。

### 3D 場景資產分層

| 資產／群組 | 現況 | 用途 |
|------------|------|------|
| `public/models/hospital_L1_environment.glb` | 已建立並由即時地圖載入 | 有效場景只掛載醫院建築、牆壁、地板、門、櫃台、設備及靜態家具；內嵌動態根節點不會進入可見場景 |
| `public/models/hospital_L1.glb` | 保留的一樓完整匯出模型 | 包含原場景中的機器人與人物，僅作來源／檢查用途，不由即時地圖載入 |
| `robot_*.glb` | 尚未建立／載入 | 未來由 OpenRMF／ROS 2 座標獨立控制 |
| `character_*.glb` | 尚未建立／載入 | 未來獨立控制人物位置、材質與動畫 |
| `environmentGroup` | 可見 | 靜態醫院環境；若未來需要素色材質，只能套用在此群組 |
| `robotGroup` | 隱藏 | 預留機器人圖層，目前不載入模型 |
| `characterGroup` | 隱藏 | 預留人物圖層，目前不載入模型 |
| `overlayGroup` | 隱藏 | 預留路線、標記和即時狀態圖層 |

原始 Blender 場景位於專案根目錄的 `blender/scenes/floor_L1.blend`。完整模型曾檢查到 3 個機器人、3 個坐姿女性訪客、1 個坐姿男性訪客、1 個站立人物、1 個女性訪客與 1 個護理師。`scripts/create-environment-glb.mjs` 會從完整 GLB 的有效場景根節點解除這些動態物件，不修改或刪除原始 Blender 場景，也不改動其他靜態 Node、Mesh、材質或貼圖。

Blender 場景儲存後，可在 `frontend` 目錄執行以下命令，一次重建完整模型與 Overview 環境模型：

```bash
cd frontend
npm run models:update
```

此命令會將 Blender 中目前可見的一樓物件匯出為 `public/models/hospital_L1.glb`，再產生不含動態人物與機器人場景根節點的 `public/models/hospital_L1_environment.glb`。

動態物件名稱設定集中在 `src/config/sceneAssets.js`。設定使用完整物件名稱，不使用模糊的 `robot` 或 `nurse` 關鍵字，避免將 `OpenRobotics` 靜態家具、`NurseTable` 或 `NurseMonitor` 誤判為動態物件。

### 啟動前端

```bash
cd frontend
npm install
npm run dev
```

正式建置檢查：

```bash
cd frontend
npm run build
```

若只看到載入畫面或錯誤訊息，請確認 `frontend/public/models/hospital_L1_environment.glb` 存在，並檢查瀏覽器開發者工具的 Network 與 Console。GLB 約 11 MB，第一次載入需要一些時間。

舊版 composables 仍保留原本的 HTTP／WebSocket 能力，但本階段的新版 Overview 不會建立 ROSBridge 連線，也不會顯示即時或假造的機器人資料。

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
| `L1.building.yaml` | **手動用 traffic-editor 編輯** | 定義所有 waypoints（護理站、病房、充電站…）、lane 連結、測量比例 → 這是整個地圖的「唯一真實來源」 |
| `L1.world` | **由 L1.building.yaml 生成** (`rmf_building_map_tools`) | Gazebo 模擬世界檔 |

#### `models/hospital_L1/`

| 檔案 | 來源 | 說明 |
|------|------|------|
| `model.config` | **由 L1.building.yaml 生成** | Gazebo 模型 metadata |
| `model.sdf` | **由 L1.building.yaml 生成** | Gazebo 模型幾何定義（牆壁、走道） |

#### `nav_graphs/`

| 檔案 | 來源 | 說明 |
|------|------|------|
| `0.yaml` | **由 L1.building.yaml 生成** | Graph 0：Open-RMF 機器人導航圖，被 fleet adapter、模擬機器人與 Gazebo overlay 使用 |
| `1.yaml` | **由 L1.building.yaml 生成** | Graph 1：前端 3D 場景中 Baymax、護士等人物的移動路線 |

> **生成流程**：`L1.building.yaml` → `rmf_building_map_tools`（`building_map_generator`）→ `L1.world` + `models/hospital_L1/` + `nav_graphs/{0,1}.yaml`。前端再將兩套 YAML 轉成 `frontend/public/generated/` 下的 JSON。

#### `config/fleet_config.yaml`

**手動設定**。定義機器人艦隊參數：速度上限、車體尺寸、電池系統、充電策略、兩台機器人的充電站位置（`charging_station`）。

**輸入**：`hospital.launch.py` 啟動時讀取
**輸出**：告訴 fleet adapter 如何管理 `hospital_robot_1`、`hospital_robot_2`

#### `launch/hospital.launch.py`

**輸入**：`maps/L1.building.yaml`、`nav_graphs/0.yaml`、`config/fleet_config.yaml`
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
ros2 launch my_hospital_rmf hospital.launch.py

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

## 地圖 Waypoints（`nav_graphs/0.yaml` / `L1.building.yaml`）

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
