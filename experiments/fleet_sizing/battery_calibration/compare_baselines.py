from __future__ import annotations

import csv
import json
import math

from collections import Counter
from statistics import mean, pstdev

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
    sha256_file,
)

from experiments.fleet_sizing import config as base_config


ROOT = cfg.RESULTS_ROOT
OUTPUT = ROOT / "baseline_comparison"

METHOD_DIRS = {
    "random_feasible": "random",
    "projected_nearest": "nearest",
    "static_weighted": "static",
    "dynamic_weighted": "dynamic",
}

EXPECTED_RAW_COUNTS = {
    "random_feasible": 10,
    "projected_nearest": 10,
    "static_weighted": 110,
    "dynamic_weighted": 550,
}

POPULATION_FIELDS = (
    "generated_tasks",
    "high_only_generated_count",
    "emergency_generated_count",
    "high_emergency_generated_count",
)

EXCLUDED_FIELDS = {
    "method",
    "seed",
    "alpha",
    "alpha_min",
    "alpha_max",
    "episode_reward",
    "battery_enabled",
    "workload_multiplier",
}

RESERVE = base_config.BATTERY_MIN_RESERVE_SOC

OUTPUT_FILES = (
    "comparison_runs.csv",
    "comparison_summary.csv",
    "comparison_metadata.json",
)


# ============================================================
# Utilities
# ============================================================

def read_csv(path):

    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path):

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_csv(path, rows):

    with path.open(
        "x",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0]),
        )

        writer.writeheader()
        writer.writerows(rows)


def prepare_output():

    OUTPUT.mkdir(parents=True, exist_ok=True)

    existing = [
        OUTPUT / name
        for name in OUTPUT_FILES
        if (OUTPUT / name).exists()
    ]

    if existing:
        raise FileExistsError(
            f"Refusing to overwrite: {existing}"
        )


# ============================================================
# Read frozen parameter selections
# ============================================================

def load_selections():

    static = read_json(
        ROOT / "static/selected_parameters.json"
    )

    dynamic = read_json(
        ROOT / "dynamic/selected_parameters.json"
    )

    alpha = float(static["selected_alpha"])

    lo = float(dynamic["selected_alpha_min"])

    hi = float(dynamic["selected_alpha_max"])

    assert alpha == 0.6
    assert (lo, hi) == (0.4, 0.9)

    return {
        "random_feasible": {},
        "projected_nearest": {},
        "static_weighted": {
            "alpha": alpha,
        },
        "dynamic_weighted": {
            "alpha_min": lo,
            "alpha_max": hi,
        },
    }


# ============================================================
# Recalculate and validate stored summaries
# ============================================================

def metric_fields(rows):

    fields = [
        field for field in rows[0]
        if field not in EXCLUDED_FIELDS
    ]

    for row in rows:

        for field in fields:

            assert math.isfinite(
                float(row[field])
            ), field

    return fields


def validate_stored_summary(
    rows,
    stored,
    fields,
):

    checked = 0

    for field in fields:

        values = [
            float(row[field])
            for row in rows
        ]

        for prefix, calculated in (
            ("mean", mean(values)),
            ("std", pstdev(values)),
        ):

            name = f"{prefix}_{field}"

            assert math.isclose(
                calculated,
                float(stored[name]),
                rel_tol=1e-10,
                abs_tol=1e-9,
            ), (name, calculated, stored[name])

            checked += 1

    assert math.isclose(
        min(float(r["completion_rate"]) for r in rows),
        float(stored["min_completion_rate"]),
        abs_tol=1e-10,
    )

    return checked


# ============================================================
# Load and validate each method
# ============================================================

def load_method(method, parameters):

    directory = ROOT / METHOD_DIRS[method]

    runs = read_csv(directory / "runs.csv")

    summaries = read_csv(directory / "summary.csv")

    metadata = read_json(
        directory / "experiment_metadata.json"
    )

    assert len(runs) == EXPECTED_RAW_COUNTS[method]

    assert metadata["method"] == method
    assert metadata["battery_enabled"] is True

    assert tuple(metadata["fleet"]) == (
        cfg.FLEET_CONFIGURATION
    )

    assert metadata["workload_multiplier"] == (
        cfg.WORKLOAD_MULTIPLIER
    )

    assert metadata["simulation_days"] == (
        cfg.SIMULATION_DAYS
    )

    assert all(
        row["method"] == method
        and row["battery_enabled"] == "True"
        and float(row["workload_multiplier"])
        == cfg.WORKLOAD_MULTIPLIER
        for row in runs
    )

    # Verify recorded environment hashes.
    nav = metadata["navigation"]

    assert nav["nav_graph_sha256"] == (
        cfg.NAV_GRAPH_SHA256
    )

    assert nav["route_summary_sha256"] == (
        cfg.ROUTE_SUMMARY_SHA256
    )

    assert nav["route_results_sha256"] == (
        cfg.ROUTE_RESULTS_SHA256
    )

    assert metadata["frozen_ppo"]["sha256"] == (
        cfg.PPO_MODEL_SHA256
    )

    # Verify source hashes where originally recorded.
    source_hashes = metadata.get(
        "source_sha256", {}
    )

    for path, expected in source_hashes.items():

        assert sha256_file(
            cfg.PROJECT_ROOT / path
        ) == expected, path

    selected = [
        row for row in runs
        if all(
            float(row[field]) == value
            for field, value in parameters.items()
        )
    ]

    stored = [
        row for row in summaries
        if all(
            float(row[field]) == value
            for field, value in parameters.items()
        )
    ]

    assert len(selected) == 10
    assert len(stored) == 1

    seeds = [
        int(row["seed"])
        for row in selected
    ]

    assert len(set(seeds)) == 10

    assert set(seeds) == set(
        cfg.CALIBRATION_SEEDS
    )

    fields = metric_fields(selected)

    checked = validate_stored_summary(
        selected,
        stored[0],
        fields,
    )

    for row in selected:

        generated = int(row["generated_tasks"])
        completed = int(row["completed_tasks"])

        assert generated > 0
        assert 0 <= completed <= generated

        assert math.isclose(
            float(row["completion_rate"]),
            completed / generated,
            abs_tol=1e-10,
        )

        assert float(
            row["minimum_robot_soc"]
        ) >= RESERVE - 1e-9

    print()
    print("Method:", method)
    print("Original rows:", len(runs))
    print("Selected rows:", len(selected))
    print("Parameters:", parameters)
    print("Summary values verified:", checked)
    print("Source hashes verified:", len(source_hashes))
    print("Method validation: PASS")

    return selected, fields, checked


# ============================================================
# Standardize run records
# ============================================================

def standardize(row, fields, selections):

    parameters = selections[row["method"]]

    return {
        "method": row["method"],
        "seed": int(row["seed"]),
        "workload_multiplier": float(
            row["workload_multiplier"]
        ),
        "battery_enabled": True,

        "alpha": parameters.get("alpha", ""),
        "alpha_min": parameters.get("alpha_min", ""),
        "alpha_max": parameters.get("alpha_max", ""),

        **{
            field: float(row[field])
            for field in fields
        },
    }


# ============================================================
# Cross-method validation
# ============================================================

def validate_comparison(rows):

    expected = {
        (method, seed)
        for method in METHOD_DIRS
        for seed in cfg.CALIBRATION_SEEDS
    }

    actual = [
        (row["method"], row["seed"])
        for row in rows
    ]

    assert len(rows) == 40
    assert set(actual) == expected

    assert all(
        count == 1
        for count in Counter(actual).values()
    )

    for seed in cfg.CALIBRATION_SEEDS:

        group = [
            row for row in rows
            if row["seed"] == seed
        ]

        assert len(group) == 4

        for field in POPULATION_FIELDS:

            values = {
                row[field]
                for row in group
            }

            assert len(values) == 1, (
                seed, field, values
            )

    print()
    print("===== CROSS-METHOD VALIDATION =====")
    print("Methods: 4")
    print("Seeds per method: 10")
    print("Comparison runs: 40")
    print("Duplicates: 0")
    print("Missing runs: 0")
    print("Task population consistency: PASS")
    print("Battery reserve: PASS")
    print("Comparison matrix: PASS")


# ============================================================
# Unified summaries
# ============================================================

def summarize(rows, fields, selections):

    summaries = []

    for method in METHOD_DIRS:

        group = [
            row for row in rows
            if row["method"] == method
        ]

        parameters = selections[method]

        summary = {
            "method": method,
            "runs": len(group),
            "workload_multiplier":
                cfg.WORKLOAD_MULTIPLIER,
            "battery_enabled": True,
            "alpha":
                parameters.get("alpha", ""),
            "alpha_min":
                parameters.get("alpha_min", ""),
            "alpha_max":
                parameters.get("alpha_max", ""),
        }

        for field in fields:

            values = [
                row[field]
                for row in group
            ]

            summary[f"mean_{field}"] = mean(values)

            summary[f"std_{field}"] = pstdev(values)

        summary["min_completion_rate"] = min(
            row["completion_rate"]
            for row in group
        )

        summary["min_observed_soc"] = min(
            row["minimum_robot_soc"]
            for row in group
        )

        summary["reserve_violations"] = sum(
            row["minimum_robot_soc"] < RESERVE - 1e-9
            for row in group
        )

        summaries.append(summary)

    return summaries


# ============================================================
# Console comparison
# ============================================================

def print_comparison(summaries):

    print()
    print("=" * 140)
    print("FOUR BASELINE COMPARISON")
    print("=" * 140)

    print(
        f"{'Method':<22}"
        f"{'Comp%':>8}"
        f"{'AvgWait':>10}"
        f"{'P95Wait':>10}"
        f"{'High':>10}"
        f"{'Emer':>10}"
        f"{'Travel':>14}"
        f"{'JainTask':>10}"
        f"{'JainUtil':>10}"
        f"{'MinSOC%':>10}"
        f"{'Charges':>9}"
    )

    for row in summaries:

        print(
            f"{row['method']:<22}"
            f"{row['mean_completion_rate']*100:>8.2f}"
            f"{row['mean_average_waiting_time_s']:>10.2f}"
            f"{row['mean_p95_waiting_time_s']:>10.2f}"
            f"{row['mean_high_waiting_time_s']:>10.2f}"
            f"{row['mean_emergency_waiting_time_s']:>10.2f}"
            f"{row['mean_total_travel_time_s']:>14.2f}"
            f"{row['mean_jain_task_fairness']:>10.4f}"
            f"{row['mean_jain_utilization_fairness']:>10.4f}"
            f"{row['min_observed_soc']*100:>10.2f}"
            f"{row['mean_total_charging_count']:>9.2f}"
        )

    print()
    print("===== BEST METHOD PER PRIMARY METRIC =====")

    for field, direction in cfg.PRIMARY_METRICS.items():

        best = max(
            summaries,
            key=lambda row:
                direction * row[f"mean_{field}"],
        )

        print(
            f"{field}: {best['method']} | "
            f"{best[f'mean_{field}']:.8f}"
        )


# ============================================================
# Main
# ============================================================

def main():

    validate_environment()

    prepare_output()

    selections = load_selections()

    rows = []

    common_fields = None

    checked_total = 0

    for method in METHOD_DIRS:

        selected, fields, checked = load_method(
            method,
            selections[method],
        )

        if common_fields is None:

            common_fields = fields

        else:

            assert set(fields) == set(common_fields), (
                method,
                set(fields) ^ set(common_fields),
            )

        rows.extend(
            standardize(
                row,
                common_fields,
                selections,
            )
            for row in selected
        )

        checked_total += checked

    validate_comparison(rows)

    summaries = summarize(
        rows,
        common_fields,
        selections,
    )

    validate_environment()

    write_csv(
        OUTPUT / "comparison_runs.csv",
        rows,
    )

    write_csv(
        OUTPUT / "comparison_summary.csv",
        summaries,
    )

    source_paths = [
        ROOT / folder / filename
        for folder in METHOD_DIRS.values()
        for filename in (
            "runs.csv",
            "summary.csv",
            "experiment_metadata.json",
        )
    ]

    source_paths += [
        ROOT / "static/selected_parameters.json",
        ROOT / "dynamic/selected_parameters.json",
    ]

    metadata = {
        "experiment":
            "battery_four_baseline_comparison_v2",

        "scope":
            "Calibration-scenario preliminary comparison",

        "methods": list(METHOD_DIRS),

        "parameters": selections,

        "fleet": list(cfg.FLEET_CONFIGURATION),

        "workload_multiplier":
            cfg.WORKLOAD_MULTIPLIER,

        "simulation_days":
            cfg.SIMULATION_DAYS,

        "battery_enabled": True,

        "battery_reserve_soc": RESERVE,

        "seeds": list(cfg.CALIBRATION_SEEDS),

        "original_calibration_and_evaluation_runs": 680,

        "comparison_runs": 40,

        "summary_values_verified": checked_total,

        "primary_metrics": cfg.PRIMARY_METRICS,

        "independent_test": False,

        "new_simulations": 0,

        "source_data_sha256": {
            str(path.relative_to(cfg.PROJECT_ROOT)):
                sha256_file(path)
            for path in source_paths
        },
    }

    with (
        OUTPUT / "comparison_metadata.json"
    ).open("x", encoding="utf-8") as f:

        json.dump(
            metadata,
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    print_comparison(summaries)

    print()
    print("===== FINAL VALIDATION =====")
    print("Summary values verified:", checked_total)
    print("Shared metric count:", len(common_fields))
    print("Original simulation records: 680")
    print("Selected comparison records: 40")
    print("Summary records:", len(summaries))
    print("New simulations: 0")
    print("Output:", OUTPUT)
    print("BASELINE COMPARISON: COMPLETE")


if __name__ == "__main__":
    main()
