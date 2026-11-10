from __future__ import annotations

import numpy as np
import pytest

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)


def make_env(
    *,
    seed: int = 3001,
    workload_multiplier: float = 0.25,
    enable_battery_model: bool = False,
):

    return HospitalSchedulingEnv(
        seed=seed,
        fleet_configuration=(
            2,
            2,
            3,
        ),
        workload_multiplier=(
            workload_multiplier
        ),
        enable_battery_model=(
            enable_battery_model
        ),
    )


def first_feasible_action(
    env: HospitalSchedulingEnv,
) -> int:

    mask = (
        env.action_masks()
    )

    indices = np.flatnonzero(
        mask
    )

    assert len(
        indices
    ) > 0

    return int(
        indices[0]
    )


def test_observation_space_shape():

    env = make_env()

    assert (
        env.observation_space.shape
        == (
            84,
        )
    )


def test_battery_observation_space_shape():

    env = make_env(
        enable_battery_model=True,
    )

    assert (
        env.observation_space.shape
        == (98,)
    )


def test_action_space_has_seven_actions():

    env = make_env()

    assert (
        env.action_space.n
        == 7
    )


def test_reset_returns_valid_observation():

    env = make_env()

    observation, info = (
        env.reset(
            seed=1234
        )
    )

    assert (
        observation.shape
        == (
            84,
        )
    )

    assert (
        observation.dtype
        == np.float32
    )

    assert np.all(
        np.isfinite(
            observation
        )
    )

    assert (
        env.observation_space
        .contains(
            observation
        )
    )

    assert (
        info[
            "current_task_id"
        ]
        is not None
    )


def test_reset_returns_valid_action_mask():

    env = make_env()

    env.reset(
        seed=1234
    )

    mask = (
        env.action_masks()
    )

    assert (
        mask.shape
        == (
            7,
        )
    )

    assert (
        mask.dtype
        == np.bool_
    )

    assert np.any(
        mask
    )


def test_same_explicit_seed_reproduces_first_state():

    env = make_env()

    first_observation, first_info = (
        env.reset(
            seed=4321
        )
    )

    first_task_id = (
        first_info[
            "current_task_id"
        ]
    )

    second_observation, second_info = (
        env.reset(
            seed=4321
        )
    )

    second_task_id = (
        second_info[
            "current_task_id"
        ]
    )

    assert (
        first_task_id
        == second_task_id
    )

    assert np.array_equal(
        first_observation,
        second_observation,
    )


def test_step_with_feasible_action():

    env = make_env()

    env.reset(
        seed=1234
    )

    action = (
        first_feasible_action(
            env
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

    assert (
        observation.shape
        == (
            84,
        )
    )

    assert np.isfinite(
        reward
    )

    assert isinstance(
        terminated,
        bool,
    )

    assert (
        truncated
        is False
    )

    assert (
        info[
            "decision_count"
        ]
        == 1
    )


def test_infeasible_action_is_rejected():

    env = make_env()

    env.reset(
        seed=1234
    )

    mask = (
        env.action_masks()
    )

    invalid = np.flatnonzero(
        ~mask
    )

    if not len(
        invalid
    ):

        pytest.skip(
            "Current task has all robots feasible."
        )

    with pytest.raises(
        ValueError
    ):

        env.step(
            int(
                invalid[0]
            )
        )


def test_selected_robot_records_assignment():

    env = make_env()

    _, reset_info = (
        env.reset(
            seed=1234
        )
    )

    selected_task_id = (
        reset_info[
            "current_task_id"
        ]
    )

    action = (
        first_feasible_action(
            env
        )
    )

    robot_id = (
        env.mask_builder
        .robot_id_from_action(
            action
        )
    )

    env.step(
        action
    )

    robot = (
        env.simulator
        ._get_robot(
            robot_id
        )
    )

    assert (
        selected_task_id
        in robot.assigned_task_ids
    )


def test_step_info_contains_reward_components():

    env = make_env()

    env.reset(
        seed=1234
    )

    action = (
        first_feasible_action(
            env
        )
    )

    (
        _,
        reward,
        _,
        _,
        info,
    ) = env.step(
        action
    )

    assert (
        "assignment_reward"
        in info
    )

    assert (
        "waiting_reward"
        in info
    )

    assert (
        "projected_approach_time_s"
        in info
    )

    assert (
        "tasks_ahead_count"
        in info
    )

    assert (
        reward
        == pytest.approx(
            info[
                "assignment_reward"
            ]
            + info[
                "waiting_reward"
            ]
        )
    )


def test_environment_can_run_multiple_steps():

    env = make_env()

    env.reset(
        seed=1234
    )

    steps = 0

    while (
        not env._terminated
        and steps < 10
    ):

        action = (
            first_feasible_action(
                env
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

        assert (
            observation.shape
            == (
                84,
            )
        )

        assert (
            truncated
            is False
        )

        steps += 1

        if terminated:
            break

    assert (
        steps > 0
    )


def test_decision_count_increases_once_per_step():

    env = make_env()

    env.reset(
        seed=5678
    )

    assert (
        env.decision_count
        == 0
    )

    for expected in (
        1,
        2,
        3,
    ):

        if env._terminated:
            break

        action = (
            first_feasible_action(
                env
            )
        )

        env.step(
            action
        )

        assert (
            env.decision_count
            == expected
        )


def test_complete_episode():

    env = make_env(
        workload_multiplier=0.25
    )

    env.reset(
        seed=2468
    )

    steps = 0

    while not env._terminated:

        action = (
            first_feasible_action(
                env
            )
        )

        (
            _,
            reward,
            terminated,
            truncated,
            _,
        ) = env.step(
            action
        )

        assert np.isfinite(
            reward
        )

        assert (
            truncated
            is False
        )

        steps += 1

        if terminated:
            break

        if steps > 5000:

            raise RuntimeError(
                "Environment failed to terminate."
            )

    assert (
        steps
        == len(
            env.simulator.tasks
        )
    )

    assert all(
        task.status
        == "completed"
        for task
        in env.simulator.tasks
    )


def test_step_after_termination_rejected():

    env = make_env(
        workload_multiplier=0.25
    )

    env.reset(
        seed=2468
    )

    while not env._terminated:

        action = (
            first_feasible_action(
                env
            )
        )

        env.step(
            action
        )

    with pytest.raises(
        RuntimeError
    ):

        env.step(
            0
        )


def test_episode_seed_pool_cycles():

    env = (
        HospitalSchedulingEnv(
            fleet_configuration=(
                2,
                2,
                3,
            ),
            workload_multiplier=0.25,
            episode_seeds=(
                3001,
                3002,
            ),
        )
    )

    _, first_info = (
        env.reset()
    )

    _, second_info = (
        env.reset()
    )

    _, third_info = (
        env.reset()
    )

    assert (
        first_info[
            "episode_seed"
        ]
        == 3001
    )

    assert (
        second_info[
            "episode_seed"
        ]
        == 3002
    )

    assert (
        third_info[
            "episode_seed"
        ]
        == 3001
    )


def test_explicit_seed_overrides_seed_pool():

    env = (
        HospitalSchedulingEnv(
            fleet_configuration=(
                2,
                2,
                3,
            ),
            workload_multiplier=0.25,
            episode_seeds=(
                3001,
                3002,
            ),
        )
    )

    _, info = (
        env.reset(
            seed=9999
        )
    )

    assert (
        info[
            "episode_seed"
        ]
        == 9999
    )


def test_empty_episode_seed_pool_rejected():

    with pytest.raises(
        ValueError
    ):

        HospitalSchedulingEnv(
            fleet_configuration=(
                2,
                2,
                3,
            ),
            workload_multiplier=0.25,
            episode_seeds=(),
        )


def test_low_battery_completion_releases_queue_for_same_time_reassignment():

    from experiments.fleet_sizing.models import (
        TaskState,
    )

    env = HospitalSchedulingEnv(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        workload_multiplier=0.25,
        enable_battery_model=True,
    )

    env.reset(
        seed=6001
    )

    assert (
        env.simulator
        is not None
    )

    simulator = env.simulator

    robot = simulator._get_robot(
        "M01"
    )

    # --------------------------------------------------------
    # Replace generated episode state with a controlled
    # low-battery completion scenario.
    # --------------------------------------------------------

    simulator._event_queue = []

    active_task = TaskState(
        task_id="T_ACTIVE",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_a_2",
        priority=1,
        arrival_time_s=100.0,
        service_time_s=0.0,
    )

    queued_low = TaskState(
        task_id="T_LOW",
        task_type="medication_delivery",
        source="pharmacy",
        destination="ward_b_2",
        priority=1,
        arrival_time_s=200.0,
        service_time_s=0.0,
    )

    queued_high = TaskState(
        task_id="T_HIGH",
        task_type="specimen_delivery",
        source="ward_a_2",
        destination="lab",
        priority=3,
        arrival_time_s=300.0,
        service_time_s=0.0,
    )

    active_task.assigned_robot = (
        robot.robot_id
    )
    active_task.status = "active"

    queued_low.assigned_robot = (
        robot.robot_id
    )
    queued_low.assignment_time_s = 400.0
    queued_low.queue_position = 1
    queued_low.status = "queued"

    queued_high.assigned_robot = (
        robot.robot_id
    )
    queued_high.assignment_time_s = 400.0
    queued_high.queue_position = 2
    queued_high.status = "queued"

    simulator.tasks = [
        active_task,
        queued_low,
        queued_high,
    ]

    simulator.tasks_by_id = {
        active_task.task_id:
        active_task,

        queued_low.task_id:
        queued_low,

        queued_high.task_id:
        queued_high,
    }

    robot.current_location = (
        "pharmacy"
    )

    robot.future_location = (
        "ward_a_2"
    )

    robot.current_task_id = (
        active_task.task_id
    )

    robot.current_task_destination = (
        active_task.destination
    )

    robot.current_task_start_time_s = (
        900.0
    )

    robot.current_task_completion_time_s = (
        1000.0
    )

    robot.status = "busy"

    # Below the official-reference 25% critical-low
    # charging trigger.
    robot.battery_soc = 0.24

    robot.queued_task_ids = [
        queued_low.task_id,
        queued_high.task_id,
    ]

    robot.assigned_task_ids = [
        active_task.task_id,
        queued_low.task_id,
        queued_high.task_id,
    ]

    env.current_task_id = None

    env.reassignment_task_ids = []

    env.current_time_s = 900.0

    env._terminated = False

    simulator._push_event(
        time_s=1000.0,
        event_priority=(
            simulator.EVENT_COMPLETION
        ),
        event_type="completion",
        payload=(
            robot.robot_id,
            active_task.task_id,
        ),
    )

    # --------------------------------------------------------
    # Process completion.
    #
    # Expected:
    # - active task completes
    # - robot detects SoC < 25%
    # - robot begins returning to charger
    # - queued tasks are released
    # - highest Priority + Aging released task becomes the
    #   next RL decision immediately at t=1000
    # --------------------------------------------------------

    env._advance_until_next_arrival()

    assert (
        env.current_time_s
        == 1000.0
    )

    assert (
        active_task.status
        == "completed"
    )

    assert (
        robot.current_task_id
        is None
    )

    assert (
        robot.status
        == "returning_to_charge"
    )

    assert (
        robot.queued_task_ids
        == []
    )

    assert (
        queued_low.status
        == "waiting"
    )

    assert (
        queued_low.assigned_robot
        is None
    )

    assert (
        queued_low.assignment_time_s
        is None
    )

    assert (
        queued_low.queue_position
        is None
    )

    assert (
        queued_low.arrival_time_s
        == 200.0
    )

    assert (
        queued_high.status
        == "waiting"
    )

    assert (
        queued_high.assigned_robot
        is None
    )

    assert (
        queued_high.assignment_time_s
        is None
    )

    assert (
        queued_high.queue_position
        is None
    )

    assert (
        queued_high.arrival_time_s
        == 300.0
    )

    # Emergency/high-priority released task should become
    # the immediate next RL decision.
    assert (
        env.current_task_id
        == queued_high.task_id
    )

    # The other released task remains waiting for another
    # reassignment decision.
    assert (
        env.reassignment_task_ids
        == [
            queued_low.task_id,
        ]
    )

    # Reassignment occurs at exactly the completion time;
    # simulation must NOT advance to the later
    # return-to-charge event.
    assert (
        env.current_time_s
        == 1000.0
    )

    assert any(
        event_type
        == "return_to_charge_complete"
        for (
            _,
            _,
            _,
            event_type,
            _,
        )
        in simulator._event_queue
    )


def test_all_false_mask_waits_until_charging_robot_becomes_available():

    from experiments.fleet_sizing.models import (
        TaskState,
    )

    env = HospitalSchedulingEnv(
        fleet_configuration=(
            2,
            2,
            3,
        ),
        workload_multiplier=0.25,
        enable_battery_model=True,
    )

    env.reset(
        seed=6001
    )

    assert (
        env.simulator
        is not None
    )

    simulator = env.simulator

    # --------------------------------------------------------
    # Controlled task.
    # --------------------------------------------------------

    task = TaskState(
        task_id="T_WAIT",
        task_type="specimen_delivery",
        source="ward_a_2",
        destination="lab",
        priority=3,
        arrival_time_s=1000.0,
        service_time_s=0.0,
    )

    simulator.tasks = [
        task,
    ]

    simulator.tasks_by_id = {
        task.task_id:
        task,
    }

    simulator._event_queue = []

    env.current_task_id = None
    env.reassignment_task_ids = []
    env.current_time_s = 900.0
    env._terminated = False

    # --------------------------------------------------------
    # Make every specimen-capable medical robot unavailable.
    # --------------------------------------------------------

    medical_robots = [
        robot
        for robot
        in simulator.robots
        if robot.robot_type
        == "medical"
    ]

    assert len(
        medical_robots
    ) == 2

    for robot in medical_robots:

        robot.status = "charging"
        robot.current_location = (
            "charging_station_2"
        )
        robot.future_location = (
            "charging_station_2"
        )
        robot.battery_soc = 0.50

    # M01 will finish charging later.
    robot_to_finish = (
        medical_robots[0]
    )

    robot_to_finish.charging_start_time_s = (
        800.0
    )

    robot_to_finish.charging_end_time_s = (
        1200.0
    )

    robot_to_finish.charging_start_soc = (
        0.50
    )

    # --------------------------------------------------------
    # Add arrival first.
    # --------------------------------------------------------

    simulator._push_event(
        time_s=1000.0,
        event_priority=(
            simulator.EVENT_ARRIVAL
        ),
        event_type="arrival",
        payload=(
            task.task_id
        ),
    )

    # Then one medical robot becomes available.
    simulator._push_event(
        time_s=1200.0,
        event_priority=(
            simulator.EVENT_CHARGING_COMPLETE
        ),
        event_type=(
            "charging_complete"
        ),
        payload=(
            robot_to_finish.robot_id
        ),
    )

    # --------------------------------------------------------
    # Advance.
    #
    # At t=1000:
    #   mask is all False
    #   task must NOT be exposed to PPO
    #
    # At t=1200:
    #   M01 charging completes
    #   task becomes schedulable
    #   task is exposed to PPO
    # --------------------------------------------------------

    env._advance_until_next_arrival()

    assert (
        env.current_time_s
        == 1200.0
    )

    assert (
        env.current_task_id
        == task.task_id
    )

    assert (
        task.status
        == "waiting"
    )

    assert (
        task.assigned_robot
        is None
    )

    # Original arrival time must be preserved.
    assert (
        task.arrival_time_s
        == 1000.0
    )

    # The task should have been removed from the waiting
    # reassignment queue when activated.
    assert (
        task.task_id
        not in env.reassignment_task_ids
    )

    # Charging completion should have restored the robot.
    assert (
        robot_to_finish.status
        == "idle"
    )

    assert (
        robot_to_finish.battery_soc
        == 0.80
    )

    mask = (
        env.action_masks()
    )

    assert bool(
        mask.any()
    )


def test_battery_observation_contains_robot_battery_features():

    env = make_env(
        enable_battery_model=True,
    )

    env.reset(
        seed=1234,
    )

    assert (
        env.simulator
        is not None
    )

    robot = (
        env.simulator.robots[0]
    )

    robot.battery_soc = 0.42
    robot.status = "charging"

    observation = (
        env._get_observation()
    )

    # Battery observation layout:
    #
    # Task features = 41
    # Per robot = 8
    #
    # First robot:
    # 0 capability_match
    # 1 assignable
    # 2 busy
    # 3 observable_load
    # 4 projected_approach
    # 5 tasks_ahead
    # 6 battery_soc
    # 7 battery_unavailable

    first_robot_base = 41

    battery_soc_index = (
        first_robot_base + 6
    )

    battery_unavailable_index = (
        first_robot_base + 7
    )

    assert (
        observation[
            battery_soc_index
        ]
        == pytest.approx(
            0.42
        )
    )

    assert (
        observation[
            battery_unavailable_index
        ]
        == pytest.approx(
            1.0
        )
    )
