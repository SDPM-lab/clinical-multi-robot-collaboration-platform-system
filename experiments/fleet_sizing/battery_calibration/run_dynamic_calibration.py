from __future__ import annotations

import csv
import json
import time
import sys
import subprocess

from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
    run_baseline_episode,
    sha256_file,
)

from experiments.fleet_sizing.battery_calibration.selection import (
    summarize_runs,
    select_parameters,
)

from experiments.fleet_sizing import config as base_config


METHOD = "dynamic_weighted"

PARAMETER_FIELDS = [
    "alpha_min",
    "alpha_max",
]

OUTPUT_DIR = cfg.DYNAMIC_OUTPUT_DIR

OUTPUT_FILES = (
    "runs.csv",
    "summary.csv",
    "pareto.csv",
    "ranking.csv",
    "selected_parameters.json",
    "experiment_metadata.json",
)


# ============================================================
# Output
# ============================================================

def prepare_output():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = [
        OUTPUT_DIR / name
        for name in OUTPUT_FILES
        if (OUTPUT_DIR / name).exists()
    ]

    if existing:

        raise FileExistsError(
            "Refusing to overwrite:\n"
            + "\n".join(str(p) for p in existing)
        )


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


# ============================================================
# Grid validation
# ============================================================

def validate_grid():

    expected = {
        (i / 10, j / 10)
        for i in range(11)
        for j in range(i + 1, 11)
    }

    ranges = cfg.DYNAMIC_ALPHA_RANGES

    assert len(ranges) == 55
    assert len(set(ranges)) == 55
    assert set(ranges) == expected

    assert cfg.ORIGINAL_DYNAMIC_ALPHA_RANGE in ranges

    assert len(cfg.CALIBRATION_SEEDS) == 10

    print("Dynamic grid validation: PASS")


# ============================================================
# Experiment metadata
# ============================================================

def save_metadata():

    git_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=cfg.PROJECT_ROOT,
        text=True,
    ).strip()

    git_status = subprocess.check_output(
        ["git", "status", "--short"],
        cwd=cfg.PROJECT_ROOT,
        text=True,
    ).splitlines()

    calibration_root = (
        cfg.FLEET_SIZING_ROOT
        / "battery_calibration"
    )

    source_files = [
        calibration_root / "config.py",
        calibration_root / "evaluation.py",
        calibration_root / "selection.py",
        calibration_root / "run_dynamic_calibration.py",

        cfg.FLEET_SIZING_ROOT / "config.py",
        cfg.FLEET_SIZING_ROOT / "scheduling_simulator.py",
        cfg.FLEET_SIZING_ROOT / "task_generator.py",
        cfg.FLEET_SIZING_ROOT / "models.py",
        cfg.FLEET_SIZING_ROOT / "travel_time.py",
        cfg.FLEET_SIZING_ROOT / "nav_graph.py",

        cfg.FLEET_SIZING_ROOT / "baseline/common.py",
        cfg.FLEET_SIZING_ROOT / "baseline/dynamic_weighted.py",

        cfg.FLEET_SIZING_ROOT
        / "rl/evaluate_reward_tuned_workload_robustness.py",
    ]

    metadata = {
        "experiment": "battery_dynamic_calibration_v2",

        "method": METHOD,

        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "git_commit": git_commit,

        "git_status": git_status,

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

        "workload_multiplier": cfg.WORKLOAD_MULTIPLIER,

        "simulation_days": cfg.SIMULATION_DAYS,

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

        "grid_search": {
            "step": 0.1,
            "constraint": "0 <= alpha_min < alpha_max <= 1",
            "candidate_count": 55,
            "alpha_ranges": [
                list(pair)
                for pair in cfg.DYNAMIC_ALPHA_RANGES
            ],
        },

        "calibration_seeds": list(
            cfg.CALIBRATION_SEEDS
        ),

        "expected_runs": 550,

        "primary_metrics": cfg.PRIMARY_METRICS,

        "min_mean_completion_rate":
            cfg.MIN_MEAN_COMPLETION_RATE,

        "min_seed_completion_rate":
            cfg.MIN_SEED_COMPLETION_RATE,

        "tie_break_metrics": list(
            cfg.TIE_BREAK_METRICS
        ),

        "selection_method":
            "Completion screening, Pareto front, rank sum",

        "rank_reference":
            "All feasible dynamic candidates",

        "rank_ties":
            "Average rank for exact ties",

        "navigation": {
            "nav_graph": str(cfg.NAV_GRAPH_PATH),

            "nav_graph_sha256":
                cfg.NAV_GRAPH_SHA256,

            "route_summary": str(cfg.ROUTE_SUMMARY_PATH),

            "route_summary_sha256":
                cfg.ROUTE_SUMMARY_SHA256,

            "route_results_sha256":
                cfg.ROUTE_RESULTS_SHA256,
        },

        "frozen_ppo": {
            "path": str(cfg.PPO_MODEL_PATH),

            "sha256": cfg.PPO_MODEL_SHA256,

            "used_in_calibration": False,
        },
    }

    write_json(
        OUTPUT_DIR / "experiment_metadata.json",
        metadata,
    )


# ============================================================
# Run simulations
# ============================================================

def run_all():

    rows = []

    total = (
        len(cfg.DYNAMIC_ALPHA_RANGES)
        * len(cfg.CALIBRATION_SEEDS)
    )

    index = 0

    start = time.perf_counter()

    with (OUTPUT_DIR / "runs.csv").open(
        "x",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = None

        for lo, hi in cfg.DYNAMIC_ALPHA_RANGES:

            print()
            print("=" * 80)
            print(
                f"DYNAMIC RANGE = [{lo:.1f}, {hi:.1f}]"
            )
            print("=" * 80)

            for seed in cfg.CALIBRATION_SEEDS:

                index += 1

                row = run_baseline_episode(
                    method=METHOD,
                    seed=seed,
                    alpha_min=lo,
                    alpha_max=hi,
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
                    f"[{index:03d}/{total}] "
                    f"range=[{lo:.1f},{hi:.1f}] "
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
                    f"{row['jain_task_fairness']:.4f}",
                    flush=True,
                )

    print()
    print(
        "Total elapsed seconds:",
        round(time.perf_counter() - start, 2),
    )

    return rows


# ============================================================
# Run matrix validation
# ============================================================

def validate_run_matrix(rows):

    expected_keys = {
        (lo, hi, seed)
        for lo, hi in cfg.DYNAMIC_ALPHA_RANGES
        for seed in cfg.CALIBRATION_SEEDS
    }

    actual_keys = [
        (
            float(row["alpha_min"]),
            float(row["alpha_max"]),
            int(row["seed"]),
        )
        for row in rows
    ]

    counts = Counter(actual_keys)

    assert len(rows) == 550

    assert all(
        count == 1
        for count in counts.values()
    )

    assert set(actual_keys) == expected_keys

    for row in rows:

        assert row["method"] == METHOD

        assert row["battery_enabled"] is True

        assert row["workload_multiplier"] == (
            cfg.WORKLOAD_MULTIPLIER
        )

    # Compare population counts with the completed
    # Static calibration under the same seeds.

    with (cfg.STATIC_OUTPUT_DIR / "runs.csv").open(
        encoding="utf-8"
    ) as f:

        static_rows = list(csv.DictReader(f))

    population_fields = (
        "generated_tasks",
        "high_only_generated_count",
        "emergency_generated_count",
        "high_emergency_generated_count",
    )

    for seed in cfg.CALIBRATION_SEEDS:

        static_group = [
            row
            for row in static_rows
            if int(row["seed"]) == seed
        ]

        dynamic_group = [
            row
            for row in rows
            if int(row["seed"]) == seed
        ]

        assert len(static_group) == 11
        assert len(dynamic_group) == 55

        for field in population_fields:

            values = {
                float(row[field])
                for row in static_group + dynamic_group
            }

            assert len(values) == 1, (
                seed, field, values
            )

    print()
    print("===== RUN MATRIX VALIDATION =====")
    print("Expected runs:", len(expected_keys))
    print("Actual runs:", len(rows))
    print("Unique runs:", len(counts))
    print("Duplicates: 0")
    print("Missing runs: 0")
    print("Seed consistency: PASS")
    print("Battery enabled for all runs: PASS")
    print("Static-Dynamic task population: PASS")
    print("Run matrix: PASS")

    minimum_soc = min(
        float(row["minimum_robot_soc"])
        for row in rows
    )

    reserve = base_config.BATTERY_MIN_RESERVE_SOC

    violations = [
        row
        for row in rows
        if float(row["minimum_robot_soc"])
        < reserve - 1e-9
    ]

    print("Global minimum SoC:", minimum_soc)
    print("Battery reserve:", reserve)
    print("Reserve violations:", len(violations))

    if violations:

        raise RuntimeError(
            "Battery reserve violations detected. "
            "Review before selecting parameters."
        )


# ============================================================
# Summarize and select
# ============================================================

def analyze(rows):

    summaries = summarize_runs(
        rows,
        PARAMETER_FIELDS,
    )

    assert len(summaries) == 55

    write_csv(
        OUTPUT_DIR / "summary.csv",
        summaries,
    )

    result = select_parameters(
        summaries,
        PARAMETER_FIELDS,
    )

    ranking = result["ranking"]

    pareto = result["pareto"]

    selected = result["selected"]

    write_csv(
        OUTPUT_DIR / "ranking.csv",
        ranking,
    )

    write_csv(
        OUTPUT_DIR / "pareto.csv",
        pareto,
    )

    data = {
        "method": METHOD,

        "selected_alpha_min":
            selected["alpha_min"],

        "selected_alpha_max":
            selected["alpha_max"],

        "original_alpha_range":
            list(cfg.ORIGINAL_DYNAMIC_ALPHA_RANGE),

        "candidate_count":
            len(summaries),

        "feasible_count":
            len(ranking),

        "pareto_count":
            len(pareto),

        "selection_method":
            "Completion screening + Pareto + Rank Sum",

        "selected_result":
            selected,
    }

    write_json(
        OUTPUT_DIR / "selected_parameters.json",
        data,
    )

    return summaries, result


# ============================================================
# Print final result
# ============================================================

def print_results(summaries, result):

    ranking_by_range = {
        (
            row["alpha_min"],
            row["alpha_max"],
        ): row
        for row in result["ranking"]
    }

    print()
    print("=" * 150)
    print("DYNAMIC CALIBRATION SUMMARY")
    print("=" * 150)

    print(
        f"{'Range':>12} "
        f"{'Comp%':>8} "
        f"{'Min%':>8} "
        f"{'AvgWait':>10} "
        f"{'P95Wait':>10} "
        f"{'High':>10} "
        f"{'Emer':>10} "
        f"{'Travel':>13} "
        f"{'JainTask':>10} "
        f"{'JainUtil':>10} "
        f"{'RankSum':>8} "
        f"{'Pareto':>7} "
        f"{'Selected':>8}"
    )

    for row in summaries:

        lo = row["alpha_min"]
        hi = row["alpha_max"]

        label = f"[{lo:.1f},{hi:.1f}]"

        rank = ranking_by_range.get((lo, hi))

        rank_text = (
            f"{rank['rank_sum']:.1f}"
            if rank is not None
            else "-"
        )

        pareto_text = (
            "YES"
            if rank and rank["pareto_optimal"]
            else "NO"
        )

        selected_text = (
            "YES"
            if rank and rank["selected"]
            else "NO"
        )

        print(
            f"{label:>12} "
            f"{row['mean_completion_rate']*100:>8.2f} "
            f"{row['min_completion_rate']*100:>8.2f} "
            f"{row['mean_average_waiting_time_s']:>10.2f} "
            f"{row['mean_p95_waiting_time_s']:>10.2f} "
            f"{row['mean_high_waiting_time_s']:>10.2f} "
            f"{row['mean_emergency_waiting_time_s']:>10.2f} "
            f"{row['mean_total_travel_time_s']:>13.2f} "
            f"{row['mean_jain_task_fairness']:>10.4f} "
            f"{row['mean_jain_utilization_fairness']:>10.4f} "
            f"{rank_text:>8} "
            f"{pareto_text:>7} "
            f"{selected_text:>8}"
        )

    print()
    print("===== TOP 10 DYNAMIC CANDIDATES =====")

    for index, row in enumerate(
        result["ranking"][:10], 1
    ):

        print(
            f"Rank {index:02d} | "
            f"[{row['alpha_min']:.1f},"
            f"{row['alpha_max']:.1f}] | "
            f"rank_sum={row['rank_sum']:.1f} | "
            f"pareto={row['pareto_optimal']} | "
            f"selected={row['selected']}"
        )

    selected = result["selected"]

    print()
    print("===== FINAL DYNAMIC SELECTION =====")

    print("Total candidates:", len(summaries))
    print("Feasible candidates:", len(result["ranking"]))
    print("Pareto candidates:", len(result["pareto"]))

    print(
        "Original range:",
        cfg.ORIGINAL_DYNAMIC_ALPHA_RANGE,
    )

    print(
        "Selected range:",
        (
            selected["alpha_min"],
            selected["alpha_max"],
        ),
    )

    print("Rank sum:", selected["rank_sum"])

    for metric in cfg.PRIMARY_METRICS:

        print(
            f"{metric}: "
            f"{selected[f'mean_{metric}']:.6f} "
            f"| rank={selected[f'rank_{metric}']}"
        )

    print()
    print("Output directory:", OUTPUT_DIR)

    for name in OUTPUT_FILES:
        print("Saved:", name)

    print()
    print("DYNAMIC CALIBRATION: COMPLETE")


def main():

    print("=" * 80)
    print("BATTERY-AWARE DYNAMIC WEIGHT CALIBRATION V2")
    print("=" * 80)

    validate_environment()

    validate_grid()

    prepare_output()

    save_metadata()

    rows = run_all()

    validate_run_matrix(rows)

    summaries, result = analyze(rows)

    validate_environment()

    print_results(summaries, result)


if __name__ == "__main__":
    main()
