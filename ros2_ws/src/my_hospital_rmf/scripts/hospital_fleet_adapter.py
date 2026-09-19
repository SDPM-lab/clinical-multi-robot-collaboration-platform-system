#!/usr/bin/env python3

import json
import sys

from std_msgs.msg import String

from rmf_demos_fleet_adapter import fleet_adapter as official_fleet_adapter


# ============================================================
# Hospital Fleet Adapter
#
# 基於官方 rmf_demos_fleet_adapter。
#
# 額外功能：
#   1. 記錄 RMF 每次 navigate() 的 named destination
#   2. 等底層 robot 回報該 cmd_id 完成
#   3. 發布：
#
#      /hospital_rmf_activity_completed
#
#   Scheduler 之後會再利用：
#
#      completed destination
#      ==
#      running_task.destination
#
#   判斷整筆 Hospital Task 是否完成。
# ============================================================


_original_navigate = official_fleet_adapter.RobotAdapter.navigate
_original_update = official_fleet_adapter.RobotAdapter.update


def _ensure_hospital_completion_state(self):

    if not hasattr(
        self,
        "_hospital_completion_pub",
    ):
        self._hospital_completion_pub = (
            self.node.create_publisher(
                String,
                "/hospital_rmf_activity_completed",
                10,
            )
        )

    if not hasattr(
        self,
        "_hospital_command_destinations",
    ):
        self._hospital_command_destinations = {}


def hospital_navigate(
    self,
    destination,
    execution,
):

    _ensure_hospital_completion_state(
        self
    )

    destination_name = getattr(
        destination,
        "name",
        None,
    )

    destination_map = getattr(
        destination,
        "map",
        None,
    )

    destination_position = getattr(
        destination,
        "position",
        None,
    )

    public_attrs = [
        attr
        for attr in dir(destination)
        if not attr.startswith("_")
    ]

    # --------------------------------------------------------
    # 先讓官方 adapter 做原本的事情。
    #
    # 官方 navigate() 內：
    #
    #   self.cmd_id += 1
    #
    # 所以 return 後的 self.cmd_id
    # 就是這一筆 navigation command 的 ID。
    # --------------------------------------------------------

    result = _original_navigate(
        self,
        destination,
        execution,
    )

    cmd_id = self.cmd_id

    self._hospital_command_destinations[
        cmd_id
    ] = {
        "destination": destination_name,
        "map": destination_map,
    }

    self.node.get_logger().info(
        "[HOSPITAL_NAVIGATE] "
        f"robot={self.name}, "
        f"cmd_id={cmd_id}, "
        f"destination_name="
        f"{destination_name!r}, "
        f"map={destination_map!r}, "
        f"position={destination_position}, "
        f"attrs={public_attrs}"
    )

    return result


def hospital_update(
    self,
    state,
    data,
):

    _ensure_hospital_completion_state(
        self
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # 一定要在 official update() 前檢查。
    #
    # 因為官方邏輯在 command 完成後會：
    #
    #   self.execution.finished()
    #   self.execution = None
    #
    # 所以我們先把這次完成資訊保存下來。
    # --------------------------------------------------------

    completed_cmd_id = None
    completion_info = None

    if self.execution is not None:

        cmd_id = self.cmd_id

        if data.is_command_completed(
            cmd_id
        ):
            completed_cmd_id = cmd_id

            completion_info = (
                self
                ._hospital_command_destinations
                .get(
                    cmd_id
                )
            )

    # --------------------------------------------------------
    # 完全保留官方 lifecycle。
    #
    # 這裡會正常呼叫：
    #
    #   execution.finished()
    #
    # RMF 才會繼續下一段 navigation / phase。
    # --------------------------------------------------------

    result = _original_update(
        self,
        state,
        data,
    )

    # --------------------------------------------------------
    # 官方確認 command completed 後，
    # 才發布 Hospital completion event。
    # --------------------------------------------------------

    if (
        completed_cmd_id is not None
        and completion_info is not None
    ):

        payload = {
            "robot_id": self.name,
            "cmd_id": (
                completed_cmd_id
            ),
            "destination": (
                completion_info[
                    "destination"
                ]
            ),
            "map": (
                completion_info[
                    "map"
                ]
            ),
        }

        msg = String()

        msg.data = json.dumps(
            payload,
            ensure_ascii=False,
        )

        self._hospital_completion_pub\
            .publish(
                msg
            )

        self.node.get_logger().info(
            "[HOSPITAL_ACTIVITY_COMPLETED] "
            f"{msg.data}"
        )

        self._hospital_command_destinations\
            .pop(
                completed_cmd_id,
                None,
            )

    return result


# ============================================================
# Monkey patch
# ============================================================

official_fleet_adapter\
    .RobotAdapter\
    .navigate = hospital_navigate

official_fleet_adapter\
    .RobotAdapter\
    .update = hospital_update


if __name__ == "__main__":
    official_fleet_adapter.main(
        sys.argv
    )
