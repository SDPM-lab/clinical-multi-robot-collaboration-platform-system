# launch 使用說明

主要使用 `hospital.launch.py`。它會啟動 Gazebo、RViz、RMF、模擬機器人、地圖服務、任務 bridge 與 WebSocket 服務。

## 啟動

```bash
# 完整模擬
ros2 launch my_hospital_rmf hospital.launch.py

# 不開 Gazebo 與 RViz
ros2 launch my_hospital_rmf hospital.launch.py \
  launch_gazebo:=false launch_rviz:=false
```

`hospital.launch.xml` 是舊版啟動檔，僅保留相容用途。

## 參數

| 參數 | 預設值 | 用途 |
|------|--------|------|
| `use_sim_time` | `false` | 有提供 ROS `/clock` 時才設為 `true` |
| `launch_gazebo` | `true` | 是否啟動 Gazebo |
| `launch_rviz` | `true` | 是否啟動 RViz |
| `server_uri` | 空字串 | 選填的 RMF API Server URI |

所有節點會近乎同時啟動，不保證按照檔案中的排列順序完成初始化。

## 服務連接埠

| 服務 | Port |
|------|------|
| HTTP API Bridge | 5050 |
| Fleet State WebSocket | 9090 |
| rosbridge WebSocket | 9091 |

按 `Ctrl+C` 可關閉 launch 啟動的節點；Gazebo 結束後會自動清理 runtime logs。
