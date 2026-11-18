from __future__ import annotations

from pathlib import Path

import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

MODEL_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "fleet_sizing"
    / "results_rl"
    / "models"
    / "ppo_battery_v2_reward_tuned_seed7104_200k"
    / "final_model.zip"
)

REFERENCE_FLEET = (
    2,
    2,
    3,
)

WORKLOAD_MULTIPLIER = 4.0

EVALUATION_SEEDS = tuple(
    range(
        9401,
        9431,
    )
)

SCALE_S = 600.0


# ============================================================
# Helpers
# ============================================================

def print_distribution(
    name: str,
    values: list[float],
) -> None:

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)

    if not values:
        print("No values collected.")
        return

    x = np.asarray(
        values,
        dtype=np.float64,
    )

    print(
        f"count      : {len(x)}"
    )
    print(
        f"min        : {np.min(x):.2f} s"
    )
    print(
        f"mean       : {np.mean(x):.2f} s"
    )
    print(
        f"median/P50 : {np.percentile(x, 50):.2f} s"
    )
    print(
        f"P75        : {np.percentile(x, 75):.2f} s"
    )
    print(
        f"P90        : {np.percentile(x, 90):.2f} s"
    )
    print(
        f"P95        : {np.percentile(x, 95):.2f} s"
    )
    print(
        f"P99        : {np.percentile(x, 99):.2f} s"
    )
    print(
        f"max        : {np.max(x):.2f} s"
    )

    above_600 = int(
        np.sum(
            x >= SCALE_S
        )
    )

    percent_above_600 = (
        100.0
        * above_600
        / len(x)
    )

    print()
    print(
        f">= 600 s   : "
        f"{above_600}/{len(x)} "
        f"({percent_above_600:.2f}%)"
    )

    normalized = np.minimum(
        x / SCALE_S,
        1.0,
    )

    print()
    print(
        "Normalized with scale=600 s"
    )
    print(
        f"mean       : {np.mean(normalized):.3f}"
    )
    print(
        f"P50        : {np.percentile(normalized, 50):.3f}"
    )
    print(
        f"P90        : {np.percentile(normalized, 90):.3f}"
    )
    print(
        f"P95        : {np.percentile(normalized, 95):.3f}"
    )
    print(
        f"P99        : {np.percentile(normalized, 99):.3f}"
    )
    print(
        f"max        : {np.max(normalized):.3f}"
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    print(
        "Loading model:"
    )
    print(
        MODEL_PATH
    )

    model = MaskablePPO.load(
        MODEL_PATH
    )

    projected_approach_times: list[
        float
    ] = []

    realized_waiting_times: list[
        float
    ] = []

    waiting_by_priority: dict[
        int,
        list[float],
    ] = {
        0: [],
        1: [],
        2: [],
        3: [],
    }

    total_decisions = 0

    for seed in EVALUATION_SEEDS:

        env = HospitalSchedulingEnv(
            seed=seed,
            fleet_configuration=(
                REFERENCE_FLEET
            ),
            workload_multiplier=(
                WORKLOAD_MULTIPLIER
            ),
            enable_battery_model=True,
        )

        observation, _ = env.reset(
            seed=seed
        )

        terminated = False

        seed_decisions = 0
        seed_waiting_events = 0

        while not terminated:

            mask = (
                env.action_masks()
            )

            action, _ = (
                model.predict(
                    observation,
                    action_masks=(
                        mask
                    ),
                    deterministic=True,
                )
            )

            action = int(
                action
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

            if truncated:
                raise RuntimeError(
                    "Unexpected environment "
                    "truncation."
                )

            approach = float(
                info[
                    "projected_approach_time_s"
                ]
            )

            projected_approach_times.append(
                approach
            )

            for event in (
                info[
                    "realized_waiting_events"
                ]
            ):

                waiting = float(
                    event[
                        "waiting_time_s"
                    ]
                )

                priority = int(
                    event[
                        "priority"
                    ]
                )

                realized_waiting_times.append(
                    waiting
                )

                waiting_by_priority[
                    priority
                ].append(
                    waiting
                )

                seed_waiting_events += 1

            seed_decisions += 1
            total_decisions += 1

        env.close()

        print(
            f"seed={seed} "
            f"decisions={seed_decisions} "
            f"waiting_events="
            f"{seed_waiting_events}"
        )

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(
        f"evaluation seeds : "
        f"{len(EVALUATION_SEEDS)}"
    )
    print(
        f"total decisions  : "
        f"{total_decisions}"
    )
    print(
        f"waiting events   : "
        f"{len(realized_waiting_times)}"
    )

    print_distribution(
        "PROJECTED APPROACH TIME",
        projected_approach_times,
    )

    print_distribution(
        "REALIZED WAITING TIME",
        realized_waiting_times,
    )

    priority_names = {
        0: "LOW",
        1: "NORMAL",
        2: "HIGH",
        3: "EMERGENCY",
    }

    for priority in range(4):

        print_distribution(
            (
                "REALIZED WAITING TIME - "
                f"{priority_names[priority]}"
            ),
            waiting_by_priority[
                priority
            ],
        )


if __name__ == "__main__":
    main()
