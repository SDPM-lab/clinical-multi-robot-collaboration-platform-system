# MediSync Scene 03｜PPO Intelligent Scheduling

PPOSchedulingPrototype · 1920 × 1080 · 30 fps · 360 幀 · 12 秒

| 幀 | 畫面與實作 | Shotcraft 配方 |
|---|---|---|
| 0–74 | T0002 從上一幕以 Pending 交棒。任務、機器人、預估工作量依序展開 | canvas-materialize-moves / diagram-cascade，連線先展開再顯示資料卡 |
| 75–164 | 七台合成車隊按正式 action index 進場。先顯示車隊，接著顯示各資格結果 | 錯峰揭露與局部狀態淡化；保持 M01、M02 並列 |
| 165–284 | 三組資料沿有限曲線收束至 PPO policy，保留遮罩後的候選集合。M01 加註 Illustrative selection | bezier-source-converge-merge，取路徑長度插值，固定線寬 |
| 285–359 | 同一 T0002 指派給 M01，保留品牌字樣與模擬標示。橘線延伸至畫面右側作 Live Map 錨點 | reticle-lock-on 的局部確認概念改為小勾；line-carry-transition 延伸出畫 |

## 真正實作與展示對照

- **Observation**。原始 ObservationEncoder（experiments/fleet_sizing/rl/observation.py）先編碼任務類型、優先級、起點、終點。每台機器人包含能力是否匹配、可指派旗標、忙碌旗標、負載、預估接近時間、前方任務數、電量和電池不可用旗標，另加全域負載不均衡。機器人位置影響預估接近時間，並非獨立的原始座標輸入。
- **硬限制**。action_mask.py 與 baseline/common.py 檢查匹配能力和可指派狀態，再以電量投影檢查新任務可否留在隊列。充電不可派，忙碌不等於不可派。
- **排程與推論**。原始 hospital_ppo_scheduler.py 將 98 維 observation 和 7 維 mask 交給 deterministic MaskablePPO，再驗證回傳動作。任務 ID、排程日期及 RMF 路由資訊用於外層流程，並非原始觀測特徵；未來實際服務時長不提供給推論。
- **訓練**。train_battery_v2.py 使用 MaskablePPO。reward.py 的指派回饋含優先級權重、接近時間、隊列與負載不均衡成本。影片未呈現訓練效能、信心或分數。
- **Demo**。沿用 Scene 02 的 T0002 / film-task-t0002、Medication Delivery、Pharmacy → Ward A、High、15:05，先從未指派 Pending 進入假設已到排程時間的隔離測試。下一幕保留同一 ID 與 M01，影片結尾只到 Assigned。
- **離線證據**。執行 `scripts/verify-ppo-scheduling-demo.py`，直接調用原始 ObservationEncoder 和 ActionMaskBuilder（啟用電量）。路徑採真實 NavGraph；本地缺少測量用 routes CSV，採 0.5 m/s 的合成估計供投影驗證。車隊電量及充電狀態為示意。得到遮罩 [false, false, true, true, false, false, false]。C01/C02 不支援藥物配送；W01/W02/W03 支援，但本情境正在充電。M01 和 M02 皆合格。部署權重缺少，因此 M01 是影片指定的合格結果，畫面標示 Illustrative Scheduling Scenario。
- **聲音**。四句精簡繁中 TTS 與同文字幕，先能力、後狀態、策略與指派，保留原生成語速。28/37/46 資料、122/147 篩選、185/204/231/255 流向、299 確認、321 路線。背景音以合成立體聲輕墊保留旁白空間。

未修改 Dashboard、Task Creation、網站、後端或 ROS 運行環境。
