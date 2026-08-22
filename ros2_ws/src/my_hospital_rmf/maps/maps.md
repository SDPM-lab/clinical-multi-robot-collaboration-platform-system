# maps 使用說明

| 檔案 | 用途 | 是否手動修改 |
|------|------|--------------|
| `hospital.building.yaml` | Traffic Editor 建築、模型、waypoint 與 lane 的主要來源 | 是 |
| `hospital_floor.png` | Traffic Editor 底圖 | 視需要替換 |
| `hospital_floor_real.png` | Nav2 使用的地圖圖片 | 視需要替換 |
| `hospital_map.yaml` | Nav2 地圖解析度、原點與障礙物門檻 | 是 |
| `hospital_real.sdf` | 從 Gazebo 儲存、供同步工具讀取的世界 | 由 Gazebo 另存 |
| `hospital.world` | Gazebo 啟動使用的世界 | 否，由工具生成 |

## 修改 Traffic Editor 地圖

編輯 `hospital.building.yaml` 後，回到專案根目錄執行：

```bash
bash ros2_ws/src/my_hospital_rmf/tools/rebuild_gazebo_scene.sh
```

這會一併更新 Gazebo world、建築模型與 `nav_graphs/0.yaml`。

## 從 Gazebo 同步模型位置

將 Gazebo 世界存成 `hospital_real.sdf`，再執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
```

執行後需重新生成並編譯。SDF 中不存在的模型會從來源設定移除；原檔備份至 `../backups/`。

## 座標設定

`hospital_map.yaml` 的 `origin` 是地圖圖片左下角在世界座標中的位置；RViz 的 Fixed Frame 使用 `map`。
