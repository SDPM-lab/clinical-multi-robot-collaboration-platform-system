# models 使用說明

此資料夾存放 Gazebo 模型；真實機器人模式不需要載入這些模型。

| 類型 | 說明 |
|------|------|
| `hospital_L1/` | 由 `L1.building.yaml` 生成的醫院建築 |
| `hospital_nav_overlay/` | 由導航圖生成的路網視覺化 |
| `*_real/` | Gazebo 儲存世界時產生或使用的本地模型 |
| 其他資料夾 | 自訂醫院設備、家具與場景模型 |

一般不直接修改 `hospital_L1/` 或 `hospital_nav_overlay/`，因為執行重建工具時會重新生成。

## 重建生成模型

```bash
cd ~/clinical-multi-robot-collaboration-platform-system
bash ros2_ws/src/my_hospital_rmf/tools/gazebo/rebuild_l1_gazebo_scene.sh
```

## 模型搜尋路徑

`hospital.launch.py` 會自動把已安裝套件的 `models/` 加入 `GZ_SIM_RESOURCE_PATH`。若要直接執行 `gz sim`，可先設定：

```bash
export GZ_SIM_RESOURCE_PATH="$GZ_SIM_RESOURCE_PATH:$HOME/clinical-multi-robot-collaboration-platform-system/ros2_ws/src/my_hospital_rmf/models"
```

額外模型建議在 `config/props.yaml` 管理，不要直接修改生成後的 `L1.world`。
