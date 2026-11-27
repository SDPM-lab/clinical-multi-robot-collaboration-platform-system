# MediSync｜Cinematic PPO Product Explainer V6

`PPOSchedulingPrototypeV6` · 20 秒 · 1920 × 1080 · 30 fps · 600 幀

| 鏡頭 | 時間與幀 | Shotcraft 配方與用途 |
|---|---|---|
| 01 | 00–03 秒，0–89 | `lead-word-zoom-assemble` 的聚焦與基線落位。英中名稱垂直展開，字形 O 的開口接車隊。 |
| 02 | 03–06 秒，90–179 | `chip-grid-single-select-blackout` 用留亮與降對比表現資格遮罩，保留兩台；借 `mosaic-reframe` 的局部重排，合格節點向前提。 |
| 03 | 06–09 秒，180–269 | `unit-dot-swarm-regroup` 的原地組合與重排。從任務標籤、車隊狀態、工作量圖形變為同色編碼向量。 |
| 04A | 09–10.4 秒，270–311 | `canvas-materialize-moves` 的 diagram-cascade 概念轉為近景輸入節點的依序啟動。 |
| 04B | 10.4–12.07 秒，312–361 | Actor 與 Critic 共用固定節點做 Match Cut。Actor 揭露動作分支，Critic 將同一位置換成單一價值概念。 |
| 04C | 12.07–14 秒，362–419 | Action、Environment、Reward 逐點接力，再重組為抽象的策略更新示意。線條變化只表示訓練更新的概念。 |
| 05 | 14–17 秒，420–509 | `circle-match-iris` 把離線訓練的圖形收束到策略核心，再以開窗揭露 Inference；現時狀態通過已訓練策略。 |
| 06 | 17–20 秒，510–599 | 共用 Assignment 機器人圖示做 Match Cut，將任務與 Robot M01 對接，示範指派停穩。 |

V5 在同一個深色鏡頭集中顯示全部網路和回饋，V6 用全片一致的淺底、固定 Logo，將網路輸入、Actor、Critic、回饋和更新分時展示。車隊與指派沿用同一個機器人符號。畫面使用中英關鍵提示，保留原生合成速度的繁中旁白與同文字幕。

## 實作對照

- 正式 `ObservationEncoder` 的 Battery Layout 實測為 98 維。任務 41 維是任務類型、優先級、來源、目的地。車隊 56 維是七台各八項，包含能力、可派狀態、忙碌、負載、接近時間、前方任務數、電量與電池不可用旗標。全域 1 維為負載不均。
- `ActionMaskBuilder` 的能力、可用與電量條件令 T0002 只剩 M01、M02 合格。七個離散動作的 mask 為 `[false,false,true,true,false,false,false]`。片尾 M01 為示範結果。
- `train_battery_v2.py` 實際呼叫 `MaskablePPO`，設定 GAE 與裁剪目標。Actor 選擇動作，Critic 估計目前狀態價值，環境回饋來自接近時間、排隊、負載與等待等成本；策略從收集的訓練經驗更新。分支動畫用於解釋角色；正式程式未明確設定自訂網路拓樸，畫面使用抽象層數與連線。
- `hospital_ppo_scheduler.py` 使用 checkpoint 的確定性推論，輸入 98 維狀態和 7 維動作遮罩。畫面在離線訓練後獨立展示此流程。

旁白 WAV、音樂與短提示音、逐句字幕均獨立保存在影片工程。
