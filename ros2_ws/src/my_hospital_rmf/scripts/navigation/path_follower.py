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
    robot_x=None,
    robot_y=None,
    segment_anchor_x=None,
    segment_anchor_y=None,
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

    # 預設仍使用原本的 waypoint tracking，
    # 只有具備有效 RMF lane anchor 時才啟用
    # segment lookahead tracking。
    desired_yaw = math.atan2(
        dy,
        dx,
    )

    if (
        robot_x is not None
        and robot_y is not None
        and segment_anchor_x is not None
        and segment_anchor_y is not None
    ):
        ax = float(segment_anchor_x)
        ay = float(segment_anchor_y)

        bx = float(target.x)
        by = float(target.y)

        segment_dx = bx - ax
        segment_dy = by - ay

        segment_length_sq = (
            segment_dx * segment_dx
            + segment_dy * segment_dy
        )

        # 避免極短 segment 除以 0。
        if segment_length_sq > 1.0e-6:
            segment_length = math.sqrt(
                segment_length_sq
            )

            robot_from_anchor_x = (
                float(robot_x) - ax
            )
            robot_from_anchor_y = (
                float(robot_y) - ay
            )

            # robot 在 RMF segment 上的投影比例。
            projection_t = (
                robot_from_anchor_x
                * segment_dx
                + robot_from_anchor_y
                * segment_dy
            ) / segment_length_sq

            projection_t = clamp(
                projection_t,
                0.0,
                1.0,
            )

            # 從投影點沿 RMF lane 往前看一小段。
            #
            # 0.50 m 先作為保守初始值：
            # 太大會切角，太小會容易左右震盪。
            lookahead_distance = 0.50

            lookahead_t = min(
                1.0,
                projection_t
                + lookahead_distance
                / segment_length,
            )

            lookahead_x = (
                ax
                + lookahead_t
                * segment_dx
            )
            lookahead_y = (
                ay
                + lookahead_t
                * segment_dy
            )

            lookahead_dx = (
                lookahead_x
                - float(robot_x)
            )
            lookahead_dy = (
                lookahead_y
                - float(robot_y)
            )

            lookahead_distance_actual = (
                math.hypot(
                    lookahead_dx,
                    lookahead_dy,
                )
            )

            if lookahead_distance_actual > 1.0e-6:
                desired_yaw = math.atan2(
                    lookahead_dy,
                    lookahead_dx,
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
