#!/usr/bin/env python3

import math

# ==========================================================
# Battery Consumption
# ==========================================================

def calculate_battery_consumption(
    travel_distance: float,
    drain_per_meter: float,
) -> float:
    """
    根據 Robot 移動距離估算 Battery Consumption。

    Battery 使用：
        0.0 ~ 1.0

    例如：

        drain_per_meter = 0.0005

    表示：

        每移動 1 meter
        消耗 0.0005 battery ratio

    注意：
    此模型目前只考慮移動距離。

    Service / Idle / Compute Energy
    暫不納入第一版。
    """

    travel_distance = float(
        travel_distance
    )

    drain_per_meter = float(
        drain_per_meter
    )

    if travel_distance < 0.0:

        raise ValueError(
            "travel_distance "
            "cannot be negative"
        )

    if drain_per_meter < 0.0:

        raise ValueError(
            "drain_per_meter "
            "cannot be negative"
        )

    return (
        travel_distance
        *
        drain_per_meter
    )


# ==========================================================
# Battery After Consumption
# ==========================================================

def calculate_remaining_battery(
    battery: float,
    consumption: float,
) -> float:
    """
    計算消耗後剩餘 Battery。

    結果限制在：

        0.0 ~ 1.0
    """

    battery = float(
        battery
    )

    consumption = float(
        consumption
    )

    if not (
        0.0
        <= battery
        <= 1.0
    ):

        raise ValueError(
            "battery must be "
            "between 0.0 and 1.0"
        )

    if consumption < 0.0:

        raise ValueError(
            "consumption "
            "cannot be negative"
        )

    return max(
        0.0,
        battery
        -
        consumption,
    )


# ==========================================================
# Safety
# ==========================================================

def has_enough_battery_for_task(
    battery: float,
    expected_consumption: float,
    safety_threshold: float,
) -> bool:
    """
    判斷 Robot 執行預定工作後，
    是否仍能保持安全 Battery。

    Rule:

        battery
        -
        expected_consumption
        >=
        safety_threshold

    因此不是只判斷：

        current battery >= threshold

    而是確保執行工作後
    仍不會低於 safety threshold。
    """

    safety_threshold = float(
        safety_threshold
    )

    if not (
        0.0
        <= safety_threshold
        <= 1.0
    ):

        raise ValueError(
            "safety_threshold must be "
            "between 0.0 and 1.0"
        )

    remaining = (
        calculate_remaining_battery(
            battery=battery,
            consumption=(
                expected_consumption
            ),
        )
    )

    return (
        remaining
        >
        safety_threshold
        or
        math.isclose(
            remaining,
            safety_threshold,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    )