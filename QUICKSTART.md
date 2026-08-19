### 自動生成導航圖

```bash
cd ros2_ws/src/my_hospital_rmf
ros2 run rmf_building_map_tools building_map_generator nav maps/hospital.building.yaml nav_graphs 
```

### 自動colcon build跟載好

-> <code>build my_hospital_rmf</code>
```bash
build() {
    local ws=~/clinical-multi-robot-collaboration-platform-system/ros2_ws
    cd "$ws" && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install --packages-select "$@" && source install/setup.bash
}
```

### 快速開啟指令

-> <code>build my_hospital_rmf</code>
```bash
- ros2 launch my_hospital_rmf hospital.launch.xml
```

#### 前端
```bash
- cd ~/clinical-multi-robot-collaboration-platform-system/frontend
- npm run dev
```
#### 後端
```bash
- cd ~/clinical-multi-robot-collaboration-platform-system/backend
- dotnet run --project Server
```


