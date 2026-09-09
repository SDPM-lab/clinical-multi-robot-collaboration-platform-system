#!/usr/bin/env python3

import random

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from rl.hospital_gym_env import (
    HospitalGymEnv,
)

from rl.rl_config import (
    TRAINING_SEEDS,
    TRAIN_TASK_COUNTS,
    TRAIN_TASK_COUNT_WEIGHTS,
    TRAIN_LOADS,
)


# ==========================================================
# Randomized Training Environment
#
# Multi-task-count + Multi-load Training vNext
#
# 每次 reset():
#
# 1. 隨機選 Training Seed
# 2. 隨機選 Task Count
# 3. 隨機選 Load
# 4. 重新產生 Scenario
# 5. 建立新的 Hospital Core Environment
#
# PPO 不再只看到：
#
# 20 tasks + medium load
#
# 而是：
#
# 20 / 50 / 100 tasks
#
# ×
#
# low / medium / high load
# ==========================================================

class RandomizedHospitalGymEnv(
    HospitalGymEnv
):

    def __init__(
        self,
        training_seeds=None,
        task_counts=None,
        task_count_weights=None,
        loads=None,
        enable_dynamic_reassignment: bool = False,
    ):

        # ==================================================
        # Training Seeds
        # ==================================================

        if training_seeds is None:

            training_seeds = (
                TRAINING_SEEDS
            )

        # ==================================================
        # Task Counts
        # ==================================================

        if task_counts is None:

            task_counts = (
                TRAIN_TASK_COUNTS
            )


        # ==================================================
        # Task Count Weights
        # ==================================================

        if task_count_weights is None:

            task_count_weights = (
                TRAIN_TASK_COUNT_WEIGHTS
            )

        # ==================================================
        # Loads
        # ==================================================

        if loads is None:

            loads = (
                TRAIN_LOADS
            )

        self.training_seeds = list(
            training_seeds
        )

        self.task_counts = list(
            task_counts
        )

        self.task_count_weights = list(
            task_count_weights
        )

        self.loads = list(
            loads
        )

        # ==================================================
        # Dynamic Reassignment Mode
        # ==================================================

        self.enable_dynamic_reassignment = (
            enable_dynamic_reassignment
        )

        # ==================================================
        # Basic Validation
        # ==================================================

        if not self.training_seeds:

            raise ValueError(
                "training_seeds must not be empty"
            )

        if not self.task_counts:

            raise ValueError(
                "task_counts must not be empty"
            )

        if (
            len(self.task_counts)
            !=
            len(self.task_count_weights)
        ):

            raise ValueError(
                "task_counts and task_count_weights "
                "must have the same length"
            )

        if any(
            weight <= 0
            for weight
            in self.task_count_weights
        ):

            raise ValueError(
                "task_count_weights must all be positive"
            )

        if not self.loads:

            raise ValueError(
                "loads must not be empty"
            )

        # ==================================================
        # RNG
        # ==================================================

        self.scenario_rng = (
            random.Random(
                12345
            )
        )

        # ==================================================
        # Current Scenario Info
        # ==================================================

        self.current_scenario_seed = (
            self.training_seeds[
                0
            ]
        )

        self.current_task_count = (
            self.task_counts[
                0
            ]
        )

        self.current_load = (
            self.loads[
                0
            ]
        )

        # ==================================================
        # First Scenario
        #
        # 只是初始化 observation_space / action_space
        # ==================================================

        first_scenario = (
            generate_random_scenario(

                task_count=(
                    self.current_task_count
                ),

                seed=(
                    self.current_scenario_seed
                ),

                load=(
                    self.current_load
                ),

                battery_profile=(
                    BATTERY_PROFILE
                ),

                capability_profile=(
                    CAPABILITY_PROFILE
                ),
            )
        )

        super().__init__(

            scenario=(
                first_scenario
            ),

            robot_speed=(
                ROBOT_SPEED
            ),

            service_time=(
                SERVICE_TIME
            ),

            enable_dynamic_reassignment=(
                self.enable_dynamic_reassignment
            ),
        )


    # ======================================================
    # Sample Training Condition
    # ======================================================

    def _sample_training_condition(
        self,
    ):

        scenario_seed = (
            self.scenario_rng.choice(
                self.training_seeds
            )
        )

        task_count = (
            self.scenario_rng.choices(

                population=(
                    self.task_counts
                ),

                weights=(
                    self.task_count_weights
                ),

                k=1,
            )[0]
        )

        load = (
            self.scenario_rng.choice(
                self.loads
            )
        )

        return (
            scenario_seed,
            task_count,
            load,
        )


    # ======================================================
    # Generate New Scenario
    # ======================================================

    def _generate_new_scenario(
        self,
    ):

        (
            scenario_seed,
            task_count,
            load,
        ) = (
            self._sample_training_condition()
        )

        # ==================================================
        # Save Current Condition
        # ==================================================

        self.current_scenario_seed = (
            scenario_seed
        )

        self.current_task_count = (
            task_count
        )

        self.current_load = (
            load
        )

        # ==================================================
        # Generate Scenario
        # ==================================================

        scenario = (
            generate_random_scenario(

                task_count=(
                    task_count
                ),

                seed=(
                    scenario_seed
                ),

                load=(
                    load
                ),

                battery_profile=(
                    BATTERY_PROFILE
                ),

                capability_profile=(
                    CAPABILITY_PROFILE
                ),
            )
        )

        return (
            scenario
        )


    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self,
        *,
        seed=None,
        options=None,
    ):

        # ==================================================
        # Gymnasium Seed
        # ==================================================

        if seed is not None:

            self.scenario_rng.seed(
                seed
            )

        # ==================================================
        # Random Scenario
        # ==================================================

        scenario = (
            self._generate_new_scenario()
        )

        # ==================================================
        # Rebuild Core Environment
        # ==================================================

        from rl.hospital_env import (
            HospitalRLEnv,
        )

        self.core_env = (
            HospitalRLEnv(

                scenario=(
                    scenario
                ),

                robot_speed=(
                    ROBOT_SPEED
                ),

                service_time=(
                    SERVICE_TIME
                ),

                enable_dynamic_reassignment=(
                    self.enable_dynamic_reassignment
                ),
            )
        )

        observation = (
            self.core_env.reset()
        )

        # ==================================================
        # Info
        # ==================================================

        info = {

            "scenario_seed":
                self.current_scenario_seed,

            "task_count":
                self.current_task_count,

            "load":
                self.current_load,

            "current_time":
                self.core_env.current_time,

            "completed_tasks":
                self.core_env.completed_task_count,
        }

        return (
            observation,
            info,
        )