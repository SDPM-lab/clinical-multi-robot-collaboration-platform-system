#!/usr/bin/env python3

import numpy as np
import gymnasium as gym

from gymnasium import spaces

from rl.hospital_env import (
    HospitalRLEnv,
)


# ==========================================================
# Gymnasium Wrapper
#
# 將 HospitalRLEnv Core
# 包裝成 Stable-Baselines3 可以使用的標準介面。
# ==========================================================

class HospitalGymEnv(
    gym.Env
):

    metadata = {
        "render_modes": [],
    }


    def __init__(
        self,
        scenario,
        robot_speed: float = 1.0,
        service_time: float = 5.0,
    ):

        super().__init__()

        # ==================================================
        # Core Environment
        # ==================================================

        self.core_env = (
            HospitalRLEnv(

                scenario=scenario,

                robot_speed=(
                    robot_speed
                ),

                service_time=(
                    service_time
                ),
            )
        )

        # ==================================================
        # Action Space
        #
        # 0 -> robot_1
        # 1 -> robot_2
        # 2 -> robot_3
        # ==================================================

        self.action_space = (
            spaces.Discrete(
                self.core_env.robot_count
            )
        )

        # ==================================================
        # Observation Space
        #
        # Task features = 6
        #
        # 每台 Robot features = 9
        #
        # 1. projected_x
        # 2. projected_y
        # 3. battery
        # 4. workload_before_task
        # 5. distance_to_source
        # 6. capability_match
        # 7. queue_length_before_task
        # 8. completed_tasks ratio
        #
        # 3 robots:
        #
        # 6 + 3 * 9
        # = 33
        # ==================================================

        observation_size = (
            6
            +
            self.core_env.robot_count * 9
        )

        self.observation_space = (
            spaces.Box(

                low=0.0,

                high=1.0,

                shape=(
                    observation_size,
                ),

                dtype=np.float32,
            )
        )


    # ======================================================
    # Reset
    #
    # Gymnasium 標準：
    #
    # return
    # observation, info
    # ======================================================

    def reset(
        self,
        *,
        seed=None,
        options=None,
    ):

        super().reset(
            seed=seed
        )

        observation = (
            self.core_env.reset()
        )

        info = {

            "current_time":
                self.core_env.current_time,

            "completed_tasks":
                self.core_env.completed_task_count,
        }

        return (
            observation,
            info,
        )


    # ======================================================
    # Step
    #
    # Gymnasium 標準：
    #
    # observation
    # reward
    # terminated
    # truncated
    # info
    # ======================================================

    def step(
        self,
        action,
    ):

        action = int(
            action
        )

        (
            observation,
            reward,
            done,
            info,
        ) = (
            self.core_env.step(
                action
            )
        )

        terminated = bool(
            done
        )

        # 第一版沒有 Time Limit
        truncated = False

        if terminated:

            info[
                "simulation_end_time"
            ] = (
                self.core_env
                .get_simulation_end_time()
            )

            info[
                "total_reward"
            ] = (
                self.core_env.total_reward
            )

            info[
                "completed_tasks"
            ] = (
                self.core_env
                .completed_task_count
            )

        return (
            observation,
            float(
                reward
            ),
            terminated,
            truncated,
            info,
        )


    # ======================================================
    # Action Mask
    #
    # sb3-contrib MaskablePPO
    # 會讀取這個函式。
    # ======================================================

    def action_masks(
        self,
    ):

        return (
            self.core_env
            .action_masks()
        )