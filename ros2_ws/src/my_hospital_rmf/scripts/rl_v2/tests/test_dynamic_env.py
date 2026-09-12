#!/usr/bin/env python3

import numpy as np

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.dynamic_env import (
    DynamicHospitalRLEnv,
)

from rl_v2.dynamic_action_mask import (
    DECISION_ASSIGNMENT,
    DECISION_REASSIGNMENT,
)


def make_env(
    seed: int = 6000,
):

    scenario = (
        generate_hospital_scenario(
            seed=seed,
            task_count=50,
        )
    )

    return DynamicHospitalRLEnv(
        scenario=scenario,
        seed=seed,
    )


def first_feasible(
    mask,
):

    indices = np.flatnonzero(
        mask
    )

    assert len(indices) > 0

    return int(
        indices[0]
    )


def test_dynamic_observation_is_54():

    env = make_env()

    observation, info = (
        env.reset()
    )

    assert observation.shape == (
        54,
    )

    assert (
        info[
            "decision_type"
        ]
        ==
        DECISION_ASSIGNMENT
    )


def test_reassignment_observation_marks_current_robot():

    env = make_env()

    observation, info = (
        env.reset()
    )

    action = first_feasible(
        env.action_masks()
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

    assert not terminated

    assert (
        info[
            "next_decision_type"
        ]
        ==
        DECISION_REASSIGNMENT
    )

    assert observation.shape == (
        54,
    )

    # Task feature 10 維。
    #
    # 每台 robot 11 維，
    # is_current_robot 是該 block 最後一維。
    current_flags = []

    for index in range(
        len(env.robot_ids)
    ):

        flag_index = (
            10
            +
            index * 11
            +
            10
        )

        current_flags.append(
            observation[
                flag_index
            ]
        )

    assert np.isclose(
        sum(current_flags),
        1.0,
    )


def test_select_current_robot_means_stay():

    env = make_env()

    observation, info = (
        env.reset()
    )

    assignment_action = (
        first_feasible(
            env.action_masks()
        )
    )

    (
        observation,
        reward,
        terminated,
        truncated,
        info,
    ) = env.step(
        assignment_action
    )

    assert (
        info[
            "next_decision_type"
        ]
        ==
        DECISION_REASSIGNMENT
    )

    current_robot = (
        info[
            "next_current_robot"
        ]
    )

    current_action = (
        env.robot_ids.index(
            current_robot
        )
    )

    assert bool(
        env.action_masks()[
            current_action
        ]
    )

    (
        observation,
        reward,
        terminated,
        truncated,
        info,
    ) = env.step(
        current_action
    )

    assert (
        info[
            "decision_type"
        ]
        ==
        DECISION_REASSIGNMENT
    )

    assert (
        info[
            "previous_robot"
        ]
        ==
        current_robot
    )

    assert (
        info[
            "selected_robot"
        ]
        ==
        current_robot
    )

    assert (
        info[
            "changed"
        ]
        is False
    )


def test_running_task_is_never_reassignment_target():

    env = make_env()

    observation, info = (
        env.reset()
    )

    step_count = 0

    while True:

        if (
            env.kernel
            .current_decision_type
            ==
            DECISION_REASSIGNMENT
        ):

            task = (
                env.kernel
                .current_task
            )

            assert task is not None

            for runtime in (
                env.kernel
                .runtimes
                .values()
            ):

                assert not (
                    runtime.running_task
                    is not None
                    and
                    runtime
                    .running_task
                    .task_id
                    ==
                    task.task_id
                )

        action = first_feasible(
            env.action_masks()
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

        assert not truncated

        step_count += 1

        if terminated:
            break

        assert step_count < 10000


def test_dynamic_env_runs_full_episode():

    env = make_env(
        seed=6001
    )

    observation, info = (
        env.reset()
    )

    step_count = 0

    while True:

        mask = (
            env.action_masks()
        )

        action = first_feasible(
            mask
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

        assert np.isfinite(
            reward
        )

        assert not truncated

        step_count += 1

        assert step_count < 10000

        if terminated:
            break

    result = (
        env.get_simulation_result()
    )

    metrics = (
        calculate_metrics(
            result
        )
    )

    assert (
        metrics.total_tasks
        ==
        50
    )

    assert (
        metrics.max_cascade_depth
        <=
        1
    )

    assert (
        metrics.reassignment_decision_count
        >
        0
    )
