# maps 使用說明

| 檔案 | 用途 | 是否手動修改 |
|------|------|--------------|
| `L1.building.yaml` | Traffic Editor 建築、模型、waypoint 與 lane 的主要來源 | 是 |
| `hospital_floor.png` | Traffic Editor 底圖 | 視需要替換 |
| `hospital_floor_real.png` | Nav2 使用的地圖圖片 | 視需要替換 |
| `L1.yaml` | Nav2 地圖解析度、原點與障礙物門檻 | 是 |
| `L1.sdf` | 從 Gazebo 儲存、供同步工具讀取的世界 | 由 Gazebo 另存 |
| `L1.world` | Gazebo 啟動使用的世界 | 否，由工具生成 |

## Traffic Editor 地圖欄位

`L1.building.yaml` 的 `L1` 樓層目前使用以下設定：

```yaml
drawing:
	filename: hospital_floor_real.png
elevation: 0
lanes:
	- [26, 3, {...}]
```

- `drawing`：Traffic Editor 顯示的底圖設定區塊。
- `drawing.filename`：底圖檔名，目前是 `hospital_floor_real.png`。它只提供畫圖和定位的視覺參考，不會儲存 waypoint。
- `elevation`：這個樓層在建築物中的高度，單位是公尺；目前 `0` 代表 L1 位於高度 0。
- `lanes`：waypoint 之間的導航連線。`[26, 3, {...}]` 代表連接 `vertices` 中編號 26 和 3 的兩個 waypoint；第三項包含雙向、速度限制等連線設定。

waypoint 本身存放在同一個檔案的 `vertices`：

```yaml
vertices:
	- [687.429, 652.016, 0, reception_back]
	- [1017.12, 296.264, 0, charging_station, {is_charger: [1, true]}]
```

其中前面的數值是 waypoint 在 Traffic Editor 底圖座標中的位置，名稱和額外設定則提供 RMF 使用。圖片是底圖，`vertices` 和 `lanes` 才是實際的導航資料。

## Traffic Editor、Nav2 與 Gazebo 的關係

`L1.yaml` 不是 Traffic Editor waypoint 的設定。它是 Nav2 `map_server` 讀取 `hospital_floor_real.png` 時使用的影像地圖設定，包含：

- `resolution`：每個像素代表多少公尺。
- `origin`：圖片左下角對應到 ROS 世界座標的 `[x, y, yaw]`。
- `negate`、`occupied_thresh`、`free_thresh`：如何把灰階像素判定為障礙物或可通行區域。

修改 Traffic Editor 地圖、waypoint 或 lane 後，從專案根目錄執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

這個流程會重新產生：

- `maps/L1.world`：Gazebo 使用的模擬世界。
- `models/`：由建築資料產生的 Gazebo 模型。
- `nav_graphs/0.yaml`：RMF fleet adapter 使用的導航圖。

接著重新編譯並載入 workspace，讓 ROS 2 使用最新產出：

```bash
cd ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

## 修改 Traffic Editor 地圖

編輯 `L1.building.yaml` 後，回到專案根目錄執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

這會一併更新 Gazebo world、建築模型與 `nav_graphs/0.yaml`。

## 從 Gazebo 同步模型位置

將 Gazebo 世界存成 `L1.sdf`，再執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

執行後需重新生成並編譯。SDF 中不存在的模型會從來源設定移除；原檔備份至 `../backups/`。

## 座標設定

`L1.yaml` 的 `origin` 是地圖圖片左下角在世界座標中的位置；RViz 的 Fixed Frame 使用 `map`。
