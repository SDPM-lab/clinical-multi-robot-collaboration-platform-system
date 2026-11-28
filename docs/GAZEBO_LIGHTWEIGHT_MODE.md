# Lightweight G1 模擬

醫院模擬預設採用 Lightweight G1。從原始 Gazebo URDF 展開後，在記憶體固定上身關節，只保留左右輪的動態關節與控制介面。原始模型保留，`robot_model:=full` 使用原本的模型展開路徑。七台藥送、運送與導航仍使用同一個 PPO、RMF、控制器與 Nav2 配置。

## 啟動

在這個 backend 工作樹的根目錄執行。已建置 ROS overlay，現有 Xvfb 與 x11vnc 繼續使用 :99。需有可執行的 .venv_rl/bin/python 和 VirtualGL。腳本優先讀本地解包路徑 .local/virtualgl，再找 PATH 上的 vglrun。亦可用 VGL_ROOT 指定已有解包路徑。

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/.worktrees/backend-lightweight
bash scripts/start-hospital-vnc.sh
```

腳本自動載入 ROS、DDS XML，啟動七台及排程整合，等待 Gazebo Server 就緒後開全螢幕 VirtualGL GUI。看到 Hospital PPO Scheduler ready 才送任務。使用其他 ROS domain 時，外部 ROS tools 需用相同值。Gazebo 客戶端使用腳本印出的 GZ_PARTITION。

```bash
bash scripts/start-hospital-vnc.sh robot_model:=full
HOSPITAL_ROBOTS=1 bash scripts/start-hospital-vnc.sh robot_model:=lightweight
```

第一條暫時選 Full，第二條啟動一台 Lightweight。都由同一個前景程序管理，Ctrl+C 會結束該輪啟動的 server 與 GUI。

只開 server 時，下列命令可沿用原 ROS launch 入口：

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=101 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export CYCLONEDDS_URI="file://$PWD/ros2_ws/src/my_hospital_rmf/config/cyclonedds_7robots.xml"
ros2 launch my_hospital_rmf hospital.launch.py robots:=7 launch_gazebo_gui:=false launch_rviz:=false
```

Gazebo Server 預設採 Ogre 2 EGL。Fleet Manager、PPO 與前後端的整合方式沿用 backend 分支。若另啟隔離網站，Backend 需設 TaskDispatch endpoint 到 http://127.0.0.1:5050/api/hospital/tasks，狀態 WebSocket 使用 ws://127.0.0.1:9091，並停用開發模擬派工。

## 模型檢查與回復

原始 Full 與 Lightweight 的動態 joints 為 32／2，兩者 45 visual、33 collision、95.2575544743 kg，模型局部重心為 (0.01907419, −0.00427514, 0.23623944) m。SDF 轉換後在相同座標系合成慣性，最大絕對差 3.6e−15 kg·m²。原始 URDF 的 visual、collision、inertial、sensor、plugin 元素逐一比較一致。保留原始輪和控制參數。

日常回復到原模型用 robot_model:=full。要回復整個整合，在 backend 工作樹對 Lightweight 整合提交執行 git revert。整合前基準為 2706c50。使用 git show 檢查整合差異。

## 隔離前後端驗收

在 backend 工作樹各開一個終端。保持正在使用的正式網站與任務程序，使用 5102／5174 及獨立帳號目錄。

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/.worktrees/backend-lightweight/backend
ASPNETCORE_ENVIRONMENT=Development \
Auth__DataDirectory=/tmp/medisync-lightweight-auth \
TaskDispatch__DevelopmentSimulation__Enabled=false \
TaskDispatch__Endpoint=http://127.0.0.1:5050/api/hospital/tasks \
RosBridge__Url=ws://127.0.0.1:9091 RosBridge__AutoConnect=true \
dotnet run --no-launch-profile --project Server -- --urls http://localhost:5102
```

```bash
cd ~/clinical-multi-robot-collaboration-platform-system/.worktrees/backend-lightweight/frontend
VITE_API_BASE_URL=http://localhost:5102 npm run dev -- --host localhost --port 5174 --strictPort
```

在 Mac 上以既有 SSH 入口轉發 5174 和 5102，再打開 http://localhost:5174。網頁「任務派遣」內建立任務，同時核對 Backend 任務狀態、PPO 指派、RMF 任務與 Nav2 結局。HTTP 送出後仍需等待排程時間與機器人到站。

## 2026-11-27 驗收

| 情境 | 結果 |
| --- | --- |
| 單台 Lightweight | 差速驅動、Joint State Broadcaster、Nav2 lifecycle 均 active，Nav2 成功，模擬／牆鐘 6.05／6.05 s。 |
| 七台 headless | 七台均啟用輪控與 Nav2，35 項就緒檢查完成，單一 /clock。六個同時導航目標中三個成功，另外三個在 155.00 s 牆鐘與 83.34 s 模擬時間的窗口結束時未回傳終局。 |
| 七台 headless 多目標初段 | 取樣 19.93 s，整窗 RTF 0.433。 |
| 七台加 GUI，派工前 | 取樣 19.92 s，整窗 RTF 0.561。 |
| 七台加 GUI，網頁病房任務派工後 | 取樣 19.92 s，整窗 RTF 0.642。Full 歷史同任務短窗 0.112，Server 渲染路徑與初始姿態有差異，不能單獨量化 Lightweight 的效益。 |
| Gazebo GPU | Server 程序有 --headless-rendering 與 Ogre 2，Server 與 GUI 皆映射 Ogre 2 及 NVIDIA EGL。GUI 另映射 VirtualGL，該 DISPLAY 的 VirtualGL GLX renderer 查詢為 NVIDIA RTX 5060 Ti。 |
| GUI | 1920×1080，VirtualGL Total 中位數約 23.8 FPS，量的是本地畫面傳送，未量遠端 TigerVNC 客戶端 FPS。 |
| CPU／GPU 取樣 | Gazebo Server 的 ps 累計 CPU 使用率在採樣約 125–128%，GUI 約 106–116%。主要 GPU 取樣峰值 headless／GUI 為 7%／11%，VRAM 約 1.37 GiB 以下。 |
| 網頁 PPO 任務 | 從 Chromium 的 MediSync「建立任務」表單送出病房服務 T0001，PPO 指派給五號，Backend 回報已指派。RMF 開始執行，Nav2 完成第一段，後續導航重試。 |

RTF 以 Gazebo stats 的模擬與牆鐘邊界差計算。GUI 前後取樣的活動目標不同，不能用這兩行估算開啟 GUI 的純成本。完整門、電梯與 component 插件仍缺。

到觀測結束，瀏覽器仍顯示五號已指派。第二段路徑有 Nav2 progress checker 重試，沒有整筆完成回報。導航地圖、控制器、感測器與 PPO 保持原配置。

若需要重新建置這份 backend overlay，在此工作樹執行：

```bash
source /opt/ros/jazzy/setup.bash
source ~/clinical-multi-robot-collaboration-platform-system-liang/ros2_ws/install/local_setup.bash
cd ros2_ws
colcon build --base-paths src/my_hospital_rmf --symlink-install
```

這只建置醫院套件，機器人及 ROS 依賴沿用 -liang。重新建置後可用 `ros2 launch my_hospital_rmf hospital.launch.py --show-args` 檢查模型預設值。這份工作樹的 .venv_rl 指向既有 PPO 環境。
