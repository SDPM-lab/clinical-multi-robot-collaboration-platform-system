#!/usr/bin/env python3

import numpy as np

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.env import (
    HospitalRLEnv,
)

from rl_v2.observation import (
    get_observation_size,
)


def test_rl_env_seed6000_runs_full_episode():

    scenario = (
        generate_hospital_scenario(
            seed=6000,
            task_count=50,
        )
    )

    env = HospitalRLEnv(
        scenario=scenario,
        seed=6000,
    )

    observation, info = (
        env.reset(
            seed=6000
        )
    )

    assert observation.shape == (
        get_observation_size(4),
    )

    assert observation.dtype == (
        np.float32
    )

    decision_count = 0

    terminated = False

    while not terminated:

        mask = (
            env.action_masks()
        )

        feasible_actions = (
            np.flatnonzero(
                mask
            )
        )

        assert (
            len(feasible_actions)
            >
            0
        )

        # Smoke test 不測 Policy。
        # 永遠選第一個 feasible action。
        action = int(
            feasible_actions[0]
        )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        assert truncated is False

        assert np.isfinite(
            observation
        ).all()

        assert np.isfinite(
            reward
        )

        decision_count += 1

        assert (
            decision_count
            <=
            50
        )

    result = (
        env.get_simulation_result()
    )

    statuses = {
        record.status
        for record
        in result
        .task_records
        .values()
    }

    assert statuses.issubset(
        {
            "completed",
            "failed",
        }
    )

    assert len(
        result.task_records
    ) == 50
