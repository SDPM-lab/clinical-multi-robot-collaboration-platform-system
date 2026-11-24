# MediSync｜Cinematic Live Map Refinement V3.1

`LiveMapPhaseV3-1`（Studio ID，Remotion 的 ID 格式使用連字號） · 18 秒 · 1920 × 1080 · 30 fps · 540 幀

| 幀 | V3 → V3.1 |
|---|---|
| 0–239 | 保留指派交棒、地圖監控、Source → En route → Destination 與連續下降到跟拍。 |
| 240–299 | Third Person。以三段控制列維持觀看位置。288–299 幀，橘色選擇器先移向 First Person。 |
| 300–359 | First Person。300–312 幀使用共享走廊方向的短遮罩交接；348–359 幀先選 Local Follow。 |
| 360–419 | Local Follow。360–372 幀接同一台機器人的高角度局部追蹤。 |
| 420–539 | 沿用 V3 回拉軌跡，接上隔離車隊模型與三條路線。M01、M02、C01 參考路徑依序在 445、457、472 幀啟動。M01 第 485 幀抵達，摘要由 3 active 改為 2 active · 1 arrived。 |

## 車隊資料

| ID | 任務與起訖 | 片尾 |
|---|---|---|
| M01 | T0002 Medication Delivery · Pharmacy → Ward A | Arrived，445–458 幀揭露路線 |
| M02 | T0003 Specimen Delivery · Blood Draw → Laboratory | En route，457–488 幀揭露路線 |
| C01 | T0004 Waste Transport · Ward B → Waste Return | En route，472–513 幀揭露路線 |
| C02 | Nurse Station | Idle |
| W01 | Charging Station A | Charging |
| W02 | Charging Station B | Charging |
| W03 | Charging Station A，區內偏移 0.9 場景單位 | Charging |

能力取自 `hospital_ppo_scheduler.py`。Medical 車隊支援送藥及送檢體，Clean 車隊支援 Waste Transport，所以 C01 接手廢棄物任務。站點限於正式 `PPO_TASK_WAYPOINT_IDS`。三條路線由原生 Live Map 讀取 RMF 有向車道並產生，使用正式機器人色票 M01 灰、M02 藍、C01 橘。白色底線提高可見度，實線表示已走、虛線表示後續參考路段。任務與模型位移在隔離瀏覽器內驅動。

## 相機與 Shotcraft

正式 `getRobotCameraPose` 支援 Third Person（後方跟隨）、First Person（虛擬前向相機）及 Local Follow（以機器人為中心的高位斜視）。沿用 V3 的 1080p 真實畫面、原生偏移與阻尼。選擇列借 `chip-grid-single-select-blackout` 的選中與非選中區隔，改為單一滑動橘色滑塊，不加回彈。借 `shot-transitions` 的短遮罩交棒相機，讓兩個角度共享相同任務時刻。片尾以 `crane-rise-reveal` 做回拉，依 `line-carry-transition` 的描線原理揭露三條有實際落點的路徑。Source → En route → Destination 留在原監控鏡頭。

原速繁體中文旁白與字幕前五句沿用 V3。片尾 420–534 幀更新為「七台機器人，多筆任務同步掌握。」擷取與編碼由影片專用腳本完成。正式前端、ROS 2、PPO 與其他 Phase 維持原樣。
