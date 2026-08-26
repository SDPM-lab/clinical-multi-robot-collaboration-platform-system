from .models import RobotState


def capability_matching(
    required_capabilities: list[str],
    robots: list[RobotState],
) -> list[RobotState]:
    """
    根據任務所需能力，
    篩選出具備全部 required capabilities 的機器人。

    條件：
        C_task ⊆ C_robot
    """

    required = set(
        required_capabilities
    )

    candidates = []

    for robot in robots:

        robot_capabilities = set(
            robot.capabilities
        )

        if required.issubset(
            robot_capabilities
        ):
            candidates.append(robot)

    return candidates