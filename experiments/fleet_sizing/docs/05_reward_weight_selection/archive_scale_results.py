from __future__ import annotations

import csv
import json
import math
import shutil
import hashlib

from pathlib import Path
from statistics import mean, stdev
from collections import defaultdict
from itertools import product
from datetime import datetime, timezone


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ROOT = PROJECT_ROOT / "experiments/fleet_sizing"

HISTORICAL = ROOT / "results_rl"

DIAGNOSTICS = (
    ROOT / "results/reward_scale_diagnostics_v2"
)

OUTPUT = (
    Path(__file__).resolve().parent
    / "data/scale_selection"
)

METRICS = (
    "completion_rate",
    "avg_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel",
    "jain_fairness",
)

MODEL_SEEDS = tuple(range(7101, 7106))

EVAL_SEEDS = tuple(range(9501, 9531))

FILES = []

CHECKED_VALUES = 0


# ============================================================
# Helpers
# ============================================================

def sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_csv(path):

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(csv.DictReader(f))


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def assert_close(actual, expected, label):

    global CHECKED_VALUES

    actual = float(actual)
    expected = float(expected)

    assert math.isfinite(actual), label
    assert math.isfinite(expected), label

    assert math.isclose(
        actual,
        expected,
        rel_tol=1e-9,
        abs_tol=1e-8,
    ), (label, actual, expected)

    CHECKED_VALUES += 1


def group_rows(rows, fields):

    groups = defaultdict(list)

    for row in rows:

        key = tuple(
            int(float(row[field]))
            for field in fields
        )

        groups[key].append(row)

    return groups


def add_file(source, destination):

    assert source.is_file(), source

    FILES.append(
        (source, OUTPUT / destination)
    )


def check_episode_metrics(rows):

    for row in rows:

        for metric in METRICS:

            value = float(row[metric])

            assert math.isfinite(value)
            assert value >= 0

            if metric in (
                "completion_rate",
                "jain_fairness",
            ):

                assert value <= 1


# ============================================================
# A. Scale Sensitivity
# ============================================================

def verify_sensitivity():

    folder = (
        HISTORICAL / "scale_sensitivity_eval"
    )

    runs = read_csv(
        folder / "episode_results.csv"
    )

    summaries = read_csv(
        folder / "summary.csv"
    )

    assert len(runs) == 120
    assert len(summaries) == 4

    check_episode_metrics(runs)

    groups = group_rows(
        runs,
        ("scale",),
    )

    assert set(groups) == {
        (150,), (200,), (300,), (600,)
    }

    summary_map = {
        int(row["scale"]): row
        for row in summaries
    }

    assert len(summary_map) == 4

    for (scale,), rows in groups.items():

        assert len(rows) == 30

        assert sorted(
            int(row["seed"])
            for row in rows
        ) == list(EVAL_SEEDS)

        summary = summary_map[scale]

        for metric in METRICS:

            expected = mean(
                float(row[metric])
                for row in rows
            )

            assert_close(
                summary[metric],
                expected,
                ("sensitivity", scale, metric),
            )

    for name in (
        "episode_results.csv",
        "summary.csv",
    ):

        add_file(
            folder / name,
            f"sensitivity/{name}",
        )

    print("Scale sensitivity: PASS")
    print("  Episodes: 120")
    print("  Scales: 150, 200, 300, 600")


# ============================================================
# B/C/D. Multi-seed experiments
# ============================================================

def verify_multiseed(
    source_name,
    destination_name,
    fields,
    expected_configs,
):

    folder = HISTORICAL / source_name

    runs = read_csv(
        folder / "episode_results.csv"
    )

    models = read_csv(
        folder / "model_seed_summary.csv"
    )

    aggregate = read_csv(
        folder / "aggregate_summary.csv"
    )

    assert len(runs) == 300
    assert len(models) == 10
    assert len(aggregate) == 2

    check_episode_metrics(runs)

    model_fields = (
        *fields,
        "model_seed",
    )

    groups = group_rows(
        runs,
        model_fields,
    )

    expected_models = {
        (*config, seed)
        for config in expected_configs
        for seed in MODEL_SEEDS
    }

    assert set(groups) == expected_models

    saved_models = group_rows(
        models,
        model_fields,
    )

    assert set(saved_models) == expected_models

    for key, rows in groups.items():

        assert len(rows) == 30

        assert sorted(
            int(row["eval_seed"])
            for row in rows
        ) == list(EVAL_SEEDS)

        assert len(saved_models[key]) == 1

        summary = saved_models[key][0]

        for metric in METRICS:

            expected = mean(
                float(row[metric])
                for row in rows
            )

            assert_close(
                summary[metric],
                expected,
                (source_name, key, metric),
            )

    config_groups = group_rows(
        models,
        fields,
    )

    saved_aggregate = group_rows(
        aggregate,
        fields,
    )

    assert set(config_groups) == set(
        expected_configs
    )

    assert set(saved_aggregate) == set(
        expected_configs
    )

    for key, rows in config_groups.items():

        assert len(rows) == 5

        assert len(saved_aggregate[key]) == 1

        summary = saved_aggregate[key][0]

        for metric in METRICS:

            values = [
                float(row[metric])
                for row in rows
            ]

            assert_close(
                summary[f"{metric}_mean"],
                mean(values),
                (source_name, key, metric, "mean"),
            )

            assert_close(
                summary[f"{metric}_model_seed_std"],
                stdev(values),
                (source_name, key, metric, "std"),
            )

    for name in (
        "episode_results.csv",
        "model_seed_summary.csv",
        "aggregate_summary.csv",
    ):

        add_file(
            folder / name,
            f"{destination_name}/{name}",
        )

    print(f"{destination_name}: PASS")
    print("  Episodes: 300")
    print("  Models: 10")
    print("  Configurations:", expected_configs)


# ============================================================
# Shared R600/O600 consistency
# ============================================================

def verify_shared_control():

    def load_shared(name):

        rows = read_csv(
            HISTORICAL
            / name
            / "episode_results.csv"
        )

        filtered = [
            row for row in rows
            if int(row["reward_scale"]) == 600
            and int(row["observation_scale"]) == 600
        ]

        indexed = {
            (
                int(row["model_seed"]),
                int(row["eval_seed"]),
            ): row
            for row in filtered
        }

        assert len(filtered) == len(indexed) == 150

        return indexed

    reward = load_shared(
        "decoupled_reward_scale_eval"
    )

    observation = load_shared(
        "decoupled_observation_scale_eval"
    )

    expected = set(
        product(MODEL_SEEDS, EVAL_SEEDS)
    )

    assert set(reward) == expected
    assert set(observation) == expected

    for key in expected:

        for metric in METRICS:

            assert_close(
                reward[key][metric],
                observation[key][metric],
                ("shared_control", key, metric),
            )

    print("Shared R600/O600 control: PASS")
    print("  Matched episodes: 150")
    print("  Matched metric values: 1050")


# ============================================================
# Diagnostic results
# ============================================================

def verify_diagnostics():

    specifications = (
        (
            "pilot",
            18,
            {
                "historical_behavior": 6,
                "corrected_behavior": 42,
                "reference_control": 42,
            },
        ),
        (
            "full_reproduction",
            300,
            {
                "corrected_behavior": 1050,
                "reference_control": 1050,
            },
        ),
    )

    historical_rows = read_csv(
        HISTORICAL
        / "decoupled_reward_scale_eval"
        / "episode_results.csv"
    )

    old = {
        (
            int(row["reward_scale"]),
            int(row["model_seed"]),
            int(row["eval_seed"]),
        ): row
        for row in historical_rows
    }

    assert len(old) == 300

    for name, n_episodes, expected in specifications:

        folder = DIAGNOSTICS / name

        runs = read_csv(
            folder / "episode_results.csv"
        )

        comparisons = read_csv(
            folder / "historical_comparison.csv"
        )

        summary = read_csv(
            folder / "summary.csv"
        )

        metadata = read_json(
            folder / "diagnostic_metadata.json"
        )

        assert len(runs) == n_episodes

        assert len(comparisons) == (
            n_episodes * len(METRICS)
        )

        assert len(summary) == len(expected)

        assert metadata["episodes"] == n_episodes

        assert metadata["model_retrained"] is False

        indexed_runs = {
            (
                row["case"],
                int(row["model_seed"]),
                int(row["eval_seed"]),
            ): row
            for row in runs
        }

        assert len(indexed_runs) == n_episodes

        matched = defaultdict(int)

        comparison_keys = set()

        for row in comparisons:

            key = (
                row["case"],
                int(row["model_seed"]),
                int(row["eval_seed"]),
            )

            metric = row["metric"]

            assert metric in METRICS

            full_key = (*key, metric)

            assert full_key not in comparison_keys

            comparison_keys.add(full_key)

            current = indexed_runs[key]

            historical = old[
                (
                    int(current["reward_scale"]),
                    key[1],
                    key[2],
                )
            ]

            assert_close(
                row["historical_value"],
                historical[metric],
                ("historical", full_key),
            )

            assert_close(
                row["current_value"],
                current[metric],
                ("current", full_key),
            )

            equal = math.isclose(
                float(row["current_value"]),
                float(row["historical_value"]),
                rel_tol=1e-9,
                abs_tol=1e-8,
            )

            assert equal == (
                row["matches"].lower() == "true"
            )

            matched[key[0]] += int(equal)

        assert len(comparison_keys) == (
            n_episodes * len(METRICS)
        )

        assert dict(matched) == expected

        for row in summary:

            case = row["case"]

            selected = [
                run for run in runs
                if run["case"] == case
            ]

            assert len(selected) == int(
                row["episodes"]
            )

            assert int(
                row["historical_metrics_matched"]
            ) == expected[case]

            for metric in METRICS:

                assert_close(
                    row[metric],
                    mean(
                        float(run[metric])
                        for run in selected
                    ),
                    (name, case, metric),
                )

        for name_file in (
            "episode_results.csv",
            "historical_comparison.csv",
            "summary.csv",
            "diagnostic_metadata.json",
        ):

            add_file(
                folder / name_file,
                f"diagnostics/{name}/{name_file}",
            )

        print(f"{name}: PASS")
        print("  Episodes:", n_episodes)
        print("  Historical matches:", dict(matched))


# ============================================================
# Historical model metadata
# ============================================================

def verify_training_metadata():

    root = HISTORICAL / "metadata"

    patterns = (
        "scale_sensitivity_*.json",
        "scale_confirm_*.json",
        "decoupled_*.json",
    )

    paths = sorted({
        path
        for pattern in patterns
        for path in root.glob(pattern)
    })

    assert len(paths) == 29

    for path in paths:

        metadata = read_json(path)

        assert metadata["total_timesteps"] == 50000

        assert metadata["battery_model_enabled"] is True

        assert metadata["fleet_configuration"] == [
            2, 2, 3
        ]

        assert metadata["workload_multiplier"] == 4.0

        model = (
            HISTORICAL
            / "models"
            / path.stem
            / "final_model.zip"
        )

        assert model.is_file(), model

        add_file(
            path,
            f"training_metadata/{path.name}",
        )

    print("Scale training metadata: PASS")
    print("  Metadata files:", len(paths))
    print("  Corresponding model files:", len(paths))


# ============================================================
# Copy only after validation
# ============================================================

def archive():

    assert not OUTPUT.exists(), (
        "Refusing to overwrite existing archive",
        OUTPUT,
    )

    destinations = [
        destination
        for _, destination in FILES
    ]

    assert len(destinations) == len(
        set(destinations)
    )

    before = {
        str(source): sha256(source)
        for source, _ in FILES
    }

    OUTPUT.mkdir(
        parents=True,
        exist_ok=False,
    )

    records = []

    for source, destination in FILES:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(source, destination)

        expected = before[str(source)]

        assert sha256(destination) == expected
        assert sha256(source) == expected

        records.append({
            "source": str(
                source.relative_to(PROJECT_ROOT)
            ),
            "archive": str(
                destination.relative_to(OUTPUT)
            ),
            "sha256": expected,
            "size_bytes": destination.stat().st_size,
        })

        print(
            "COPY PASS:",
            destination.relative_to(OUTPUT),
        )

    manifest = {
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "historical_experiments": 4,
        "historical_training_models": 29,
        "historical_episode_records": 1020,
        "pilot_diagnostic_episodes": 18,
        "full_reproduction_episodes": 300,
        "full_reproduction_metric_matches": 2100,
        "full_reproduction_mismatches": 0,
        "numeric_values_verified": CHECKED_VALUES,
        "retained_reward_approach_scale_s": 600,
        "retained_observation_approach_scale_s": 600,
        "copied_files": len(records),
        "historical_files_modified": False,
        "new_model_training": False,
        "new_simulation_runs": 0,
        "files": records,
    }

    with (OUTPUT / "archive_manifest.json").open(
        "x",
        encoding="utf-8",
    ) as f:

        json.dump(
            manifest,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("===== ARCHIVE SUMMARY =====")
    print("Copied files:", len(records))
    print("Numeric values verified:", CHECKED_VALUES)
    print("Archived file SHA256: PASS")
    print("Historical data modified: NO")
    print("New simulation runs: 0")
    print("Models retrained: NO")
    print("SCALE DATA ARCHIVE: COMPLETE")


# ============================================================
# Main
# ============================================================

def main():

    print("===== SCALE EXPERIMENT VALIDATION =====")

    verify_sensitivity()

    verify_multiseed(
        "scale_confirmation_eval",
        "confirmation",
        ("scale",),
        ((150,), (200,)),
    )

    verify_multiseed(
        "decoupled_reward_scale_eval",
        "decoupled_reward",
        ("reward_scale", "observation_scale"),
        ((150, 600), (600, 600)),
    )

    verify_multiseed(
        "decoupled_observation_scale_eval",
        "decoupled_observation",
        ("reward_scale", "observation_scale"),
        ((600, 150), (600, 600)),
    )

    verify_shared_control()

    verify_diagnostics()

    verify_training_metadata()

    assert len(FILES) == 48

    print()
    print("ALL SCALE DATA VALIDATION: PASS")
    print()

    archive()


if __name__ == "__main__":

    main()
