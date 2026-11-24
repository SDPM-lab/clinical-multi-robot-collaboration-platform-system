# 前後端流程驗收清單

這份文件用來**逐頁操作並確認前端、API、後端及 ROS/RMF 的資料流程**。請在實際測試並確認結果後勾選對應項目；未測試、只看過程式碼或只通過單元測試時，先不要勾選。

> 勾選代表該項流程已在指定環境實際驗證，不單純代表程式碼已存在。

## 測試紀錄

- 測試日期：＿＿＿＿＿＿
- 測試分支／版本：＿＿＿＿＿＿
- 測試環境：
  - [ ] 本機開發
  - [ ] Render / 部署環境
  - [ ] ROS/RMF 整合環境
- 測試人員：＿＿＿＿＿＿

## 0. 測試前準備與共通檢查

- [ ] 後端可啟動，健康檢查 `GET /api/health` 回傳 `200` 與 `{ "status": "healthy" }`。
- [ ] 前端可開啟；後端網址及 Vite proxy / `VITE_API_BASE_URL` 指向目前測試的 API。
- [ ] 瀏覽器開發者工具 Network 沒有 CORS、連線或憑證錯誤。
- [ ] API 的 OpenAPI 文件 `GET /api.yml` 可取得；Development 環境 Swagger UI 可載入此規格。
- [ ] 確認測試資料來源：正式後端資料、ROS 即時資料、前端示範資料、路網推算或模擬資料；在本次結果中有標明來源。
- [ ] 確認後端的任務儲存方式及服務重啟後資料是否保留；目前任務資料使用記憶體儲存，重啟後不應假設任務仍存在。

## 1. 登入、註冊與個人資料

### 登入 / 註冊頁

- [ ] 未登入直接開啟首頁時，導向登入頁；登入後可回到原本要求的頁面。
- [ ] 使用有效帳密登入，前端呼叫 `POST /api/auth/login`，成功後收到使用者資料及登入 Cookie，並進入平台。
- [ ] 使用錯誤帳密登入，API 回傳 `401`；畫面顯示錯誤且不進入平台。
- [ ] 註冊時驗證名稱、Email、密碼與確認密碼；有效資料呼叫 `POST /api/auth/register`，成功後建立登入狀態。
- [ ] 使用已註冊 Email 再註冊，API 回傳 `409`，畫面顯示重複帳號錯誤。
- [ ] Development 環境的快速登入可用；正式環境或非本機來源呼叫 `POST /api/auth/dev-login` 時不可登入。
- [ ] 更新頁面後，前端呼叫 `GET /api/auth/me` 並以 Cookie 還原登入者；無效/過期工作階段會回到登入頁。
- [ ] 登入失效時，受保護 API 的 `401` 會清除前端登入狀態並導向登入頁。

### Cookie / CSRF 防護

- [ ] 登入前可呼叫 `GET /api/auth/csrf`；回應包含 token，瀏覽器保存防偽 Cookie。
- [ ] 註冊、登入、登出及其他寫入 API 使用 Cookie credentials，並帶上 `X-CSRF-TOKEN`。
- [ ] 登入或註冊成功後，前端會重新取得 CSRF token，再送出後續寫入請求。
- [ ] 不帶有效 CSRF token 的寫入請求被拒絕；正常前端操作不會因 CSRF 驗證失敗。
- [ ] 正式 HTTPS 環境登入 Cookie 為安全的 HttpOnly Cookie；跨來源部署時瀏覽器實際能帶上登入 Cookie。

### 登出 / 個人資料

- [ ] 登出呼叫 `POST /api/auth/logout`；成功清除 Cookie 並回到登入頁。
- [ ] 登出 API 失敗時，畫面會顯示錯誤，不假裝登出成功。
- [ ] 更新個人名稱及有效 PNG/JPEG/WebP 頭像，呼叫 `PATCH /api/auth/profile`；重新載入後資料仍正確。
- [ ] 不支援的圖片格式、超過大小限制或不合法名稱會被拒絕並顯示錯誤。

## 2. Dashboard / Overview 首頁

- [ ] 登入後首頁顯示 Overview；無登入狀態不可進入。
- [ ] Overview 呼叫 `GET /api/robots` 與 `GET /api/v1/task`，兩者成功時以後端資料產生即時摘要。
- [ ] 等待約 5 秒確認 Overview 會重新取得機器人與任務資料；離開頁面後不再持續輪詢。
- [ ] 後端回傳機器人數量、連線狀態、電量或任務狀態變化時，對應的即時區塊會更新。
- [ ] 今日完成率、任務日曆及每台機器人的任務進度與 API 任務資料一致；零任務時不顯示虛構的完成資料。
- [ ] 即時網路/連線資訊依 API 的 `connection` 狀態顯示，斷線時不把舊快照標成最新。
- [ ] 後端/API 失敗時，畫面明確顯示資料錯誤或過期狀態；不把示範資料冒充成即時後端資料。
- [ ] 確認本頁仍可能使用 `overviewDemoData` / `demoFleetStore` 的區塊（例如外框或部分展示元件）；已標示哪些數字是示範值，沒有把它們當成 API 實測結果。
- [ ] 點選樓層、日期、Dashboard 導航與版面互動正常；不會因即時資料更新重設使用者選擇。

## 3. Task Dispatch / 任務派遣頁

### 載入清單與機器人

- [ ] 開啟派遣頁呼叫 `GET /api/v1/task` 和 `GET /api/robots`；任務及機器人分別正確顯示。
- [ ] 任務及機器人清單約每 5 秒更新；任一請求失敗時呈現 stale/error 狀態，不清除另一個成功取得的資料。
- [ ] 任務依選定日期篩選；`completed`、`failed`、`cancelled` 終止任務不出現在待處理清單。
- [ ] 地圖與表單使用相同的起點、目的地及 waypoint ID 對應；畫面顯示名稱與 API 傳送的 ID 正確。

### 建立任務

- [ ] 輸入任務類型、起點、目的地、優先級、排程時間及可選備註後，前端呼叫 `POST /api/v1/task`。
- [ ] 確認 request body 欄位正確：`taskType`、`origin`、`destination`、`priority`、`scheduledAt`，以及可選 `robotId`、`note`。
- [ ] API 回傳 `201` 時顯示任務代碼/成功通知，並重新讀取清單，新任務出現在正確日期。
- [ ] 建立成功只代表後端建立任務；未設定外部分派端點時不宣稱已經派給機器人。
- [ ] 欄位驗證失敗、未登入、CSRF 失敗或伺服器錯誤時顯示錯誤，不顯示成功通知。

### 修改排程 / 刪除

- [ ] 對允許變更的任務修改時間，先出現確認流程，再呼叫 `PATCH /api/v1/task/{task_id}/schedule`。
- [ ] 排程更新成功回傳替代任務後，前端以新任務 ID/代碼更新清單，不保留已替換的舊任務卡片。
- [ ] 對已開始、等待外部派工確認或不允許變更的任務修改排程，後端回傳對應錯誤，前端不顯示成功。
- [ ] 刪除任務前顯示確認；確認後呼叫 `DELETE /api/v1/task/{task_id}`，成功後清單移除該任務。
- [ ] 後端拒絕刪除已處理任務時顯示錯誤，前端保留仍存在的任務。
- [ ] 檢查任務卡片時間、狀態與任務 ID 和 API 回應一致，沒有用前端示範值覆蓋正式資料。

### 優先級與取消 API（需驗證 API，即使目前畫面未提供操作）

- [ ] 呼叫 `PATCH /api/v1/task/{task_id}/priority` 修改未處理任務；成功為 `204`，不允許修改時正確回 `403`。
- [ ] 呼叫 `PATCH /api/v1/task/{task_id}/abort` 取消尚未送出/指派的任務；成功狀態更新為 cancelled。
- [ ] 嘗試取消已送出或已指派任務時回 `409`，前端/API client 不顯示取消成功。
- [ ] 以不存在的 ID 查詢、修改、取消或刪除任務時回 `404`。

## 4. Schedule History / 排程歷史頁

- [ ] 開啟歷史頁時呼叫 `GET /api/v1/task` 和 `GET /api/robots`；不使用示範任務填補 API 空結果。
- [ ] API 任務只在終止狀態時被整理成歷史事件；待處理或進行中任務不誤列為已完成歷史。
- [ ] 日、週、月檢視、日期切換、狀態/優先級/機器人篩選及文字搜尋均正確作用於 API 任務。
- [ ] 選取一筆歷史任務時，任務詳情、任務代碼、起終點、機器人名稱及備註和 API 資料一致。
- [ ] Actual start/end 與耗時只使用後端實際時間；缺少實際時間時顯示 `—`，不以預定時間填成實際時間。
- [ ] 開始延遲以實際開始時間與預定時間計算；缺少任一時間時顯示缺值。
- [ ] 頁面讀取失敗時顯示錯誤通知並允許重試；刷新後資料仍由 API 取得。
- [ ] 路線小地圖標示為路網推算/任務起終點示意，不宣稱是機器人實際行駛軌跡。
- [ ] 若歷史摘要或趨勢元件仍使用固定示意資料，已在測試結果標示，未當成後端回傳統計。

## 5. Live Map / 即時地圖頁

- [ ] 開啟即時地圖後呼叫 `GET /api/robots` 與 `GET /api/v1/task`，並約每 5 秒刷新快照。
- [ ] ROS bridge 連線狀態依 `connection.status`、錯誤訊息及 retry count 顯示；API 斷線不標示為已連線。
- [ ] 已收到 telemetry 的機器人位置、樓層、電量及狀態依 API 顯示；無 telemetry 的機器人不顯示成真實定位。
- [ ] 任務狀態及指派機器人與 API 一致；`running` 顯示為執行中，其他狀態不被錯誤推斷為已完成。
- [ ] 路線由任務起終點及本地 Traffic Editor 路網推算時，明確視為參考路線，不當成 ROS 實際路徑/進度。
- [ ] 尚未收到真實座標時的預覽位置，明確視為前端預覽，不寫回或冒充後端 telemetry。
- [ ] Development 模擬路線到達時呼叫 `POST /api/v1/task/{task_id}/simulation/arrive`，API 回 `204` 後狀態更新。
- [ ] 在非 Development 環境呼叫模擬抵達端點會回 `404`；正式任務完成只能依正式派工/機器人狀態回報。
- [ ] 地圖模型、樓層切換與路網載入失敗時有明確錯誤或降級狀態，不影響 API 狀態判讀。

## 6. Robot Status / 機器人狀態頁

- [ ] 確認目前 `RobotFleetView.vue` 的資料來源；若仍使用 `demoFleetStore`，將本頁標記為示範資料頁，不能勾選「已串接即時機器人 API」。
- [ ] 若驗收示範頁互動，機器人搜尋、樓層篩選、選取機器人、模型視角及區域聚焦正常。
- [ ] 若後續接入即時 API，應由 `GET /api/robots` 提供機器人基本資料、狀態與 telemetry；應另外驗證斷線、缺值及未註冊機器人的呈現。
- [ ] 新增/移除機器人等前端示範操作沒有被誤認為已寫入後端名冊。

## 7. App Shell / 共用互動

- [ ] Overview、Dispatch、History、Live Map、Robot Status 導航按鈕切換至正確頁面；切頁後沒有殘留重複輪詢。
- [ ] 頂部登入者名稱與頭像來自目前登入資料；修改個人資料後立即更新。
- [ ] 登出後受保護頁面不能繼續顯示為登入狀態。
- [ ] 語言切換、明暗主題、通知中心及個人資料視窗操作正常。
- [ ] 共用外框若顯示 demoFleetStore 統計，已和 API 即時統計明確區隔。

## 8. 機器人 API / ROS bridge

### 後端 API

- [ ] `GET /api/robots` 回傳 `connection`、`robots`、`pendingRobots`；七台已註冊機器人在尚無 telemetry 時仍標示離線/無 telemetry。
- [ ] `POST /api/robots/connect` 提供有效 WebSocket URL 後回成功，後端開始連線並更新 connection 狀態。
- [ ] `POST /api/robots/connect` 傳空白 URL 時回 `400`，既有連線狀態不被誤報為新連線成功。
- [ ] `POST /api/robots/disconnect` 後連線中斷，狀態與機器人 telemetry 清除符合預期。
- [ ] `POST /api/robots/confirm` 只更新已註冊機器人的顯示名稱；未知機器人不會被新增。
- [ ] `GET /api/v1/robot` 回傳機器人 `id` / `name` 清單；`GET /api/v1/place` 回傳地點 `id` / `name` / `type` 清單。

### ROS / RMF 整合（需 ROS 環境；未接實際發布者時不要勾選）

- [ ] ROS bridge WebSocket 可連線，重連、手動斷線、錯誤訊息及 retry count 符合預期。
- [ ] `/fleet_states` 訊息可由 bridge 收到並更新 `RobotStateStore`；位置、電量、樓層及機器人對應正確。
- [ ] `/dispatch_states` 只有有效的已派送/分配失敗結果更新任務派工狀態；排隊/選取不誤標為已分配。
- [ ] `/task_summaries` 的 ACTIVE、COMPLETED、FAILED、CANCELED 正確更新任務狀態。
- [ ] 實際開始時間只在首次有效開始回報時記錄；終止時間只從有效終止回報設定；執行中的預估 `end_time` 不當作實際結束。
- [ ] 重複或亂序回報不重設既有實際時間、不讓終止任務退回執行中。
- [ ] 確認 ROS `task_id` 與後端 task ID 對得上；無法對應的回報被忽略並留下可追查的日誌。
- [ ] 驗證 `/robot_nearest_waypoint` 的真實發布者與 adapter 轉送；未有發布者時明確記錄位置資訊尚未完成，不以 topic 訂閱成功當成資料已接通。

## 9. 任務派工服務 / Fleet sizing 模型

Development 預設以 `ws://localhost:9091` 連接 ROS WebSocket adapter，並透過 `POST http://localhost:5050/api/hospital/tasks` 送出派工。可用 `RosBridge__Url` 與 `TaskDispatch__Endpoint` 覆寫連線位址。若要使用後端內建模擬，可設 `TaskDispatch__DevelopmentSimulation__Enabled=true`。

- 派工請求包含 `task_id`、`task_type`、`source`、`destination`、`priority`、`required_capabilities`、`created_at`、`scheduled_at` 與 `note`。HTTP 成功代表 bridge 已接受請求。
- PPO 透過 `/hospital_ppo_assignment` 回傳 JSON。指派成功回傳 `task_id`、`status: 3` 與 `assignment: { "is_assigned": true, "expected_robot_name": "<ROS 機器人名稱>" }`，分配失敗回傳 `task_id` 與 `status: 4`。
- 前端繼續使用既有的任務 API 與 `GET /api/robots`。任務狀態由後端根據 ROS 回報更新，即時車隊遙測來自 `/fleet_states`。

- [ ] 任務建立與派工狀態分開驗證：建立任務成功不等於模型已選定機器人。
- [ ] 未設定 `TaskDispatch:Endpoint` 時，到期任務不會假裝派送成功；狀態及 UI 顯示符合目前服務規則。
- [ ] 設定正式派工 endpoint 後，確認 payload 的任務 ID、類型、起終點、優先級、能力需求及建立時間符合模型契約。
- [ ] 確認 fleet sizing experiment 的輸入/輸出介面、任務分配回傳格式、錯誤處理、逾時及重試規則後，才勾選模型端到端整合。
- [ ] 模型成功回覆後，後端只在收到有效的分配確認時更新 assigned robot / `assigned` 狀態；HTTP 接受請求不當成已執行。
- [ ] 模型拒絕任務、逾時、離線或回傳不合法資料時，任務狀態與錯誤日誌可追蹤，前端不顯示虛假的指派成功。
- [ ] 重新排程已外部分派的任務前，先驗證模型/派工服務支援撤回舊指派；撤回未確認時保留原任務，不建立替代任務。
- [ ] 用固定輸入及已知結果測試模型與後端的轉換；確認模擬/實驗結果沒有被當成真實 ROS 執行結果。

## 10. SSE 任務狀態更新

- [ ] 登入後連線 `GET /api/v1/task/event/trace`，回應 Content-Type 為 `text/event-stream`。
- [ ] 任務狀態改變時收到 `data:` JSON 事件，包含 task ID、舊狀態及新狀態。
- [ ] 狀態未改變時不會每秒送出完整任務快照；關閉連線後伺服器停止該客戶端串流。

## 11. 自動化測試與發版前檢查

- [ ] 執行後端單元測試並確認任務狀態轉移、派工、排程、ROS 回報及帳號驗證案例通過。
- [ ] 執行後端 Controller 整合測試並確認 HTTP 狀態碼、Cookie/CSRF、驗證錯誤與授權行為通過。
- [ ] 執行前端測試並確認登入、Dashboard 快照、派遣表單、排程歷史及錯誤狀態案例通過。
- [ ] 前端 production build 成功；後端 build 成功；沒有新增編譯警告/錯誤未處理。
- [ ] 在 Render 部署環境確認前端來源已列入 CORS、API 網址正確、HTTPS Cookie 正常、環境變數已設定且沒有依賴 `localhost`。
- [ ] 手動完成本清單中適用於此次版本的端到端流程；未具備 ROS/模型服務的項目保留未勾選並記錄阻塞原因。

## 未通過項目 / 待處理紀錄

| 日期 | 頁面 / 流程 | 預期結果 | 實際結果 / 錯誤 | 後續處理 |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
