# tools 使用說明

## 常用指令

### 重新生成 Gazebo 世界與導航圖

修改下列任一檔案後執行：

- `maps/hospital.building.yaml`
- `config/fleet_config.yaml`
- `config/props.yaml`

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/rebuild_gazebo_scene.sh
```

產出：

- `maps/hospital.world`
- `models/hospital_L1/`
- `models/hospital_nav_overlay/`
- `nav_graphs/0.yaml`

生成後重新編譯：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

### 同步 Gazebo 模型位置

1. 在 Gazebo 將世界存成 `maps/hospital_real.sdf`。
2. 執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

工具會：

- 將模型位置寫回 `maps/hospital.building.yaml`。
- 將額外模型位置寫回 `config/props.yaml`。
- 移除 Gazebo SDF 中不存在的模型。
- 將修改前檔案備份到 `backups/`，最多保留 5 次。

完成後重新生成並編譯。

### 匯入 Blender

從 `hospital.world` 產生輕量代理場景（建築全mesh + 家具/機器人 box proxy）：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
blender --background --python src/my_hospital_rmf/tools/blender_import_hospital_proxy.py
```

輸出至專案根目錄：`hospital_raw.blend`、`hospital_raw_preview.png`（每次覆蓋）。

只檢查解析結果（不需要 Blender）：

```bash
python3 src/my_hospital_rmf/tools/blender_import_hospital_proxy.py --audit
```

## 腳本用途

| 檔案 | 用途 |
|------|------|
| `rebuild_gazebo_scene.sh` | 執行完整生成流程 |
| `sync_gazebo_to_traffic_editor.py` | 將 Gazebo SDF 的模型位置同步回來源設定 |
| `blender_import_hospital_proxy.py` | 從 hospital.world 產生 Blender 代理場景 |
| `patch_world.py` | 加入導航覆蓋層及 `fleet_config.yaml` 中的機器人 |
| `patch_props.py` | 加入 `props.yaml` 中的額外模型並套用縮放 |
| `patch_fuel_uris.py` | 將無法解析的 `model://` URI 改為 Fuel URI |
| `generate_nav_overlay_model.py` | 生成 Gazebo 導航路網覆蓋層 |
| `generate_gazebo_nav_model.py` | 產生 Gazebo 導航模型的輔助工具 |
| `generate_hospital_props_model.py` | 產生醫院 props 模型的輔助工具 |

## 新增機器人

在 `config/fleet_config.yaml` 的 `robots` 下新增：

```yaml
hospital_robot_N:
  charger: charging_station
  start_waypoint: waypoint_name
  start_pose: [x, y, 0.05, 0, 0, 0]
```

`start_waypoint` 必須存在於 `nav_graphs/0.yaml`，之後重新生成並編譯。

## 新增額外模型

在 `config/props.yaml` 的 `props` 下新增：

```yaml
- name: unique_name
  uri: "https://fuel.gazebosim.org/1.0/OWNER/models/MODEL"
  pose: [x, y, z, roll, pitch, yaw]
```

`name` 不可重複，之後重新生成並編譯。
