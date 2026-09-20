# 快速啟動

以下指令預設專案位於：

```text
~/clinical-multi-robot-collaboration-platform-system
```

## 1. 編譯 ROS 2 套件

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

每個新的終端機都要執行：

```bash
source /opt/ros/jazzy/setup.bash
source ~/clinical-multi-robot-collaboration-platform-system/ros2_ws/install/setup.bash
```

## 2. 啟動系統

### ROS 2、RMF、Gazebo、RViz

```bash
ros2 launch my_hospital_rmf hospital.launch.py
```

不開 Gazebo 和 RViz：

```bash
ros2 launch my_hospital_rmf hospital.launch.py launch_gazebo:=false launch_rviz:=false
```

### 後端（另一個終端機）

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/backend
dotnet run --project Server
```

### 前端（另一個終端機）

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/frontend
npm run dev
```

## 3. 調整 Overview camera／model preset

若要手動調整場景鏡頭並保存 preset，可在瀏覽器網址上加入 query string：

```text
http://localhost:5173/?cameraDebug=1&modelDebug=1
http://localhost:5173/?mapCameraDebug=1
```

- `?cameraDebug=1`：調整 Overview 相機角度、距離與 target。拖曳旋轉、右鍵平移、滾輪縮放。
- `?modelDebug=1`：調整 Overview 診所模型。左鍵拖曳平移、`Shift` 拖曳高度、`Alt`＋左鍵或右鍵拖曳旋轉 Y 軸、滾輪縮放。
- 同時加入兩個參數時，使用玻璃控制面板的「操作相機／操作模型」切換目標，兩種控制不會同時接收事件。
- `?mapCameraDebug=1`：調整即時地圖模式的相機角度

Overview 的相機和模型分別自動保存到 localStorage 的 `overview-camera-preset-v3` 與 `overview-model-preset-v3`。結束相機操作或停止模型調整後會保存，重新整理會自動套用。工具列提供 `Copy preset`、`Reset model`、`Reset camera` 與 `Save preset`；每次保存也會在 Console 以 `[Overview preset]` 輸出完整的模型與相機 JSON。

## 4. 修改地圖後重新生成

修改 `L1.building.yaml`、`fleet_config.yaml` 或 `props.yaml` 後：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh

cd ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

若已在 `~/.bashrc` 設定捷徑，可改用：

```bash
rebuild-hospital
build my_hospital_rmf
```

## 5. 把 Gazebo 調整結果同步回 Traffic Editor

先在 Gazebo 將世界另存為：

```text
ros2_ws/src/my_hospital_rmf/maps/L1.sdf
```

再執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
rebuild-hospital
build my_hospital_rmf
```

同步工具會更新 `L1.building.yaml` 和 `props.yaml`，並在 `backups/` 保留最近 5 次備份。Gazebo 中被刪除的模型也會從來源設定移除，因此執行前先確認 SDF 內容完整。

## 6. Blender

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
blender blender/scenes/floor_L1.blend
```

將目前 Gazebo 場景同步到 Blender 主檔：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
blender --background blender/scenes/floor_L1.blend \
  --python ros2_ws/src/my_hospital_rmf/tools/blender/sync_l1_world_to_blender.py \
  -- --apply
```

更新前端使用的 GLB：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/frontend
npm run models:update
```

詳細資料：[tools/README.md](ros2_ws/src/my_hospital_rmf/tools/README.md)、[maps.md](ros2_ws/src/my_hospital_rmf/maps/maps.md)、[launch/README.md](ros2_ws/src/my_hospital_rmf/launch/README.md)、[models.md](ros2_ws/src/my_hospital_rmf/models/models.md)。
