#!/usr/bin/env python3

import random

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.env import (
    HospitalRLEnv,
)


class SeededHospitalRLEnv(
    HospitalRLEnv
):
    """
    PPO Training Environment。

    每次 reset() 都重新從指定的
    scenario seed pool 中抽一個 seed，
    避免 PPO 只記住單一 Scenario。
    """

    def __init__(
        self,
        scenario_seeds,
        sampling_seed: int = 0,
        task_count: int = 50,
        mean_interarrival_seconds: float = 20.0,
        robot_speed_mps: float = 1.0,
        service_time_seconds: float = 30.0,
    ):

        self.scenario_seeds = tuple(
            int(seed)
            for seed in scenario_seeds
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
            seed=sampling_seed,
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

        # Gymnasium / SB3 第一次可能傳入 seed。
        # 這裡只用來控制「Scenario 抽樣順序」。
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
