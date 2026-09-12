#!/usr/bin/env python3

import numpy as np

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.long_horizon_env import (
    LongHorizonHospitalRLEnv,
)

from rl_v2.system_reward import (
    SystemRewardConfig,
    calculate_system_reward,
)


def test_system_reward_components():

    result = calculate_system_reward(
        weighted_waiting_delta=300.0,
        travel_distance_delta=50.0,
        failed_task_delta=0,
    )

    # waiting:
    # 300 / 300 = 1.0
    #
    # distance:
    # 0.25 * 50 / 50 = 0.25
    #
    # reward = -1.25

    assert result.waiting_cost == 1.0

    assert result.distance_cost == 0.25

    assert result.failure_cost == 0.0

    assert result.reward == -1.25


def test_failure_penalty():

    result = calculate_system_reward(
        weighted_waiting_delta=0.0,
        travel_distance_delta=0.0,
        failed_task_delta=1,
    )

    assert result.reward == -10.0


def test_long_horizon_env_runs_full_episode():

    scenario = (
        generate_hospital_scenario(
            seed=6000,
            task_count=50,
        )
    )

    env = LongHorizonHospitalRLEnv(
        scenario=scenario,
        seed=6000,
    )

    observation, info = (
        env.reset(
            seed=6000
        )
    )

    terminated = False

    total_reward = 0.0

    step_count = 0

    while not terminated:

        mask = (
            env.action_masks()
        )

        feasible = (
            np.flatnonzero(
                mask
            )
        )

        assert len(feasible) > 0

        action = int(
            feasible[0]
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
            reward
        )

        assert (
            info[
                "system_weighted_waiting_delta"
            ]
            >=
            0.0
        )

        assert (
            info[
                "system_distance_delta"
            ]
            >=
            0.0
        )

        total_reward += reward

        step_count += 1

        assert step_count <= 50

    assert total_reward <= 0.0

    result = (
        env.get_simulation_result()
    )

    assert len(
        result.task_records
    ) == 50


def test_long_horizon_accounting_matches_episode_result():

    from rl_v2.reward import (
        get_priority_weight,
    )

    scenario = (
        generate_hospital_scenario(
            seed=6001,
            task_count=50,
        )
    )

    env = LongHorizonHospitalRLEnv(
        scenario=scenario,
        seed=6001,
    )

    observation, info = env.reset(
        seed=6001
    )

    terminated = False

    summed_waiting_delta = 0.0
    summed_distance_delta = 0.0

    while not terminated:

        mask = (
            env.action_masks()
        )

        feasible = (
            np.flatnonzero(
                mask
            )
        )

        action = int(
            feasible[0]
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

        summed_waiting_delta += (
            info[
                "system_weighted_waiting_delta"
            ]
        )

        summed_distance_delta += (
            info[
                "system_distance_delta"
            ]
        )

    result = (
        env.get_simulation_result()
    )

    expected_weighted_waiting = sum(
        record.waiting_time
        *
        get_priority_weight(
            record.priority
        )
        for record
        in result.task_records.values()
        if record.waiting_time
        is not None
    )

    expected_distance = sum(
        record.total_travel_distance
        for record
        in result.robot_records.values()
    )

    assert np.isclose(
        summed_waiting_delta,
        expected_weighted_waiting,
        rtol=1e-9,
        atol=1e-7,
    )

    assert np.isclose(
        summed_distance_delta,
        expected_distance,
        rtol=1e-9,
        atol=1e-7,
    )


def test_system_reward_stay_has_no_reassignment_penalty():

    result = calculate_system_reward(
        weighted_waiting_delta=0.0,
        travel_distance_delta=0.0,
        failed_task_delta=0,
        reassignment_delta=0,
    )

    assert np.isclose(
        result.reassignment_cost,
        0.0,
    )


def test_system_reward_stay_has_no_reassignment_penalty():

    result = calculate_system_reward(
        weighted_waiting_delta=0.0,
        travel_distance_delta=0.0,
        failed_task_delta=0,
        reassignment_delta=0,
    )

    assert np.isclose(
        result.reassignment_cost,
        0.0,
    )

def test_system_reward_reassignment_penalty():

    result = calculate_system_reward(
        weighted_waiting_delta=0.0,
        travel_distance_delta=0.0,
        failed_task_delta=0,
        reassignment_delta=1,
        config=SystemRewardConfig(
            reassignment_penalty=0.02,
        ),
    )

    assert np.isclose(
        result.reassignment_cost,
        0.02,
    )

    assert np.isclose(
        result.reward,
        -0.02,
    )