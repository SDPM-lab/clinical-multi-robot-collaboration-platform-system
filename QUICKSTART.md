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

## 3. 修改地圖後重新生成

修改 `hospital.building.yaml`、`fleet_config.yaml` 或 `props.yaml` 後：

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/rebuild_gazebo_scene.sh

cd ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

若已在 `~/.bashrc` 設定捷徑，可改用：

```bash
rebuild-hospital
build my_hospital_rmf
```

## 4. 把 Gazebo 調整結果同步回 Traffic Editor

先在 Gazebo 將世界另存為：

```text
ros2_ws/src/my_hospital_rmf/maps/hospital_real.sdf
```

再執行：

```bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
rebuild-hospital
build my_hospital_rmf
```

同步工具會更新 `hospital.building.yaml` 和 `props.yaml`，並在 `backups/` 保留最近 5 次備份。Gazebo 中被刪除的模型也會從來源設定移除，因此執行前先確認 SDF 內容完整。

## 5. blender

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
blender --background --python ros2_ws/src/my_hospital_rmf/tools/blender_import_hospital_proxy.py
blender --python ros2_ws/src/my_hospital_rmf/tools/blender_import_hospital_proxy.py
blender ./hospital_raw.blend
```

詳細資料：[tools.md](ros2_ws/src/my_hospital_rmf/tools/tools.md)、[maps.md](ros2_ws/src/my_hospital_rmf/maps/maps.md)、[launch.md](ros2_ws/src/my_hospital_rmf/launch/launch.md)、[models.md](ros2_ws/src/my_hospital_rmf/models/models.md)。
