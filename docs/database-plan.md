# 資料庫建立前的模型盤點

目前專案尚未使用資料庫。這份文件先整理需要保存的資料與現有程式的對應；確定資料庫種類後，再寫建表檔與連線程式。

## 建議的第一版資料表

| 資料表 | 主鍵與主要欄位 | 關聯 | 程式碼依據 |
| --- | --- | --- | --- |
| `robots` | `id`、`ros_name`（唯一）、`name`、`model`、`floor_id` | 一台機器人可被指派多個任務 | `RobotStateStore.cs`、`RobotDto` |
| `places` | `id`、`name`、`type`、`floor_id` | 一個地點可作為多個任務的起點或終點 | `PlaceController.cs` |
| `tasks` | `id`、`task_type`、`source_place_id`、`destination_place_id`、`priority`、`status`、`assigned_robot_id`（可空）、`created_at` | 分別連到起點、終點與機器人 | `RobotTask.cs`、`TaskService.cs` |
| `task_capabilities` | `task_id`、`capability` | 一個任務需要零到多種能力 | `RobotTask.RequiredCapabilities` |
| `task_events` | `id`、`task_id`、`status`、`occurred_at` | 一個任務有零到多筆狀態紀錄 | 排程歷史需要可查詢的時間線；目前後端尚無此類別 |

## 尚待對齊的欄位

1. 後端 `RobotTask.AssignedRobot` 存的是 ROS 名稱（如 `hospital_robot_1`），但 `RobotDto.Id` 另有 `robot-a` 等識別碼。入庫時必須先決定以哪個識別碼作為外鍵。
2. 前端示範機器人使用 `R01` 等 ID，與後端的 ROS 名稱和 ID 不同；前端目前也未直接讀後端任務服務。
3. 後端地點清單寫死在控制器，前端使用的地點名稱也不完全一致；建立 `places` 前需要確定統一的 ID。
4. 後端只有任務目前狀態，沒有完整狀態變更時間線。`task_events` 是為排程歷史提出的新資料表，尚未實作。
5. 機器人的電量、座標和連線狀態是即時資料。第一版建議先保留在現有 `RobotStateStore`，之後若要追蹤歷史再設計狀態快照表。

## 建立順序

1. 確定資料庫種類與 ID 規則。
2. 定稿資料表、欄位型別、外鍵和狀態值，繪製 ER 圖。
3. 建立資料庫與建表檔，驗證外鍵與基本新增／查詢。
4. 將後端任務服務改為資料庫存取，確認 API 行為。
5. 最後依資料模型與服務關係繪製類別圖。

類別圖描述程式中的類別、方法和依賴；資料庫結構則由 ER 圖與建表檔描述。兩者應相互對應，但不是同一張圖。
