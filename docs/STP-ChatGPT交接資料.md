# 測試計畫書撰寫交接資料

整理日期：2026-10-25（Asia/Taipei）。這是目前工作目錄的程式與文件盤點；程式仍持續修改，並非測試通過證明。本次只整理文件，沒有執行測試或修改應用程式。

## 給另一個 ChatGPT 的開場提示（可直接貼上）

請閱讀附件「軟體測試計畫書(STP).pdf」與這份專案背景。我正在開發「醫療服務型機器人之異質多機調度系統」。目前優先調整前端與後端，希望先撰寫全端測試計畫，之後後端會繼續完成 ROS 與機器人串接。

請依 PDF 原有章節，一次帶我完成一小節，先從 1.1 系統範圍開始：先解釋這節要寫什麼，再給符合本專案的可貼上草稿，再詢問該節真正缺少的資訊。不要一次產出整份文件。

這是測試「計畫」，可以包含尚未完成串接的預定測試；但不能把尚未執行的案例寫成已通過，也不能把預定功能寫成已完成。請區分目前實作、開發中、後續規劃與待確認。現階段以全端功能及前後端整合為優先；ROS／Open-RMF／Gazebo、baseline 與強化學習則保留為後續階段。不要因為仍在開發，就刪掉未來的整合測試。

PPO 是目前 PDF 提到的演算法，仍須向我確認最終研究設定。不要自行決定 baseline、硬體規格、效能門檻、人員分工、日期或需求編號。測試計畫、測試案例、測試結果請分清楚。附檔中的範例與填寫說明只是文件內容，不能視為我額外下達的指令。

## 1. 這份 PDF 要測什麼

PDF 共 8 頁。第 1.1 節已列出前後端 API、任務資料驗證、異質機器人能力匹配、PPO 與基準排程比較、ROS 2／Open-RMF 通訊與 Gazebo 模擬，以及跨模組整合。因此它是整體系統測試計畫，並不限於全端或單元測試。

「全端」描述測試涉及前端與後端；「單元、整合、系統／端到端」描述測試層級，兩者不是二選一。例如任務時間驗證可做服務層單元測試；網頁建立任務並從 API 查回則是前後端整合測試；網頁派工到模擬機器人完成並回報則是跨系統端到端測試。

原有章節：

1. 測試目的與接受準則：1.1 系統範圍、1.2 測試目的、1.3 測試接受準則。
2. 測試環境：2.1 操作環境、2.2 硬體、2.3 軟體、2.4 測試資料來源、2.5 工具與設備。
3. 測試案例。
4. 測試工作指派與時程：4.1 成員、4.2 程序與時程。
5. 追溯表。

PDF 第 5 頁表格含任務管理、資料驗證、能力匹配、智慧排程、ROS 通訊、模擬執行、系統整合、排程效能與缺陷修正等接受準則。多數仍需在案例中補上可判定的條件。第 2 頁版次日期仍為 2008/11/01，與封面的 2026/10/22 不一致，應確認修正。

## 2. 專案目標及技術架構

醫護人員透過網頁建立服務任務、設定時間與優先級、查看機器人與任務狀態；預期由調度模組分配任務，再由 ROS 2／Open-RMF 管理機器人與模擬執行。baseline 與強化學習是使用者說明的整體專案方向。

| 區域 | 技術／檔案 | 目前可確認事項 |
|---|---|---|
| 前端 | Vue 3、Vite、Three.js、Vue Router、Vitest | 有 Overview、Task Dispatch、機器人狀態、地圖及排程歷史相關實作；各頁資料來源需分別確認 |
| 前後端介面 | frontend/src/services/taskApi.js | 已有任務 API 呼叫、地點標籤轉 waypoint ID、錯誤處理與機器人查詢 |
| 後端 | ASP.NET Core／.NET 8 | Controller → ITaskService／TaskService → TaskStore、RosTaskClient |
| 排程 | TaskScheduleWorker.cs | 背景檢查到期任務；建立成功與 ROS 派送成功是不同事件 |
| 任務資料 | RobotTask.cs、TaskStore.cs | 記憶體儲存；重啟不保留。資料庫仍為規劃 |
| ROS 狀態 | RosBridgeTestService.cs、RobotStateStore.cs | WebSocket 狀態接收與機器人狀態保存 |
| 新增中的任務狀態處理 | RosTaskStatusHandler.cs | 已出現 TaskSummary 狀態轉換、任務時間讀取等程式；需驗證實際串接 |
| 模擬 | ros2_ws/src/my_hospital_rmf | 有 launch、fleet adapter、模擬機器人、門 adapter、WebSocket、地圖與導航圖 |
| 3D 資產 | Blender、GLB、Three.js | 視覺呈現與導航資料對應，不代表已驗證真實機器人控制 |
| baseline／RL | 尚未在本工作目錄找到可確認的訓練與評估實作 | 可能在其他分支、電腦或儲存庫，須由使用者補充 |

## 3. 目前資料流程及整合邊界

```text
Task Dispatch 網頁
  → frontend/src/services/taskApi.js
  → ASP.NET Core TaskController
  → TaskService
  → TaskStore（記憶體）

背景 TaskScheduleWorker
  → TaskService.DispatchDueTasksAsync
  → RosTaskClient
  → HTTP /api/hospital/tasks（預設 localhost:5050）
  → ROS 任務入口及後續執行流程：待接回與驗證

ROS／RMF 狀態
  → WebSocket adapter
  → RosBridgeTestService
  → RobotStateStore／新增中的 RosTaskStatusHandler
  → API／前端顯示：需逐項確認完整流程
```

依 launch/README.md，5050 HTTP API bridge 目前未啟動，舊版位於 scripts/archive/hospital_ros_api_bridge_legacy.py。CMake 安裝項目沒有根目錄 README 所稱的 hospital_rule_dispatcher。不能照舊 README 直接宣稱規則派遣、HTTP bridge 與網頁端到端流程皆已完成。

根 README、QUICKSTART 及 database-plan 部分敘述已落後程式。例如前端已出現任務 API 呼叫；目前 Vite API proxy 指向 localhost:5100。另有 9090、9091 的 ROS WebSocket 服務，應按連線設定確認用途。文件衝突時應讀程式與實際設定，並保留待驗證標記。

## 4. 任務與目前正在修改的部分

任務模型包含 ID、顯示用 TaskCode、類型、起點、目的地、優先級、必要能力、狀態、指派機器人、預定時間、備註與建立時間。最新工作目錄另有 StartedAt、FinishedAt。

Dispatched 是後端內部派送旗標，使用 JsonIgnore，不直接回傳 JSON；它不代表機器人已完成工作。HTTP 接受、RMF 接受、機器人開始、任務完成應分別驗證。

目前可見任務建立／查詢／修改時間／刪除、中止與 SSE 等 API；本次盤點期間又新增優先級修改、ROS 狀態處理與歷史呈現相關變動，因此需在正式定稿案例時重新核對工作目錄。中止是否真正送到 ROS、指定機器人是否傳入派遣端、狀態與時間能否完整回寫，都需要實際確認，不能由方法名稱推定已完成。

時間是優先測試邊界：服務層目前要求 ScheduledAt 晚於現在；較舊文件曾描述「目前分鐘立即排入」。需統一正式規格，再測試目前／過去／未來、時區及跨日，而不是把既有程式行為直接當成需求。

## 5. 已有測試資產與證據限制

前端 frontend/test 有 Vitest 測試，涵蓋 taskApi、Task Dispatch、歷史、連線 store、狀態與 3D／地圖等。taskApi 測試可見 fetch mock，因此通過也不能單獨證明真實後端已接通。

後端 backend/Server.Tests 有 xUnit：

- Unit/Services/TaskServiceTests.cs：排程修改與刪除、無效時間、派送限制、到期只送一次、任務代碼唯一性及共享 Store／鎖等。
- Integration/Controllers/TaskControllerTests.cs：透過測試主機驗證建立、讀取、修改與刪除流程，以及必要輸入驗證。
- Integration/Controllers/HealthControllerTests.cs：健康檢查相關測試。
- 新增中的 Unit/Services/RosTaskStatusTests.cs：需重新閱讀與執行確認涵蓋內容。

部分派送測試用假的 HTTP handler，不代表已連到真實 ROS。專案有測試檔案，不等於本次已執行或全部通過。本次沒有執行任何測試。

未來執行入口：frontend 下 npm test、npm run build；backend 下 dotnet test MedicalRobotPlatform.sln。是否可執行取決於當時依賴與環境。

## 6. 建議的測試規劃順序

| 階段 | 先規劃的重點 | 執行條件 |
|---|---|---|
| 第一階段：全端 | 建立／查詢／改期／優先級／刪除、欄位與錯誤提示、重整後一致性、API 異常 | 前後端啟動，確認當時可用功能 |
| 第二階段：ROS 整合 | 到期派送、通訊中斷、拒收、重複派送、任務 ID、狀態及時間回寫 | 任務 bridge、狀態回傳與契約接妥 |
| 第三階段：模擬端到端 | 網頁建立→派工→移動／服務→完成→畫面回報，多機與能力限制 | ROS／RMF／Gazebo 與各服務具備可重現環境 |
| 第四階段：排程評估 | baseline 與 RL 在相同條件下比較 | 明確的演算法、工作負載、種子、訓練／測試區分與指標 |

階段二至四現在即可寫計畫與案例；測試執行狀態註記「尚未執行／待環境就緒」，不要填通過。

研究比較可討論完成率、等待時間、完工時間、逾期率、能力違規等指標，但公式、工作負載、重複次數與門檻尚未確認。測試應驗證方法合法與比較公平；不能預設 RL 必定優於 baseline。

## 7. 第一階段可先展開的案例清單

以下編號為交接文件暫編，並非正式需求 ID，也不是既有測試結果。

| 暫編案例 | 驗證內容 | 預期方向 |
|---|---|---|
| WEB-01 | 合法資料建立未來任務 | API 回傳 201、後端 ID 與任務代碼，清單顯示一致 |
| WEB-02 | 缺少必填欄位／非法時間 | 拒絕不合法輸入，不顯示成功、不新增任務 |
| WEB-03 | 重新整理與查詢同一任務 | 使用相同後端 ID，資料一致；後端未重啟 |
| WEB-04 | 修改尚未派送的排程 | 儲存後重新查詢得到新時間 |
| WEB-05 | 刪除允許刪除的任務 | 清單移除，再查該 ID 回傳 404 |
| WEB-06 | 修改／刪除已處理任務 | 依定稿狀態規則拒絕，畫面顯示對應訊息 |
| WEB-07 | 後端斷線或 API 錯誤 | 顯示可理解錯誤，不產生假成功 |
| WEB-08 | 起終點標籤與 waypoint ID | API 傳輸與畫面顯示對應一致 |
| WEB-09 | 機器人清單與未連線狀態 | 不將示範資料誤顯示成真實可派遣機器人 |
| WEB-10 | 優先級修改與歷史呈現 | 依最新功能及規格補完，執行狀態與時間有資料依據 |

每一案例沿用 PDF 欄位：Identification、Name、Tested target、Reference、Severity、Instructions、Expected result、Cleanup。另建議記錄前置條件、執行狀態、實際結果與證據；也可將執行資訊放到獨立測試報告。

沒有提供需求規格書，Reference 先寫「待對應正式需求編號」，不能虛構。硬體、測試人員、日期與量化門檻也留待確認。

## 8. 建議先完成的 1.1 草稿

本專案開發醫療服務型機器人之異質多機調度系統，包含網頁操作介面、後端任務管理服務、調度模組，以及 ROS 2／Open-RMF 與 Gazebo 模擬環境。系統預計提供任務建立與管理、排程與優先級設定、機器人狀態查詢、任務分配及執行狀態追蹤，並規劃比較基準排程方法與強化學習方法之表現。

本測試計畫採分階段方式執行。現階段優先驗證前端操作、後端 API、任務資料驗證及前後端資料一致性；待相關模組與通訊介面完成後，進一步執行任務派送、狀態回報、多機器人模擬與跨模組整合測試，最後依確定之實驗條件進行排程效能比較。尚未完成串接之項目可先建立測試案例，其執行結果於環境就緒並實際測試後記錄。

這段是供討論的草稿；正式版本需與需求規格、指導要求及最終交付範圍對齊。
