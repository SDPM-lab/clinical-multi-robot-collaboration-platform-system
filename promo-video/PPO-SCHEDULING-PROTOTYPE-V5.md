# MediSync｜PPO Explanation Rebuild

Remotion Composition `PPOSchedulingPrototypeV5`，18 秒，1920 × 1080，30 fps，540 幀。

| 時間 | 幀 | 動效 | 視覺意義 |
|---|---|---|---|
| 0–2.5 秒 | 0–74 | `lead-word-zoom-assemble` 的首字聚焦，加上錯峰字母組裝與雙語遮罩 | 先讀 PPO，再讀全名與「近端策略優化」。 |
| 2.5–5 秒 | 75–149 | `chip-grid-single-select-blackout` 改編為整面候選篩選 | 將能力不符及充電中的列降權，保留 M01、M02。 |
| 5–8 秒 | 150–239 | `chart-live-moves` 的 `unit-dot-swarm-regroup` 改編為編碼條匯流 | 把任務、車隊、全域特徵編排成一條 98 維輸入向量。 |
| 8–13 秒 | 240–389 | `canvas-materialize-moves` 的 `diagram-cascade`，搭配局部連線描繪 | 狀態進網路，分出 Actor 和 Critic。環境獎勵沿底部回到更新節點，網路連線權重隨後改變。 |
| 13–18 秒 | 390–539 | `circle-match-iris` 的局部開窗，接策略核心到指派結果 | 切換到推論。已訓練策略接收當前狀態，結果停穩至少 1 秒。 |

## 正式程式對照

- `experiments/fleet_sizing/rl/observation.py` 的 Battery Layout 產生 98 維。任務 41 維是任務類型、優先級、起點、終點。車隊 56 維是 7 台各 8 個特徵，包含能力、可指派、忙碌、負載、預估接近時間、前方任務數、電量、電池不可用旗標。系統 1 維是全域負載不均衡。
- `experiments/fleet_sizing/rl/action_mask.py` 用能力、可指派條件及電量投影限制 7 個離散動作。T0002 為 Medication delivery、Pharmacy → Ward A、High。隔離情境只有 M01、M02 合格，C01、C02 能力不符，W01–W03 充電中。M01 為電影示意指派。
- `experiments/fleet_sizing/rl/reward.py` 的環境回饋反映接近時間、前方任務、負載不均衡及等待等成本。Critic 估計狀態價值，獎勵由環境提供。圖中的網路與線寬為概念圖，未將實際模型的層數或參數曝露。
- `experiments/fleet_sizing/rl/train_battery_v2.py` 使用 MaskablePPO，以收集到的經驗、優勢估計與裁剪目標更新策略。學習鏡頭先顯示環境回饋，再進入策略更新。
- `ros2_ws/src/my_hospital_rmf/scripts/hospital_ppo_scheduler.py` 在派工時將 98 維目前狀態及 7 維遮罩交給已載入的模型進行 deterministic predict，再驗證動作。畫面以獨立的 INFERENCE 階段表示此流程。

字幕時間軸位於 `src/ppo-v5-captions.json`，獨立繁中旁白位於 `public/ppo-v5/voice.wav`。合成音樂和提示音存於獨立聲軌。
