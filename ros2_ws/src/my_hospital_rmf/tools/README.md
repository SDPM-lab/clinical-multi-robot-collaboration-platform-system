# 場景工具使用說明

目前的場景資料流：

```text
maps/L1.building.yaml
  → tools/gazebo/rebuild_l1_gazebo_scene.sh
  → maps/L1.world + models/ + nav_graphs/

Gazebo 另存 maps/L1.sdf
  → tools/traffic_editor/sync_gazebo_to_traffic_editor.py
  → maps/L1.building.yaml / config/props.yaml
```

`L1.building.yaml` 是場景結構、模型位置與導航圖的主要來源；`L1.world`、建築模型與導航圖則屬於生成結果。

目前機器人不再直接寫入 `L1.world`。Agibot G1 由 `hospital_g1_fleet.launch.py` 根據 `fleet_instances.yaml` 在 Gazebo 啟動後動態建立。

---

## 常用指令

### 重新生成 Gazebo 世界與導航圖

修改下列任一場景相關檔案後執行：

- `maps/L1.building.yaml`
- `config/props.yaml`

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
rebuild-hospital
```

也可以直接執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

腳本預設會在 Gazebo 加入導航線與 waypoint overlay。

若只需要模擬場景，不顯示導航 overlay：

```bash
rebuild-hospital --without-nav-overlay
```

主要產出：

- `maps/L1.world`
- `models/hospital_L1/`
- `models/hospital_nav_overlay/`
- `nav_graphs/0.yaml`
- `nav_graphs/1.yaml`

其中：

- `nav_graphs/0.yaml`：RMF 機器人使用的主要導航圖。
- `nav_graphs/1.yaml`：前端 3D 場景中 Baymax、護士等人物的移動路線。

兩者都由 `L1.building.yaml` 生成，分別對應 Traffic Editor lane 的 `graph_idx: 0` 與 `graph_idx: 1`。

---

## 前端導航圖

前端不直接載入 RMF YAML。

執行：

```bash
npm run navigation:generate
```

時，`frontend/scripts/generate-rmf-navigation.sh` 會重新生成兩套導航圖，再轉換成瀏覽器可直接使用的 JSON：

- `frontend/public/generated/rmf-navigation.json`
  - 來源：Graph 0
  - 用途：主要 RMF 機器人導航圖

- `frontend/public/generated/rmf-navigation-graph-1.json`
  - 來源：Graph 1
  - 用途：前端人物或其他場景角色移動

---

## Gazebo 場景重建流程

目前完整流程共七步：

1. 從 `L1.building.yaml` 生成 `L1.world` 與 `hospital_L1`。
2. 將 Traffic Editor 產生的 OpenRobotics 模型 URI 解析為 Gazebo Fuel URI。
3. 生成 RMF 導航圖。
4. 生成選用的 Gazebo 導航 overlay。
5. 將導航 overlay 加入 `L1.world`。
6. 依 `props.yaml` 套用額外模型、模型替換與縮放。
7. 加入供 DART 使用的隱形 primitive physics floor。

目前不再於場景重建階段加入機器人。

G1 機器人會在正式啟動時，由：

```text
config/fleet_instances.yaml
        ↓
hospital_g1_fleet.launch.py
        ↓
g1_hospital_robot.launch.py
        ↓
Gazebo 動態 spawn
```

建立到既有的 `L1.world` 中。

目前大部分家具來自 `OpenRobotics/...`。

最後的 world 可能引用本機 `*_real` 模型，這是因為 Fuel 原始模型經縮放或位置修正後存成本機模型；不代表 Fuel URI 解析步驟沒有使用。

---

## 重新編譯

場景、launch、config 或 script 修改完成後，可重新編譯：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws

colcon build \
  --symlink-install \
  --packages-select my_hospital_rmf

source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

---

## 同步 Gazebo 模型位置

若直接在 Gazebo GUI 中調整模型位置，可將調整結果反向同步回來源設定。

### 操作流程

1. 在 Gazebo 將目前世界另存為：

```text
maps/L1.sdf
```

2. 執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

同步工具會：

- 將模型位置寫回 `maps/L1.building.yaml`。
- 將額外模型位置寫回 `config/props.yaml`。
- 移除 Gazebo SDF 中不存在的模型。
- 將修改前的檔案備份到 `backups/`。
- `backups/` 最多保留 5 次同步備份。

此工具會直接修改來源 YAML，因此同步後應先查看 Git diff。

完成後再執行：

```bash
rebuild-hospital
```

重新生成正式 Gazebo 場景。

> `L1.sdf` 不是正式啟動時使用的 world。
>
> 正式模擬使用的是 `maps/L1.world`；`L1.sdf` 主要作為 Gazebo GUI 調整後，反向同步位置資訊的中介檔案。

---

## 腳本用途

| 路徑 | 用途 |
|------|------|
| `gazebo/rebuild_l1_gazebo_scene.sh` | 執行完整 L1 Gazebo 場景生成流程 |
| `gazebo/add_nav_overlay.py` | 將生成好的導航 overlay 加入 `L1.world` |
| `gazebo/patch_props.py` | 套用 `props.yaml` 的模型替換、額外模型與縮放 |
| `gazebo/patch_fuel_uris.py` | 將 OpenRobotics `model://` URI 改為 Gazebo Fuel URI |
| `gazebo/generate_nav_overlay_model.py` | 生成 Gazebo 導航路網覆蓋層 |
| `gazebo/add_physics_floor.py` | 在 world 中加入供 DART 使用的隱形 primitive floor |
| `traffic_editor/sync_gazebo_to_traffic_editor.py` | 將 Gazebo SDF 中的模型位置同步回來源設定 |
| `blender/blender_import_hospital_proxy.py` | 從 `L1.world` 產生 Blender 代理場景 |

---

# G1 機器人設定

目前醫院模擬使用 Agibot G1，並採用動態 Fleet 架構。

機器人不再直接寫入 `L1.world`，而是在 Gazebo 啟動後由 launch 動態加入。

主要流程：

```text
robot_profiles.yaml
       ↓
fleet_instances.yaml
       ↓
hospital_g1_fleet.launch.py
       ↓
g1_hospital_robot.launch.py
       ↓
Gazebo G1
```

---

## 機器人設定檔分工

### `config/robot_profiles.yaml`

定義「機器人類型」。

例如：

```yaml
robot_types:
  clean:
    model: agibot_g1
    capabilities:
      - waste_transport
      - clothes_collection

  medical:
    model: agibot_g1
    capabilities:
      - specimen_delivery
      - medication_delivery

  ward:
    model: agibot_g1
    capabilities:
      - medication_delivery
      - ward_service
```

目前不同功能型機器人可共用同一個 G1 模型，但透過 capability 區分可執行的任務。

---

### `config/fleet_instances.yaml`

定義目前實際存在的機器人 instance。

例如：

```yaml
robots:
  hospital_robot_1:
    type: clean
    model: agibot_g1
    enabled: true

    spawn:
      x: 8.953
      y: -16.200
      z: 0.2
      yaw: 0.0

    rmf:
      start_waypoint: left_mid_junction
      charger: charging_station_2
```

欄位說明：

- `type`
  - 必須存在於 `robot_profiles.yaml`。

- `model`
  - 目前使用 `agibot_g1`。

- `enabled`
  - `true`：正式啟動時建立此機器人。
  - `false`：保留設定但不建立。

- `spawn`
  - Gazebo 中的初始位置與朝向。

- `rmf.start_waypoint`
  - RMF 認定的初始 waypoint。
  - 必須存在於 `nav_graphs/0.yaml`。

- `rmf.charger`
  - 此機器人的充電站 waypoint。

---

### `config/fleet_config.yaml`

此檔仍提供官方 RMF Fleet Adapter 與 Fleet Manager 使用，包括：

- fleet 名稱
- 線速度與角速度限制
- footprint / vicinity
- reversible 設定
- Fleet Manager IP / port
- RMF robot 初始 waypoint
- charger
- start pose

目前新增或移除實際機器人時，`fleet_instances.yaml` 與 `fleet_config.yaml` 的 robot 設定仍需要同步。

後續可再將這個同步流程自動化，避免重複維護。

---

## 新增機器人

新增一台機器人時，主要在：

```text
config/fleet_instances.yaml
```

新增 instance。

例如：

```yaml
hospital_robot_2:
  type: medical
  model: agibot_g1
  enabled: true

  spawn:
    x: 10.0
    y: -10.0
    z: 0.2
    yaw: 0.0

  rmf:
    start_waypoint: some_waypoint
    charger: charging_station_2
```

需要注意：

1. `type` 必須存在於 `robot_profiles.yaml`。
2. `start_waypoint` 必須存在於 `nav_graphs/0.yaml`。
3. Gazebo `spawn` 應盡量與 RMF `start_waypoint` 座標一致。
4. `fleet_config.yaml` 中也必須具有對應的 RMF robot 設定。
5. `hospital_g1_fleet.launch.py` 會自動建立所有 `enabled: true` 的 G1。

---

## G1 Launch 架構

### `launch/g1_hospital_robot.launch.py`

負責單台 G1。

主要工作：

- 產生 G1 `robot_description`
- 設定 namespace
- 啟動 `robot_state_publisher`
- 動態 spawn Gazebo entity
- 啟動 `joint_state_broadcaster`
- 啟動 `diff_drive_controller`
- 建立 namespaced `/cmd_vel`
- 建立對應 odometry

單台 G1 的 namespace 例如：

```text
/hospital_robot_1
```

常用 topic：

```text
/hospital_robot_1/cmd_vel
/hospital_robot_1/diff_drive_controller/cmd_vel
/hospital_robot_1/diff_drive_controller/odom
/hospital_robot_1/joint_states
/hospital_robot_1/robot_description
```

---

### `launch/hospital_g1_fleet.launch.py`

負責根據：

```text
config/fleet_instances.yaml
```

批次建立所有啟用的 G1。

獨立執行時：

```bash
ros2 launch my_hospital_rmf hospital_g1_fleet.launch.py
```

第一台 G1 可同時負責啟動 Gazebo world。

若由正式 `hospital.launch.py` 啟動：

```text
start_world=false
```

此時 Gazebo world 已由主 launch 啟動，G1 Fleet 只負責動態 spawn 機器人。

---

# RMF 與 G1 導航

目前正式模擬使用：

```text
scripts/hospital_g1_navigation_bridge.py
```

作為 RMF 與 G1 之間的導航橋接。

主要流程：

```text
RMF / Fleet Manager
        ↓
/robot_path_requests
        ↓
hospital_g1_navigation_bridge
        ↓
/hospital_robot_N/cmd_vel
        ↓
diff_drive_controller
        ↓
gz_ros2_control
        ↓
Gazebo G1
        ↓
odometry
        ↓
hospital_g1_navigation_bridge
        ↓
/robot_state
        ↓
Fleet Manager / RMF
```

Navigation Bridge 會：

- 訂閱 `/robot_path_requests`
- 根據 waypoint 計算轉向與前進速度
- 發布 `/hospital_robot_N/cmd_vel`
- 訂閱 G1 odometry
- 將 odom-relative pose 轉換成醫院 map pose
- 發布 `/robot_state`
- 回報目前 task id、移動狀態與剩餘 path

---

## Odom 與 Map 座標

G1 的 odometry 是相對於 spawn 起點：

```text
odom = (0, 0)
```

而 RMF 使用醫院 map 座標。

因此 Navigation Bridge 會使用：

```text
fleet_instances.yaml → spawn
```

進行轉換：

```text
map_x = x0 + cos(yaw0) * odom_x - sin(yaw0) * odom_y

map_y = y0 + sin(yaw0) * odom_x + cos(yaw0) * odom_y

map_yaw = yaw0 + odom_yaw
```

因此 G1 即使 odometry 從 `(0, 0)` 開始，RMF 仍會看到正確的醫院位置。

---

## Fake Robot

仍保留：

```text
scripts/hospital_fake_robot_state_publisher.py
```

但它不屬於正式 G1 模擬流程。

此程式主要用途為：

- RMF 輕量測試
- 不啟動 Gazebo 時測試 RMF topic
- Scheduler / task flow 開發
- baseline 或 regression test
- 除錯 `/robot_path_requests` 與 `/robot_state`

正式醫院模擬使用：

```text
hospital_g1_navigation_bridge.py
```

不應同時啟動 Fake Robot publisher 與 G1 Navigation Bridge，避免兩者同時發布 `/robot_state`。

---

# 正式啟動醫院模擬

先進入 workspace：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
```

載入 ROS 2：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

設定 DDS：

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=22

export CYCLONEDDS_URI="<CycloneDDS><Domain><General><NetworkInterfaceAddress>127.0.0.1</NetworkInterfaceAddress></General></Domain><Discovery><ParticipantIndex>auto</ParticipantIndex></Discovery></CycloneDDS>"
```

設定 Gazebo model path：

```bash
export GZ_SIM_RESOURCE_PATH="$PWD/src/my_hospital_rmf/models:${GZ_SIM_RESOURCE_PATH:-}"
```

如果需要 door plugin：

```bash
DOOR_LIB=$(find /opt/ros/jazzy \
  -type f \
  -name "libdoor.so" \
  -print -quit)

if [ -n "$DOOR_LIB" ]; then
  export GZ_SIM_SYSTEM_PLUGIN_PATH="$(dirname "$DOOR_LIB"):${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
fi
```

啟動：

```bash
ros2 launch my_hospital_rmf hospital.launch.py \
  use_sim_time:=true
```

若不需要 RViz：

```bash
ros2 launch my_hospital_rmf hospital.launch.py \
  use_sim_time:=true \
  launch_rviz:=false
```

---

# 驗證 G1

## 檢查模擬時間

```bash
ros2 topic echo /clock --once
```

再次執行時時間應持續增加。

---

## 檢查 Controller

```bash
ros2 control list_controllers \
  -c /hospital_robot_1/controller_manager
```

正常情況：

```text
diff_drive_controller    ... active
joint_state_broadcaster  ... active
```

---

## 檢查 Odometry

```bash
ros2 topic echo \
  /hospital_robot_1/diff_drive_controller/odom \
  --once
```

---

## 檢查 RMF RobotState

```bash
ros2 topic echo \
  /robot_state \
  --once
```

應可看到：

```yaml
name: hospital_robot_1
model: hospital_fleet
mode:
  mode: 0

location:
  level_name: L1

path: []
```

---

# Fleet Manager

Fleet Manager 設定位於：

```text
config/fleet_config.yaml
```

目前預設：

```yaml
fleet_manager:
  ip: 127.0.0.1
  port: 22013
```

查詢機器人狀態：

```bash
curl -s \
  "http://127.0.0.1:22013/open-rmf/rmf_demos_fm/status/?robot_name=hospital_robot_1" \
  | python3 -m json.tool
```

---

## Fleet Manager Navigation Test

此 API 可直接測試：

```text
Fleet Manager
→ /robot_path_requests
→ G1 Navigation Bridge
→ Gazebo G1
```

例如：

```bash
curl -s -X POST \
  "http://127.0.0.1:22013/open-rmf/rmf_demos_fm/navigate/?robot_name=hospital_robot_1&cmd_id=9001" \
  -H "Content-Type: application/json" \
  -d '{
    "map_name": "L1",
    "destination": {
      "x": 8.952,
      "y": -14.843,
      "yaw": 0.0
    },
    "speed_limit": 0.25
  }' \
  | python3 -m json.tool
```

可以另外監看：

```bash
ros2 topic echo /robot_path_requests
```

此方式主要用於底層導航整合測試。

正式任務派工之後會由 Scheduler / RMF Task Flow 從更上層產生導航命令，不需要人工直接呼叫 Fleet Manager `/navigate/`。

---

# 新增額外模型

額外模型放在：

```text
config/props.yaml
```

例如：

```yaml
props:
  - name: unique_name
    uri: "https://fuel.gazebosim.org/1.0/OWNER/models/MODEL"
    pose:
      - x
      - y
      - z
      - roll
      - pitch
      - yaw
```

注意：

- `name` 不可重複。
- 修改後需重新執行 `rebuild-hospital`。
- 若模型需要特殊縮放，應在 `props.yaml` 中設定，而不是直接修改生成後的 `L1.world`。

---

# 開發原則

## 哪些是來源檔案

主要來源：

```text
maps/L1.building.yaml
config/props.yaml
config/robot_profiles.yaml
config/fleet_instances.yaml
config/fleet_config.yaml
```

應優先修改這些檔案。

---

## 哪些是生成結果

以下內容通常不建議直接手動修改：

```text
maps/L1.world
models/hospital_L1/
models/hospital_nav_overlay/
nav_graphs/0.yaml
nav_graphs/1.yaml
```

因為重新執行場景生成工具後可能會被覆寫。

---

## 備份

開發過程不再於 source tree 中長期保留：

```text
*.backup_*
*.bak
```

版本回溯統一使用 Git。

`sync_gazebo_to_traffic_editor.py` 自己建立的 `backups/` 屬於工具執行時的短期保護機制，可保留最近數次同步結果。

---

# 目前系統架構摘要

```text
Traffic Editor
    │
    ▼
L1.building.yaml
    │
    ├──────────────► nav_graphs/
    │
    ▼
L1.world
    │
    ▼
Gazebo
    │
    ├── hospital_G1_fleet
    │       │
    │       └── Agibot G1
    │
    ▼
gz_ros2_control
    │
    ▼
diff_drive_controller
    │
    ▲
    │ cmd_vel
hospital_g1_navigation_bridge
    │
    ├── odom → map pose
    ├── /robot_state
    └── /robot_path_requests
            ▲
            │
      Fleet Manager
            ▲
            │
      RMF Fleet Adapter
            ▲
            │
      Scheduler / Task Flow
```

目前已完成的底層整合包含：

- Gazebo 醫院場景
- Agibot G1 動態 spawn
- Namespaced `ros2_control`
- Differential-drive 控制
- G1 odometry
- Map / odom 座標轉換
- `/robot_state`
- `/robot_path_requests`
- Fleet Manager navigation
- G1 實際 Gazebo 閉環移動

Task Dispatcher、Baseline Scheduler、RL Scheduler 與完整多機器人任務派工流程將在後續整合。
