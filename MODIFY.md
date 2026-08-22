# 修改記錄（自 commit a9b579f 後）

## 新增檔案

- **`ros2_ws/src/my_hospital_rmf/launch/hospital.launch.py`**
  - 將原本的 `hospital.launch.xml` 改寫成 Python launch 檔
  - 支援條件參數：`launch_gazebo`、`launch_rviz`（可個別關閉）
  - 啟動時自動開 Gz Sim（Gazebo Harmonic）與 RViz2
  - Ctrl+C 後自動清理殘留的 gz sim process

- **`ros2_ws/src/my_hospital_rmf/rviz/hospital.rviz`**
  - RViz2 預設設定檔，launch 時自動載入
  - 訂閱 `/map` topic，QoS 設為 Transient Local（對應 map_server 發布方式）
  - 視角設為俯視（TopDownOrtho），Fixed Frame 為 `map`

- **`ros2_ws/src/my_hospital_rmf/tools/tools.md`**
  - `rebuild_gazebo_scene.sh` 完整說明：前提、四個 step、整體流程圖、新增機器人方式

- **`ros2_ws/src/my_hospital_rmf/launch/launch.md`**
  - launch 參數說明、啟動順序、常見 log 解釋

- **`ros2_ws/src/my_hospital_rmf/maps/maps.md`**
  - 地圖相關檔案說明（hospital.world、hospital_map.yaml、Lifecycle Node 概念）

- **`ros2_ws/src/my_hospital_rmf/models/models.md`**
  - 四個 Gazebo 模型說明（hospital_L1、hospital_nav_overlay、hospital_props、hospital_slam_robot）

---

## 修改現有檔案

- **`config/fleet_config.yaml`**
  - `account_for_battery_drain: true` → `false`（消除每 10 秒出現的電池 WARN log）
  - 每台機器人新增 `start_waypoint`（初始停靠路點）與 `start_pose`（Gazebo 初始位置）
  - 這兩個欄位是自定義的，fleet adapter 讀不到會忽略，供我們自己的 script 使用
  - 新增第三台機器人 `hospital_robot_3`，起點 `center_mid_junction`（醫院中央走廊）

- **`maps/hospital.world`**
  - 原本只有一台 `<name>hospital_slam_robot</name>`
  - 改成三台：`hospital_robot_1`、`hospital_robot_2`、`hospital_robot_3`（都使用 `hospital_slam_robot` 模型）
  - 名稱需與 fleet_config.yaml 一致，toggle_floors 插件才能找到對應節點

- **`scripts/hospital_fake_robot_state_publisher.py`**
  - `ROBOT_STARTS`（機器人初始路點對應表）原本是寫死的 dict
  - 改成啟動時從 `fleet_config.yaml` 動態讀取，新增機器人只需改 yaml，不需改程式碼

- **`tools/rebuild_gazebo_scene.sh`**
  - 原本 Step 3 只負責補上 nav_overlay include
  - 現在擴充為：移除生成器產生的單台 `hospital_slam_robot`，改從 `fleet_config.yaml` 讀取所有機器人並寫入 `<include>` block
  - 新增 Step 4：執行 `building_map_generator nav` 重新生成 `nav_graphs/0.yaml`
  - 改完 Traffic Editor 後只需跑此 script，world、models、nav_graphs 全部同步

- **`CMakeLists.txt`**
  - 安裝目錄新增 `rviz`，讓 `hospital.rviz` 被打包進 install/

---

## 機器人台數擴充方式

只需修改 `config/fleet_config.yaml`，新增一個 robot 條目：

```yaml
robots:
  hospital_robot_4:
    charger: charging_station
    start_waypoint: <nav_graphs/0.yaml 裡的路點名稱>
    start_pose: [x, y, 0.05, 0.0, 0.0, 0.0]
```

然後重新跑：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/rebuild_gazebo_scene.sh
colcon build --symlink-install --packages-select my_hospital_rmf
```

`hospital.world`、`hospital_fake_robot_state_publisher`、`nav_graphs` 會全部自動更新。
