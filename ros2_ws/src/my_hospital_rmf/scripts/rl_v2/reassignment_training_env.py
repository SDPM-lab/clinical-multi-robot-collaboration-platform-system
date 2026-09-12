#!/usr/bin/env python3

import random

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.reassignment_env import (
    ReassignmentHospitalRLEnv,
)

from rl_v2.system_reward import (
    SystemRewardConfig,
)

from rl_v2.reassignment_shaping import (
    ReassignmentShapingConfig,
)


class SeededReassignmentHospitalRLEnv(
    ReassignmentHospitalRLEnv
):
    """
    Dedicated Reassignment PPO
    多 Scenario Training Environment。

    Initial Assignment：
        Frozen Static Long-Horizon PPO

    RL Agent：
        只處理 Waiting Task Reassignment
    """

    def __init__(
        self,
        assignment_policy,
        scenario_seeds,
        sampling_seed: int = 0,
        task_count: int = 50,
        mean_interarrival_seconds: float = 20.0,
        robot_speed_mps: float = 1.0,
        service_time_seconds: float = 30.0,
        reward_config: (
            SystemRewardConfig
            |
            None
        ) = None,
        shaping_config: (
            ReassignmentShapingConfig
            |
            None
        ) = None,
    ):

        self.scenario_seeds = tuple(
            int(seed)
            for seed
            in scenario_seeds
        )

        if not self.scenario_seeds:

            raise ValueError(
                "scenario_seeds cannot be empty"
            )

        self.scenario_rng = (
            random.Random(
                sampling_seed
            )
        )

        self.task_count = int(
            task_count
        )

        self.mean_interarrival_seconds = float(
            mean_interarrival_seconds
        )

        self.robot_speed_mps = float(
            robot_speed_mps
        )

        self.service_time_seconds = float(
            service_time_seconds
        )

        self.last_scenario_seed = None

        initial_seed = (
            self.scenario_seeds[0]
        )

        initial_scenario = (
            self._generate_scenario(
                initial_seed
            )
        )

        super().__init__(
            scenario=initial_scenario,
            assignment_policy=assignment_policy,
            seed=initial_seed,
            reward_config=reward_config,
            shaping_config=shaping_config,
        )


    def _generate_scenario(
        self,
        scenario_seed: int,
    ):

        return (
            generate_hospital_scenario(
                seed=scenario_seed,
                task_count=(
                    self.task_count
                ),
                mean_interarrival_seconds=(
                    self
                    .mean_interarrival_seconds
                ),
                robot_speed_mps=(
                    self.robot_speed_mps
                ),
                service_time_seconds=(
                    self.service_time_seconds
                ),
            )
        )


    def reset(
        self,
        *,
        seed=None,
        options=None,
    ):

        if seed is not None:

            self.scenario_rng.seed(
                int(seed)
            )

        scenario_seed = (
            self.scenario_rng.choice(
                self.scenario_seeds
            )
        )

        self.last_scenario_seed = (
            scenario_seed
        )

        self.original_scenario = (
            self._generate_scenario(
                scenario_seed
            )
        )

        observation, info = (
            super().reset(
                seed=scenario_seed,
                options=options,
            )
        )

        info[
            "scenario_seed"
        ] = scenario_seed

        return (
            observation,
            info,
        )
