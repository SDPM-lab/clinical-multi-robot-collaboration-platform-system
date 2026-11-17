# Live Map 前後端欄位對齊與顯示檢查

## 已修改

- Live Map 每 5 秒共用機器人／任務後端快照，清單、樓層數字、任務與模型使用同一份資料。
- 七台機器人名冊預設 L1（前端 F1）；內部保留 robot-a、robot-b、robot-hospital_robot_3～7。
- 任務 UUID 用於關聯，TaskCode 用於顯示，AssignedRobot 使用後端機器人 ID。
- 七台缺定位時可使用已獲同意的分散路網展示位置，輪詢不跳位；收到實際定位時優先採用實際值。
- 七組路線／卡片配色已建立，與後端 ID 有明確視覺對照，不修改後端識別碼。
- 路線依後端 Running 任務的起終點查 Traffic Editor 完整路網，不限原本三筆示範任務。
- 上方摘要原本擋住導覽列，已移到左側「總覽」工具面板；僅錯誤保留獨立提示並放在導覽列下方。
- Live Map 優先級與 Create task 共用 priority 翻譯鍵，英文 emergency 統一顯示 Emergency；不再透過舊中文轉譯為 Urgent。
- 圖層面板補齊英文房間標籤等文案。

## 後端 ID 程式位置

| 資料 | 使用方式 | 程式位置 |
| --- | --- | --- |
| 機器人名冊 | 七台預設 L1；前兩台 robot-a／robot-b，其餘 robot-hospital_robot_3～7 | backend/Server/Services/RobotStateStore.cs 建構子、GetMapping() |
| 獨立註冊資料 | 名稱、ID、ROS 名稱與預設樓層 | backend/Server/Models/RobotRegistration.cs |
| 任務內部 ID | Guid.NewGuid().ToString() | backend/Server/Services/TaskService.cs CreateTaskAsync() |
| 任務顯示代碼 | T0001 等流水號 | backend/Server/Services/Tasks/TaskStore.cs NextTaskCode() |

ConcurrentDictionary 是執行緒安全的記憶體字典，不是資料庫；跨字典或多屬性修改也不會自動成為原子交易。

## 圖層選項是否來自後端

| 選項 | 資料來源與作用 | 對齊情況 |
| --- | --- | --- |
| Location nodes | Traffic Editor 地點節點顯示開關 | 靜態地圖資產，不是後端欄位 |
| Base navigation graph | Graph 0 可通行節點與連線 | 靜態地圖資產，不是後端欄位 |
| Reference routes | 後端 Running 任務起終點，配合路網搜尋參考線 | 任務來自後端；路徑不是實際導航回報 |
| Reference route arrows | 參考線方向視覺效果 | 本地顯示開關 |
| Location and task labels | 地點來自地圖；任務代碼、機器人與優先級來自後端 | 混合來源，內部關聯仍用 UUID |
| All room labels | 房間名稱與標籤 | 靜態地圖資料；已補英文 |
| People | 粉紅色人物與動畫 | 前端展示，不是後端機器人或人員定位 |
| Robots | 實際定位優先，缺定位時展示已核准的暫時位置 | 名冊／樓層來自後端，暫時位置不是即時資料 |
| Task priority | 依任務 priority 篩選參考線、標籤及關聯模型 | low、normal、high、emergency 與後端一致 |
| Only show selected priorities | 未選優先級隱藏，或未啟用時淡化 | 本地顯示偏好，不修改後端任務優先級 |

TaskPriority enum 位於 backend/Server/Models/TaskPriority.cs：Low=0、Normal=1、High=2、Emergency=3。HTTP JSON 使用 camelCase 字串。前端排序可緊急優先，並不代表 enum 或傳輸值不同。歷史頁的 urgent 是既有展示分類，不是 Live Map 寫回後端的值。

## 左側各工具的資料來源

| 工具 | 資料來源／限制 |
| --- | --- |
| 總覽 | 路網點數來自 Graph 0；執行中任務與機器人數依目前樓層的後端快照計算。缺樓層者另列，不隨意指定樓層。 |
| 機器人 | 後端名冊、名稱、狀態、電量與樓層；未收到資料時電量為 —，不假造在線狀態。 |
| 執行中任務 | 僅 Running 且指派機器人能對應目前樓層的任務。Assigned 尚未開始，不算 Running。 |
| 地圖圖層 | 見上表；大多數是前端顯示開關，並非每個項目都需要對應一個 API 欄位。 |
| 樓層／縮放／重設／跟隨 | 樓層用於篩選資料；其餘為本地相機控制。F2／F3 地圖仍未提供。 |

## 任務現在能做到哪一步

1. POST 建立後進入 Pending，背景工作下一輪立即提交派工，不等到預定開始時間。
2. TaskDispatch:Endpoint 尚未接強化學習模型；Development 開啟模擬時會立即選擇名冊中的可用機器人並轉 Assigned，到預定時間才轉 Running。
3. 外部 HTTP 入口提交成功但尚無分配結果時維持 Pending，`dispatched=true`；收到分配的機器人 ID 才轉 Assigned。已移除 AwaitingAssignment。
4. Assigned 與 assignedRobot 有效時，可顯示已指派資訊；尚未開始不會被當成執行中。
5. Running、可對應樓層及可連通的起終點都有資料時，Live Map 會顯示參考路線。
6. Development 模擬任務進入 Running 且沒有真實定位時，前端會讓暫時模型沿 Graph 0 參考線移動；每次輪詢不重置動畫。畫面確認模型抵達任務終點後，呼叫僅限 Development 的抵達 API；後端核對任務、機器人與起終點才標記 Completed。若收到真實定位，立即改由後端座標控制模型。

目前 Development 可展示「建立成功 → 模擬選機器人 → 顯示參考線 → 模型沿線動畫」；真實派工、即時定位與完成回報仍未接通。

## 本輪執行中版本檢查

後端 PID 92569 在 2026-11-08 15:48:10 啟動，七台 F1 名冊相關組件在 16:30 後更新。此程序早於名冊更新，需重啟並核對新版 GET /api/robots 應回傳七台、levelName=L1；只刷新前端不會更新已載入的後端程式。本輪未擅自停止後端，因記憶體任務重啟後不保留。

## 待確認／待修改

- [ ] 在未接強化學習與 ROS 2 時，是否建立只限開發環境的指派／狀態模擬入口，供驗證整個前後端流程。
- [ ] 實際路徑、進度、ETA、定位有效性與過期判斷的契約；不能把參考線當真實執行資料。
- [ ] 七台畫面名稱是否統一 R01～R07；建議新增 displayCode，不更動原 ID。
- [ ] 資料庫保存名冊、樓層、任務與歷程，目前仍在記憶體。
- [ ] 每層七台的配置管理與超額限制；目前不是直接隱藏第八台。
- [ ] F2／F3 地圖、座標校準及型號對應模型資產。
- [ ] Dashboard、Robot Status、全域搜尋尚有各自的示範來源，本輪不宣稱整站已接通。
