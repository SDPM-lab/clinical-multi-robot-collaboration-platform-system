# MediSync Phase 2｜TaskCreationPhaseVNext

原版 Studio Composition `Scene-2` 指向 `TaskCreationPrototypeV10`，保留可比較。精修版沿用 16.5 秒、1920 × 1080、30 fps。下列影格從 0 起算。

## 根因與修改

- V10 以 1600 × 900 畫面切出 416 × 620 表單及 480 × 234 確認窗，再分別放大 1.38 倍與 1.95 倍。這兩個裁切區的來源像素本來就低於輸出覆蓋區；排程列表本身則由 HTML 排版，細節因此特別明顯。VNext 在相同 1600 × 900 CSS viewport 擷取原生 3200 × 1800 PNG，保留同樣的設計尺寸、欄位與字型。
- V10 表單和地圖是獨立場景。圓形遮罩的地圖亮底先遮住表單，而回切遮罩又讓新版表單從一條中線才開始出現。游標也在分開的地圖片段中重新起步。這些是影格內容和圖層交接問題。VNext 持續保留同一表單，先在旁邊打開同一張地圖，確認 Ward A 後將它重構成主畫面，保留地標與已畫路線，再縮回表單旁完成交棒。兩個面板以位置移動交棒，避免半透明疊在一起時讓表單文字透到地圖上。
- Vue 的 Medication delivery 會固定唯一的 Pharmacy 起點。擷取腳本確認 Source 控制不可用，並實際以 Ward A 地標選定 Destination。影片相應顯示自動帶入的 Pharmacy 與一次定位提示。
- 同一個游標連續追蹤表單、地標與按鈕；各項回應依固定影格觸發。無 spring 或以真實時間驅動的重置。Reschedule 確認窗為原版擷取，於清單上方以透明度與 6 px 垂直位移開關。

## Shot Timing Sheet

| 操作 | 到達／Hover | Press | 回應、閱讀與交棒 |
|---|---|---|---|
| Task type | 22 | 26 | 28 開原生選單；44 游標到 Medication delivery 並高亮；48 選取；50 按原網站規則固定 Pharmacy |
| Form → Map | — | — | 60–86 表單移到左側；75–90 在右側揭露同一張地圖；102 輕亮 Pharmacy |
| Ward A | 130 | 135 | 137 表單目的地更新並顯示地標；137–154 地圖成為主畫面；154–183 逐段描路；183–193 閱讀 |
| Map → Form | — | — | 193–202 保留地標與路線並縮回；202–211 地圖退出、表單回到中央；保留 Pharmacy、Ward A、14:20 |
| Task note | — | — | 211–239 逐字輸入；239 起可讀全文 |
| Priority | 241 | 245 | 245–254 Normal → High，表單保持固定 |
| Create task | 274 | 279 | 282–299 提交中；300 成功；304–309 鈴鐺出現；322–334 通知展開；334–358 讀 T0002 |
| Schedule handoff | — | — | 359–374 共用 T0002 卡片交接；清單接手 |
| Edit / start time | 389 / 399 | 391 / 401 | 393 啟用編輯；410 草稿切至 15:05 |
| Save / Re-add | 420 / 452 | 422 / 454 | 424–430 顯示原版確認窗；456 模擬成功；456–462 關閉；461–473 重排；488 可讀已更新的 15:05 |

## Shotcraft 配方

- `canvas-materialize-moves / panel-to-canvas` 的共用視覺物件移動原則用於 Form → Map → Form；表單和地圖各用獨立幾何插值。
- `line-carry-transition` 的資訊延續用在地標到路線：同一條實際路徑以 SVG dash offset 展開，縮回後保留同一個進度。
- `mosaic-reframe` 的固定項目 ID 和獨立位置插值用在既有 Task Schedule 重新排序，保持 T0002 身分。
- 保留 V10 的 `document-typewriter-reveal`、`segmented-thumb-hero` 和 `row-embed`，分別用於 Task Note、Priority 和通知到排程的共用卡片。

擷取以瀏覽器隔離回應執行原版 Task Dispatch 的建立與重新排程，使用 T0002、Medication delivery、Pharmacy → Ward A、High、14:20 → 15:05。旁白、字幕、音樂與音效沿用 V10 的錄音和時間位置。
