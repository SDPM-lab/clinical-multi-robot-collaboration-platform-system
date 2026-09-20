# 導航圖說明

這個資料夾的 YAML 由 `maps/L1.building.yaml` 自動生成。請在 Traffic Editor 修改 lane，再執行 `rebuild-hospital`；不要直接修改生成後的 `0.yaml` 或 `1.yaml`。

## `0.yaml`：機器人導航圖

- 來源：`L1.building.yaml` 中 `graph_idx: 0` 的 lane。
- 用途：Open-RMF Fleet Adapter 的機器人路徑規劃。
- 使用者：`hospital.launch.py`、`hospital_fleet_adapter.py`、模擬機器人與 Gazebo 導航 overlay。
- waypoint 應有清楚且唯一的名稱，供機器人起點、目的地及任務系統引用。

## `1.yaml`：前端人物走路路線

- 來源：`L1.building.yaml` 中 `graph_idx: 1` 的 lane。
- 用途：前端 3D 場景內 Baymax、護士等人物的移動。
- 目前由多組分離的短路線構成，waypoint 不需要命名。
- 前端使用的是轉換後的 `frontend/public/generated/rmf-navigation-graph-1.json`。

## 前端 JSON

前端不直接讀取這兩個 YAML。執行下列指令會重新生成導航圖並轉成 JSON：

```bash
cd frontend
npm run navigation:generate
```

輸出對應關係：

| 來源 | 前端輸出 | 用途 |
|------|----------|------|
| `nav_graphs/0.yaml` | `frontend/public/generated/rmf-navigation.json` | 機器人導航與路線顯示 |
| `nav_graphs/1.yaml` | `frontend/public/generated/rmf-navigation-graph-1.json` | 人物走路動畫 |
