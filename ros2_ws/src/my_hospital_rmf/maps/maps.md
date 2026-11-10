# maps 使用說明

此資料夾主要存放 Traffic Editor、Gazebo、Nav2 與 RMF 使用的地圖與世界檔案。

目前正式場景的主要來源是：

```text
maps/L1.building.yaml
```

Gazebo 正式啟動使用：

```text
maps/L1.world
```

而：

```text
maps/L1.sdf
```

主要作為 Gazebo GUI 另存後，供模型位置反向同步工具讀取的中介檔案。

---

## 檔案用途

| 檔案 | 用途 | 是否手動修改 |
|------|------|--------------|
| `L1.building.yaml` | Traffic Editor 建築、模型、waypoint 與 lane 的主要來源 | 是 |
| `hospital_floor.png` | Traffic Editor / 舊場景底圖資源 | 視需要 |
| `hospital_floor_real.png` | Traffic Editor 與 Nav2 使用的主要地圖圖片 | 視需要替換 |
| `L1.yaml` | Nav2 map_server 使用的地圖解析度、原點與障礙物門檻 | 是 |
| `L1.sdf` | Gazebo 另存後供同步工具讀取的中介世界檔 | 由 Gazebo 另存 |
| `L1.world` | 正式 Gazebo 模擬啟動使用的世界 | 否，由工具生成 |

> `L1.building.yaml` 是主要來源資料。
>
> `L1.world`、建築模型與 RMF navigation graph 都是由工具重新生成的結果。
>
> `L1.sdf` 不是正式模擬啟動來源，應保留作為現有 Gazebo → Traffic Editor 同步流程的中介檔。

---

# Traffic Editor 地圖欄位

`L1.building.yaml` 的 `L1` 樓層目前包含類似以下設定：

```yaml
drawing:
  filename: hospital_floor_real.png

elevation: 0

lanes:
  - [26, 3, {...}]
```

各欄位用途如下。

## `drawing`

Traffic Editor 顯示的底圖設定區塊。

例如：

```yaml
drawing:
  filename: hospital_floor_real.png
```

`drawing.filename` 指定 Traffic Editor 顯示的底圖。

圖片本身只提供：

- 場景繪製參考
- waypoint 定位參考
- lane 配置參考

圖片不會保存 waypoint 或 lane。

---

## `elevation`

例如：

```yaml
elevation: 0
```

代表此樓層在建築物中的高度，單位為公尺。

目前：

```text
L1 elevation = 0 m
```

---

## `vertices`

waypoint 儲存在：

```yaml
vertices:
  - [687.429, 652.016, 0, reception_back]
  - [1017.12, 296.264, 0, charging_station, {is_charger: [1, true]}]
```

其中包含：

- waypoint 在 Traffic Editor 底圖中的座標
- waypoint 名稱
- 額外 RMF 屬性

例如：

```yaml
{is_charger: [1, true]}
```

表示該 waypoint 可作為充電站。

---

## `lanes`

lane 定義 waypoint 之間的導航連線。

例如：

```yaml
- [26, 3, {...}]
```

代表連接：

```text
vertices[26]
    ↕
vertices[3]
```

第三個欄位中可以包含：

- 是否雙向
- graph index
- 速度限制
- door / lift 相關設定
- 其他 RMF lane property

因此：

```text
vertices = waypoint
lanes    = waypoint 之間的導航關係
```

---

# Navigation Graph

目前 `L1.building.yaml` 會產生兩套 navigation graph。

## Graph 0

輸出：

```text
nav_graphs/0.yaml
```

用途：

```text
RMF 機器人導航
```

目前 G1 Fleet Adapter 使用這套 navigation graph。

機器人的：

```text
start_waypoint
charger
destination
```

都應對應 Graph 0 中存在的 waypoint。

---

## Graph 1

輸出：

```text
nav_graphs/1.yaml
```

用途：

```text
前端 3D 場景中的人物或非 RMF 角色移動
```

例如：

- Baymax
- 護士
- 其他前端場景角色

Graph 0 與 Graph 1 都來自：

```text
L1.building.yaml
```

但 lane 透過不同的：

```text
graph_idx
```

區分。

---

# 前端 Navigation JSON

前端不直接讀取：

```text
nav_graphs/0.yaml
nav_graphs/1.yaml
```

執行：

```bash
npm run navigation:generate
```

時：

```text
frontend/scripts/generate-rmf-navigation.sh
```

會重新生成導航資料並轉換成瀏覽器可使用的 JSON。

輸出：

```text
frontend/public/generated/rmf-navigation.json
```

來源：

```text
Graph 0
```

以及：

```text
frontend/public/generated/rmf-navigation-graph-1.json
```

來源：

```text
Graph 1
```

因此完整關係為：

```text
L1.building.yaml
      │
      ├── Graph 0
      │      ↓
      │   nav_graphs/0.yaml
      │      ↓
      │   rmf-navigation.json
      │
      └── Graph 1
             ↓
          nav_graphs/1.yaml
             ↓
          rmf-navigation-graph-1.json
```

---

# Traffic Editor、Nav2 與 Gazebo 的關係

這三套系統使用相同醫院場景，但用途不同。

```text
Traffic Editor
    ↓
L1.building.yaml
    ├── 建築
    ├── waypoint
    ├── lane
    └── RMF navigation graph
```

```text
Nav2
    ↓
hospital_floor_real.png
+
L1.yaml
```

```text
Gazebo
    ↓
L1.world
+
models/
```

---

## Traffic Editor

Traffic Editor 主要管理：

- 建築配置
- 模型位置
- waypoint
- lane
- charger
- graph index
- door / lift 相關交通資訊

主要來源：

```text
L1.building.yaml
```

---

## Nav2

`L1.yaml` 不是 Traffic Editor waypoint 的設定。

它是 Nav2 `map_server` 讀取：

```text
hospital_floor_real.png
```

時使用的影像地圖設定。

典型內容：

```yaml
image: hospital_floor_real.png
resolution: ...
origin: [...]
negate: ...
occupied_thresh: ...
free_thresh: ...
```

---

### `resolution`

表示：

```text
1 pixel = ? meter
```

例如：

```text
0.05
```

就代表每個像素對應 0.05 公尺。

---

### `origin`

格式：

```yaml
origin: [x, y, yaw]
```

表示圖片左下角在 ROS map frame 中對應的位置。

---

### `negate`

控制影像灰階值是否反轉。

---

### `occupied_thresh`

高於此障礙機率的 pixel 會被判定為 occupied。

---

### `free_thresh`

低於此障礙機率的 pixel 會被判定為 free。

---

# Gazebo 世界

正式 Gazebo 使用：

```text
maps/L1.world
```

此檔案由場景工具產生，不建議直接手動修改。

來源流程：

```text
L1.building.yaml
      ↓
rebuild_l1_gazebo_scene.sh
      ↓
L1.world
```

正式 G1 機器人目前不直接寫在：

```text
L1.world
```

而是由：

```text
fleet_instances.yaml
      ↓
hospital_g1_fleet.launch.py
      ↓
g1_hospital_robot.launch.py
      ↓
Gazebo 動態 spawn
```

加入場景。

---

# 重新生成 Gazebo 世界與 Navigation Graph

修改以下檔案後：

```text
maps/L1.building.yaml
config/props.yaml
```

回到專案根目錄：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
```

執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

或使用：

```bash
rebuild-hospital
```

---

## 主要產出

重建流程會更新：

```text
maps/L1.world
models/hospital_L1/
models/hospital_nav_overlay/
nav_graphs/0.yaml
nav_graphs/1.yaml
```

其中：

```text
nav_graphs/0.yaml
```

供 RMF 機器人使用。

```text
nav_graphs/1.yaml
```

供前端人物 / 場景角色使用。

---

## 不顯示 Navigation Overlay

如果只需要模擬場景，不需要在 Gazebo 顯示 waypoint 與 lane：

```bash
rebuild-hospital --without-nav-overlay
```

---

# 修改 Traffic Editor 地圖

若需要修改：

- waypoint
- lane
- charger
- 模型位置
- graph index
- 建築配置

應編輯：

```text
maps/L1.building.yaml
```

完成後重新執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

這會一併更新：

```text
L1.world
hospital_L1
hospital_nav_overlay
nav_graphs/0.yaml
nav_graphs/1.yaml
```

---

# 從 Gazebo 同步模型位置

若直接在 Gazebo GUI 中拖曳模型並希望將位置寫回來源設定，可以使用反向同步流程。

流程：

```text
Gazebo GUI
    ↓ Save As
maps/L1.sdf
    ↓
sync_gazebo_to_traffic_editor.py
    ↓
L1.building.yaml
+
props.yaml
```

---

## 操作方式

先在 Gazebo 中將世界另存為：

```text
maps/L1.sdf
```

再執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

工具會：

- 將模型位置寫回 `maps/L1.building.yaml`
- 將額外模型位置寫回 `config/props.yaml`
- 移除 Gazebo SDF 中不存在的模型
- 將修改前的來源檔備份到 `backups/`
- 最多保留最近數次備份

同步完成後應先查看：

```bash
git diff
```

確認修改內容。

接著重新執行：

```bash
rebuild-hospital
```

重新產生正式場景。

---

## 關於 `L1.sdf`

`L1.sdf` 目前保留，因為現有同步工具仍會使用它。

但需注意：

```text
L1.sdf ≠ 正式 Gazebo world
```

正式 Gazebo 啟動使用：

```text
L1.world
```

`L1.sdf` 主要用途是：

```text
Gazebo GUI 調整
      ↓
另存
      ↓
同步位置回 Traffic Editor
```

若未重新產生新的 `L1.sdf`，應保留現有檔案，避免影響既有同步流程。

---

# RMF 與 G1 起點設定

G1 的 Gazebo spawn 位置定義於：

```text
config/fleet_instances.yaml
```

而 RMF 的起始 waypoint 與 charger 會對應：

```text
config/fleet_config.yaml
```

以及：

```text
nav_graphs/0.yaml
```

目前應維持：

```text
Gazebo spawn
≈
RMF start_waypoint 座標
```

避免：

```text
Gazebo 認為機器人在 A
RMF 認為機器人在 B
```

造成導航狀態不一致。

例如：

```text
left_mid_junction
≈ (8.953, -16.200)
```

若某台 G1 的：

```text
start_waypoint = left_mid_junction
```

則 Gazebo spawn 也應設定在相同位置附近。

---

# 座標設定

`L1.yaml` 中：

```yaml
origin: [x, y, yaw]
```

表示：

```text
地圖圖片左下角
        ↓
ROS map frame 中的世界座標
```

RViz 的 Fixed Frame 使用：

```text
map
```

RMF 與目前 G1 Navigation Bridge 也以：

```text
map
```

作為醫院中的全域位置概念。

---

# G1 Odom 與 Map 座標

Gazebo G1 的 odometry 從 spawn 位置開始時通常為：

```text
odom x = 0
odom y = 0
```

RMF 則需要醫院 map 座標。

因此：

```text
hospital_g1_navigation_bridge.py
```

會根據 `fleet_instances.yaml` 中的 spawn pose 將 odom-relative pose 轉換為 map pose。

公式：

```text
map_x =
x0
+ cos(yaw0) * odom_x
- sin(yaw0) * odom_y
```

```text
map_y =
y0
+ sin(yaw0) * odom_x
+ cos(yaw0) * odom_y
```

```text
map_yaw =
yaw0 + odom_yaw
```

因此 G1 即使 odometry 從：

```text
(0, 0)
```

開始，RMF 仍能收到正確的醫院 map 座標。

---

# 重新編譯

地圖、world、launch 或 package 資源更新後：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
```

執行：

```bash
colcon build \
  --symlink-install \
  --packages-select my_hospital_rmf
```

再載入：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

---

# 建議修改原則

## 應優先修改

```text
maps/L1.building.yaml
maps/L1.yaml
config/props.yaml
config/fleet_instances.yaml
config/fleet_config.yaml
```

---

## 通常不直接修改

```text
maps/L1.world
models/hospital_L1/
models/hospital_nav_overlay/
nav_graphs/0.yaml
nav_graphs/1.yaml
```

因為這些檔案可能在：

```text
rebuild-hospital
```

後被重新生成。

---

# 地圖資料流摘要

```text
hospital_floor_real.png
        │
        ├──────────────► Nav2
        │                 ▲
        │                 │
        │              L1.yaml
        │
        ▼
Traffic Editor
        │
        ▼
L1.building.yaml
        │
        ├──────────────► nav_graphs/0.yaml
        │                      │
        │                      └── RMF / G1
        │
        ├──────────────► nav_graphs/1.yaml
        │                      │
        │                      └── Frontend Characters
        │
        ▼
rebuild_l1_gazebo_scene.sh
        │
        ├── hospital_L1
        ├── hospital_nav_overlay
        └── L1.world
                │
                ▼
             Gazebo
                │
                └── G1 dynamically spawned
```

反向同步：

```text
Gazebo
   │
   ▼
Save As
   │
   ▼
L1.sdf
   │
   ▼
sync_gazebo_to_traffic_editor
   │
   ├── L1.building.yaml
   └── props.yaml
```

目前的核心原則是：

```text
L1.building.yaml = 場景與 RMF 導航主要來源

L1.world         = 正式 Gazebo 執行世界

L1.sdf           = Gazebo → Traffic Editor 同步中介檔

L1.yaml          = Nav2 地圖參數

nav_graphs/0     = RMF 機器人導航

nav_graphs/1     = 前端人物 / 場景角色導航
```
