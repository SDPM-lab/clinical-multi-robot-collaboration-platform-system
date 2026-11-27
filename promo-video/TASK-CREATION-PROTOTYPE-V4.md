# MediSync Scene 02 V4｜Continuity Refinement

TaskCreationPrototypeV4 · 1920 × 1080 · 30 fps · 510 frames · 17 seconds

## Shot Motion Matrix

| Shot | Composition | Primary Effect | Secondary Effect | Transition | Sound Cue |
|---|---|---|---|---|---|
| 01 · 0–89 | **Create. Simply.** 左側，原生完整表單右側 | Typography mask reveal。以 blur-slide 的錯峰文字節拍變奏 | 表單淺透視收平，原生選單點擊 | 表單任務類別接樓層畫面，中央裁幅揭露 | 短立體聲氣流；39、64 幀點擊 |
| 02 · 90–115 | 獨立 F1 桌面俯視 | overhead-camera-moves / tilt-reveal | 固定軸重整角度與裁幅 | shot-transitions / mask-wipe 的中央窗口展開 | 91 幀柔和空間音 |
| 03 · 116–209 | F1 固定，Pharmacy 至 Ward A | icon-performance-moves / attention-bounce，兩個原生標記各一次 | 依弧長沿原生路線畫單一路徑 | 兩個位置的共用標籤匹配完整表單欄位 | 126 固定起點提示、152 點擊、160 路線氣流 |
| 04 · 210–299 | 完整表單，左側仍為 **Create. Simply.** | segmented-thumb-hero，局部狀態揭露 | 優先級短暫聚焦、真實按鈕按壓與 loading | 同機位保存表單，以成功事件引入通知景深 | 233、283 幀分別為優先級、建立觸聲 |
| 05 · 300–374 | 成功通知前景與原始表單後景 | spotlight-hero-card 的前景抬升與單次微彈 | 表單略退亮度、ID 建立視覺錨點 | T0002 進入原生排程列 | 300 幀播放短 Chime |
| 06 · 375–509 | 左側 **Schedule with flexibility.**，右側完整排程 | row-embed 逐列收平與 list-reveal 錯峰 | 指示同一任務、Edit、時間欄、原生 Dialog 與 Save | 對話框確認後回到完整面板，留作未來接點 | 415、425、439、458、480 幀操作；482 幀儲存回饋；490 幀退出 Edit Mode |

另研究 element-body-moves、mosaic-reframe 與 transition-hidden-cut。把分層、穩定構圖和相同內容交接的原則轉用到既有真實介面。相鄰段落主效果依序是文字遮罩、俯視收平、標記與描線、控制項選取、前景通知、排程列入槽。

## 真實操作與音訊

- 藥品配送的 Pharmacy 固定。126 幀揭示固定起點，沒有模擬選取點擊。原生 Ward A 於 152 幀點擊後，154 幀出現目的標記，160 幀開始畫路線。
- 原生底圖擷取時單獨隱藏已選標記，再由原生擷取差分提取兩個透明圖層。路線的單一 SVG 中心線沿原生 WebGL 路徑量取。使用固定線寬與連續長度插值。
- 隔離 Demo API 驗證 POST High 任務與 PATCH 同一筆 `film-task-t0002`。排程利用真實列表、編輯、時間輸入與重新加入確認。六筆排程沿用既有優先級色、原生 ID、時間和機器人欄位。狀態由 Demo API 管理，影片沿用原版列的顯示能力。T0002 從 14:20 改為 15:05，排序維持原位。
- 旁白為新合成的 zh-TW-HsiaoYuNeural 試音。字幕依實際可聽區間編排，旁白可用 Composition 的 voiceover 屬性替換。背景樂和互動音由影片工程獨立合成。
- 擷取本身是固定畫面，運動以輸出影格計算。全片用絕對影格；俯視與後續選點共用同一地圖實例。相機插值無回彈、無整數位移取整；只有地標和通知含一次局部彈性落位。

## 實際輸出驗收

- 最終 MP4 解碼 510 幀，時間戳連續等距 1/30 秒，無黑幀或空白幀。五段取樣的運動區間皆持續更新，固定構圖停留依分鏡設計。
- 在 MP4 的原生走廊位置量測，橘色描線覆蓋隨時間遞增並停在原生終點。逐段抽查畫面確認地標順序、完整表單、通知背景、編輯視窗及更新時間。
- 原生排程最後一列底部位於捲動區下緣，影片保留原有面板尺寸及捲動裁幅。前五列完整可見，第六列可見任務時間、ID、機器人、狀態與名稱。儲存結果回到同一份六筆清單。
- Studio 已測可播放。擷取工作並行時，headless 瀏覽器的動畫更新有明顯延遲。成片編碼時間戳與運動抽樣未出現相同的缺幀。
