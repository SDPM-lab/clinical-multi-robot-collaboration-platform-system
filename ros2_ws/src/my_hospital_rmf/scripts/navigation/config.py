import math


# ============================================================
# Waypoint follower
# ============================================================

CONTROL_PERIOD = 0.1

ARRIVE_DISTANCE = 0.25

GOAL_APPROACH_DISTANCE = 0.75
GOAL_APPROACH_MAX_SPEED = 0.12
GOAL_EMERGENCY_STOP_DISTANCE = 0.30

FINAL_YAW_TOLERANCE = 0.12

ROTATE_FIRST_THRESHOLD = 0.30

LINEAR_KP = 0.7
ANGULAR_KP = 1.5

MAX_LINEAR_SPEED = 0.7
MAX_ANGULAR_SPEED = 0.8

MIN_LINEAR_SPEED = 0.06


# ============================================================
# LiDAR obstacle avoidance
# ============================================================

OBSTACLE_SLOW_DISTANCE = 0.8
OBSTACLE_STOP_DISTANCE = 0.55

AVOID_TURN_ANGLE = math.radians(60.0)
AVOID_TURN_TOLERANCE = math.radians(8.0)

AVOID_FORWARD_DISTANCE = 1.2
AVOID_LINEAR_SPEED = 0.30
AVOID_EXTRA_TURN_ANGLE = math.radians(30.0)

SIDE_SAFE_DISTANCE = 0.45

SIDE_CORRECTION_KP = 2.0
SIDE_MAX_ANGULAR_SPEED = 0.50

RECOVER_MIN_SIDE_CLEARANCE = 0.30

BYPASS_PATH_KP = 0.5
BYPASS_PATH_MAX_ANGULAR_SPEED = 0.20


# ============================================================
# Robot-to-robot right-of-way
# ============================================================

ROBOT_CONFLICT_DISTANCE = 1.80
ROBOT_RESUME_DISTANCE = 2.00
ROBOT_CONFLICT_ANGLE = math.radians(60.0)


# ============================================================
# Head-on reciprocal avoidance
# ============================================================

HEAD_ON_MIN_OPPOSITE_ANGLE = math.radians(150.0)

HEAD_ON_TURN_ANGLE = math.radians(35.0)
HEAD_ON_FORWARD_DISTANCE = 1.00
HEAD_ON_SHIFT_DISTANCE = 0.55

HEAD_ON_WALL_MIN_DISTANCE = 0.45
HEAD_ON_BEHIND_MARGIN = 0.20
HEAD_ON_LANE_TOLERANCE = 0.10
HEAD_ON_CLEAR_DISTANCE = 1.40

HEAD_ON_LINEAR_SPEED = 0.18
HEAD_ON_MAX_ANGULAR_SPEED = 0.30
