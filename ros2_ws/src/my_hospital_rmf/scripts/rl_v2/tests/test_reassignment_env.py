#!/usr/bin/env python3

import numpy as np

from experiment_v2.metrics import (
    calculate_metrics,
)

from experiment_v2.scenario_generator import (
    generate_hospital_scenario,
)

from rl_v2.dynamic_action_mask import (
    DECISION_REASSIGNMENT,
)

from rl_v2.reassignment_env import (
    ReassignmentHospitalRLEnv,
)

from rl_v2.reassignment_shaping import (
    ReassignmentShapingConfig,
)


class FirstFeasibleAssignmentPolicy:

    def predict(
        self,
        observation,
        action_masks=None,
        deterministic=True,
    ):

        assert observation.shape == (
            49,
        )

        feasible = np.flatnonzero(
            action_masks
        )

        assert len(feasible) > 0

        return (
            int(
                feasible[0]
            ),
            None,
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

    return (
        ReassignmentHospitalRLEnv(
            scenario=scenario,
            assignment_policy=(
                FirstFeasibleAssignmentPolicy()
            ),
            seed=seed,
        )
    )


def first_feasible(
    mask,
):

    feasible = np.flatnonzero(
        mask
    )

    assert len(feasible) > 0

    return int(
        feasible[0]
    )


def test_reset_exposes_only_reassignment():

    env = make_env()

    observation, info = (
        env.reset()
    )

    assert observation.shape == (
        54,
    )

    assert (
        env.kernel
        .current_decision_type
        ==
        DECISION_REASSIGNMENT
    )

    assert (
        info[
            "automatic_assignment_count"
        ]
        >=
        1
    )


def test_agent_step_is_reassignment_only():

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

    assert (
        info[
            "decision_type"
        ]
        ==
        DECISION_REASSIGNMENT
    )

    if not terminated:

        assert (
            env.kernel
            .current_decision_type
            ==
            DECISION_REASSIGNMENT
        )

    assert observation.shape == (
        54,
    )


def test_stay_is_valid_reassignment_action():

    env = make_env()

    observation, info = (
        env.reset()
    )

    current_robot = (
        env.kernel
        .current_previous_robot
    )

    assert current_robot is not None

    action = (
        env.robot_ids.index(
            current_robot
        )
    )

    mask = env.action_masks()

    if bool(
        mask[action]
    ):

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )

        assert (
            info[
                "changed"
            ]
            is False
        )

        assert (
            info[
                "selected_robot"
            ]
            ==
            current_robot
        )


def test_reassignment_env_runs_full_episode():

    env = make_env(
        seed=6001
    )

    observation, info = (
        env.reset()
    )

    rl_steps = 0

    while True:

        current_robot = (
            env.kernel
            .current_previous_robot
        )

        mask = (
            env.action_masks()
        )

        if (
            current_robot is not None
        ):

            stay_action = (
                env.robot_ids.index(
                    current_robot
                )
            )

        else:

            stay_action = -1

        if (
            stay_action >= 0
            and
            bool(
                mask[
                    stay_action
                ]
            )
        ):

            action = stay_action

        else:

            action = (
                first_feasible(
                    mask
                )
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

        rl_steps += 1

        assert rl_steps < 10000

        if terminated:
            break

        assert (
            env.kernel
            .current_decision_type
            ==
            DECISION_REASSIGNMENT
        )

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

    # Initial Assignment 仍然全部存在，
    # 只是沒有暴露成 Dedicated PPO step。
    assignment_records = [
        decision
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "assignment"
        )
    ]

    reassignment_records = [
        decision
        for decision
        in result.decision_records
        if (
            decision.decision_type
            ==
            "reassignment"
        )
    ]

    assert len(
        assignment_records
    ) == 50

    assert (
        rl_steps
        ==
        len(
            reassignment_records
        )
    )

    assert (
        metrics.max_cascade_depth
        <=
        1
    )

def test_reassignment_shaping_disabled_by_default():

    env = make_env(
        seed=7309
    )

    observation, info = (
        env.reset()
    )

    current_robot = (
        env.kernel
        .current_previous_robot
    )

    action = (
        env.robot_ids.index(
            current_robot
        )
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

    assert np.isclose(
        info[
            "reassignment_shaping_reward"
        ],
        0.0,
    )

def test_reassignment_shaping_stay_is_zero():

    scenario = (
        generate_hospital_scenario(
            seed=7309,
            task_count=50,
        )
    )

    env = (
        ReassignmentHospitalRLEnv(
            scenario=scenario,
            assignment_policy=(
                FirstFeasibleAssignmentPolicy()
            ),
            seed=7309,
            shaping_config=(
                ReassignmentShapingConfig(
                    shaping_weight=0.25,
                )
            ),
        )
    )

    observation, info = (
        env.reset()
    )

    current_robot = (
        env.kernel
        .current_previous_robot
    )

    action = (
        env.robot_ids.index(
            current_robot
        )
    )

    assert bool(
        env.action_masks()[
            action
        ]
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

    assert np.isclose(
        info[
            "reassignment_shaping_reward"
        ],
        0.0,
    )

    assert np.isclose(
        info[
            "reassignment_raw_improvement"
        ],
        0.0,
    )

def test_reassignment_move_has_projected_shaping():

    scenario = (
        generate_hospital_scenario(
            seed=7309,
            task_count=50,
        )
    )

    env = (
        ReassignmentHospitalRLEnv(
            scenario=scenario,
            assignment_policy=(
                FirstFeasibleAssignmentPolicy()
            ),
            seed=7309,
            shaping_config=(
                ReassignmentShapingConfig(
                    shaping_weight=0.25,
                )
            ),
        )
    )

    observation, info = (
        env.reset()
    )

    current_robot = (
        env.kernel
        .current_previous_robot
    )

    mask = (
        env.action_masks()
    )

    alternative_actions = [
        index
        for index, feasible
        in enumerate(mask)
        if (
            feasible
            and
            env.robot_ids[index]
            !=
            current_robot
        )
    ]

    assert alternative_actions

    action = (
        alternative_actions[0]
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
        info[
            "reassignment_shaping_reward"
        ]
    )

    assert np.isfinite(
        info[
            "reassignment_raw_improvement"
        ]
    )

    assert (
        info[
            "reassignment_current_projected_cost"
        ]
        is not None
    )

    assert (
        info[
            "reassignment_selected_projected_cost"
        ]
        is not None
    )