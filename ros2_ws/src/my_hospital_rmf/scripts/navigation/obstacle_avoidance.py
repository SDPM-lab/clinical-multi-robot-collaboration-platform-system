import math

from navigation.config import (
    OBSTACLE_STOP_DISTANCE,
    GOAL_APPROACH_DISTANCE,
    GOAL_EMERGENCY_STOP_DISTANCE,
)


def analyze_lidar_scan(msg):
    """
    從 LaserScan 計算導航目前使用的：
    - front clearance
    - left clearance
    - right clearance
    - front debug statistics

    此函式只做資料計算，不包含 ROS logger
    或避障 state machine。
    """

    front_values = []
    left_values = []
    right_values = []

    front_limit = math.radians(10.0)

    side_inner = math.radians(25.0)
    side_outer = math.radians(80.0)

    for index, value in enumerate(
        msg.ranges
    ):
        distance = float(value)

        if not math.isfinite(
            distance
        ):
            continue

        if (
            distance < msg.range_min
            or
            distance > msg.range_max
        ):
            continue

        angle = (
            float(msg.angle_min)
            + index
            * float(msg.angle_increment)
        )

        if abs(angle) <= front_limit:
            front_values.append(
                distance
            )

        elif (
            side_inner
            <= angle
            <= side_outer
        ):
            left_values.append(
                distance
            )

        elif (
            -side_outer
            <= angle
            <= -side_inner
        ):
            right_values.append(
                distance
            )

    front_beam_count = len(
        front_values
    )

    front_raw_min = (
        min(front_values)
        if front_values
        else math.inf
    )

    front_close_count = sum(
        1
        for value in front_values
        if value <= OBSTACLE_STOP_DISTANCE
    )

    if front_values:
        sorted_front = sorted(
            front_values
        )

        front_index = int(
            0.25
            * (
                len(sorted_front)
                - 1
            )
        )

        front_clearance = (
            sorted_front[
                front_index
            ]
        )
    else:
        front_clearance = math.inf

    left_clearance = (
        min(left_values)
        if left_values
        else math.inf
    )

    right_clearance = (
        min(right_values)
        if right_values
        else math.inf
    )

    return {
        "front_beam_count": front_beam_count,
        "front_raw_min": front_raw_min,
        "front_close_count": front_close_count,
        "front_clearance": front_clearance,
        "left_clearance": left_clearance,
        "right_clearance": right_clearance,
    }


from navigation.config import (
    ANGULAR_KP,
    MAX_ANGULAR_SPEED,
    AVOID_TURN_TOLERANCE,
    AVOID_LINEAR_SPEED,
    AVOID_FORWARD_DISTANCE,
    OBSTACLE_SLOW_DISTANCE,
    SIDE_SAFE_DISTANCE,
    SIDE_CORRECTION_KP,
    SIDE_MAX_ANGULAR_SPEED,
    RECOVER_MIN_SIDE_CLEARANCE,
    BYPASS_PATH_KP,
    BYPASS_PATH_MAX_ANGULAR_SPEED,
    ROTATE_FIRST_THRESHOLD,
)

from navigation.utils import (
    clamp,
    normalize_angle,
)


def compute_turn_command(
    current_yaw,
    target_yaw,
    max_angular_speed=MAX_ANGULAR_SPEED,
):
    turn_error = normalize_angle(
        target_yaw - current_yaw
    )

    reached = (
        abs(turn_error)
        <= AVOID_TURN_TOLERANCE
    )

    angular = clamp(
        ANGULAR_KP * turn_error,
        -max_angular_speed,
        max_angular_speed,
    )

    return (
        reached,
        angular,
    )


def can_recover_from_bypass(
    robot,
    bypass_distance,
):
    side_clearance = math.inf

    if robot.avoidance_turn_direction > 0:
        side_clearance = robot.right_clearance

    elif robot.avoidance_turn_direction < 0:
        side_clearance = robot.left_clearance

    can_recover = (
        bypass_distance >= AVOID_FORWARD_DISTANCE
        and robot.front_clearance > OBSTACLE_SLOW_DISTANCE
        and side_clearance > RECOVER_MIN_SIDE_CLEARANCE
    )

    return (
        can_recover,
        side_clearance,
    )


def compute_bypass_command(
    robot,
    dx,
    dy,
    yaw,
):
    bypass_linear = AVOID_LINEAR_SPEED
    bypass_angular = 0.0

    if robot.received_scan:

        left = robot.left_clearance
        right = robot.right_clearance

        side_too_close = (
            left < SIDE_SAFE_DISTANCE
            or right < SIDE_SAFE_DISTANCE
        )

        if side_too_close:

            bypass_linear = 0.15

            if left <= right:

                correction = (
                    SIDE_SAFE_DISTANCE - left
                )

                bypass_angular = clamp(
                    -SIDE_CORRECTION_KP
                    * correction,
                    -SIDE_MAX_ANGULAR_SPEED,
                    SIDE_MAX_ANGULAR_SPEED,
                )

            else:

                correction = (
                    SIDE_SAFE_DISTANCE - right
                )

                bypass_angular = clamp(
                    SIDE_CORRECTION_KP
                    * correction,
                    -SIDE_MAX_ANGULAR_SPEED,
                    SIDE_MAX_ANGULAR_SPEED,
                )

        else:

            waypoint_yaw = math.atan2(
                dy,
                dx,
            )

            waypoint_error = normalize_angle(
                waypoint_yaw - yaw
            )

            path_correction = clamp(
                BYPASS_PATH_KP
                * waypoint_error,
                -BYPASS_PATH_MAX_ANGULAR_SPEED,
                BYPASS_PATH_MAX_ANGULAR_SPEED,
            )

            bypass_angular += path_correction

    bypass_angular = clamp(
        bypass_angular,
        -SIDE_MAX_ANGULAR_SPEED,
        SIDE_MAX_ANGULAR_SPEED,
    )

    return (
        bypass_linear,
        bypass_angular,
    )


def compute_recover_command(
    dx,
    dy,
    yaw,
):
    recover_yaw = math.atan2(
        dy,
        dx,
    )

    recover_error = normalize_angle(
        recover_yaw - yaw
    )

    recovered = (
        abs(recover_error)
        <= ROTATE_FIRST_THRESHOLD
    )

    angular = clamp(
        ANGULAR_KP
        * recover_error,
        -MAX_ANGULAR_SPEED,
        MAX_ANGULAR_SPEED,
    )

    return (
        recovered,
        angular,
    )


def should_trigger_obstacle_avoidance(
    robot,
    distance,
    is_last,
):
    near_final_goal = (
        is_last
        and
        distance <= GOAL_APPROACH_DISTANCE
    )

    goal_emergency_obstacle = (
        near_final_goal
        and
        robot.received_scan
        and
        robot.front_clearance
        <= GOAL_EMERGENCY_STOP_DISTANCE
    )

    should_trigger = (
        robot.avoidance_state == "normal"
        and
        robot.received_scan
        and
        robot.front_clearance
        <= OBSTACLE_STOP_DISTANCE
        and
        (
            not near_final_goal
            or goal_emergency_obstacle
        )
    )

    return should_trigger


def choose_avoidance_direction(
    robot,
):
    if (
        robot.left_clearance
        >= robot.right_clearance
    ):
        return (
            1,
            "LEFT",
        )

    return (
        -1,
        "RIGHT",
    )
