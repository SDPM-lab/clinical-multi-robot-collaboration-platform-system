from __future__ import annotations

import csv
import json
import hashlib
import shutil
import subprocess

from pathlib import Path
from importlib.metadata import version
from datetime import datetime, timezone
from dataclasses import asdict

import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.environment import (
    HospitalSchedulingEnv,
)

from experiments.fleet_sizing.rl.observation import (
    DEFAULT_LAYOUT,
    BATTERY_LAYOUT,
    TASK_TYPES,
    SUPPORTED_PRIORITIES,
    LOCATIONS,
    LOAD_SCALE,
    TASKS_AHEAD_SCALE,
)

from experiments.fleet_sizing.rl.reward import (
    DEFAULT_REWARD_CONFIG,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
)


# ============================================================
# Paths and configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ROOT = PROJECT_ROOT / "experiments/fleet_sizing"

OUTPUT = Path(__file__).resolve().parent / "data"

RUN_NAME = (
    "reward_confirm_sweep27_"
    "w50_a30_q15_i05_seed7104_200k"
)

MODEL_PATH = (
    ROOT / "results_rl/models"
    / RUN_NAME / "final_model.zip"
)

METADATA_PATH = (
    ROOT / "results_rl/metadata"
    / f"{RUN_NAME}.json"
)

EXPECTED_MODEL_SHA256 = (
    "ba278857a1042ed58ae38e9522c7a962d"
    "73abd467d539de9479773cf96fe55e0"
)

EXAMPLE_SEED = 3001

OUTPUT_FILES = (
    "observation_layout.csv",
    "action_mapping.csv",
    "reward_config.json",
    "model_architecture.json",
    "model_parameters.csv",
    "ppo_hyperparameters.json",
    "final_model_metadata.json",
    "model_integrity.json",
    "example_observation.csv",
    "example_decision.json",
)


def sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def write_json(name, content):

    path = OUTPUT / name

    with path.open(
        "x",
        encoding="utf-8",
    ) as f:

        json.dump(
            content,
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    print("Saved:", path.name)


def write_csv(name, rows):

    assert rows

    path = OUTPUT / name

    with path.open(
        "x",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()

        writer.writerows(rows)

    print("Saved:", path.name)


# ============================================================
# Observation definitions
# ============================================================

def build_observation_layout(env):

    rows = []

    def add(group, feature, encoding, robot_id=""):

        rows.append({
            "index": len(rows),
            "group": group,
            "robot_id": robot_id,
            "feature": feature,
            "encoding": encoding,
        })

    for task_type in TASK_TYPES:

        add(
            "task_type",
            task_type,
            "one_hot",
        )

    for priority in SUPPORTED_PRIORITIES:

        add(
            "priority",
            str(priority),
            "one_hot",
        )

    for location in LOCATIONS:

        add(
            "source",
            location,
            "one_hot",
        )

    for location in LOCATIONS:

        add(
            "destination",
            location,
            "one_hot",
        )

    features = (
        (
            "capability_match",
            "binary: task type in robot capabilities",
        ),
        (
            "assignable",
            "binary: status is idle or busy",
        ),
        (
            "busy",
            "binary: active task exists",
        ),
        (
            "observable_load",
            f"min(load / {LOAD_SCALE}, 1)",
        ),
        (
            "projected_approach",
            "min(approach_time_s / "
            f"{env.observation_approach_scale_s}, 1)"
            "; zero if no placement evaluation",
        ),
        (
            "tasks_ahead",
            f"min(tasks_ahead / {TASKS_AHEAD_SCALE}, 1)"
            "; zero if no placement evaluation",
        ),
        (
            "battery_soc",
            "continuous battery fraction [0,1]",
        ),
        (
            "battery_unavailable",
            "binary: charging or returning_to_charge",
        ),
    )

    for robot_id in env.observation_encoder.robot_ids:

        for feature, encoding in features:

            add(
                "robot",
                feature,
                encoding,
                robot_id,
            )

    add(
        "global",
        "load_imbalance",
        "(max_load - min_load) / max_load"
        "; zero when all loads are zero",
    )

    assert len(rows) == 98

    assert [
        row["index"] for row in rows
    ] == list(range(98))

    return rows


# ============================================================
# Action mapping
# ============================================================

def build_action_mapping(env):

    rows = []

    for action, robot in enumerate(
        env.simulator.robots
    ):

        robot_id = (
            env.mask_builder
            .robot_id_from_action(action)
        )

        assert robot_id == robot.robot_id

        assert robot_id == (
            env.observation_encoder
            .robot_ids[action]
        )

        start = 41 + action * 8

        rows.append({
            "action": action,
            "robot_id": robot_id,
            "capabilities": "|".join(
                sorted(robot.capabilities)
            ),
            "observation_start_index": start,
            "observation_end_index": start + 7,
        })

    assert len(rows) == 7

    assert [
        row["robot_id"] for row in rows
    ] == [
        "C01", "C02",
        "M01", "M02",
        "W01", "W02", "W03",
    ]

    return rows


# ============================================================
# Network architecture and parameter counts
# ============================================================

def inspect_network(model):

    policy = model.policy

    rows = []

    actor_count = 0

    critic_count = 0

    for name, parameter in (
        policy.named_parameters()
    ):

        count = parameter.numel()

        if name.startswith((
            "mlp_extractor.policy_net.",
            "action_net.",
        )):

            branch = "actor"

            actor_count += count

        elif name.startswith((
            "mlp_extractor.value_net.",
            "value_net.",
        )):

            branch = "critic"

            critic_count += count

        else:

            raise RuntimeError(
                f"Unexpected parameter: {name}"
            )

        rows.append({
            "branch": branch,
            "parameter_name": name,
            "shape": "x".join(
                str(n)
                for n in parameter.shape
            ),
            "parameter_count": count,
            "trainable": parameter.requires_grad,
        })

    total = actor_count + critic_count

    trainable = sum(
        row["parameter_count"]
        for row in rows
        if row["trainable"]
    )

    assert actor_count == 10951
    assert critic_count == 10561
    assert total == 21512
    assert trainable == 21512

    architecture = {
        "algorithm": type(model).__name__,
        "policy_class": type(policy).__name__,
        "observation_shape": list(
            model.observation_space.shape
        ),
        "observation_dtype": str(
            model.observation_space.dtype
        ),
        "action_count": int(
            model.action_space.n
        ),
        "feature_extractor": repr(
            policy.features_extractor
        ),
        "actor_network": repr(
            policy.mlp_extractor.policy_net
        ),
        "actor_output": repr(
            policy.action_net
        ),
        "critic_network": repr(
            policy.mlp_extractor.value_net
        ),
        "critic_output": repr(
            policy.value_net
        ),
        "complete_policy": repr(policy),
        "actor_parameters": actor_count,
        "critic_parameters": critic_count,
        "total_parameters": total,
        "trainable_parameters": trainable,
        "action_mask_is_separate_input": True,
    }

    return architecture, rows


# ============================================================
# PPO training configuration
# ============================================================

def inspect_hyperparameters(model, metadata):

    fields = (
        "learning_rate",
        "n_steps",
        "batch_size",
        "n_epochs",
        "gamma",
        "gae_lambda",
        "ent_coef",
        "vf_coef",
        "max_grad_norm",
    )

    settings = {
        name: getattr(model, name)
        for name in fields
    }

    settings["clip_range"] = float(
        model.clip_range(1.0)
    )

    for name, value in settings.items():

        assert np.isclose(
            value,
            metadata["ppo_config"][name],
        ), name

    requested = metadata["total_timesteps"]

    actual = int(model.num_timesteps)

    rollout_size = (
        model.n_steps * model.n_envs
    )

    assert actual % rollout_size == 0

    rollout_count = actual // rollout_size

    minibatches = rollout_size // model.batch_size

    assert actual == 200192

    return {
        "settings": settings,
        "model_seed": int(model.seed),
        "n_envs": int(model.n_envs),
        "policy_kwargs": model.policy_kwargs,
        "requested_timesteps": requested,
        "actual_timesteps": actual,
        "rollout_count_derived": rollout_count,
        "samples_per_rollout": rollout_size,
        "minibatches_per_epoch": minibatches,
        "theoretical_minibatch_updates": (
            rollout_count
            * minibatches
            * model.n_epochs
        ),
        "actual_gradient_update_count_verified": False,
        "training_scenario_seed_pool": list(
            range(
                metadata["training_seed_start"],
                metadata["training_seed_end"] + 1,
            )
        ),
        "historical_episode_seed_sequence_verified": False,
    }


# ============================================================
# Main
# ============================================================

def main():

    validate_environment()

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = [
        name for name in OUTPUT_FILES
        if (OUTPUT / name).exists()
    ]

    if existing:

        raise FileExistsError(
            f"Refusing to overwrite: {existing}"
        )

    before_hash = sha256(MODEL_PATH)

    assert before_hash == EXPECTED_MODEL_SHA256

    metadata = json.loads(
        METADATA_PATH.read_text(
            encoding="utf-8"
        )
    )

    model = MaskablePPO.load(
        str(MODEL_PATH),
        device="cpu",
    )

    assert model.observation_space.shape == (98,)
    assert model.action_space.n == 7
    assert model.seed == 7104

    env = HospitalSchedulingEnv(
        seed=EXAMPLE_SEED,
        fleet_configuration=(2, 2, 3),
        workload_multiplier=4.0,
        enable_battery_model=True,
    )

    obs, info = env.reset(
        seed=EXAMPLE_SEED
    )

    mask = env.action_masks()

    assert DEFAULT_LAYOUT.total_size == 84

    assert BATTERY_LAYOUT.total_size == 98

    assert obs.shape == (98,)

    assert env.observation_space.contains(obs)

    assert model.observation_space.contains(obs)

    assert mask.shape == (7,)

    assert np.any(mask)

    layout = build_observation_layout(env)

    mapping = build_action_mapping(env)

    architecture, parameters = inspect_network(model)

    hyperparameters = inspect_hyperparameters(
        model,
        metadata,
    )

    # Historical reward settings must match current defaults.
    reward_config = metadata["reward_config"]

    assert reward_config == asdict(
        DEFAULT_REWARD_CONFIG
    )

    example_observation = [
        {
            **row,
            "value": float(obs[row["index"]]),
        }
        for row in layout
    ]

    # One inference only. No env.step() and no learning.
    action, _ = model.predict(
        obs,
        action_masks=mask,
        deterministic=True,
    )

    action = int(
        np.asarray(action).item()
    )

    assert bool(mask[action])

    robot_id = (
        env.mask_builder
        .robot_id_from_action(action)
    )

    task = env.simulator.tasks_by_id[
        env.current_task_id
    ]

    assert task.task_id == "T00153"

    assert task.task_type == "specimen_delivery"

    assert mask.astype(int).tolist() == [
        0, 0, 1, 1, 0, 0, 0
    ]

    example_decision = {
        "scenario_seed": EXAMPLE_SEED,
        "workload_multiplier": 4.0,
        "battery_enabled": True,
        "task_id": task.task_id,
        "task_type": task.task_type,
        "priority": int(task.priority),
        "source": task.source,
        "destination": task.destination,
        "arrival_time_s": float(task.arrival_time_s),
        "observation_approach_scale_s": (
            env.observation_approach_scale_s
        ),
        "action_mask": mask.astype(int).tolist(),
        "valid_actions": np.flatnonzero(
            mask
        ).tolist(),
        "selected_action": action,
        "selected_robot_id": robot_id,
        "deterministic": True,
        "environment_step_executed": False,
        "model_training_performed": False,
        "scope": "Current-environment inference example",
    }

    env.close()

    # Record current source hashes, not historical training hashes.
    source_paths = [
        ROOT / "rl/observation.py",
        ROOT / "rl/action_mask.py",
        ROOT / "rl/reward.py",
        ROOT / "rl/environment.py",
        ROOT / "rl/train_battery_v2.py",
        ROOT / "rl/evaluate_battery_v2.py",
        ROOT / "rl/run_reward_weight_confirmation.py",
        ROOT / "rl/run_final_reward_confirmation.py",
        ROOT / "baseline/common.py",
        ROOT / "scheduling_simulator.py",
        ROOT / "config.py",
    ]

    after_hash = sha256(MODEL_PATH)

    assert before_hash == after_hash

    validate_environment()

    integrity = {
        "exported_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
        ).strip(),
        "model_path": str(
            MODEL_PATH.relative_to(PROJECT_ROOT)
        ),
        "model_sha256": before_hash,
        "model_size_bytes": MODEL_PATH.stat().st_size,
        "historical_metadata_sha256": sha256(
            METADATA_PATH
        ),
        "current_source_sha256": {
            str(path.relative_to(PROJECT_ROOT)):
                sha256(path)
            for path in source_paths
        },
        "current_package_versions": {
            name: version(name)
            for name in (
                "numpy",
                "torch",
                "gymnasium",
                "stable-baselines3",
                "sb3-contrib",
            )
        },
        "observation_approach_scale_s_current": (
            example_decision[
                "observation_approach_scale_s"
            ]
        ),
        "historical_observation_scale_recorded": (
            "observation_approach_scale_s"
            in metadata
        ),
        "source_hash_scope":
            "Current inspected source, not historical training snapshot",
        "model_modified": False,
        "model_retrained": False,
    }

    # Save data only after all checks pass.
    write_csv(
        "observation_layout.csv",
        layout,
    )

    write_csv(
        "action_mapping.csv",
        mapping,
    )

    write_json(
        "reward_config.json",
        reward_config,
    )

    write_json(
        "model_architecture.json",
        architecture,
    )

    write_csv(
        "model_parameters.csv",
        parameters,
    )

    write_json(
        "ppo_hyperparameters.json",
        hyperparameters,
    )

    shutil.copy2(
        METADATA_PATH,
        OUTPUT / "final_model_metadata.json",
    )

    assert sha256(
        OUTPUT / "final_model_metadata.json"
    ) == sha256(METADATA_PATH)

    print("Saved: final_model_metadata.json")

    write_json(
        "model_integrity.json",
        integrity,
    )

    write_csv(
        "example_observation.csv",
        example_observation,
    )

    write_json(
        "example_decision.json",
        example_decision,
    )

    print()
    print("===== ACTUAL PPO INFERENCE =====")
    print("Task:", task.task_id)
    print("Action mask:", mask.astype(int).tolist())
    print("Selected action:", action)
    print("Selected robot:", robot_id)
    print("Selected action feasible: PASS")

    print()
    print("===== FINAL MODEL DESIGN CHECK =====")
    print("Observation features:", len(layout))
    print("Action mappings:", len(mapping))
    print("Actor parameters:", architecture["actor_parameters"])
    print("Critic parameters:", architecture["critic_parameters"])
    print("Total parameters:", architecture["total_parameters"])
    print("Actual timesteps:", model.num_timesteps)
    print("Reward config consistency: PASS")
    print("PPO hyperparameter consistency: PASS")
    print("Model SHA256: PASS")
    print("Data files:", len(OUTPUT_FILES))
    print("Model modified: NO")
    print("Model retrained: NO")
    print("MODEL DESIGN EXPORT: COMPLETE")


if __name__ == "__main__":

    main()
