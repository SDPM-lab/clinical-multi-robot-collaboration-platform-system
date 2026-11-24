# MediSync｜Unified PPO Explanation V8

`PPOSchedulingPrototypeV8` · 1920 × 1080 · 30 fps · 600 幀 · 20 秒

| 時間 | 幀 | V7 → V8 與套用的動效 |
|---|---|---|
| 0–2 秒 | 0–59 | 壓縮 PPO 開場，保留雙語名稱與資料形狀在車隊鏡頭中的共用位置。沿用文字遮罩與 `mosaic-reframe` 的形狀、位置插值。 |
| 2–5 秒 | 60–149 | 保留大型任務與七台候選陣列，把兩個合格動作交給之後的 Actor。 |
| 5–8 秒 | 150–239 | 保留 V7 由三組資料形成矩陣的語意。矩陣縮至與下一幕相同的輸入口，採 `mosaic-reframe` 重排。 |
| 8–14 秒 | 240–419 | V7 的 Network、Actor、Critic 三張畫面整合。借 `depth-layer-moves` 固定背景與前景相對焦點，網路逐層啟動；借 `scanline-annotate-focus` 先導視線再揭露標註的概念，用局部線條和色塊聚焦，不疊全幅掃描線。 |
| 14–17 秒 | 420–509 | 沿同一網路揭露環境、獎勵、訓練經驗與優勢估計。以 `canvas-materialize-moves` 的順序落地和 `bezier-source-converge-merge` 的曲線收束概念，把更新路徑送回策略網路一側。 |
| 17–20 秒 | 510–599 | 回饋路徑退出，原網路標題換成 Trained PPO Policy，當前狀態流向 Actor。M01 從原候選位置擴展為指派主角，採 `shot-transitions` 的共用錨點方式維持位置連續。 |

08–20 秒只掛載一次 Unified 圖層。Actor、Critic、訓練回饋與 Inference 均以同一全域幀數驅動，切換不重播網路進場。標題、圖形及字幕各有獨立垂直區域。

## 技術核對

沿用原始 `observation.py` 的 Battery Layout 41 + 56 + 1，共 98 維。遮罩依能力、可派狀態及電量投影驗證七個離散動作，T0002 的合格候選為 M01、M02。M01 是 Demo 指派。Actor 分支表示策略輸出，Critic 估計預期未來回報；環境給出 Reward，訓練收集經驗並估計優勢，再限制策略更新幅度。網路連線與節點為概念圖，未指定正式模型的特徵共享方式、拓樸或權重。推論沿用已訓練策略與動作遮罩。

旁白以原生繁中語速合成，Actor 與 Critic 使用不同字幕時段。畫面結尾保留示範指派揭露。
