# 任務與機器人類型對照

本次以 `task_profiles.yaml`、`robot_profiles.yaml` 為基準，前端建立任務與後端 API 使用五種任務代碼：`waste_transport`、`clothes_collection`、`medication_delivery`、`specimen_delivery`、`ward_service`。表單依任務類型顯示合法起終點；後端建立端點也會拒絕不在設定檔範圍內的組合。能力需求仍由後端自動產生，但建立表單不再顯示內部能力清單。

| 顯示編號 | ROS 名稱 | 類型 | 可執行任務 |
| --- | --- | --- | --- |
| R01–R02 | hospital_robot_1–2 | clean | waste_transport、clothes_collection |
| R03–R04 | hospital_robot_3–4 | medical | medication_delivery、specimen_delivery |
| R05–R07 | hospital_robot_5–7 | ward | medication_delivery、ward_service |

後端名冊的原始 ID 維持不變，新增 `robotType` 供前端識別；開發模擬派工只會選相容的機器人。七台機器人依 2 Clean／2 Medical／3 Ward 對應：C01/C02、M01/M02、W01/W02/W03。`fleet_instances.yaml`、執行用 PPO 排程程式、後端名冊與前端顯示碼均採此順序；此分布也與 `sweep27 / seed7104 / 200k` metadata 的 `[2,2,3]` 一致。

建立任務時，只有一個合法 Source 或 Destination 的欄位會自動填入、灰色鎖定並顯示禁止選取圖示。地圖會標出固定端點；使用者從欄位或地圖選取另一端後，也會標出該端點及參考路線。例如檢體配送選 Ward B 時，地圖顯示 Ward B 起點與 Laboratory 終點。規則由前後端的任務地點對照表對應 `task_profiles.yaml`。

目前前後端各有一份合法地點表；日後若 `task_profiles.yaml` 改動，應改成建置時產生共享設定，避免兩份規則漂移。正式強化學習派工仍未接入，現階段相容性派工是 Development 模擬。
