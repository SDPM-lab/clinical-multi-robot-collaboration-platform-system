# Baseline Scheduling Algorithms and Battery-aware Calibration

醫療異質多機器人智慧任務調度系統 —
基準派工演算法設計、參數校準與效能評估

---

## 1. 實驗目的

本研究設計四種非學習式派工演算法，
作為 Maskable PPO 智慧派工策略的比較基準。

| Method | Strategy |
|---|---|
| Random Feasible | 可行候選隨機分配 |
| Projected Nearest | 預估移動時間最短 |
| Static Weighted | 固定多目標權重 |
| Dynamic Weighted | 動態多目標權重 |

為避免使用未充分校準的比較基準，
本研究針對兩種具有權重參數的演算法
進行完整網格搜尋與多目標參數選擇。

Random Feasible 與 Projected Nearest
不具有需要搜尋的權重參數，
因此直接進行相同情境下的電量感知效能評估。

本階段不使用 PPO 評估結果選擇 Baseline 參數，
也不重新訓練既有 PPO 模型。

---

## 2. 共用派工規則

### 2.1 異質機器人

固定車隊配置為：

$$
(Clean, Medical, Ward)=(2,2,3)
$$

共七台機器人。

機器人必須具有任務所需能力，
並符合機器人狀態及電量可行性限制，
才能成為候選機器人。

### 2.2 任務優先級

| Priority | Level |
|---|---|
| 0 | Low |
| 1 | Normal |
| 2 | High |
| 3 | Emergency |

Emergency 任務在等待佇列中具有獨立的優先地位。

非 Emergency 任務使用 Aging 機制：

$$
P_{\mathrm{effective}}
=P_{\mathrm{base}}+\frac{T_{\mathrm{wait}}}{120}
$$

Aging interval 為 120 秒。

排序時考量有效優先級、任務到達時間及任務 ID。

已開始執行的任務不因等待佇列重新排序而中斷。

### 2.3 電量限制

所有 V2 實驗均啟用 Battery Model。

派工流程考量預估移動能耗、
剩餘電量及最低保留電量。

電量修復機制可能釋放未來佇列中
電量不可行的任務，使其重新進入待派工流程。

返回充電站中的機器人是否可接受新任務，
依共用模擬器設定及電量可行性決定。

### 2.4 Duration-free scheduling

派工策略不使用未來真實服務時間或完成時間。

預估移動時間根據候選機器人的可觀測狀態、
未來任務佇列及導航資料取得。

---

## 3. Baseline 演算法設計

### 3.1 Random Feasible

從符合能力、狀態及電量限制的候選機器人中，
以均勻隨機方式選擇一台。

若共有 m 台可行機器人，
每台機器人被選中的機率為：

$$
P(a=i)=\frac{1}{m}
$$

候選機器人依 ID 排序，
並使用具有固定 Seed 的隨機數產生器。

此方法不使用移動時間或負載作為加權評分依據，
但電量可行性檢查仍可能使用預估移動成本。

特性：

- 演算法簡單。
- 不需要權重參數。
- 可作為最低限度決策資訊的比較基準。
- 不直接最佳化等待時間或移動效率。

程式：
[Random Feasible](../../baseline/random_feasible.py)

### 3.2 Projected Nearest

選擇預估前往任務來源地移動時間最短的機器人。

與直接比較目前位置不同，
此方法考量任務插入未來佇列後的預估出發位置。

$$
a^*=\arg\min_i A_i
$$

其中 A_i 為候選機器人的預估來源地移動時間。

同分時依序比較：

1. Tasks ahead count
2. Projected queue length
3. Robot ID

此方法不是直接比較機器人目前距離，
也不等同於預估任務完成時間最短。

特性：

- 不需要權重參數。
- 主要考量移動效率。
- 任務可能集中在特定機器人，
  因而影響等待時間及公平性。

程式：
[Projected Nearest](../../baseline/projected_nearest.py)

### 3.3 Static Weighted

同時考量預估移動時間與可觀測任務負載。

$$
C_i=\alpha\hat{A}_i+(1-\alpha)\hat{L}_i
$$

其中：

- C_i：候選機器人的加權成本。
- A_i：預估來源地移動時間。
- L_i：目前執行中及等待佇列的任務數量。
- alpha：固定移動時間權重。

使用可行候選中的最大值進行正規化：

$$
\hat{A}_i=\frac{A_i}{\max_j A_j}
$$

$$
\hat{L}_i=\frac{L_i}{\max_j L_j}
$$

若分母為零，正規化結果設定為零。

選擇加權成本最低的候選機器人。

若成本相同，依序比較預估移動時間、
任務負載及 Robot ID。

原始參數：

$$
\alpha=0.5
$$

V2 最終參數：

$$
\alpha=0.6
$$

即移動時間權重為 60%，任務負載權重為 40%。

程式：
[Static Weighted](../../baseline/static_weighted.py)

### 3.4 Dynamic Weighted

沿用 Static Weighted 的評分公式，
但依目前候選機器人的負載不平衡程度調整權重。

$$
I_t=\max_i(\hat{L}_i)-\min_i(\hat{L}_i)
$$

$$
\alpha_t=\alpha_{\max}
-(\alpha_{\max}-\alpha_{\min})I_t
$$

$$
C_i=\alpha_t\hat{A}_i+(1-\alpha_t)\hat{L}_i
$$

當負載較平衡時，提高移動時間的重要性。

當負載不平衡程度增加時，
提高任務負載的重要性。

若所有候選負載相同：

$$
I_t=0,\quad\alpha_t=\alpha_{\max}
$$

若同時存在零負載及非零負載候選：

$$
I_t=1,\quad\alpha_t=\alpha_{\min}
$$

原始權重範圍：

$$
[\alpha_{\min},\alpha_{\max}]=[0.4,0.8]
$$

V2 最終權重範圍：

$$
[\alpha_{\min},\alpha_{\max}]=[0.4,0.9]
$$

Dynamic Weighted 為規則式自適應策略，
不包含模型訓練。

程式：
[Dynamic Weighted](../../baseline/dynamic_weighted.py)

### 3.5 演算法特性比較

| Method | Approach scoring | Load scoring | Adaptive weight | Learning |
|---|---|---|---|---|
| Random Feasible | No | No | No | No |
| Projected Nearest | Yes | Tie-break only | No | No |
| Static Weighted | Yes | Yes | No | No |
| Dynamic Weighted | Yes | Yes | Yes | No |
| Maskable PPO | State information | State information | Learned policy | Yes |

共用派工工具：
[Common utilities](../../baseline/common.py)

---

## 4. 原始參數校準 V1

### 4.1 Static Weighted V1

原始實驗使用五組固定權重，
每組執行十次模擬。

Seeds: 1001–1010

| Alpha | Avg Wait (s) | P95 Wait (s) | Total Travel (s) | Jain Utilization |
|---|---:|---:|---:|---:|
| 0.5 | 19.39 | 175.61 | 361083.06 | 0.8036 |
| 0.6 | 19.48 | 176.14 | 361105.85 | 0.8031 |
| 0.7 | 21.54 | 187.31 | 360520.70 | 0.8019 |
| 0.8 | 25.91 | 222.68 | 359829.96 | 0.7962 |
| 0.9 | 93.00 | 524.38 | 359191.77 | 0.6583 |

原始選定 alpha = 0.5，
其平均等待時間、P95 等待時間及利用率公平性
在當時的候選集合中表現最佳。

資料：

- [Runs](data/calibration_v1/static_weight_sensitivity_runs.csv)
- [Summary](data/calibration_v1/static_weight_sensitivity_summary.csv)

### 4.2 Dynamic Weighted V1

原始實驗使用五組動態權重範圍，
每組執行十次模擬。

Seeds: 2001–2010

| Range | Avg Wait (s) | P95 Wait (s) | Total Travel (s) | Jain Utilization |
|---|---:|---:|---:|---:|
| [0.5,0.7] | 20.64 | 177.12 | 361302.05 | 0.7921 |
| [0.4,0.8] | 18.88 | 163.58 | 362532.47 | 0.7915 |
| [0.6,0.8] | 21.24 | 179.37 | 361257.22 | 0.7920 |
| [0.5,0.9] | 21.22 | 179.23 | 361271.37 | 0.7912 |
| [0.7,0.9] | 22.39 | 189.14 | 360857.21 | 0.7942 |

原始選定 [0.4,0.8]，
其平均等待時間及 P95 等待時間最低。

資料：

- [Runs](data/calibration_v1/dynamic_weight_sensitivity_runs.csv)
- [Summary](data/calibration_v1/dynamic_weight_sensitivity_summary.csv)

### 4.3 Dynamic Priority Analysis V1

另外分析 Emergency 與 High+ 任務的等待時間。

High+ 包含 Priority 2 與 Priority 3。

| Range | Emergency Avg | Emergency P95 | High+ Avg | High+ P95 |
|---|---:|---:|---:|---:|
| [0.5,0.7] | 14.41 | 116.79 | 13.96 | 117.01 |
| [0.4,0.8] | 11.87 | 89.72 | 12.01 | 93.10 |
| [0.6,0.8] | 14.20 | 117.01 | 14.06 | 120.10 |
| [0.5,0.9] | 14.13 | 116.13 | 14.21 | 120.77 |
| [0.7,0.9] | 14.96 | 123.47 | 15.00 | 128.27 |

時間單位為秒。

[0.4,0.8] 在上述四項等待時間指標均具有最低平均值。

此分析與原始 Dynamic 敏感度分析使用相同情境 Seeds，
不應視為獨立驗證。

資料：

- [Runs](data/calibration_v1/dynamic_weight_priority_runs.csv)
- [Summary](data/calibration_v1/dynamic_weight_priority_summary.csv)

---

## 5. Battery-aware Experiment V2

### 5.1 補充實驗原因

V1 原始校準存在下列限制：

1. 原始校準未啟用電量模型。
2. Static 搜尋範圍未完整涵蓋 0 至 1。
3. Dynamic 只測試人工選擇的五組權重範圍。
4. 原始校準使用 Utilization Fairness，
   與 PPO 比較所採用的 Task Fairness 不完全一致。
5. 尚未建立一致的多目標參數選擇流程。

因此 V2 啟用電量模型，
擴大權重搜尋範圍，
並統一四種 Baseline 的評估指標。

V1 結果保留作為歷史紀錄，
不直接將跨版本數值變化歸因於單一因素。

### 5.2 實驗環境

| Setting | Value |
|---|---|
| Fleet configuration | (2,2,3) |
| Total robots | 7 |
| Workload multiplier | 4.0 |
| Task generation horizon | 7 days |
| Scenario seeds | 3001–3010 |
| Replications | 10 |
| Battery model | Enabled |
| Initial SoC | 100% |
| Charge trigger SoC | 25% |
| Minimum reserve SoC | 15% |
| Resume SoC | 80% |
| Full charge time | 7200 s |
| Full battery travel runtime | 5400 s |
| Navigation | Nav2 route measurements and graph fallback |

每次模擬平均生成 1636.6 筆任務，
約每日 233.8 筆。

所有方法使用相同情境 Seeds。

校準 Seeds 已針對當時現存的 78 份歷史 CSV
進行重疊檢查，未發現重疊紀錄。

### 5.3 實驗規模

| Method | Candidates | Replications | Total runs |
|---|---:|---:|---:|
| Random Feasible | 1 fixed strategy | 10 | 10 |
| Projected Nearest | 1 fixed strategy | 10 | 10 |
| Static Weighted | 11 | 10 | 110 |
| Dynamic Weighted | 55 | 10 | 550 |
| Total | | | 680 |

不包含 Smoke Test、診斷模擬及歷史 V1 實驗。

---

## 6. Evaluation Metrics

### 6.1 主要評估指標

| Metric | Definition | Direction |
|---|---|---|
| Average Waiting Time | 任務到達至開始執行的平均時間 | Lower |
| P95 Waiting Time | 任務等待時間第 95 百分位數 | Lower |
| High Waiting Time | Priority 2 任務平均等待時間 | Lower |
| Emergency Waiting Time | Priority 3 任務平均等待時間 | Lower |
| Total Travel Time | 來源地移動與任務路線移動時間總和 | Lower |
| Jain Task Fairness | 機器人完成任務數量的公平性 | Higher |
| Completion Rate | 完成任務數除以生成任務數 | Higher |

等待時間以具有開始執行紀錄的任務計算。

每次模擬分別計算 P95，
再對十次模擬的 P95 取平均，
並非合併所有任務後計算單一 P95。

Total Travel Time 不涵蓋所有充電往返移動成本，
因此不等同於總能耗。

### 6.2 Jain Fairness

$$
J(x)=\frac{(\sum_{i=1}^{n}x_i)^2}
{n\sum_{i=1}^{n}x_i^2}
$$

本研究同時保存兩種公平性指標：

- Task Fairness：使用各機器人的完成任務數量。
- Utilization Fairness：使用各機器人的利用率。

機器人利用率以 busy time 除以 makespan 計算。

僅 Task Fairness 參與參數選擇的 Rank Sum。

異質車隊中的任務種類與需求不同，
較高的公平性不必然代表最佳資源配置。

### 6.3 輔助評估指標

包括：

- Average / P95 Source Response Time
- Average / P95 Total Task Time
- High-only P95 Waiting Time
- Emergency P95 Waiting Time
- High+ Average / P95 Waiting Time
- High+ Source Response Time
- Average / Maximum Robot Utilization
- Jain Utilization Fairness
- Charging Count
- Return-to-charge Count
- Minimum Robot SoC
- Average Final SoC

Source Response Time 為任務到達至機器人抵達來源地的時間，
與 Waiting Time 不同。

四種方法整合後共有 46 項共用數值指標。

共用評估程式：
[Unified evaluation](../../battery_calibration/evaluation.py)

---

## 7. Parameter Selection

Static 與 Dynamic 分別獨立進行參數選擇。

### 7.1 Completion screening

候選參數必須同時符合：

$$
MeanCompletionRate\geq0.99
$$

$$
MinimumCompletionRate\geq0.99
$$

### 7.2 Pareto Front

使用六項主要效能指標的平均值判斷支配關係。

若候選 A 在所有指標中均不劣於 B，
且至少一項優於 B，則 A 支配 B。

所有未被其他可行候選支配的參數
構成 Pareto Front。

### 7.3 Rank Sum

對全部可行候選的六項主要效能指標分別排名。

完全相同的數值使用平均名次。

$$
R(\theta)=\sum_{k=1}^{6}r_k(\theta)
$$

從 Pareto 候選中選擇 Rank Sum 最低者。

若 Rank Sum 相同，依序比較：

1. Emergency Waiting Time
2. High Waiting Time
3. P95 Waiting Time
4. Average Waiting Time
5. Total Travel Time
6. Jain Task Fairness
7. Numeric parameter order

Completion Rate 作為篩選門檻，
不再重複納入六項排名加總。

選擇規則於正式校準前制定。

程式：
[Parameter selection](../../battery_calibration/selection.py)

---

## 8. Static Weighted Calibration V2

### 8.1 Grid search

$$
\alpha\in\{0.0,0.1,0.2,\ldots,1.0\}
$$

- Candidate count: 11
- Replications per candidate: 10
- Total simulations: 110

### 8.2 完整實驗結果

所有候選參數的完成率均為 100%。

| Alpha | Avg Wait | P95 Wait | High Wait | Emergency | Travel | Jain Task | Rank Sum |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 130.94 | 641.75 | 80.45 | 43.41 | 241918.11 | 0.7493 | 38 |
| 0.1 | 130.94 | 641.75 | 80.45 | 43.41 | 241918.11 | 0.7493 | 38 |
| 0.2 | 130.94 | 641.75 | 80.45 | 43.41 | 241918.11 | 0.7493 | 38 |
| 0.3 | 130.94 | 641.75 | 80.45 | 43.41 | 241918.11 | 0.7493 | 38 |
| 0.4 | 129.46 | 621.32 | 77.71 | 41.21 | 241879.67 | 0.7470 | 28 |
| 0.5 | 119.38 | 505.88 | 66.00 | 73.55 | 241313.79 | 0.7508 | 20 |
| **0.6** | **120.12** | **541.27** | **61.67** | **66.26** | **241147.56** | **0.7501** | **18** |
| 0.7 | 122.65 | 577.82 | 72.30 | 69.38 | 240692.87 | 0.7467 | 29 |
| 0.8 | 138.63 | 582.05 | 97.31 | 68.89 | 240493.81 | 0.7453 | 41 |
| 0.9 | 205.80 | 1087.31 | 191.19 | 143.92 | 240466.31 | 0.6770 | 51 |
| 1.0 | 264.54 | 1426.77 | 259.21 | 160.10 | 240479.61 | 0.6378 | 57 |

時間單位為秒。

### 8.3 等待時間分析

![Waiting time](figures/static/01_static_waiting_time.png)

alpha = 0.5 具有最低平均等待時間及 P95 等待時間。

當 alpha 接近 1.0，
等待時間明顯增加。

![Priority waiting](figures/static/02_static_priority_waiting_time.png)

High Wait 最佳候選為 alpha = 0.6。

Emergency Wait 最佳候選為 alpha = 0.4。

### 8.4 移動效率及公平性

![Travel](figures/static/03_static_total_travel.png)

提高移動時間權重通常降低移動成本，
但實際移動時間差異相對有限。

![Fairness](figures/static/04_static_fairness.png)

當 alpha 接近 1.0 時，
兩種 Jain Fairness 均明顯下降。

### 8.5 最終參數選擇

| Stage | Candidates |
|---|---:|
| Grid search | 11 |
| Completion screening | 11 |
| Pareto front | 10 |
| Final selection | 1 |

![Rank sum](figures/static/05_static_rank_sum.png)

最終選定 alpha = 0.6。

| Metric | Value | Rank |
|---|---:|---:|
| Average Wait | 120.116753 | 2 |
| P95 Wait | 541.269591 | 2 |
| High Wait | 61.674936 | 1 |
| Emergency Wait | 66.255152 | 6 |
| Total Travel | 241147.563089 | 5 |
| Jain Task | 0.750063 | 2 |
| Rank Sum | | 18.0 |

alpha = 0.6 在四項指標中位於前兩名，
具有最低 Rank Sum。

### 8.6 電量驗證

![Battery](figures/static/06_static_battery_soc.png)

- Global minimum SoC: 18.1960%
- Minimum reserve: 15%
- Reserve violations: 0

### 8.7 新舊參數比較

![Original vs selected](figures/static/07_static_original_vs_selected.png)

在相同 V2 情境下，
alpha = 0.6 改善 High、Emergency 等待時間及總移動時間。

平均等待時間、P95 等待時間及 Task Fairness 則略為退步。

選擇 alpha = 0.6 的理由是整體排名，
而不是所有指標皆有改善。

### 8.8 低權重等價現象

alpha = 0.0、0.1、0.2、0.3
在全部十個 Seeds 下，
已記錄的評估指標均在指定數值容差內一致。

這表示部分權重變化未造成可觀測的效能差異，
但尚不能證明所有逐次派工行為完全相同。

### 8.9 實驗資料

- [Runs](data/calibration_v2/static/runs.csv)
- [Summary](data/calibration_v2/static/summary.csv)
- [Pareto](data/calibration_v2/static/pareto.csv)
- [Ranking](data/calibration_v2/static/ranking.csv)
- [Selected parameters](data/calibration_v2/static/selected_parameters.json)
- [Metadata](data/calibration_v2/static/experiment_metadata.json)

---

## 9. Dynamic Weighted Calibration V2

### 9.1 Grid search

設定上下界來自：

$$
\{0.0,0.1,0.2,\ldots,1.0\}
$$

限制：

$$
0\leq\alpha_{\min}<\alpha_{\max}\leq1
$$

上下界相等時為固定權重，
已由 Static 實驗涵蓋。

因此共有：

$$
\binom{11}{2}=55
$$

組合法候選範圍。

- Candidates: 55
- Replications: 10
- Total simulations: 550

初步規劃曾使用 15 組代表性候選，
正式實驗前擴大為完整 55 組離散網格，
避免人工選擇搜尋範圍的限制。

### 9.2 等待時間敏感度

![Average wait](figures/dynamic/01_dynamic_average_wait.png)

![P95 wait](figures/dynamic/02_dynamic_p95_wait.png)

![High wait](figures/dynamic/03_dynamic_high_wait.png)

![Emergency wait](figures/dynamic/04_dynamic_emergency_wait.png)

[0.5,0.8] 具有最低 Average、P95 及 High Waiting Time。

[0.3,1.0] 具有最低 Emergency Waiting Time。

### 9.3 移動效率與公平性

![Travel](figures/dynamic/05_dynamic_total_travel.png)

![Task fairness](figures/dynamic/06_dynamic_task_fairness.png)

![Utilization fairness](figures/dynamic/07_dynamic_utilization_fairness.png)

不同指標的最佳候選並不相同，
說明等待時間、移動效率及公平性之間存在取捨。

全部 55 組候選的完整數值請見：
[Dynamic summary](data/calibration_v2/dynamic/summary.csv)

### 9.4 參數選擇結果

| Stage | Candidates |
|---|---:|
| Grid search | 55 |
| Completion screening | 55 |
| Pareto front | 24 |
| Final selection | 1 |

![Rank sum](figures/dynamic/08_dynamic_rank_sum.png)

![Top 10](figures/dynamic/09_dynamic_top10_candidates.png)

| Rank | Range | Rank Sum | Pareto |
|---:|---|---:|---|
| 1 | [0.4,0.9] | 59.5 | Yes |
| 2 | [0.3,1.0] | 60.5 | Yes |
| 3 | [0.5,0.8] | 72.0 | Yes |
| 4 | [0.6,0.9] | 82.0 | Yes |
| 5 | [0.5,0.6] | 83.0 | Yes |
| 6 | [0.5,0.7] | 86.0 | No |
| 7 | [0.6,0.7] | 92.0 | Yes |
| 8 | [0.6,1.0] | 96.0 | No |
| 9 | [0.6,0.8] | 106.0 | Yes |
| 10 | [0.5,1.0] | 112.0 | Yes |

最終選定 [0.4,0.9]。

| Metric | Selected value | Rank |
|---|---:|---:|
| Average Wait | 119.893772 | 5 |
| P95 Wait | 525.141423 | 4.5 |
| High Wait | 67.224498 | 5 |
| Emergency Wait | 41.138152 | 2 |
| Total Travel | 241849.076940 | 16 |
| Jain Task | 0.747182 | 27 |
| Rank Sum | | 59.5 |

四項等待時間指標皆位於前五名。

第一名與第二名 Rank Sum 僅差 1.0，
尚不能宣稱兩者具有統計顯著差異。

### 9.5 新舊參數比較

| Metric | Original [0.4,0.8] | Selected [0.4,0.9] | Improvement |
|---|---:|---:|---:|
| Average Wait | 127.134292 | 119.893772 | +5.6952% |
| P95 Wait | 601.168659 | 525.141423 | +12.6466% |
| High Wait | 75.096439 | 67.224498 | +10.4824% |
| Emergency Wait | 41.361295 | 41.138152 | +0.5395% |
| Total Travel | 241912.020404 | 241849.076940 | +0.0260% |
| Jain Task | 0.745869 | 0.747182 | +0.1761% |

![Improvement](figures/dynamic/10_dynamic_original_vs_selected.png)

在相同 V2 校準環境下，
新版參數的六項主要指標平均值均有所改善。

其中 P95 Wait 與 High Wait 改善最明顯。

以上僅為校準資料上的描述性改善，
並非獨立測試的統計顯著性結論。

### 9.6 電量驗證

![Battery](figures/dynamic/12_dynamic_battery_soc.png)

- Global minimum SoC: 18.1912%
- Minimum reserve: 15%
- Reserve violations: 0

此數值為全部 550 次校準模擬的最低觀測值，
而非單獨選定參數的最低值。

### 9.7 Pareto Front

![Pareto front](figures/dynamic/13_dynamic_pareto_front.png)

55 組候選中共有 24 組非支配候選。

原始 [0.4,0.8] 不位於本次 Pareto Front。

選定的 [0.4,0.9] 位於 Pareto Front，
且具有最低 Rank Sum。

### 9.8 實驗資料

- [Runs](data/calibration_v2/dynamic/runs.csv)
- [Summary](data/calibration_v2/dynamic/summary.csv)
- [Pareto](data/calibration_v2/dynamic/pareto.csv)
- [Ranking](data/calibration_v2/dynamic/ranking.csv)
- [Selected parameters](data/calibration_v2/dynamic/selected_parameters.json)
- [Metadata](data/calibration_v2/dynamic/experiment_metadata.json)

---

## 10. Dynamic Weight Behavior Diagnostics

### 10.1 實驗目的

初步 Smoke Test 發現不同權重範圍在 Seed 3001
產生相同效能結果。

因此額外檢查：

- 動態權重公式。
- 候選加權成本。
- 機器人選擇規則。
- 實際 alpha 分布。
- 不同參數的派工序列差異。

診斷程式使用原始 Scheduler 的繼承類別，
只增加紀錄功能，不改變原始決策。

### 10.2 實驗規模

| Item | Value |
|---|---:|
| Diagnostic ranges | 7 |
| Seeds | 3001, 3002, 3003 |
| Diagnostic runs | 21 |
| Reference runs | 21 |
| Decision records | 39990 |

### 10.3 實際動態權重分布

| Range | Multi-candidate % | Alpha Min % | Alpha Max % | Intermediate % |
|---|---:|---:|---:|---:|
| [0.0,0.4] | 82.033 | 41.193 | 57.141 | 1.666 |
| [0.0,1.0] | 82.360 | 40.885 | 57.334 | 1.781 |
| [0.4,0.8] | 82.360 | 40.910 | 57.334 | 1.756 |
| [0.4,1.0] | 82.463 | 40.546 | 57.530 | 1.924 |
| [0.6,0.8] | 82.699 | 41.126 | 57.034 | 1.840 |
| [0.6,1.0] | 82.268 | 40.993 | 57.070 | 1.938 |
| [0.9,1.0] | 82.142 | 45.466 | 52.229 | 2.305 |

![Alpha distribution](figures/dynamic/11_dynamic_alpha_distribution.png)

Multi-candidate 比例以存在可行候選的決策為分母。

Alpha Min、Alpha Max 與 Intermediate 比例
以具有兩台以上可行候選的決策為分母。

以上為三個 Seeds 的比例平均。

約 97.7%–98.3% 的多候選決策使用上下界權重。

當候選負載相同時，不平衡程度為零；
當同時存在零負載與非零負載時，不平衡程度為一。

因此原本連續調整的公式，
在觀察到的情境下較接近上下界切換。

### 10.4 派工序列分析

| Seed | Tested ranges | Unique decision sequences |
|---|---:|---:|
| 3001 | 7 | 3 |
| 3002 | 7 | 5 |
| 3003 | 7 | 7 |

以任務 ID、決策時間、機器人 ID 及決策狀態
建立派工序列 SHA256。

結果顯示不同權重確實可能改變派工序列。

相同序列雜湊值不代表所有內部狀態完全一致。

### 10.5 診斷驗證

| Check | Result |
|---|---|
| Dynamic alpha formula | PASS |
| Weighted cost formula | PASS |
| Robot selection rule | PASS |
| Wrapper metric equivalence | PASS |
| Navigation hashes | PASS |
| PPO model hash | PASS |

診斷未發現需要修改原始演算法的問題。

但診斷只包含七組權重及三個 Seeds，
且未包含最後選定的 [0.4,0.9]，
不能將此分布直接視為最終參數的實測分布。

### 10.6 參數等價性

![Parameter equivalence](figures/dynamic/14_dynamic_parameter_equivalence.png)

全部 55 組候選共有 27 種不同主要指標結果。

等價定義為全部十個 Seeds 的六項主要效能指標
及 Completion Rate 數值完全相同。

| Group | Candidate count |
|---|---:|
| G1 | 12 |
| G2 | 4 |
| G3 | 6 |
| G4 | 6 |
| G5 | 3 |
| G6 | 2 |
| G7 | 2 |
| Unique singletons | 20 |

35 組候選屬於七個非單一等價群組，
另外 20 組各自具有獨立結果。

正式排名仍保留全部 55 組候選，
不因事後發現等價結果而重新修改排名規則。

### 10.7 診斷資料

- [Decision records](data/calibration_v2/diagnostics/dynamic_behavior/decision_records.csv)
- [Behavior summary](data/calibration_v2/diagnostics/dynamic_behavior/behavior_summary.csv)
- [Episode metrics](data/calibration_v2/diagnostics/dynamic_behavior/episode_metrics.csv)

---

## 11. Random Feasible Battery-aware Evaluation

### 11.1 實驗設計

Random Feasible 無須校準權重，
直接使用共用模擬器及電量可行性限制進行評估。

- Fleet: (2,2,3)
- Workload: 4.0x
- Seeds: 3001–3010
- Battery model: Enabled
- Total simulations: 10

### 11.2 實驗結果

| Metric | Value |
|---|---:|
| Average Waiting Time | 169.71 s |
| P95 Waiting Time | 816.39 s |
| High Waiting Time | 113.34 s |
| Emergency Waiting Time | 111.99 s |
| Total Travel Time | 247184.05 s |
| Jain Task Fairness | 0.8695 |
| Jain Utilization Fairness | 0.9649 |
| Completion Rate | 100% |
| Minimum observed SoC | 18.37% |
| Average charging count | 75.90 |
| Reserve violations | 0 |

Random Feasible 在四種方法中具有最高的
Task Fairness 及 Utilization Fairness。

但總移動時間亦為四種方法中最高。

此結果顯示隨機分配在目前異質車隊及任務情境中
能產生較平均的任務分配，
但不一定具有較佳等待時間或移動效率。

### 11.3 實驗資料

- [Runs](data/calibration_v2/random/runs.csv)
- [Summary](data/calibration_v2/random/summary.csv)
- [Metadata](data/calibration_v2/random/experiment_metadata.json)

獨立執行程式：
[Random evaluation](../../battery_calibration/run_random_evaluation.py)

---

## 12. Projected Nearest Battery-aware Evaluation

### 12.1 實驗設計

Projected Nearest 不具有需要搜尋的權重參數。

使用預估來源地移動時間及相同電量可行性限制，
直接進行十次模擬。

- Fleet: (2,2,3)
- Workload: 4.0x
- Seeds: 3001–3010
- Battery model: Enabled
- Total simulations: 10

### 12.2 實驗結果

| Metric | Value |
|---|---:|
| Average Waiting Time | 289.08 s |
| P95 Waiting Time | 1692.40 s |
| High Waiting Time | 299.81 s |
| Emergency Waiting Time | 180.20 s |
| Total Travel Time | 240245.62 s |
| Jain Task Fairness | 0.6250 |
| Jain Utilization Fairness | 0.7017 |
| Completion Rate | 100% |
| Minimum observed SoC | 18.46% |
| Average charging count | 73.60 |
| Reserve violations | 0 |

Projected Nearest 在四種方法中具有最低總移動時間，
但四項等待時間指標均為最高，
兩種公平性指標亦為最低。

結果與任務可能集中於特定機器人的解釋一致，
但尚未建立負載集中與等待時間的獨立因果驗證。

### 12.3 實驗資料

- [Runs](data/calibration_v2/nearest/runs.csv)
- [Summary](data/calibration_v2/nearest/summary.csv)
- [Metadata](data/calibration_v2/nearest/experiment_metadata.json)

獨立執行程式：
[Nearest evaluation](../../battery_calibration/run_nearest_evaluation.py)

---

## 13. Four-Baseline Preliminary Comparison

### 13.1 固定參數

| Method | Final configuration |
|---|---|
| Random Feasible | Uniform random among feasible candidates |
| Projected Nearest | Minimum projected approach time |
| Static Weighted | alpha = 0.6 |
| Dynamic Weighted | alpha_min = 0.4, alpha_max = 0.9 |

### 13.2 統一比較結果

從已完成的 680 筆實驗結果中，
擷取四種方法固定設定的各十筆紀錄，共 40 筆。

| Metric | Random | Nearest | Static | Dynamic |
|---|---:|---:|---:|---:|
| Avg Wait (s) | 169.71 | 289.08 | 120.12 | **119.89** |
| P95 Wait (s) | 816.39 | 1692.40 | 541.27 | **525.14** |
| High Wait (s) | 113.34 | 299.81 | **61.67** | 67.22 |
| Emergency Wait (s) | 111.99 | 180.20 | 66.26 | **41.14** |
| Total Travel (s) | 247184.05 | **240245.62** | 241147.56 | 241849.08 |
| Jain Task | **0.8695** | 0.6250 | 0.7501 | 0.7472 |
| Jain Utilization | **0.9649** | 0.7017 | 0.8579 | 0.8542 |
| Completion Rate | 100% | 100% | 100% | 100% |
| Minimum observed SoC | 18.37% | 18.46% | 18.27% | 18.47% |
| Mean charging count | 75.90 | 73.60 | 73.40 | 73.80 |

除最低觀測 SoC 外，
表中效能數值皆為十次模擬的平均值。

### 13.3 研究發現

Random Feasible：
具有最佳公平性，但總移動時間最高。

Projected Nearest：
具有最低移動時間，但等待時間及公平性表現較差。

Static Weighted：
同時考量移動時間與任務負載，
具有最低 High Waiting Time。

Dynamic Weighted：
依負載調整權重，
具有最低 Average、P95 及 Emergency Waiting Time。

沒有任何一種 Baseline 在全部主要指標中均取得最佳表現。

這些差異提供後續多目標 PPO 派工策略的比較基準。

目前結果僅來自校準情境，
不能直接作為獨立測試或統計顯著性結論。

四種 Baseline 的比較圖表暫不另外製作，
將於後續正式 PPO 比較完成後，
使用獨立測試資料統一繪製五種方法的效能圖表。

### 13.4 統一比較資料

- [Comparison runs](data/calibration_v2/baseline_comparison/comparison_runs.csv)
- [Comparison summary](data/calibration_v2/baseline_comparison/comparison_summary.csv)
- [Comparison metadata](data/calibration_v2/baseline_comparison/comparison_metadata.json)

資料整合程式：
[Compare baselines](../../battery_calibration/compare_baselines.py)

---

## 14. Experimental Integrity

| Check | Random | Nearest | Static | Dynamic |
|---|---:|---:|---:|---:|
| Expected runs | 10 | 10 | 110 | 550 |
| Actual runs | 10 | 10 | 110 | 550 |
| Duplicate runs | 0 | 0 | 0 | 0 |
| Missing runs | 0 | 0 | 0 | 0 |
| Battery enabled | Yes | Yes | Yes | Yes |
| Reserve violations | 0 | 0 | 0 | 0 |
| Source hashes verified | 13 | 13 | Not recorded | 13 |
| Navigation hashes | PASS | PASS | PASS | PASS |
| PPO model hash | PASS | PASS | PASS | PASS |

額外完整性驗證：

| Check | Result |
|---|---|
| Static recalculated summary values | 1056 |
| Dynamic recalculated summary values | 5335 |
| Unified comparison records | 40 |
| Shared numeric metrics | 46 |
| Unified recalculated summary values | 368 |
| Cross-method task population | PASS |
| Source data hashes | PASS |
| Documentation data files | 30 |
| PNG figures | 21 |
| SVG figures | 21 |

Static 原始實驗 Metadata 未保存完整原始碼雜湊，
因此不宣稱其原始碼驗證程度與其他三種方法完全相同。

跨方法驗證已確認相同 Seed 下的任務生成總數、
High、Emergency 及 High+ 數量一致。

尚未驗證每筆任務的所有屬性完全一致。

### Frozen PPO model

既有部署模型：

```
results_rl/models/
reward_confirm_sweep27_w50_a30_q15_i05_seed7104_200k/
final_model.zip
```

SHA256:

```
ba278857a1042ed58ae38e9522c7a962d73abd467d539de9479773cf96fe55e0
```

本階段僅驗證 PPO 模型完整性，
不執行 PPO 訓練或使用其結果調整 Baseline。

---

## 15. Limitations

1. Static 與 Dynamic 使用間距 0.1 的離散網格搜尋，
   不代表連續權重空間中的全域最佳解。

2. 校準使用固定七台車隊及 4.0x Workload，
   尚未確認其他工作負載下的泛化表現。

3. 原始 Fleet Sizing 未啟用電量模型，
   七台配置為後續固定研究條件，
   並非已重新證明為電量感知環境的最佳配置。

4. Rank Sum 使用等權排名，
   不反映各項指標實際差距的大小。

5. 等價候選仍納入排名，
   搜尋集合的組成可能影響排名結果。

6. Static 與 Dynamic 的 Rank Sum
   具有不同排名基準，不能直接跨方法比較。

7. 校準結果未建立獨立測試中的統計顯著性。

8. 動態權重診斷僅使用七組權重及三個 Seeds。

9. Jain Fairness 未直接反映異質機器人的能力需求差異。

10. 電量模型未涵蓋所有實際硬體耗電因素。

11. Total Travel Time 不包含所有充電相關移動成本。

12. V1 與 V2 實驗條件及評估方式不同，
    無法將跨版本效能差異歸因於單一因素。

13. Static 原始 Metadata 缺少完整原始程式雜湊。

14. 相同任務數量不等於每筆任務屬性均一致，
    後續正式比較前仍須進一步驗證。

---

## 16. Reproducibility

### 16.1 共用實驗程式

- [Configuration](../../battery_calibration/config.py)
- [Evaluation](../../battery_calibration/evaluation.py)
- [Selection](../../battery_calibration/selection.py)

### 16.2 獨立實驗入口

- [Random](../../battery_calibration/run_random_evaluation.py)
- [Nearest](../../battery_calibration/run_nearest_evaluation.py)
- [Static](../../battery_calibration/run_static_calibration.py)
- [Dynamic](../../battery_calibration/run_dynamic_calibration.py)
- [Dynamic diagnostics](../../battery_calibration/diagnose_dynamic_behavior.py)
- [Baseline comparison](../../battery_calibration/compare_baselines.py)

### 16.3 執行環境

從專案根目錄執行：

```bash
source .venv_rl/bin/activate

export PYTHONPATH="$PWD:$PWD/experiments/fleet_sizing${PYTHONPATH:+:$PYTHONPATH}"
```

Python 及套件版本請參考各實驗 Metadata。

### 16.4 重現實驗

```bash
python -m experiments.fleet_sizing.battery_calibration.run_random_evaluation

python -m experiments.fleet_sizing.battery_calibration.run_nearest_evaluation

python -m experiments.fleet_sizing.battery_calibration.run_static_calibration

python -m experiments.fleet_sizing.battery_calibration.diagnose_dynamic_behavior

python -m experiments.fleet_sizing.battery_calibration.run_dynamic_calibration

python -m experiments.fleet_sizing.battery_calibration.compare_baselines
```

各實驗具有輸出防覆蓋機制。

若結果已存在，應使用獨立工作副本及輸出位置，
不要為了重跑而刪除歷史實驗數據。

四種 Baseline 的統一比較程式
只讀取既有數據，不重新執行模擬。

### 16.5 重現圖表

```bash
python experiments/fleet_sizing/docs/03_baseline/plot_static_results.py

python experiments/fleet_sizing/docs/03_baseline/plot_dynamic_results.py
```

- [Static plotting](plot_static_results.py)
- [Dynamic plotting](plot_dynamic_results.py)

圖表直接讀取 CSV 及 JSON。

每張圖輸出 300 DPI PNG 與 SVG。

重新執行繪圖程式會更新同名圖表。

### 16.6 資料夾結構

```
03_baseline/
├── README.md
├── plot_static_results.py
├── plot_dynamic_results.py
├── data/
│   ├── calibration_v1/
│   └── calibration_v2/
│       ├── random/
│       ├── nearest/
│       ├── static/
│       ├── dynamic/
│       ├── baseline_comparison/
│       └── diagnostics/
│           └── dynamic_behavior/
└── figures/
    ├── static/
    └── dynamic/
```

---

## 17. Conclusion and Next Stage

本研究完成四種 Baseline 的電量感知校準與效能評估，
共 680 次模擬。

最終設定：

| Method | Parameters |
|---|---|
| Random Feasible | No tunable weights |
| Projected Nearest | No tunable weights |
| Static Weighted | alpha = 0.6 |
| Dynamic Weighted | alpha_min = 0.4, alpha_max = 0.9 |

所有 V2 模擬的任務完成率均為 100%，
且未觀察到低於 15% 保留電量門檻的紀錄。

後續將固定四種 Baseline 與既有 PPO 模型，
使用不同工作負載及獨立測試 Seeds 進行正式比較。

預計設定：

- Fleet: (2,2,3)
- Workloads: 3.0, 3.5, 4.0, 4.5, 5.0
- Methods: 5
- Seeds per workload: 30
- Total formal episodes: 750

正式測試 Seeds 仍須進行歷史重疊檢查。

PPO 模型維持 Sweep 27、Model Seed 7104，
不重新訓練。

後續使用 Paired Bootstrap 分析效能差異，
並統一製作五種方法的比較圖表。

本文件完成時，
新版 750 次正式比較尚未執行。

