#!/usr/bin/env python3

from rl_v2.env import (
    HospitalRLEnv,
)

from rl_v2.system_reward import (
    calculate_system_reward,
)


class LongHorizonHospitalRLEnv(
    HospitalRLEnv
):
    """
    與原本 HospitalRLEnv 使用相同：

    - Observation
    - Action Mask
    - Simulator
    - Assignment semantics

    唯一差別：

    Reward 不再看單一 Task 的 projected score。

    改成：
        此 action 之後，
        到下一個 RL decision 前，
        系統真正累積的 waiting / distance / failure。
    """

    # ======================================================
    # Helpers
    # ======================================================

    def _total_travel_distance(
        self,
    ) -> float:

        if self.kernel is None:
            return 0.0

        return sum(
            record.total_travel_distance
            for record
            in self.kernel
            .robot_records
            .values()
        )


    def _failed_task_count(
        self,
    ) -> int:

        if self.kernel is None:
            return 0

        return sum(
            1
            for record
            in self.kernel
            .task_records
            .values()
            if record.status
            ==
            "failed"
        )


    # ======================================================
    # Step
    # ======================================================

    def step(
        self,
        action,
    ):

        if self.kernel is None:

            raise RuntimeError(
                "Call reset() first"
            )

        # --------------------------------------------------
        # Snapshot BEFORE action
        # --------------------------------------------------

        waiting_before = (
            self.kernel
            .accumulated_priority_waiting_cost
        )

        distance_before = (
            self._total_travel_distance()
        )

        failed_before = (
            self._failed_task_count()
        )

        # --------------------------------------------------
        # 執行原本 assignment + simulator progression。
        #
        # old_reward 是舊 projected reward，
        # 僅保留做 debug，不拿來訓練。
        # --------------------------------------------------

        (
            observation,
            old_reward,
            terminated,
            truncated,
            info,
        ) = super().step(
            action
        )

        # --------------------------------------------------
        # Snapshot AFTER simulator reaches next decision
        # --------------------------------------------------

        waiting_after = (
            self.kernel
            .accumulated_priority_waiting_cost
        )

        distance_after = (
            self._total_travel_distance()
        )

        failed_after = (
            self._failed_task_count()
        )

        waiting_delta = (
            waiting_after
            -
            waiting_before
        )

        distance_delta = (
            distance_after
            -
            distance_before
        )

        failed_delta = (
            failed_after
            -
            failed_before
        )

        reward_breakdown = (
            calculate_system_reward(
                weighted_waiting_delta=(
                    waiting_delta
                ),
                travel_distance_delta=(
                    distance_delta
                ),
                failed_task_delta=(
                    failed_delta
                ),
            )
        )

        # --------------------------------------------------
        # Debug information
        # --------------------------------------------------

        info[
            "legacy_projected_reward"
        ] = float(
            old_reward
        )

        info[
            "system_weighted_waiting_delta"
        ] = (
            reward_breakdown
            .weighted_waiting_delta
        )

        info[
            "system_distance_delta"
        ] = (
            reward_breakdown
            .travel_distance_delta
        )

        info[
            "system_failed_delta"
        ] = (
            reward_breakdown
            .failed_task_delta
        )

        info[
            "system_waiting_cost"
        ] = (
            reward_breakdown
            .waiting_cost
        )

        info[
            "system_distance_cost"
        ] = (
            reward_breakdown
            .distance_cost
        )

        info[
            "system_failure_cost"
        ] = (
            reward_breakdown
            .failure_cost
        )

        return (
            observation,
            reward_breakdown.reward,
            terminated,
            truncated,
            info,
        )
