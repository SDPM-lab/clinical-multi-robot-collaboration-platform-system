# 前端測試與響應式驗證紀錄

日期：2026-11-16

## 本次調整

- 深色模式的任務派遣左側面板改用不偏粉的深棕底色 `rgba(48, 41, 37, 0.96)`；表單按鈕維持原有桃橘色。
- 淺色模式維持原面板樣式，未套用深色面板覆寫。
- 窄螢幕且高度較短時微調面板上方留白，避免建立表單面板超出視窗底部。
- 中英文語系鍵一致性與地點名稱翻譯測試已納入前端測試。

## 自動化測試

執行指令：`cd frontend && npm test`

結果：**65 個測試檔通過，261 項測試通過。**

本次相關測試涵蓋：

- `frontend/test/i18n.test.js`
  - 比對繁體中文與英文語系的鍵結構（略過 `legacy` 字串橋接區）。
  - 驗證包含撇號的地點名稱 `Women's Restroom` 可依語系翻譯。
  - 驗證介面文字切換、語系保存，以及機器人識別碼等內容不被誤翻。
- `frontend/test/overviewBottomModes.test.js`
  - 更新預設繁體中文下樓層名稱與連線狀態的預期文案。

建置指令：`cd frontend && npm run build`

結果：**建置成功**。仍有既有的單一 JavaScript bundle 超過 500 kB 提示；不影響本次建置通過。

## 語系瀏覽器檢查

- 即時地圖的房間名稱與定位標籤會跟隨目前語系更新。
- 繁體中文模式下檢查到的房間與定位名稱沒有未翻譯英文地點名稱。
- 英文模式下同一批地點名稱沒有繁體中文字。
- 任務文字、`test` 等使用者輸入，以及機器人 ID 是資料內容／識別碼，保留原文而不強制翻譯。

## 任務派遣響應式檢查

在瀏覽器以深色模式檢查任務派遣頁；確認表單沒有內部捲動、建立按鈕仍在視窗可見範圍，且頁面沒有水平溢出。

| 視窗尺寸 | 側欄尺寸 | Task note 高度 | 表單內部捲動 | 建立按鈕可見 | 水平溢出 |
|---|---:|---:|---|---|---|
| 1440 × 900 | 374 × 550 | 72 px | 無 | 是 | 無 |
| 1184 × 768 | 360 × 550 | 約 61 px | 無 | 是 | 無 |
| 768 × 1024 | 520 × 550 | 72 px | 無 | 是 | 無 |
| 390 × 844 | 366 × 550 | 約 68 px | 無 | 是 | 無 |
| 390 × 640 | 366 × 544 | 58 px | 無 | 是 | 無 |

- 桌面版側欄與地圖左右排列；寬度不超過 1099 px 時改為側欄在上、地圖在下。
- 手機尺寸下表單欄位改為單欄；地圖位於表單下方，可透過頁面垂直捲動查看。
- 深色側欄實際背景色確認為 `rgba(48, 41, 37, 0.96)`，建立按鈕維持 `rgb(251, 153, 102)`。
- 淺色模式實測面板背景仍為 `rgba(255, 255, 255, 0.52)`，未被深色樣式改動。

響應式結果是本次瀏覽器手動量測；自動化測試未加入 viewport 截圖或像素比對。

## 主題、Dashboard 與表單彈出選單回歸

### 本輪調整

- 將主題狀態統一由根節點 `html[data-theme]` 提供，避免頁面節點與全域主題狀態不同步造成深淺色混用。
- 放大 Dashboard 樓層選擇按鈕文字，並補上「全棟／Building」翻譯。
- 增加任務表單欄位的垂直留白；低高度裝置仍採較緊湊的欄位間距。
- 日期與時間選單以 Teleport 脫離表單的裁切區域，使用 fixed 定位及較高層級，依視窗位置安排彈出位置。
- 調整 Dashboard 底部電量趨勢、網路、機器人連線面板高度，使其與 Task progress 面板上下對齊。

### 自動化回歸測試

執行指令：`cd frontend && npm test -- test/taskDispatchView.test.js test/clinicFloorSelector.test.js test/themeSwitch.test.js`

結果：**3 個測試檔通過，34 項測試通過。**

- 主題切換測試連續切換 4 次，確認主題只由根節點提供，主頁不再保留重複的 `data-theme`。
- 任務派遣測試確認 Teleport 時間選單可分別選取小時與分鐘，選取結果會更新時間欄位。
- 樓層選擇器測試確認投影連接線位置，以及英文「Building」與繁體中文「全棟」翻譯。

### 瀏覽器手動檢查

- Dashboard 在 1440 × 900 下，Task progress、Robot status、Network、Battery trend 面板的上緣皆為 `y = 597`、下緣皆為 `y = 890`。
- 連續切換主題時，`html[data-theme]` 交替更新；Dashboard 節點沒有另外持有主題標記。卡片實際背景會隨主題改變（淺色 `rgba(255, 255, 255, 0.92)`、深色 `rgb(85, 66, 61)`）。
- 在 390 × 640 下，派遣表單欄位區域高度 406 px（列距調整前為 382 px），`scrollHeight` 與 `clientHeight` 相同，沒有內部捲動；頁面寬度與 viewport 相同，沒有水平溢出。
- 同一手機尺寸下，日期選單位於 `body` 下、`position: fixed`、`z-index: 1100`，位置為 `y = 349–621`；時間選單同樣位於 `body` 下，位置為 `y = 405–565`。兩者皆在 640 px 視窗內，且不受表單面板裁切。
- 瀏覽器實際選取小時 `03` 與分鐘 `25` 後，開始時間欄位更新為 `03:25`。
- 390 px 寬時 Dashboard 頂部「全部／全棟」及三個樓層按鈕皆在視窗寬度內，沒有水平溢出。

上述 viewport、主題顏色與彈出選單幾何位置為瀏覽器手動量測；未使用截圖像素比對。

### 最終驗證

- `cd frontend && npm test`：**65 個測試檔通過，266 項測試通過**。
- `cd frontend && npm run build`：建置成功；仍有既有的 JavaScript bundle 大於 500 kB 提示。
- `git diff --check`：通過。

### 表單列距補充調整

使用者指出每一列仍然太擠後，將建立任務表單欄位列距由 8 px 增加至 14 px；視窗高度不超過 660 px 時使用 10 px，保留低高度螢幕的空間。

瀏覽器確認 1440 × 900、1184 × 768、390 × 844、390 × 640 下，欄位區域 `scrollHeight` 均等於 `clientHeight`，表單沒有內部捲動，建立按鈕仍在面板內，且沒有水平溢出。各尺寸量得列距依序為 14、14、14、10 px；390 × 640 下建立按鈕底部為 y = 602，仍在 640 px 視窗內。

本次相關測試：`cd frontend && npm test -- test/taskDispatchView.test.js`，**1 個測試檔、26 項測試通過**。

## 完成率卡片與全域字級選項

### 本輪調整

- 移除 Today's completion rate 卡片的展開箭頭與全螢幕切換；保留完成率儀表。
- 完成率與 Daily schedule 標題統一使用共用面板標題字級。
- 使用者選單新增小／中／大字級選擇，小為預設；選擇會套用至介面並保存，字級變化採保守級距。
- 任務表單欄位標籤行高調整為 18 px，面板最大高度調整為 594 px；一般螢幕列距為 18 px，視窗高度不超過 660 px 時採 10 px。

### 自動化驗證

- `cd frontend && npm test`：**65 個測試檔、266 項測試通過**。
- `cd frontend && npm run build`：建置成功；仍顯示既有 JavaScript bundle 大於 500 kB 的提示。
- `git diff --check`：通過。
- 字級選單測試確認小／中／大選項、中英文標籤、小為預設、選取狀態及偏好保存。
- 完成率卡片測試確認展開箭頭與按鈕不存在，儀表仍顯示。

### 瀏覽器響應式檢查

以小／中／大三種字級檢查 Dashboard 與任務表單，視窗尺寸為 1440 × 900、1184 × 768、390 × 844、390 × 640：

- Dashboard 面板及文字沒有溢出；完成率卡片右緣與 Floor 3 選項右緣對齊。
- 任務表單欄位區域沒有內部捲動或水平溢出，建立按鈕維持在面板內。
- 390 × 640 下建立按鈕底部為 y = 620，仍在視窗可見範圍內。

上述尺寸與文字溢出檢查為瀏覽器手動量測；未使用截圖像素比對。

## Dashboard 與表單再調整

- 完成率卡片等比例放大至 `scale: 1.14`，右緣與 Floor 3 選項右緣對齊。1440 px 寬時兩者皆為 `x = 362`；320 px 窄螢幕縮放後，卡片及樓層選項都未超出視窗。
- 移除 Task progress 的位置估算／路線參考提示，保留進度時間軸。
- Dashboard 的「查看全部」現在會開啟「任務派遣」的「任務排程」分頁；從導覽列再次選取任務派遣時會回到「建立任務」分頁。
- 建立任務列距再增加：一般高度為 18 px，視窗高度不超過 660 px 時為 14 px。為容納較寬鬆的列距，表單面板最大高度由 550 px 增至 574 px；低高度手機仍按可用視窗高度縮小。
- 瀏覽器在 1440 × 900、1184 × 768、390 × 844、390 × 640 檢查列距；所有尺寸欄位區域皆無內部捲動，建立按鈕仍在面板內，沒有水平溢出。390 × 640 的建立按鈕底部為 y = 626。
- 自動化回歸：`cd frontend && npm test`，**65 個測試檔、266 項測試通過**；`npm run build` 成功（仍有既有 bundle 大於 500 kB 的提示）；`git diff --check` 通過。

## 排程週檢視與任務備註欄位

- 將排程歷史的作用中檢視選項（包含 Weekly）前景色改用主題橘色 token，避免顯示成棕色。
- 任務備註欄由 3 列增加至 4 列；表單面板可用高度上限調至 620 px，視窗高度不超過 660 px 時縮小欄位列距及表單內距，維持短螢幕可用空間。
- `cd frontend && npm test -- test/scheduleHistoryView.test.js test/taskDispatchView.test.js`：**2 個測試檔、37 項測試通過**。
- `cd frontend && npm run build`：建置成功，仍有既有 JavaScript bundle 大於 500 kB 提示；`git diff --check` 通過。
- 本輪未重新進行瀏覽器 viewport 手動量測。

### 時間選單自動關閉

- 時間選擇器需分別選取小時與分鐘；兩欄都完成選取後自動關閉，完成第一欄時維持開啟以便選擇另一欄。
- `cd frontend && npm test -- test/taskDispatchView.test.js`：**1 個測試檔、27 項測試通過**。
- `cd frontend && npm run build`：建置成功，仍有既有 JavaScript bundle 大於 500 kB 提示；`git diff --check` 通過。

### Priority 選項列填滿修正

- 移除優先級分段列多出的 2 px 內距，並把按鈕高度調整至填滿選項軌道；四個選項均分整列寬度。
- `cd frontend && npm test -- test/taskDispatchView.test.js`：**1 個測試檔、27 項測試通過**。
- `cd frontend && npm run build`：建置成功，仍有既有 JavaScript bundle 大於 500 kB 提示；`git diff --check` 通過。

## 統一七台機器人配置為 2／2／3

- 統一為 2 Clean、2 Medical、3 Ward：C01/C02、M01/M02、W01/W02/W03。
- ROS fleet、PPO action 順序、後端名冊、前端展示／示範名冊及相關測試與文件同步；`hospital_robot_5` 現為 W01（ward），robot 6–7 為 W02/W03（ward）。
- 前端 5 個測試檔、22 項測試通過；後端 `RobotRegistrationTests` 3 項通過。
- Python AST、PPO ID 對應與 ROS YAML 名冊驗證通過，確認順序與 2／2／3 類型分布一致；`git diff --check` 通過。
- `cd frontend && npm run build` 成功；仍有既有 bundle 大於 500 kB 的提示。

## Robot Status 移除 Required capabilities

- 從 Robot Status 資訊卡移除不必要的 Required capabilities 列及對應標籤樣式，不再佔用資訊卡垂直空間；下方資訊與結構控制隨版面自然上移。
- `cd frontend && npm test -- test/robotFleetView.test.js`：**1 個測試檔、4 項測試通過**，包含確認該欄位不再顯示且結構控制保留。
- `cd frontend && npm run build`：建置成功，仍有既有 JavaScript bundle 大於 500 kB 提示；`git diff --check` 通過。

### 移除重複的 ROS telemetry 詳細列

- Robot Status 資訊卡移除 ROS telemetry 狀態、時間戳與說明文字；仍保留 Connected／Disconnected 判斷使用的資料新鮮度邏輯。
- 回歸測試確認 telemetry 詳細列不存在、未收到資料時仍顯示 Disconnected，且過期資料不會顯示為已連線。
- `cd frontend && npm test -- test/robotFleetView.test.js`：**1 個測試檔、4 項測試通過**。
- `cd frontend && npm run build`：建置成功，仍有既有 JavaScript bundle 大於 500 kB 提示；`git diff --check` 通過。
