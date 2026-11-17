# Task Dispatch 檢查與可用性調整

本文件記錄 Task Dispatch 檢查；API 規格書另外整理，不部署網站。

## 後端現況

- 建立任務只保存為 Pending；背景排程在預定時間到達後傳送 HTTP 請求。
- 建立後立即提交派工；HTTP 成功而尚未收到分配結果時為 Pending 且 `dispatched=true`，收到派工服務有效分配結果才為 Assigned；舊 RMF 分配回報預設停用，執行回報才設 Running。
- RequiredCapabilities 由 TaskService 依任務類型推導，再透過 HttpTaskDispatcher 傳送 required_capabilities。它是任務需求，不代表已驗證機器人的能力。
- archive/hospital_ros_api_bridge_legacy.py 有能力檢查與排程相關程式，但此為舊版程式，不再作為預設派工入口。強化學習模型整合暫緩，TaskDispatch:Endpoint 預設為 null。
- RequestedRobotId 有保存，但目前不傳送指定機器人。本輪前端停用手動指定選項，送出 robotId: null；API 本身仍保留原欄位。
- 修改時間允許未送出的 Pending 與未開始的 Assigned；確認重新排程後建立新任務、新 ID 並清空指派。執行中鎖定。Task schedule 不再編輯優先級，建立表單保留優先級。刪除只允許未送出的 Pending。
- 外部服務已設定時，Assigned 重新排程須先確認撤回原指派；此協定尚未串接，會拒絕操作並保留原任務。模型未接時只處理平台本地狀態。
- 使用者取消只允許未送出的 Pending；已指派與執行中禁止取消。即時地圖也不提供執行中取消入口。
- 任務保存在記憶體，後端重啟後不保留。
- 本輪補上建立任務時的 TaskType／Priority 列舉值驗證。缺省 TaskType 仍使用 enum 預設值，尚未改成必須明確提供。

## Nielsen 十項原則對照

| 原則 | 本輪處理／現有限制 |
| --- | --- |
| 系統狀態可見 | 載入、每 5 秒更新、更新失敗、送出中均顯示；失敗保留舊資料並可重試。 |
| 貼近使用者語言 | 說明自動分配與當地時間；能力需求改為補充說明。 |
| 使用者控制與自由 | 將實際重設表單的 Cancel 改名為 Reset form；保留 Esc／外部點擊收起選單。尚未提供重設復原。 |
| 一致性與標準 | 中英文同步，保留既有優先級與成功／錯誤提示風格。 |
| 錯誤預防 | 預設時間為現在加 5 分鐘；檢查未來時間、有效地點與不同起終點；送出時鎖定表單。地點檢查目前是前端規則，後端仍需建立地點目錄驗證。 |
| 辨識優於回憶 | 保留地點選單與路線預覽，增加地圖選點步驟提示。 |
| 彈性與效率 | 可由表單或地圖選點，時間仍可輸入或使用時／分選擇器。自訂 listbox 的完整方向鍵操作尚待改善。 |
| 精簡設計 | 能力需求預設收合；機器人選項明示尚未支援指定。 |
| 錯誤辨識與修復 | 本地驗證錯誤以文字呈現並聚焦，輪詢失敗可重試。 |
| 說明文件 | 在表單與地圖就地說明自動分配、時間與預覽用途。 |

這是針對本頁的啟發式改善，並非整站可用性驗收或正式使用者測試。

參考：[使用者提供的文章](https://medium.com/@hales_tsai/從十大可用性原則入手-奠定你的ux基礎-cb914d611caa)、[Nielsen Norman Group 原始原則](https://www.nngroup.com/articles/ten-usability-heuristics/)。
