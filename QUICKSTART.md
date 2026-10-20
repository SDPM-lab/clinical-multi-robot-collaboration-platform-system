# 快速啟動

## 編譯 ROS 2

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

## 啟動系統

### ROS 2 / RMF / Gazebo / RViz

```bash
source /opt/ros/jazzy/setup.bash
source ~/clinical-multi-robot-collaboration-platform-system/ros2_ws/install/setup.bash
ros2 launch my_hospital_rmf hospital.launch.py
```

### ROS 2 / RMF（不啟動 Gazebo、RViz）

```bash
source /opt/ros/jazzy/setup.bash
source ~/clinical-multi-robot-collaboration-platform-system/ros2_ws/install/setup.bash
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
npm run dev -- --port 5174
```

## 前端網址

```text
一般頁面：http://localhost:5174/
Robot Status 視角：http://localhost:5174/?robotDebug=1&cameraDebug=1&modelDebug=1
Task Dispatch 視角：http://localhost:5174/?dispatchDebug=1&cameraDebug=1&modelDebug=1
Overview 視角：http://localhost:5174/?cameraDebug=1&modelDebug=1
Live Map 視角：http://localhost:5174/?mapCameraDebug=1
```

## 重建地圖

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
cd ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

## Gazebo → Traffic Editor（先另存為 `ros2_ws/src/my_hospital_rmf/maps/L1.sdf`）

```bash
source /opt/ros/jazzy/setup.bash
source ~/clinical-multi-robot-collaboration-platform-system/ros2_ws/install/setup.bash
ros2 run my_hospital_rmf sync_gazebo_to_traffic_editor
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
cd ros2_ws
colcon build --symlink-install --packages-select my_hospital_rmf
source install/setup.bash
```

## Blender

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
blender blender/scenes/floor_L1.blend
```

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
blender --background blender/scenes/floor_L1.blend \
  --python ros2_ws/src/my_hospital_rmf/tools/blender/sync_l1_world_to_blender.py \
  -- --apply
```

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/frontend
npm run models:update
```
