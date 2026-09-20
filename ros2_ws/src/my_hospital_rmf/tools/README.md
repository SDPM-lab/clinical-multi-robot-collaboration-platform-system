# 場景工具使用說明

目前的場景資料流：

```text
maps/L1.building.yaml
  → tools/gazebo/rebuild_l1_gazebo_scene.sh
  → maps/L1.world + models/ + nav_graphs/

Gazebo 另存 maps/L1.sdf
  → tools/traffic_editor/sync_gazebo_to_traffic_editor.py
  → maps/L1.building.yaml
```

`L1.building.yaml` 是場景結構與模型位置的主要來源；`L1.world`、建築模型和導航圖是生成結果。

## 常用指令

### 重新生成 Gazebo 世界與導航圖

修改下列任一檔案後執行：

- `maps/L1.building.yaml`
- `config/fleet_config.yaml`
- `config/props.yaml`

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
rebuild-hospital
```

也可以直接執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

腳本預設會在 Gazebo 加入導航線與 waypoint overlay。若只需要模擬場景：

```bash
rebuild-hospital --without-nav-overlay
```

產出：

- `maps/L1.world`
- `models/hospital_L1/`
- `models/hospital_nav_overlay/`
- `nav_graphs/0.yaml`
- `nav_graphs/1.yaml`

`0.yaml` 是 RMF 機器人使用的主要導航圖；`1.yaml` 是前端 3D 場景中 Baymax、護士等人物的移動路線。兩者都由 `L1.building.yaml` 生成，分別對應 Traffic Editor lane 的 `graph_idx: 0` 與 `graph_idx: 1`。

前端不直接載入 YAML。執行 `npm run navigation:generate` 時，`frontend/scripts/generate-rmf-navigation.sh` 會重新生成兩套導航圖，再轉成瀏覽器使用的 JSON：

- `frontend/public/generated/rmf-navigation.json`：來自 Graph 0。
- `frontend/public/generated/rmf-navigation-graph-1.json`：來自 Graph 1。

完整流程共七步：

1. 從 `L1.building.yaml` 生成 `L1.world` 與 `hospital_L1`。
2. 將 Traffic Editor 產生的 OpenRobotics 模型 URI 解析為 Gazebo Fuel URI。
3. 生成 RMF 導航圖。
4. 生成選用的 Gazebo 導航 overlay。
5. 將 overlay 加入 `L1.world`。
6. 依 `fleet_config.yaml` 加入模擬機器人。
7. 依 `props.yaml` 套用模型替換與縮放。

目前大部分家具來自 `OpenRobotics/...`。最後的 world 會引用本機 `*_real` 模型，是因為 Fuel 原始模型經第七步縮放後存成本機模型；不代表 Fuel 解析步驟沒有使用。

生成後重新編譯：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

### 同步 Gazebo 模型位置

1. 在 Gazebo 將世界存成 `maps/L1.sdf`。
2. 執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

工具會：

- 將模型位置寫回 `maps/L1.building.yaml`。
- 將額外模型位置寫回 `config/props.yaml`。
- 移除 Gazebo SDF 中不存在的模型。
- 將修改前檔案備份到 `backups/`，最多保留 5 次。

工具會直接修改來源 YAML，因此應先查看輸出差異。完成後執行 `rebuild-hospital` 重新生成 Gazebo 場景。

## 腳本用途

| 路徑 | 用途 |
|------|------|
| `gazebo/rebuild_l1_gazebo_scene.sh` | 執行完整 L1 Gazebo 生成流程 |
| `gazebo/add_nav_overlay.py` | 將生成好的導航 overlay 加入 `L1.world` |
| `gazebo/add_fleet_robots.py` | 依 `fleet_config.yaml` 將模擬機器人加入 `L1.world` |
| `gazebo/patch_props.py` | 套用 `props.yaml` 的模型替換與縮放 |
| `gazebo/patch_fuel_uris.py` | 將 OpenRobotics `model://` URI 改為 Fuel URI |
| `gazebo/generate_nav_overlay_model.py` | 生成 Gazebo 導航路網覆蓋層 |
| `traffic_editor/sync_gazebo_to_traffic_editor.py` | 將 Gazebo SDF 的模型位置同步回來源設定 |
| `blender/blender_import_hospital_proxy.py` | 從 `L1.world` 產生全新 Blender 代理場景 |

## 新增機器人

在 `config/fleet_config.yaml` 的 `robots` 下新增：

```yaml
hospital_robot_N:
  charger: charging_station
  start_waypoint: waypoint_name
  start_pose: [x, y, 0.05, 0, 0, 0]
```

`start_waypoint` 必須存在於機器人導航圖 `nav_graphs/0.yaml`，之後重新生成並編譯。

## 新增額外模型

在 `config/props.yaml` 的 `props` 下新增：

```yaml
- name: unique_name
  uri: "https://fuel.gazebosim.org/1.0/OWNER/models/MODEL"
  pose: [x, y, z, roll, pitch, yaw]
```

`name` 不可重複，之後重新生成並編譯。
