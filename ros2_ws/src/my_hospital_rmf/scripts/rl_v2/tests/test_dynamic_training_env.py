#!/usr/bin/env python3

from sb3_contrib.common.maskable.utils import (
    is_masking_supported,
)

from rl_v2.dynamic_training_env import (
    SeededDynamicHospitalRLEnv,
)


def test_dynamic_training_env_reset():

    env = SeededDynamicHospitalRLEnv(
        scenario_seeds=range(
            6000,
            6010,
        ),
        sampling_seed=42,
    )

    observation, info = (
        env.reset()
    )

    assert observation.shape == (
        54,
    )

    assert (
        6000
        <=
        info["scenario_seed"]
        <=
        6009
    )

    assert (
        info["decision_type"]
        ==
        "assignment"
    )

    assert is_masking_supported(
        env
    )
