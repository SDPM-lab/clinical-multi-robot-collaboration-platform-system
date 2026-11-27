# MediSync｜PPO Scheduling V4

PPOSchedulingPrototypeV4 · 1920 × 1080 · 30 fps · 450 幀 · 15 秒

| 鏡頭 | 幀 | 主要動效 | 次要動效與轉場 | 聲音 |
|---|---:|---|---|---|
| PPO | 0–59 | lead-word-zoom-assemble 的聚焦與落位，改為三個字母分深度組合 | 全名以遮罩展開，七點沿下一鏡節點位置展開 | 22、31 幀文字拍點 |
| Capability matching | 60–149 | chip-grid-single-select-blackout 的原地篩選，保留兩個合格項 | 借 quad-split-parallel-scenes 的並行節奏；中央任務、節點半徑與接觸陰影表現深度 | 105、122 幀篩選音 |
| 98D state | 150–239 | chart-live-moves 的 unit-dot-swarm-regroup，98 個元素由三組重排為有透視的向量 | 98D 主字停穩，資料收束到下一鏡策略核心中心 | 168、197、215 幀組合音 |
| PPO learning | 240–359 | 透視軌道的一次訓練循環，前後弧和核心分層 | circle-match-iris 以政策核心為原點，由離線訓練切到推論 | 251、272、292、319 幀脈衝；350 幀切換 |
| Assignment | 360–449 | 同半徑、同位置、同色圓形做 Match Cut，從訓練好的策略切到 M01 | 兩個候選初始可見，M02 降權，T0002 和結果停穩 | 394、400 幀確認和弦 |

## 技術核對

- 正式 PPO 路徑使用 98 維 float32 observation。任務 41 維，分別為任務類型 5、優先級 4、起點 16、終點 16，採獨熱編碼。車隊 56 維，每台八項依序為能力匹配、可派遣、忙碌、負載、預估接近時間、前方任務數、電量與電池不可用旗標。全域 1 維為負載不均衡。負載、前方任務數和預估接近時間各以 10、10、600 秒為尺度做有界正規化；電量為 state of charge 比率。畫面用 98 個資料點表達 observation，策略核心是抽象圖形。
- 候選人來自七個離散 action。action mask 檢查能力、可派狀態和電量投影。唯讀執行正式 encoder 與 action mask，T0002 得到 98 維及 `[false,false,true,true,false,false,false]`。C01、C02 能力不符，W01–W03 充電，M01、M02 合格。情境使用現有 NavGraph，路徑時間使用示意速度估算。
- 訓練端使用 MaskablePPO 收集環境 rollout，依回報估計 advantage，再以 clipped objective 更新策略。專案設定 GAE lambda 0.95、clip range 0.2。環境回饋包含預估接近時間、前方任務數、指派後負載不均衡的成本，以及實際等待成本。圖形循環壓縮了這個過程，策略核心從資料收集階段到更新階段才變化。
- 推論端載入既有 checkpoint，用目前 observation 與 action mask 呼叫 deterministic predict，再驗證選到的 index 並對應邏輯及 RMF ID。M01 是影片指定的合格示範結果。本機沒有正式 checkpoint，這支影片未執行正式模型推論或派工。
- 來源在 `experiments/fleet_sizing/rl/` 的 `observation.py`、`action_mask.py`、`reward.py`、`train_battery_v2.py`，以及 `ros2_ws/src/my_hospital_rmf/scripts/hospital_ppo_scheduler.py`。

## 配音與運動

旁白用台灣華語合成聲線，以原生速度生成。依各段測得的語音長度生成中文字幕。配樂與短提示音為原創合成，與視覺事件逐幀對齊。所有畫面位置由同一全域幀數及限幅插值決定，沒有相機 shake 或 spring。
