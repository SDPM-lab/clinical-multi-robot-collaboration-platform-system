from __future__ import annotations

import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)


TRAIN_SEED = 3001
TOTAL_TIMESTEPS = 10_000


def make_env():
    return HospitalSchedulingEnv(
        seed=TRAIN_SEED,
        fleet_configuration=(
            2,
            2,
            3,
        ),
        workload_multiplier=4.0,
    )


def main():

    env = make_env()

    observation, info = (
        env.reset(
            seed=TRAIN_SEED
        )
    )

    print(
        "Observation shape:",
        observation.shape,
    )

    print(
        "Action space:",
        env.action_space,
    )

    print(
        "Initial task:",
        info[
            "current_task_id"
        ],
    )

    print(
        "Initial mask:",
        env.action_masks(),
    )

    model = MaskablePPO(
        policy="MlpPolicy",
        env=env,

        learning_rate=3e-4,

        n_steps=512,

        batch_size=64,

        gamma=0.99,

        gae_lambda=0.95,

        clip_range=0.2,

        ent_coef=0.01,

        verbose=1,

        seed=TRAIN_SEED,

        device="cpu",
    )

    print(
        "\nStarting smoke training..."
    )

    model.learn(
        total_timesteps=(
            TOTAL_TIMESTEPS
        )
    )

    print(
        "\nTraining completed."
    )

    # --------------------------------------------------------
    # Deterministic evaluation smoke test
    # --------------------------------------------------------

    eval_env = (
        HospitalSchedulingEnv(
            seed=5001,
            fleet_configuration=(
                2,
                2,
                3,
            ),
            workload_multiplier=0.25,
        )
    )

    observation, info = (
        eval_env.reset(
            seed=5001
        )
    )

    terminated = False
    step_count = 0
    total_reward = 0.0

    print(
        "\nStarting prediction smoke test..."
    )

    while not terminated:

        mask = (
            eval_env.action_masks()
        )

        action, _ = (
            model.predict(
                observation,
                action_masks=mask,
                deterministic=True,
            )
        )

        action = int(
            action
        )

        if not bool(
            mask[
                action
            ]
        ):

            raise RuntimeError(
                "MaskablePPO selected "
                "an infeasible action."
            )

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = eval_env.step(
            action
        )

        if truncated:

            raise RuntimeError(
                "Unexpected truncation."
            )

        total_reward += (
            reward
        )

        step_count += 1

    print(
        "Prediction episode completed."
    )

    print(
        "Steps:",
        step_count,
    )

    print(
        "Total reward:",
        round(
            total_reward,
            4,
        ),
    )

    print(
        "Tasks:",
        len(
            eval_env
            .simulator
            .tasks
        ),
    )

    print(
        "Assignments:",
        len(
            eval_env
            .simulator
            .assignments
        ),
    )

    print(
        "All completed:",
        all(
            task.status
            == "completed"
            for task
            in (
                eval_env
                .simulator
                .tasks
            )
        ),
    )


if __name__ == "__main__":
    main()