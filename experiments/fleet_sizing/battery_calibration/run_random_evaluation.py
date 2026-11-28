from __future__ import annotations

import csv
import json
import math
import sys
import time
import subprocess

from datetime import datetime, timezone
from importlib.metadata import version
from statistics import mean, pstdev

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
    validate_metrics,
    run_baseline_episode,
    sha256_file,
)

from experiments.fleet_sizing import config as base_config


METHOD = "random_feasible"

OUTPUT_DIR = cfg.RESULTS_ROOT / "random"

OUTPUT_FILES = (
    "runs.csv",
    "summary.csv",
    "experiment_metadata.json",
)

POPULATION_FIELDS = (
    "generated_tasks",
    "high_only_generated_count",
    "emergency_generated_count",
    "high_emergency_generated_count",
)

RESERVE = base_config.BATTERY_MIN_RESERVE_SOC


# ============================================================
# Output utilities
# ============================================================

def read_csv(path):

    with path.open(
        encoding="utf-8-sig"
    ) as f:

        return list(csv.DictReader(f))


def write_csv(path, rows):

    if not rows:
        raise ValueError(f"No rows: {path}")

    with path.open(
        "x",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):

    with path.open(
        "x",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )


def prepare_output(output):

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = [
        output / name
        for name in OUTPUT_FILES
        if (output / name).exists()
    ]

    if existing:

        raise FileExistsError(
            "Refusing to overwrite:\n"
            + "\n".join(
                str(p) for p in existing
            )
        )


# ============================================================
# Experiment metadata
# ============================================================

def create_metadata(method):

    root = cfg.FLEET_SIZING_ROOT

    calibration = root / "battery_calibration"

    source_files = [
        calibration / "config.py",
        calibration / "evaluation.py",
        calibration / "selection.py",
        calibration / "run_random_evaluation.py",

        root / "config.py",
        root / "scheduling_simulator.py",
        root / "task_generator.py",
        root / "models.py",
        root / "travel_time.py",
        root / "nav_graph.py",

        root / "baseline/common.py",
        root / f"baseline/{method}.py",

        root / "rl/evaluate_reward_tuned_workload_robustness.py",
    ]

    return {
        "experiment":
            "battery_random_feasible_evaluation_v2",

        "method": method,

        "created_at_utc":
            datetime.now(timezone.utc).isoformat(),

        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cfg.PROJECT_ROOT,
            text=True,
        ).strip(),

        "git_status": subprocess.check_output(
            ["git", "status", "--short"],
            cwd=cfg.PROJECT_ROOT,
            text=True,
        ).splitlines(),

        "python_version": sys.version,

        "packages": {
            name: version(name)
            for name in (
                "numpy",
                "torch",
                "gymnasium",
                "stable-baselines3",
                "sb3-contrib",
            )
        },

        "source_sha256": {
            str(path.relative_to(cfg.PROJECT_ROOT)):
                sha256_file(path)
            for path in source_files
        },

        "fleet": list(cfg.FLEET_CONFIGURATION),

        "workload_multiplier":
            cfg.WORKLOAD_MULTIPLIER,

        "simulation_days":
            cfg.SIMULATION_DAYS,

        "battery_enabled": True,

        "battery_config": {
            name: getattr(base_config, name)
            for name in (
                "BATTERY_INITIAL_SOC",
                "BATTERY_CHARGE_TRIGGER_SOC",
                "BATTERY_MIN_RESERVE_SOC",
                "BATTERY_RESUME_SOC",
                "BATTERY_TRAVEL_RUNTIME_FULL_S",
                "BATTERY_TRAVEL_DRAIN_PER_SECOND",
                "BATTERY_FULL_CHARGE_TIME_S",
                "BATTERY_CHARGE_RATE_PER_SECOND",
            )
        },

        "scenario_seeds":
            list(cfg.CALIBRATION_SEEDS),

        "expected_runs":
            len(cfg.CALIBRATION_SEEDS),

        "primary_metrics":
            cfg.PRIMARY_METRICS,

        "parameter_search": False,

        "parameter_selection": False,

        "evaluation_scope":
            "Calibration-scenario preliminary evaluation",

        "navigation": {
            "nav_graph": str(cfg.NAV_GRAPH_PATH),
            "nav_graph_sha256": cfg.NAV_GRAPH_SHA256,

            "route_summary":
                str(cfg.ROUTE_SUMMARY_PATH),

            "route_summary_sha256":
                cfg.ROUTE_SUMMARY_SHA256,

            "route_results_sha256":
                cfg.ROUTE_RESULTS_SHA256,
        },

        "frozen_ppo": {
            "path": str(cfg.PPO_MODEL_PATH),
            "sha256": cfg.PPO_MODEL_SHA256,
            "used_in_evaluation": False,
        },
    }


# ============================================================
# Load selected weighted baseline results
# ============================================================

def load_reference_populations():

    static = read_csv(
        cfg.STATIC_OUTPUT_DIR / "runs.csv"
    )

    dynamic = read_csv(
        cfg.DYNAMIC_OUTPUT_DIR / "runs.csv"
    )

    with (
        cfg.STATIC_OUTPUT_DIR
        / "selected_parameters.json"
    ).open() as f:

        static_selection = json.load(f)

    with (
        cfg.DYNAMIC_OUTPUT_DIR
        / "selected_parameters.json"
    ).open() as f:

        dynamic_selection = json.load(f)

    static_alpha = static_selection[
        "selected_alpha"
    ]

    dynamic_min = dynamic_selection[
        "selected_alpha_min"
    ]

    dynamic_max = dynamic_selection[
        "selected_alpha_max"
    ]

    assert static_alpha == 0.6

    assert (
        dynamic_min, dynamic_max
    ) == (0.4, 0.9)

    reference = {}

    for seed in cfg.CALIBRATION_SEEDS:

        s = [
            r for r in static
            if int(r["seed"]) == seed
            and float(r["alpha"]) == static_alpha
        ]

        d = [
            r for r in dynamic
            if int(r["seed"]) == seed
            and float(r["alpha_min"]) == dynamic_min
            and float(r["alpha_max"]) == dynamic_max
        ]

        assert len(s) == 1
        assert len(d) == 1

        for field in POPULATION_FIELDS:

            assert float(s[0][field]) == (
                float(d[0][field])
            )

        reference[seed] = {
            field: float(s[0][field])
            for field in POPULATION_FIELDS
        }

    print("Weighted baseline reference: PASS")

    return reference


# ============================================================
# Validate a single run
# ============================================================

def validate_run(row, method, seed, reference):

    validate_metrics(row)

    assert row["method"] == method

    assert int(row["seed"]) == seed

    assert row["battery_enabled"] is True

    assert row["workload_multiplier"] == (
        cfg.WORKLOAD_MULTIPLIER
    )

    assert row["generated_tasks"] > 0

    assert (
        0 <= row["completed_tasks"]
        <= row["generated_tasks"]
    )

    assert math.isclose(
        row["completion_rate"],
        row["completed_tasks"] / row["generated_tasks"],
        rel_tol=1e-10,
        abs_tol=1e-10,
    )

    for field in POPULATION_FIELDS:

        assert float(row[field]) == (
            reference[seed][field]
        ), (method, seed, field)


# ============================================================
# Run evaluation
# ============================================================

def run_all(method, output, reference):

    rows = []

    start = time.perf_counter()

    with (output / "runs.csv").open(
        "x",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = None

        for index, seed in enumerate(
            cfg.CALIBRATION_SEEDS,
            1,
        ):

            row = run_baseline_episode(
                method=method,
                seed=seed,
                workload_multiplier=cfg.WORKLOAD_MULTIPLIER,
            )

            validate_run(
                row,
                method,
                seed,
                reference,
            )

            if writer is None:

                writer = csv.DictWriter(
                    f,
                    fieldnames=list(row.keys()),
                )

                writer.writeheader()

            writer.writerow(row)

            f.flush()

            rows.append(row)

            print(
                f"[{index:02d}/10] "
                f"method={method} "
                f"seed={seed} | "
                f"completion="
                f"{row['completion_rate']:.4%} | "
                f"avg="
                f"{row['average_waiting_time_s']:.2f} | "
                f"p95="
                f"{row['p95_waiting_time_s']:.2f} | "
                f"emergency="
                f"{row['emergency_waiting_time_s']:.2f} | "
                f"jain="
                f"{row['jain_task_fairness']:.4f} | "
                f"soc="
                f"{row['minimum_robot_soc']:.4f}",
                flush=True,
            )

    print()
    print(
        "Total elapsed seconds:",
        round(time.perf_counter() - start, 2),
    )

    return rows


# ============================================================
# Validate complete experiment
# ============================================================

def validate_run_matrix(rows):

    seeds = [
        int(row["seed"])
        for row in rows
    ]

    assert len(seeds) == 10

    assert len(set(seeds)) == 10

    assert set(seeds) == set(
        cfg.CALIBRATION_SEEDS
    )

    violations = [
        row for row in rows
        if row["minimum_robot_soc"]
        < RESERVE - 1e-9
    ]

    print()
    print("===== RUN MATRIX VALIDATION =====")
    print("Expected runs: 10")
    print("Actual runs:", len(rows))
    print("Duplicates:", len(seeds) - len(set(seeds)))
    print("Missing runs: 0")
    print("Seed consistency: PASS")
    print("Task population consistency: PASS")
    print("Battery enabled: PASS")

    print(
        "Global minimum SoC:",
        min(
            row["minimum_robot_soc"]
            for row in rows
        ),
    )

    print("Reserve threshold:", RESERVE)
    print("Reserve violations:", len(violations))

    print("Run matrix: PASS")

    return len(violations)


# ============================================================
# Summarize all metrics
# ============================================================

def summarize(rows, method, violations):

    summary = {
        "method": method,
        "runs": len(rows),
        "workload_multiplier":
            cfg.WORKLOAD_MULTIPLIER,
        "battery_enabled": True,
    }

    excluded = {
        "method",
        "seed",
        "episode_reward",
        "workload_multiplier",
        "battery_enabled",
    }

    for field in rows[0]:

        if field in excluded:
            continue

        values = [
            float(row[field])
            for row in rows
        ]

        assert all(
            math.isfinite(value)
            for value in values
        ), field

        summary[f"mean_{field}"] = mean(values)

        summary[f"std_{field}"] = pstdev(values)

    summary["min_completion_rate"] = min(
        row["completion_rate"]
        for row in rows
    )

    summary["min_observed_soc"] = min(
        row["minimum_robot_soc"]
        for row in rows
    )

    summary["reserve_violations"] = violations

    summary["completion_threshold_met"] = (
        summary["mean_completion_rate"]
        >= cfg.MIN_MEAN_COMPLETION_RATE
        and
        summary["min_completion_rate"]
        >= cfg.MIN_SEED_COMPLETION_RATE
    )

    return summary


# ============================================================
# Print experiment summary
# ============================================================

def print_summary(summary):

    print()
    print("=" * 80)
    print("RANDOM_FEASIBLE EVALUATION SUMMARY")
    print("=" * 80)

    print("Method:", summary["method"])
    print("Runs:", summary["runs"])

    fields = (
        "generated_tasks",
        "completed_tasks",
        "completion_rate",

        "average_waiting_time_s",
        "p95_waiting_time_s",
        "high_waiting_time_s",
        "emergency_waiting_time_s",

        "total_travel_time_s",

        "jain_task_fairness",
        "jain_utilization_fairness",

        "average_response_time_s",
        "p95_response_time_s",

        "emergency_p95_wait_s",
        "high_emergency_avg_wait_s",
        "high_emergency_p95_wait_s",

        "average_robot_utilization",
        "max_robot_utilization",

        "total_charging_count",
        "total_return_to_charge_count",

        "minimum_robot_soc",
        "average_final_soc",
    )

    for field in fields:

        print(
            f"{field}: "
            f"mean={summary[f'mean_{field}']:.6f} | "
            f"std={summary[f'std_{field}']:.6f}"
        )

    print()
    print(
        "Minimum completion rate:",
        summary["min_completion_rate"],
    )

    print(
        "Completion threshold met:",
        summary["completion_threshold_met"],
    )

    print(
        "Minimum observed SOC:",
        summary["min_observed_soc"],
    )

    print(
        "Reserve violations:",
        summary["reserve_violations"],
    )


# ============================================================
# Main
# ============================================================

def main():



    method = METHOD

    output = OUTPUT_DIR

    print("=" * 80)
    print("BATTERY-AWARE RANDOM_FEASIBLE EVALUATION V2")
    print("Method:", method)
    print("=" * 80)

    validate_environment()

    prepare_output(output)

    reference = load_reference_populations()

    metadata = create_metadata(method)

    write_json(
        output / "experiment_metadata.json",
        metadata,
    )

    rows = run_all(
        method,
        output,
        reference,
    )

    violations = validate_run_matrix(rows)

    summary = summarize(
        rows,
        method,
        violations,
    )

    write_csv(
        output / "summary.csv",
        [summary],
    )

    validate_environment()

    for path, expected_hash in (
        metadata["source_sha256"].items()
    ):

        assert sha256_file(
            cfg.PROJECT_ROOT / path
        ) == expected_hash

    print("Source integrity: PASS")

    print_summary(summary)

    print()
    print("Output directory:", output)

    for name in OUTPUT_FILES:

        print("Saved:", name)

    if violations:

        print("BATTERY REVIEW REQUIRED")

        raise RuntimeError(
            "Reserve violations recorded. "
            "Raw data and summary preserved."
        )

    print()
    print("RANDOM_FEASIBLE EVALUATION: COMPLETE")


if __name__ == "__main__":

    main()
