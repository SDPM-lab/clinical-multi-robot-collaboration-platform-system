# MediSync PPO Matrix, Masking & Policy Explanation

`PPOSchedulingPrototypeV9` · 1920 × 1080 · 30 fps · 720 幀 · 24 秒

| 時間 | 幀 | Shotcraft 配方與畫面 |
|---|---|---|
| 0–2 秒 | 0–59 | `lead-word-zoom-assemble` 的標題聚焦，沿用 PPO 全名與中文。 |
| 2–6 秒 | 60–179 | `canvas-materialize-moves` 的錯峰建立，七列和八欄依序對齊；局部導視先指向 Capability／Assignable。 |
| 6–10 秒 | 180–299 | `chip-grid-single-select-blackout` 的合格焦點改用獨立的 0／1 欄位，不修改特徵列。 |
| 10–13 秒 | 300–389 | `mosaic-reframe` 與 `unit-dot-swarm-regroup` 的分群重排，保留 98 維矩陣與七位遮罩為平行資料。特徵矩陣收束到下一鏡 PPO 輸入口。 |
| 13–18 秒 | 390–539 | `diagram-cascade` 逐層描線，借 `scanline-annotate-focus` 的導視概念依序強調 Actor 和 Critic。七個 logits 動作用 ID 呈現，畫叉者受遮罩；未編造分數或機率。 |
| 18–22 秒 | 540–659 | 用 `canvas-materialize-moves` 的逐段落位，在共用網路底部展開環境、獎勵、經驗、估計優勢、裁剪更新。 |
| 22–24 秒 | 660–719 | 共用元素銜接，Actor 的 M01 圖示成為任務指派主體。原網路留作低對比背景。 |

## 技術查證

- ObservationEncoder / Battery Layout 輸出 float32 98 維。41 維任務特徵由類型 5、優先級 4、來源 16、目的地 16 構成；56 維車隊特徵為七台各八欄，依序是能力符合、可派遣、忙碌、負載、預估接近時間、前方任務數、電量、電池不可用旗標；1 維為全域負載不均。影片矩陣使用同一個正式 encoder 對隔離 T0002 Demo 的實算結果。Load、Approach、Tasks ahead 為正規化值；未直接呈現 Location 或 Current Task 為模型欄位。
- Capability 屬於 Observation 的每台機器人特徵，也是 ActionMaskBuilder 可行性檢查的一部分。Action Mask 另加可派狀態及電量投影條件。這條正式路徑未見把不合格機器人整列清除的 Observation Mask；Observation 內可另有按條件取得或缺省為零的欄位。
- `hospital_ppo_scheduler.py` 先 encode 狀態，再 build 獨立遮罩，檢查 98 與 7 的形狀後傳入 `predict(observation, action_masks=mask, deterministic=True)`，回傳 index 再驗 mask。T0002 Demo 為 `[0,0,1,1,0,0,0]`。MaskableCategorical 把不可用 logits 替換為 dtype 相容的極小負值（常數 -1e8）；合法 logits 保留，分布依遮罩重新正規化。
- `train_battery_v2.py` 使用 `MaskablePPO("MlpPolicy")` 且未指定自訂拓樸。環境安裝的 sb3-contrib 2.9.0 預設共享 FlattenExtractor，政策與價值 MLP 各有兩層 64，Actor 輸出七個動作 logits，Critic 輸出一個純量價值。預設架構依本地套件與訓練設定核對，未讀受部署 checkpoint 約束的確切拓樸。畫面使用概念節點，不暗示隱藏層數或共享 MLP 權重。
- PPO clipping 作用於策略損失中的新舊動作機率比，訓練設定 clip_range = 0.2。程式取原始與裁剪後優勢目標的較小值，和七位動作選擇遮罩用途不同。片尾 M01 為合格的示範指派，未作正式模型的推論成果宣告。
