# 全站資料對照檢查（2026-11-15）

| 頁面 | 目前前後端對照 | 仍需處理 |
| --- | --- | --- |
| Task Dispatch | 五種 `taskType`、`source`、`destination`、四級 `priority` 與後端建立任務 API 相符；固定端點依 `task_profiles.yaml` 對照。 | 前端與後端各自維護一份合法端點表，設定檔變動時需同步或產生共享資料。正式 PPO 派工未接通。 |
| Dashboard | 今日完成率、行事曆、七台機器人及任務進度來自 `GET /api/v1/task` 與 `GET /api/robots`；電量歷史明確標示為模擬。 | 參考路線不是實際路點回報；電量歷史、網路狀態及心跳期限尚無對應 API。 |
| Schedule History | 終止任務的 `scheduledAt`、`startedAt`、`finishedAt`、`taskCode`、`assignedRobot` 來自任務 API。 | 後端任務仍存記憶體，重啟後不保留歷史；未開始／結束時間不能補成真實執行時刻。 |
| Live Map | 七台名冊、任務狀態、起終點及 ID 使用後端資料；Traffic Editor Graph 0 計算參考線。 | 沒有 ROS 定位時機器人位置與移動是 Development 預覽；實際行走路線、路點進度及真實完成回報尚未對接。 |
| Robot Status | 七台機器人的執行名冊是 2 Clean／2 Medical／3 Ward；樓層、狀態、電量、G1 型號與描述套件來自 `/api/robots`。 | 沒有遙測時電量／位置缺值；溫度及心跳期限尚無 API。ROS 的 G1 是分件模型，網頁互動 3D 暫時仍使用現有 A2D 整機預覽。 |

## 本次修正的即時地圖路線

`toScheduleTask()` 為排程畫面把 `source` 轉成顯示名稱，Live Map 過去重用這個結果去查 Graph 0 的地點 ID，導致已開始的任務只顯示標籤、沒有路線。`adaptLiveMapSnapshot()` 現在保留後端原始 `source` 和 `destination` ID 供路徑搜尋；畫面仍在顯示時翻譯名稱。當任務是 Running、已指派機器人且兩端在 Graph 0 連通，會畫出 Source → Destination 的參考線。圖中的 M01／M02 是已指派的機器人顯示碼；Pending 尚未分配機器人時不列為執行中任務。

## PPO 模型與執行配置

現有 `reward_confirm_sweep27_w50_a30_q15_i05_seed7104_200k.json` 明確記錄 `fleet_configuration: [2,2,3]`；`experiments/fleet_sizing/rl/train_battery_v2.py` 也設定 2 Clean／2 Medical／3 Ward。執行名冊現已統一為相同分布：C01/C02 為 Clean、M01/M02 為 Medical、W01/W02/W03 為 Ward；`final_model.zip` 仍未存在於排程程式設定的模型路徑，因此不能據此宣稱正式 PPO 推論已接通。

五種任務代碼、四級優先級與 16 個固定地點的名稱及順序，目前在前端設定、後端 API 和 `observation.py` 可對應；這不等於既有模型的機器人 action 順序已一致。
