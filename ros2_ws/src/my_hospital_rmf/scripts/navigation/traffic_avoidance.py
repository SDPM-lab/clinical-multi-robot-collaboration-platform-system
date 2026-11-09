import math

from navigation.config import (
    ROBOT_CONFLICT_DISTANCE,
    ROBOT_CONFLICT_ANGLE,
    HEAD_ON_MIN_OPPOSITE_ANGLE,
)

from navigation.utils import normalize_angle


def find_robot_conflict(
    robots,
    robot,
    x,
    y,
    yaw,
):
    """
    找出目前 robot 前方一定距離內，
    是否有另一台正在導航的 robot。

    回傳：
        other_robot
    或：
        None
    """

    closest_robot = None
    closest_distance = math.inf

    for other in robots.values():

        if other.robot_id == robot.robot_id:
            continue

        if not other.received_odom:
            continue

        if not other.navigating():
            continue

        (
            other_x,
            other_y,
            _,
        ) = other.map_pose()

        dx = other_x - x
        dy = other_y - y

        distance = math.hypot(
            dx,
            dy,
        )

        if distance > ROBOT_CONFLICT_DISTANCE:
            continue

        direction_to_other = math.atan2(
            dy,
            dx,
        )

        angle_error = normalize_angle(
            direction_to_other - yaw
        )

        if abs(angle_error) > ROBOT_CONFLICT_ANGLE:
            continue

        if distance < closest_distance:
            closest_distance = distance
            closest_robot = other

    return closest_robot


def is_head_on_conflict(
    robot,
    other,
    x,
    y,
    yaw,
):
    """
    判斷兩台正在移動的 robot 是否接近正面相遇。
    """

    if other is None:
        return False

    if not other.received_odom:
        return False

    if not other.navigating():
        return False

    (
        other_x,
        other_y,
        other_yaw,
    ) = other.map_pose()

    heading_difference = abs(
        normalize_angle(
            other_yaw - yaw
        )
    )

    if (
        heading_difference
        < HEAD_ON_MIN_OPPOSITE_ANGLE
    ):
        return False

    direction_other_to_me = math.atan2(
        y - other_y,
        x - other_x,
    )

    other_front_error = normalize_angle(
        direction_other_to_me
        - other_yaw
    )

    if (
        abs(other_front_error)
        > ROBOT_CONFLICT_ANGLE
    ):
        return False

    return True
