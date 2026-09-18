#!/usr/bin/env python3

# ==========================================================
# Scheduler Capability Configuration
#
# 這裡是正式 Runtime 的 Capability 單一資料來源。
#
# 注意：
#
# Backend 負責：
#   TaskType -> required_capabilities
#
# Scheduler 不重新推導 Task 所需能力，
# 只驗證 Backend 傳入的 capability 是否合法，
# 並與 Robot capabilities 做 matching。
#
# RMF fleet_config.yaml 裡的：
#
#   task_capabilities:
#     loop: true
#     delivery: true
#
# 是 RMF 自己的 task category，
# 與這裡的 heterogeneous robot capabilities 不同。
# ==========================================================


# ==========================================================
# Supported Hospital Task Types
# ==========================================================

VALID_TASK_TYPES = {
    "medicine_delivery",
    "specimen_delivery",
    "general_delivery",
    "waste_collection",
}


# ==========================================================
# Supported Robot Capabilities
# ==========================================================

VALID_CAPABILITIES = {
    "navigation",
    "general_delivery",
    "medicine_delivery",
    "specimen_delivery",
    "manipulation",
}


# ==========================================================
# Formal RMF Deployment Robot Capabilities
#
# Experiment II / RMF runtime：
#
# R1:
#   medicine + general
#
# R2:
#   specimen + general
#
# R3:
#   medicine + specimen + general
#
# R4:
#   general
#
# 所有 Robot 都具備 navigation。
# ==========================================================

ROBOT_CAPABILITIES = {
    "hospital_robot_1": {
        "navigation",
        "medicine_delivery",
        "general_delivery",
    },

    "hospital_robot_2": {
        "navigation",
        "specimen_delivery",
        "general_delivery",
    },

    "hospital_robot_3": {
        "navigation",
        "general_delivery",
    },

    "hospital_robot_4": {
        "navigation",
        "medicine_delivery",
        "specimen_delivery",
        "general_delivery",
    },
}
