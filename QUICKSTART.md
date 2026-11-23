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

也可以直接執行 `npm run dev`：預設從 5173 開始，若該埠已被使用會嘗試下一個埠，請以終端顯示的 Local 網址為準。

### 手動停止前端 Vite

```bash
bash ~/clinical-multi-robot-collaboration-platform-system/scripts/stop-frontend-vite.sh
```

此腳本會停止目前帳號啟動的本專案 Vite（包括背景程序）。Vite 結束後會釋放其佔用的埠；腳本不會自動執行，也不會停止其他 Node 程序。

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


### 任務派遣表單 API

Task Dispatch 頁面使用後端 API 建立、查詢、修改排程及刪除任務，不再寫入前端 demo store。
先啟動 ASP.NET Core 後端（`http://localhost:5100`），再於 `frontend` 執行 `npm run dev`。
Vite 將 `/api` 代理到後端。部署時需設定同源 `/api` 反向代理，或使用 `VITE_API_BASE_URL` 指向後端並設定 CORS。
表單地點標籤會轉成 Graph 0 waypoint ID，建立成功回傳 HTTP 201 與後端產生的任務 ID。
目前分鐘代表立即排入派送，未來時間則等待背景排程；早於目前分鐘會被拒絕。
任務仍存於後端記憶體，重啟會清空。建立時不手動選機器人；`/api/robots` 有七台 F1 名冊，但未收到 ROS 遙測時仍顯示離線。
Development 且未設定外部派工入口時，建立後下一輪背景工作會模擬 `Pending → Assigned`，到預定時間才轉 `Running`。即時地圖會讓暫時模型沿參考路線做前端動畫；模型到達任務終點後，Development 專用 API 核對起終點與機器人，再將任務標記 `Completed`。這不是機器人的真實定位或實際移動。其他環境不啟用模擬。
