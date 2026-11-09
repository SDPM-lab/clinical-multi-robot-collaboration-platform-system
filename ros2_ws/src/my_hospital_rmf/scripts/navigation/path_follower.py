import math

from navigation.config import (
    ARRIVE_DISTANCE,
    GOAL_APPROACH_DISTANCE,
    GOAL_APPROACH_MAX_SPEED,
    FINAL_YAW_TOLERANCE,
    ROTATE_FIRST_THRESHOLD,
    LINEAR_KP,
    ANGULAR_KP,
    MAX_LINEAR_SPEED,
    MAX_ANGULAR_SPEED,
    MIN_LINEAR_SPEED,
)

from navigation.utils import (
    clamp,
    normalize_angle,
)


def compute_normal_tracking_command(
    target,
    dx,
    dy,
    distance,
    yaw,
    is_last,
):
    """
    計算正常 waypoint tracking 所需的速度命令。

    這裡只負責沿目前 target 行走，
    不包含：
    - LiDAR obstacle slowdown
    - obstacle avoidance state machine
    - robot-to-robot avoidance
    - final waypoint completion
    """

    desired_yaw = math.atan2(
        dy,
        dx,
    )

    heading_error = normalize_angle(
        desired_yaw - yaw
    )

    angular = clamp(
        ANGULAR_KP
        * heading_error,
        -MAX_ANGULAR_SPEED,
        MAX_ANGULAR_SPEED,
    )

    # 朝向誤差太大時，先原地旋轉
    if (
        abs(heading_error)
        > ROTATE_FIRST_THRESHOLD
    ):
        return (
            0.0,
            angular,
        )

    linear_limit = (
        MAX_LINEAR_SPEED
    )

    # RMF Location approach speed limit
    if (
        target.obey_approach_speed_limit
        and
        target.approach_speed_limit > 0.0
    ):
        linear_limit = min(
            linear_limit,
            float(
                target.approach_speed_limit
            ),
        )

    linear = min(
        linear_limit,
        LINEAR_KP * distance,
    )

    # 最後 waypoint 附近降低速度
    if (
        is_last
        and
        distance <= GOAL_APPROACH_DISTANCE
    ):
        linear = min(
            linear,
            GOAL_APPROACH_MAX_SPEED,
        )

    if (
        distance > ARRIVE_DISTANCE
        and
        linear < MIN_LINEAR_SPEED
    ):
        linear = min(
            MIN_LINEAR_SPEED,
            linear_limit,
        )

    # heading error 越大，前進速度越低
    heading_scale = max(
        0.25,
        1.0
        - abs(heading_error)
        / ROTATE_FIRST_THRESHOLD,
    )

    linear *= heading_scale

    return (
        linear,
        angular,
    )


def compute_final_goal_command(
    target,
    distance,
    yaw,
    is_last,
):
    """
    判斷是否已到 final waypoint。

    回傳：
        None
            -> 尚未到 final waypoint

        ("rotate", 0.0, angular)
            -> 已到位置，但仍需調整 final yaw

        ("complete", 0.0, 0.0)
            -> 位置與 final yaw 都已完成
    """

    if (
        not is_last
        or distance > ARRIVE_DISTANCE
    ):
        return None

    target_yaw = float(
        target.yaw
    )

    if math.isfinite(
        target_yaw
    ):
        final_yaw_error = normalize_angle(
            target_yaw - yaw
        )

        if (
            abs(final_yaw_error)
            > FINAL_YAW_TOLERANCE
        ):
            angular = clamp(
                ANGULAR_KP
                * final_yaw_error,
                -MAX_ANGULAR_SPEED,
                MAX_ANGULAR_SPEED,
            )

            return (
                "rotate",
                0.0,
                angular,
            )

    return (
        "complete",
        0.0,
        0.0,
    )
