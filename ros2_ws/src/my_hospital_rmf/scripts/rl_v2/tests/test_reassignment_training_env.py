#!/usr/bin/env python3

import numpy as np

from sb3_contrib.common.maskable.utils import (
    is_masking_supported,
)

from rl_v2.reassignment_training_env import (
    SeededReassignmentHospitalRLEnv,
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

        feasible = (
            np.flatnonzero(
                action_masks
            )
        )

        assert len(feasible) > 0

        return (
            int(
                feasible[0]
            ),
            None,
        )


def test_reassignment_training_env_reset():

    env = (
        SeededReassignmentHospitalRLEnv(
            assignment_policy=(
                FirstFeasibleAssignmentPolicy()
            ),
            scenario_seeds=range(
                6000,
                6010,
            ),
            sampling_seed=42,
        )
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
        info[
            "scenario_seed"
        ]
        <=
        6009
    )

    assert (
        env.kernel
        .current_decision_type
        ==
        "reassignment"
    )

    assert is_masking_supported(
        env
    )
