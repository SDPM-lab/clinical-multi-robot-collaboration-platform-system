from __future__ import annotations

import csv
import json
import time
import sys
import subprocess

from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
    run_baseline_episode,
)

from experiments.fleet_sizing.battery_calibration.selection import (
    summarize_runs,
    select_parameters,
)


METHOD = "static_weighted"

PARAMETER_FIELDS = ["alpha"]

OUTPUT_DIR = cfg.STATIC_OUTPUT_DIR


# ============================================================
# Output files
# ============================================================

OUTPUT_FILES = (
    "runs.csv",
    "summary.csv",
    "pareto.csv",
    "ranking.csv",
    "selected_parameters.json",
    "experiment_metadata.json",
)


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
            "Refusing to overwrite existing files:\n"
            + "\n".join(str(p) for p in existing)
        )


def write_csv(path, rows):

    if not rows:
        raise ValueError(f"No rows for {path}")

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

    metadata = {
        "experiment": "battery_static_calibration_v2",
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

        "fleet": list(cfg.FLEET_CONFIGURATION),
        "workload_multiplier": cfg.WORKLOAD_MULTIPLIER,
        "simulation_days": cfg.SIMULATION_DAYS,
        "battery_enabled": cfg.ENABLE_BATTERY_MODEL,

        "alphas": list(cfg.STATIC_ALPHAS),
        "calibration_seeds": list(cfg.CALIBRATION_SEEDS),

        "expected_runs": (
            len(cfg.STATIC_ALPHAS)
            * len(cfg.CALIBRATION_SEEDS)
        ),

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
            "All feasible static candidates",

        "rank_ties":
            "Average rank for exact ties",

        "navigation": {
            "nav_graph": str(cfg.NAV_GRAPH_PATH),
            "nav_graph_sha256": cfg.NAV_GRAPH_SHA256,
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
# Validate full run matrix
# ============================================================

def validate_run_matrix(rows):

    expected_keys = {
        (float(alpha), int(seed))
        for alpha in cfg.STATIC_ALPHAS
        for seed in cfg.CALIBRATION_SEEDS
    }

    actual_keys = [
        (
            float(row["alpha"]),
            int(row["seed"]),
        )
        for row in rows
    ]

    counts = Counter(actual_keys)

    if any(count != 1 for count in counts.values()):
        raise RuntimeError("Duplicate experiment runs")

    if set(actual_keys) != expected_keys:
        raise RuntimeError("Incomplete experiment matrix")

    for row in rows:

        if row["method"] != METHOD:
            raise RuntimeError("Unexpected method")

        if not row["battery_enabled"]:
            raise RuntimeError("Battery model disabled")

        if row["workload_multiplier"] != (
            cfg.WORKLOAD_MULTIPLIER
        ):
            raise RuntimeError("Unexpected workload")

    # All alphas should receive the same generated
    # task count under the same scenario seed.

    for seed in cfg.CALIBRATION_SEEDS:

        generated_counts = {
            int(row["generated_tasks"])
            for row in rows
            if int(row["seed"]) == seed
        }

        if len(generated_counts) != 1:

            raise RuntimeError(
                f"Task count mismatch for seed {seed}"
            )

    print()
    print("===== RUN MATRIX VALIDATION =====")
    print("Expected runs:", len(expected_keys))
    print("Actual runs:", len(rows))
    print("Unique runs:", len(counts))
    print("Seed consistency: PASS")
    print("Generated task count consistency: PASS")
    print("Battery enabled for all runs: PASS")
    print("Run matrix: PASS")


# ============================================================
# Execute Static calibration
# ============================================================

def run_all():

    rows = []

    total = (
        len(cfg.STATIC_ALPHAS)
        * len(cfg.CALIBRATION_SEEDS)
    )

    index = 0

    start = time.perf_counter()

    # Save each completed run immediately.

    path = OUTPUT_DIR / "runs.csv"

    with path.open(
        "x",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = None

        for alpha in cfg.STATIC_ALPHAS:

            print()
            print("=" * 80)
            print(f"STATIC ALPHA = {alpha:.1f}")
            print("=" * 80)

            for seed in cfg.CALIBRATION_SEEDS:

                index += 1

                row = run_baseline_episode(
                    method=METHOD,
                    seed=seed,
                    alpha=alpha,
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
                    f"alpha={alpha:.1f} "
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

    elapsed = time.perf_counter() - start

    print()
    print("Total elapsed seconds:", round(elapsed, 2))

    return rows


# ============================================================
# Summarize and select
# ============================================================

def analyze(rows):

    summaries = summarize_runs(
        rows,
        PARAMETER_FIELDS,
    )

    if len(summaries) != len(cfg.STATIC_ALPHAS):
        raise RuntimeError(
            "Unexpected number of candidates"
        )

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

    selected_data = {
        "method": METHOD,

        "selected_alpha":
            selected["alpha"],

        "original_alpha":
            cfg.ORIGINAL_STATIC_ALPHA,

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
        selected_data,
    )

    return summaries, result


# ============================================================
# Console output
# ============================================================

def print_results(summaries, result):

    ranking_by_alpha = {
        row["alpha"]: row
        for row in result["ranking"]
    }

    print()
    print("=" * 140)
    print("STATIC CALIBRATION SUMMARY")
    print("=" * 140)

    print(
        f"{'Alpha':>5} "
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

        rank = ranking_by_alpha.get(row["alpha"])

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
            f"{row['alpha']:>5.1f} "
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
    print("===== FINAL STATIC SELECTION =====")

    selected = result["selected"]

    print("Total candidates:", len(summaries))
    print("Feasible candidates:", len(result["ranking"]))
    print("Pareto candidates:", len(result["pareto"]))
    print("Original alpha:", cfg.ORIGINAL_STATIC_ALPHA)
    print("Selected alpha:", selected["alpha"])
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
    print("STATIC CALIBRATION: COMPLETE")


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 80)
    print("BATTERY-AWARE STATIC WEIGHT CALIBRATION V2")
    print("=" * 80)

    validate_environment()

    prepare_output()

    save_metadata()

    rows = run_all()

    validate_run_matrix(rows)

    summaries, result = analyze(rows)

    validate_environment()

    print_results(
        summaries,
        result,
    )


if __name__ == "__main__":
    main()
