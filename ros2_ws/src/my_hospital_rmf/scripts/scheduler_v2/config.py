#!/usr/bin/env python3


# ==========================================================
# Task Scheduling
# ==========================================================

# 每等待多少秒，
# Effective Priority 增加 1。
#
# 例如：
#
# Low priority = 0
#
# 等待 120 秒：
# effective_priority = 1
#
# 等待 240 秒：
# effective_priority = 2
#
# 等待 360 秒：
# effective_priority = 3
#
# 正式實驗前可以透過 validation 固定此值，
# Final Test 開始後不可再修改。
AGING_INTERVAL_SECONDS = 120.0


# ==========================================================
# Robot Safety
# ==========================================================

# Robot 電量低於此門檻時，
# 不允許接受新的 Task。
#
# Scheduler 內部 battery 統一使用：
#
# 0.0 ~ 1.0
#
# 此值目前作為 v2 初始實驗設定，
# 正式 Final Test 前需固定。
MIN_BATTERY_LEVEL = 0.20


# ==========================================================
# Battery Consumption
# ==========================================================

# Algorithm-level simulator 使用的初始耗電模型。
#
# Battery 內部使用 0.0 ~ 1.0。
#
# 0.0005 代表：
#
# 每移動 1 meter
# 消耗 0.0005
#
# 即每 100 m 約消耗 5% Battery。
#
# 此值目前為 Development Setting，
# 正式實驗前需固定。
BATTERY_DRAIN_PER_METER = 0.0005


# ==========================================================
# Projection / Simulation
# ==========================================================

# Algorithm-level simulator 中使用的預設 Robot 移動速度。
#
# 單位：
# meter / second
#
# 正式實驗前需根據模擬設定固定。
DEFAULT_ROBOT_SPEED_MPS = 1.0


# 每個 Task 到達 Destination 後，
# 額外需要的固定服務時間。
#
# 例如：
# - 交付
# - 取放物品
# - 任務確認
#
# 單位：
# second
#
# 正式實驗前需固定。
DEFAULT_TASK_SERVICE_TIME_SECONDS = 30.0


# ==========================================================
# Weighted Heuristic
# ==========================================================

# ----------------------------------------------------------
# Cost Weights
#
# Cost =
#   wd * normalized_distance
#   +
#   wb * battery_cost
#   +
#   wl * normalized_workload
#
# 目前為 v2 開發階段初始設定。
# 正式實驗前需透過 Validation 固定。
# ----------------------------------------------------------

WEIGHTED_DISTANCE_WEIGHT = 0.50

WEIGHTED_BATTERY_WEIGHT = 0.30

WEIGHTED_WORKLOAD_WEIGHT = 0.20


# ----------------------------------------------------------
# Normalization References
#
# Distance：
# projected position -> task source
#
# Workload：
# task 開始前的 projected workload
#
# 超過 reference 時會截斷為 1.0。
#
# 這兩個值目前只是開發階段初始值，
# 正式 Scenario 完成後再固定。
# ----------------------------------------------------------

DISTANCE_NORMALIZATION_REFERENCE = 50.0

WORKLOAD_NORMALIZATION_REFERENCE_SECONDS = 300.0


# ==========================================================
# Dynamic Reassignment
# ==========================================================

# Dynamic Weighted 只有在 Alternative Robot
# 的 Weighted Cost 改善幅度超過此值時才真正 Reassign。
#
# Weighted Cost 已正規化至約 0.0 ~ 1.0，
# 因此 0.05 表示至少需要約 5 percentage points
# 的成本改善，避免微小差異造成來回重新派工。
#
# Development setting：
# 正式 Final Experiment 前固定。
DYNAMIC_REASSIGNMENT_MIN_IMPROVEMENT = 0.05