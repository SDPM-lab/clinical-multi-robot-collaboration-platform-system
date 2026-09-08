#!/usr/bin/env python3


# ==========================================================
# Training / Validation / Final Test Seeds
#
# Seed 使用原則：
#
# 0 ~ 29
# → Initial benchmark
# → 已經看過結果，不再拿來做調參依據
#
# 1000 ~ 1029
# → Validation
#
# 2000 ~ 2029
# → Final unseen test
#
# 3000 ~ 4999
# → Training scenarios
# ==========================================================

TRAINING_SEEDS = list(
    range(
        3000,
        5000,
    )
)

VALIDATION_SEEDS = list(
    range(
        5000,
        5030,
    )
)

FINAL_TEST_SEEDS = list(
    range(
        2000,
        2030,
    )
)


# ==========================================================
# Training Scenario Distribution
#
# vNext:
#
# 不再固定：
#
# 20 tasks
# medium load
#
# 改為：
#
# Multi-task-count
# +
# Multi-load
#
# 第一版先完全對齊正式實驗條件：
#
# Task Count:
# 20 / 50 / 100
#
# Load:
# low / medium / high
#
# 每次 reset() 隨機抽一組。
# ==========================================================

TRAIN_TASK_COUNTS = [
    20,
    50,
    100,
]

TRAIN_LOADS = [
    "low",
    "medium",
    "high",
]

# ==========================================================
# Balanced Multi-task-count Sampling
#
# 原本每種 episode 機率相同：
#
# 20 / 50 / 100
# = 1/3 / 1/3 / 1/3
#
# 但 episode 長度不同，因此 PPO rollout 中：
#
# 20-task  transition 比例偏低
# 100-task transition 比例偏高
#
# 使用 inverse task-count weighting：
#
# 1/20 : 1/50 : 1/100
# =
# 5 : 2 : 1
#
# 因此 episode sampling：
#
# 20  -> 62.5%
# 50  -> 25.0%
# 100 -> 12.5%
#
# 使三種 task count 對 training transitions
# 的期望貢獻接近相同。
# ==========================================================

TRAIN_TASK_COUNT_WEIGHTS = [
    5,
    2,
    1,
]

# ==========================================================
# PPO Training
#
# vNext 第一輪只改 Training Distribution。
#
# Observation:
# 33D
#
# Reward:
# v3
#
# PPO Hyperparameters:
# 不變
#
# Training:
# 100K timesteps
# ==========================================================

TOTAL_TIMESTEPS = (
    100000
)

PPO_SEED = (
    42
)