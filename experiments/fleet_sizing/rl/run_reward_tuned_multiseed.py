from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_SEEDS = [
    7101,
    7102,
    7103,
    7104,
]

TIMESTEPS = 200000

for seed in MODEL_SEEDS:

    run_name = (
        f"ppo_battery_v2_reward_tuned_"
        f"seed{seed}_200k"
    )

    final_model = (
        PROJECT_ROOT
        / "experiments"
        / "fleet_sizing"
        / "results_rl"
        / "models"
        / run_name
        / "final_model.zip"
    )

    print()
    print("=" * 90)
    print(
        f"Seed {seed} | "
        f"run={run_name}"
    )
    print("=" * 90)

    if final_model.exists():

        print(
            "Already completed, skipping:",
            final_model,
        )

        continue

    command = [
        sys.executable,
        "-m",
        "experiments.fleet_sizing.rl.train_battery_v2",

        "--model-seed",
        str(seed),

        "--timesteps",
        str(TIMESTEPS),

        "--run-name",
        run_name,

        "--approach-weight",
        "0.30",

        "--queue-weight",
        "0.15",

        "--imbalance-weight",
        "0.05",

        "--waiting-weight",
        "0.50",

        "--checkpoint-frequency",
        "20000",
    ]

    env = os.environ.copy()

    existing_pythonpath = env.get(
        "PYTHONPATH",
        "",
    )

    extra_paths = [
        str(PROJECT_ROOT),
        str(
            PROJECT_ROOT
            / "experiments"
            / "fleet_sizing"
        ),
    ]

    env["PYTHONPATH"] = (
        ":".join(
            extra_paths
            + (
                [existing_pythonpath]
                if existing_pythonpath
                else []
            )
        )
    )

    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


print()
print("=" * 90)
print("MULTISEED TRAINING COMPLETE")
print("=" * 90)
