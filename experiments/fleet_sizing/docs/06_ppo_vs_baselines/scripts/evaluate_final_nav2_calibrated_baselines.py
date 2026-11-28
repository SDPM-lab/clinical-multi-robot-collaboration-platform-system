from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
import time
import math
import platform

from pathlib import Path
from datetime import datetime
from collections import Counter
from functools import wraps
from importlib.metadata import version

import pandas as pd
import numpy as np

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl import (
    evaluate_reward_tuned_workload_robustness as shared
)

from experiments.fleet_sizing.rl import (
    evaluate_final_policy_vs_baselines_nav2_sweep12_seed7101
    as historical
)

# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

FLEET_ROOT = ROOT / "experiments/fleet_sizing"

CALIBRATION = (
    FLEET_ROOT
    / "results/battery_baseline_calibration_v2"
)

OUTPUT_ROOT = (
    FLEET_ROOT
    / "results_rl"
    / "final_nav2_calibrated_baselines_sweep12_seed7101"
)

NAV2_RAW = ROOT / "ros2_ws/batch_route_results_nav2.csv"

NAV2_SUMMARY = ROOT / "ros2_ws/batch_route_summary_nav2.csv"

NAV_GRAPH = (
    ROOT
    / "ros2_ws/src/my_hospital_rmf/nav_graphs/0.yaml"
)

MODEL = historical.MODEL_PATH

BASELINES = historical.BASELINES
PPO_NAME = historical.PPO_NAME

WORKLOADS = historical.WORKLOADS
SEEDS = historical.EVAL_SEEDS

STATIC_PATH = (
    CALIBRATION / "static/selected_parameters.json"
)

DYNAMIC_PATH = (
    CALIBRATION / "dynamic/selected_parameters.json"
)

EXPECTED_MODEL_HASH = (
    "1972295e176e6907d3bee4d01b301fa105"
    "26dac40dca38a5e867fe1a63825d07"
)

EXPECTED_SUMMARY_HASH = (
    "0baf6a695bacd2dac8f99a9e1b540dbb"
    "30901dfff0086afb93a0666acf030399"
)

EXPECTED_RAW_HASH = (
    "2afdbdf57e8f5f0ffe6d318ec689c10b8"
    "b638477476ea63e56483b3ef6377b4a"
)

EXPECTED_GRAPH_HASH = (
    "91c491b860ce97036ecceba4cf2460085"
    "baf9169d22484c1328cd722dc94bf79"
)

EXPECTED_STATIC_HASH = (
    "5f861974ac565aebdbc846de5559b1cc"
    "0030b7328a72d3e84b02cf4caaaebc80"
)

EXPECTED_DYNAMIC_HASH = (
    "4fa9c6c8d468db99843700a5faa6eef"
    "1945e36cdcf7cd71e86f464f10bf1df00"
)

def sha256(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()

def read_json(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8")
    )

def git(*args):
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()

def verify_hash(path, expected):

    actual = sha256(path)

    assert actual == expected, (
        f"Hash mismatch: {path}\n"
        f"Expected: {expected}\n"
        f"Actual: {actual}"
    )

    return actual

# ============================================================
# Selected Baseline parameters
# ============================================================

def load_parameters():

    verify_hash(
        STATIC_PATH,
        EXPECTED_STATIC_HASH,
    )

    verify_hash(
        DYNAMIC_PATH,
        EXPECTED_DYNAMIC_HASH,
    )

    static = read_json(STATIC_PATH)

    dynamic = read_json(DYNAMIC_PATH)

    assert static["candidate_count"] == 11
    assert dynamic["candidate_count"] == 55

    alpha = float(
        static["selected_alpha"]
    )

    alpha_min = float(
        dynamic["selected_alpha_min"]
    )

    alpha_max = float(
        dynamic["selected_alpha_max"]
    )

    assert alpha == 0.6

    assert (alpha_min, alpha_max) == (
        0.4, 0.9
    )

    for method in ("static", "dynamic"):

        metadata = read_json(
            CALIBRATION
            / method
            / "experiment_metadata.json"
        )

        navigation = metadata["navigation"]

        assert navigation[
            "route_summary_sha256"
        ] == EXPECTED_SUMMARY_HASH

        assert navigation[
            "nav_graph_sha256"
        ] == EXPECTED_GRAPH_HASH

        assert navigation[
            "route_results_sha256"
        ] == EXPECTED_RAW_HASH

        assert metadata["fleet"] == [2, 2, 3]

        assert metadata["battery_enabled"] is True

        assert metadata["simulation_days"] == 7

        assert metadata["calibration_seeds"] == (
            list(range(3001, 3011))
        )

        assert not (
            set(metadata["calibration_seeds"])
            & set(SEEDS)
        )

    return {
        "static_alpha": alpha,
        "dynamic_alpha_min": alpha_min,
        "dynamic_alpha_max": alpha_max,
    }

# ============================================================
# Runtime Nav2 model verification
# ============================================================

def check_travel_model(model):

    actual = Path(
        model.summary_csv_path
    ).resolve()

    assert actual == NAV2_SUMMARY.resolve(), actual

    verify_hash(
        actual,
        EXPECTED_SUMMARY_HASH,
    )

    assert len(model.route_stats) == 31

    assert math.isclose(
        model.effective_speed_mps,
        0.3289677419354839,
        rel_tol=1e-9,
    )

    assert math.isclose(
        model.get_travel_time_mean(
            "pharmacy",
            "ward_a_2",
        ),
        115.296,
        abs_tol=1e-8,
    )

def locate_travel_classes():

    module = inspect.getmodule(
        shared.SchedulingSimulator
    )

    cls = getattr(
        module,
        "TravelTimeModel",
        None,
    )

    assert cls is not None

    # Include any additional loaded aliases of the
    # same TravelTimeModel source file.

    source = Path(
        inspect.getfile(cls)
    ).resolve()

    classes = {cls}

    for mod in list(sys.modules.values()):

        candidate = getattr(
            mod,
            "TravelTimeModel",
            None,
        )

        if not inspect.isclass(candidate):
            continue

        try:

            path = Path(
                inspect.getfile(candidate)
            ).resolve()

        except (TypeError, OSError):

            continue

        if path == source:

            classes.add(candidate)

    return classes

# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--smoke",
        action="store_true",
    )

    args = parser.parse_args()

    start = time.perf_counter()

    workloads = (
        (4.0,)
        if args.smoke
        else WORKLOADS
    )

    seeds = (
        (9601,)
        if args.smoke
        else SEEDS
    )

    methods = (*BASELINES, PPO_NAME)

    output = (
        OUTPUT_ROOT
        / ("smoke" if args.smoke else "full")
    )

    if output.exists() and any(output.iterdir()):

        raise RuntimeError(
            f"Refusing to overwrite: {output}"
        )

    params = load_parameters()

    verify_hash(
        MODEL,
        EXPECTED_MODEL_HASH,
    )

    verify_hash(
        NAV2_RAW,
        EXPECTED_RAW_HASH,
    )

    verify_hash(
        NAV2_SUMMARY,
        EXPECTED_SUMMARY_HASH,
    )

    verify_hash(
        NAV_GRAPH,
        EXPECTED_GRAPH_HASH,
    )

    assert tuple(shared.REFERENCE_FLEET) == (
        2, 2, 3
    )

    planned = (
        len(methods)
        * len(workloads)
        * len(seeds)
    )

    print("===== FINAL NAV2 CALIBRATED COMPARISON =====")
    print("Fleet:", shared.REFERENCE_FLEET)
    print("Workloads:", workloads)
    print("Seeds:", seeds)
    print("Parameters:", params)
    print("PPO:", MODEL)
    print("Planned episodes:", planned)
    print("Input hashes: PASS")

    # --------------------------------------------------------
    # Load frozen PPO model
    # --------------------------------------------------------

    model = MaskablePPO.load(
        str(MODEL),
        device="cpu",
    )

    assert model.observation_space.shape == (98,)
    assert model.action_space.n == 7

    print("PPO model identity: PASS")

    # --------------------------------------------------------
    # Override only scheduler creation in this process.
    # Do not change original implementation files.
    # --------------------------------------------------------

    old_factory = shared.create_baseline_scheduler

    def calibrated_factory(method, seed):

        if method == "static_weighted":

            return shared.StaticWeightedScheduler(
                alpha=params["static_alpha"]
            )

        if method == "dynamic_weighted":

            return shared.DynamicWeightedScheduler(
                alpha_min=params["dynamic_alpha_min"],
                alpha_max=params["dynamic_alpha_max"],
            )

        return old_factory(
            method=method,
            seed=seed,
        )

    # --------------------------------------------------------
    # Record experiment provenance
    # --------------------------------------------------------

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_hashes = {}

    for path in sorted(
        FLEET_ROOT.rglob("*.py")
    ):

        relative = path.relative_to(FLEET_ROOT)

        if any(
            part in {
                "docs",
                "__pycache__",
                "results",
                "results_rl",
            }
            for part in relative.parts
        ):
            continue

        source_hashes[
            str(path.relative_to(ROOT))
        ] = sha256(path)

    metadata = {
        "status": "running",
        "started_at": (
            datetime.now().astimezone().isoformat()
        ),
        "mode": "smoke" if args.smoke else "full",
        "git_commit": git("rev-parse", "HEAD"),
        "git_status": git("status", "--short"),
        "python_version": platform.python_version(),
        "packages": {
            name: version(name)
            for name in [
                "numpy",
                "pandas",
                "torch",
                "gymnasium",
                "stable-baselines3",
                "sb3-contrib",
            ]
        },
        "fleet": [2, 2, 3],
        "battery_enabled": True,
        "workloads": list(workloads),
        "evaluation_seeds": list(seeds),
        "calibration_seeds": list(range(3001, 3011)),
        "methods": list(methods),
        "baseline_parameters": params,
        "static_selection_sha256": sha256(STATIC_PATH),
        "dynamic_selection_sha256": sha256(DYNAMIC_PATH),
        "model_path": str(MODEL.relative_to(ROOT)),
        "model_seed": 7101,
        "model_sha256": sha256(MODEL),
        "reward_weights": {
            "W": 0.40,
            "A": 0.35,
            "Q": 0.15,
            "I": 0.10,
        },
        "nav2_summary_sha256": sha256(NAV2_SUMMARY),
        "nav2_raw_sha256": sha256(NAV2_RAW),
        "nav_graph_sha256": sha256(NAV_GRAPH),
        "source_sha256": source_hashes,
        "planned_episodes": planned,
    }

    metadata_path = (
        output / "experiment_metadata.json"
    )

    def save_metadata():

        metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

    save_metadata()

    # --------------------------------------------------------
    # Instrument actual runtime travel models
    # --------------------------------------------------------

    runtime_checks = []

    original_initializers = {}

    def make_checked_init(original):

        @wraps(original)
        def checked_init(self, *a, **kw):

            original(self, *a, **kw)

            check_travel_model(self)

            runtime_checks.append({
                "summary_csv": str(
                    self.summary_csv_path
                ),
                "routes": len(self.route_stats),
                "effective_speed_mps": (
                    self.effective_speed_mps
                ),
            })

        return checked_init

    for cls in locate_travel_classes():

        original_initializers[cls] = cls.__init__

        cls.__init__ = make_checked_init(
            cls.__init__
        )

    shared.create_baseline_scheduler = (
        calibrated_factory
    )

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    rows = []
    summaries = []
    runtime_rows = []

    try:

        for workload in workloads:

            for method in methods:

                group = []

                for seed in seeds:

                    before = len(runtime_checks)

                    if method == PPO_NAME:

                        result = (
                            shared.run_ppo_episode(
                                model=model,
                                seed=seed,
                                method_name=method,
                                workload_multiplier=workload,
                            )
                        )

                    else:

                        result = (
                            shared.run_baseline_episode(
                                method=method,
                                seed=seed,
                                workload_multiplier=workload,
                            )
                        )

                    count = (
                        len(runtime_checks) - before
                    )

                    assert count > 0, (
                        f"No verified Nav2 model: "
                        f"{method}, {workload}, {seed}"
                    )

                    result["training_seed"] = (
                        7101
                        if method == PPO_NAME
                        else ""
                    )

                    result["workload_multiplier"] = (
                        workload
                    )

                    rows.append(result)
                    group.append(result)

                    runtime_rows.append({
                        "method": method,
                        "workload_multiplier": workload,
                        "seed": seed,
                        "verified_travel_models": count,
                        "nav2_verified": True,
                    })

                    print(
                        f"[{len(rows)}/{planned}] "
                        f"{method:<24} "
                        f"workload={workload:.1f} "
                        f"seed={seed} "
                        f"completion="
                        f"{result['completion_rate']:.4f} "
                        f"wait="
                        f"{result['average_waiting_time_s']:.2f} "
                        f"emergency="
                        f"{result['emergency_waiting_time_s']:.2f} "
                        f"nav2=PASS",
                        flush=True,
                    )

                summary = shared.aggregate_method(
                    method,
                    group,
                )

                summary["workload_multiplier"] = workload

                summaries.append(summary)

                shared.write_csv(
                    output / "comparison_runs.csv",
                    rows,
                )

                shared.write_csv(
                    output / "comparison_summary.csv",
                    summaries,
                )

                shared.write_csv(
                    output / "runtime_nav2_checks.csv",
                    runtime_rows,
                )

        # ----------------------------------------------------
        # Verify coverage and completion
        # ----------------------------------------------------

        assert len(rows) == planned

        assert len(summaries) == (
            len(methods) * len(workloads)
        )

        df = pd.DataFrame(rows)

        keys = [
            "method",
            "workload_multiplier",
            "seed",
        ]

        assert not df.duplicated(keys).any()

        scenario = df.groupby([
            "workload_multiplier",
            "seed",
        ])

        assert (
            scenario.size() == len(methods)
        ).all()

        assert (
            scenario["generated_tasks"].nunique() == 1
        ).all()

        assert (
            df["generated_tasks"] > 0
        ).all()

        assert np.allclose(
            df["completion_rate"],
            df["completed_tasks"]
            / df["generated_tasks"],
        )

        assert len(runtime_rows) == planned

        metadata["status"] = "complete"

        metadata["completed_episodes"] = len(rows)

        metadata["summary_groups"] = len(summaries)

        metadata["minimum_completion_rate"] = float(
            df["completion_rate"].min()
        )

        metadata["runtime_travel_checks"] = len(
            runtime_checks
        )

        metadata["elapsed_seconds"] = (
            time.perf_counter() - start
        )

        metadata["finished_at"] = (
            datetime.now().astimezone().isoformat()
        )

        metadata["output_sha256"] = {
            name: sha256(output / name)
            for name in [
                "comparison_runs.csv",
                "comparison_summary.csv",
                "runtime_nav2_checks.csv",
            ]
        }

        # Ensure key inputs stayed unchanged.

        verify_hash(
            MODEL,
            EXPECTED_MODEL_HASH,
        )

        verify_hash(
            NAV2_SUMMARY,
            EXPECTED_SUMMARY_HASH,
        )

        verify_hash(
            NAV_GRAPH,
            EXPECTED_GRAPH_HASH,
        )

        save_metadata()

    except BaseException as error:

        metadata["status"] = "failed"

        metadata["error"] = repr(error)

        metadata["completed_episodes"] = len(rows)

        save_metadata()

        raise

    finally:

        shared.create_baseline_scheduler = (
            old_factory
        )

        for cls, original in (
            original_initializers.items()
        ):

            cls.__init__ = original

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("===== FINAL EVALUATION COMPLETE =====")
    print("Episodes:", len(rows))
    print("Summary groups:", len(summaries))
    print("Static alpha:", params["static_alpha"])

    print(
        "Dynamic range:",
        params["dynamic_alpha_min"],
        params["dynamic_alpha_max"],
    )

    print(
        "Runtime Nav2 checks:",
        len(runtime_checks),
    )

    print(
        "Minimum completion rate:",
        metadata["minimum_completion_rate"],
    )

    print("Historical results overwritten: NO")
    print("Fleet sizing repeated: NO")
    print("Baseline calibration repeated: NO")
    print("PPO training performed: NO")
    print("Output:", output)

    print("Evaluation: PASS")

if __name__ == "__main__":

    main()

