# MediSync Scene 02 V6｜Creative Layout Redesign

TaskCreationPrototypeV6 · 1920 × 1080 · 30 fps · 585 幀 · 19.5 秒

## Shot Motion Matrix

| 幀 | 構圖與動作 | Shotcraft 配方與客製 |
|---|---|---|
| 0–89 | Create. Simply. 搭配正面原生完整表單 | 沿用 V5 的詞節拍遮罩。游標使用不帶投影、取樣殘影或路徑線的單一 SVG |
| 90–209 | 欄位遮罩揭露獨立地圖。原生位置局部短亮，選定後固定座標揭示標記，單一橘色路徑完成後停穩 | 沿用 V5 的 circle-match-iris 入口；退出時以兩個地標色匹配表單欄位。取消飛行標籤，地圖與表單各自只在所屬鏡頭顯示名稱 |
| 210–299 | 正面完整表單，選 High 和送出共用構圖 | 沿用 segmented-thumb-hero 的控制項局部切換。游標轉向按鈕仍由一個絕對影格插值控制 |
| 300–389 | 表單後景，前景橘色 Bell 搖一次後展開綠色成功通知 | 單次 icon performance，使用獨立向量 Bell、完成指示圖示及可遮罩的訊息正文。T0002 與 Medication delivery 在同一行；不分離 ID。308、318 幀雙音提示 |
| 390–422 | 中央 Flexible scheduling. 收成左上小標，交接寬幅卡片 | **title-demote-to-label**。字級與座標同一曲線連續移動 |
| 411–443 | 四筆寬幅任務逐列進場 | **canvas-materialize-moves / panel-to-canvas**，抽出原生任務欄位和優先級配色。**row-embed** 以錯峰逐列定位，保留四筆完整卡片 |
| 450–540 | T0002 成為主卡，展開 Start time，鄰列讓出空間。依原生流程進入 Re-add 和確認框 | **mosaic-reframe**。各列以自身座標與高度調整。autolayout-gap-dial 的參數式讓位概念用於編輯展開，無彈簧 |
| 541–584 | 儲存成功，14:45 的 T0171 先於 15:05 的 T0002 | 同一組任務 ID 維持掛載，依實際開始時間重新計算列位置；交換期間獨立調整兩列寬度，落定後回到寬幅列表 |

研究 timeline-travel、text-as-mask、transition-travel 後，保留穩定背景與資料卡局部運動。

## 三張構圖

A 列表展開，B T0002 聚焦及時間編輯，C 儲存與重排序。原生側欄只用作設計參照。寬幅任務區約為畫面 69%，六筆隔離資料中顯示排序前四筆。

T0002 採 Medication delivery、Pharmacy 固定起點、點選 Ward A、High，與既有隔離任務一致。V6 將另一筆相鄰 Demo 任務 T0171 設為 14:45，以實際測到排序改變。擷取腳本攔截真實前端請求，比對 POST 建立、PATCH 修改以及儲存前後的原生 DOM 順序。確認對話框使用 V6 原生擷取。排程卡由影片工程依原始任務 ID、類型、時間、狀態、機器人、優先級重排，正式 UI 原件未修改。

## 聲音

沿用繁中旁白與已對時字幕。新版點擊主要使用 33 ms Clean Digital Tick 和 49 ms Crisp Mouse Click，時間欄採 55 ms Soft High-frequency Tap。聲音只放在操作事件，固定起點使用提示聲。保留雙音通知以及儲存確認。

## 實際驗收

- 隔離前端在修改前顯示 T0173、T0002、T0171、T0174、T0172、T0175；確認後顯示 T0173、T0171、T0002、T0174、T0172、T0175。原生 PATCH 前後為同一個任務內部 ID。
- 正式 MP4 解碼 585 幀，時間戳連續，無黑幀或空白幀。九段抽樣的運動區間持續更新。High 到 Create Task 的游標通過區域抽驗，未出現第二個深色游標輪廓；路線的走廊樣本單調增加。
- 成片中只使用一個 Create. Simply. 的開場；結尾在更新後清單停住。Studio 實測預設 Loop 開啟，切為關閉後可播放到片尾並停止。
