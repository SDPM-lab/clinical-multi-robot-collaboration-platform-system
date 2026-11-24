# MediSync Scene 03｜PPO Scheduling V2

1920 × 1080 · 30 fps · 450 幀 · 15 秒。

## Shot Timing Sheet 與配方

| 幀 | 動作 | 配方及空間改編 |
|---|---|---|
| 0–89 | T0002 與三組資料逐項顯示，L1 由較低角度抬升成等角空間 | crane-rise-reveal 與 overhead-camera-moves 的升高、露出全圖及落位。相機運動直接改變 3D 投影 |
| 90–179 | 對同一 L1 做短角度調整。七台原模型出現在示範位置，合格 M01、M02 保持原材質，其餘轉為低彩灰 | carousel-3d 只取立體物件辨識；空間座標取正式地圖。充電站三台使用區內錯位，顯示為影片用車隊快照 |
| 180–237 | 三個獨立實體資料平面沿高度分離，接著收束 | space-camera-moves / exploded-view 與 depth-layer-moves，保留真實深度與視差。方格表示輸入維度 |
| 238–299 | 同一資料結構旁展示 Training 與 Inference 兩段 | 資料層同構圖停留，訓練用 State → Action → Reward → Policy update；調度以 Current state → Trained PPO → Assignment |
| 300–389 | 原始 M01 GLB 產品特寫，受控 3/4 相機繞行後停穩 | 取 space-camera-moves 的局部空間運鏡，柔光呈現原始材質 |
| 390–449 | 同方向同尺度以 M01 對位回到 Pharmacy 的實際站點，後拉至院區並停留 | 以 silhouette match cut 客製化 shot-transitions，只有落在三維地圖的機器人錨點 |

本地確有 space-camera-moves、crane-rise-reveal、depth-layer-moves、overhead-camera-moves、shot-transitions、circle-match-iris。地圖模式使用原 GLB 幾何與房間相對位置；影片空間示意含同一層，分層的是資料平面，未虛構樓層與航線。

## Observation 與實際調度

正式 `BATTERY_LAYOUT` 為 **41 + 56 + 1 = 98**。41 維為類型 5、優先級 4、來源 16、目的地 16 的 one-hot。七台機器人各八欄，含能力匹配、可派、忙碌、負載、預估接近時間、前方任務數、電量、電池不可用。最後一欄為全域負載不均衡。接近時間除以 600 秒，負載及前方任務數各以 10 正規化並截界；電量是 0–1。為易讀，影片把逐機器人的 56 維拆成狀態 35 和工作 21，再把全域負載 1 合併至工作圖層。因此畫面為 **41／35／22**；原始向量仍是任務、逐機器人、全域的順序。方格僅對應維度數，沒有把方格表述為神經元或有效數值。

可派性由能力、機器人狀態和電量投影的硬限制先篩選，再把動作遮罩送入 deterministic MaskablePPO。候選動作為七個正式 ID。訓練回饋包含接近時間、隊列及負載不均衡成本；影片只展示訓練流程，沒有用戶每派一筆任務就重新訓練的畫面。實作位置為 `experiments/fleet_sizing/rl/{observation,action_mask,reward,train_battery_v2}.py`，執行整合於 `ros2_ws/src/my_hospital_rmf/scripts/hospital_ppo_scheduler.py`。

沿用 T0002 / Pharmacy → Ward A / High / 15:05。先前的隔離原始編碼器及遮罩驗證得到 M01、M02 兩台可派。工作區沒有部署權重，M01 仍是標示在結果位置的 **Demo assignment**，不在右上角常駐。車隊站位屬影片用空間快照，未連到 ROS 或實際遙測。結尾 T0002 為 Assigned。

## 原始 3D 素材與聲音

- 院區使用產品 Dispatch 的 `frontend/public/models/L1__flat.glb`，選正式 `L1_Solid_Block_Map_v5` 場景。站點取原 `dispatch-route-mapping.json`。保留原始房間幾何並遮掉開發預覽與線層。
- 產品預設使用 `frontend/public/models/AGIBOT_A2D.glb`。使用原始外觀、等比尺寸與 Live Map 既有 60° 機械臂姿勢。Three.js 依全域影格運算相機並預繪實際角度。Remotion 合成已對時的 3D 圖層與字幕；軟體渲染時採鏡內光流補間，切點與候選狀態變更使用實際取樣，落位後沿用定格。
- 繁中旁白為合成試音，濃縮成四句，無後製加速。音效對齊資料揭露、候選匹配、觀測收束、指派與場景交接，避免點擊聲和低頻撞擊。
