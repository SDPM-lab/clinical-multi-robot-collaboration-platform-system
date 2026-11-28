from __future__ import annotations

import csv
import hashlib
import json
import math

from pathlib import Path
from statistics import mean

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
)

from experiments.fleet_sizing.rl.evaluate_scale_sensitivity import (
    evaluate_one,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

ROOT = PROJECT_ROOT / "experiments/fleet_sizing"

RESULTS = ROOT / "results_rl"

OUTPUT = (
    ROOT
    / "results"
    / "reward_scale_diagnostics_v2"
    / "full_reproduction"
)

HISTORICAL_CSV = (
    RESULTS
    / "decoupled_reward_scale_eval"
    / "episode_results.csv"
)

MODEL_SEEDS = tuple(range(7101, 7106))

EVAL_SEEDS = tuple(range(9501, 9531))

METRICS = (
    "completion_rate",
    "avg_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel",
    "jain_fairness",
)

CASES = (
    ("corrected_behavior", 150, 600),
    ("reference_control", 600, 600),
)


def sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_historical():

    with HISTORICAL_CSV.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:

        rows = list(csv.DictReader(f))

    indexed = {}

    for row in rows:

        key = (
            int(row["reward_scale"]),
            int(row["observation_scale"]),
            int(row["model_seed"]),
            int(row["eval_seed"]),
        )

        if key in indexed:
            raise RuntimeError(
                f"Duplicate historical row: {key}"
            )

        indexed[key] = row

    return indexed


def main():

    if OUTPUT.exists():

        raise FileExistsError(
            f"Output already exists: {OUTPUT}"
        )

    print("===== ENVIRONMENT VALIDATION =====")

    validate_environment()

    historical = read_historical()

    protected_paths = [
        HISTORICAL_CSV,
        ROOT / "rl/evaluate_scale_sensitivity.py",
        ROOT / "rl/evaluate_decoupled_reward_scale.py",
        ROOT / "rl/environment.py",
        ROOT / "rl/observation.py",
        ROOT / "rl/reward.py",
        ROOT / "config.py",
    ]

    models = {}

    metadata = {}

    for reward_scale in (150, 600):

        for model_seed in MODEL_SEEDS:

            run_name = (
                f"decoupled_r{reward_scale}"
                f"_o600_seed{model_seed}_50k"
            )

            model_path = (
                RESULTS
                / "models"
                / run_name
                / "final_model.zip"
            )

            metadata_path = (
                RESULTS
                / "metadata"
                / f"{run_name}.json"
            )

            meta = json.loads(
                metadata_path.read_text(
                    encoding="utf-8"
                )
            )

            assert meta["model_seed"] == model_seed

            assert meta["total_timesteps"] == 50000

            assert meta["battery_model_enabled"] is True

            assert meta["fleet_configuration"] == [2, 2, 3]

            assert meta["workload_multiplier"] == 4.0

            assert (
                meta["reward_config"]["approach_scale_s"]
                == reward_scale
            )

            assert (
                meta["observation_approach_scale_s"]
                == 600.0
            )

            protected_paths.extend(
                (model_path, metadata_path)
            )

            metadata[(reward_scale, model_seed)] = meta

            models[(reward_scale, model_seed)] = model_path

    before_hashes = {
        str(path): sha256(path)
        for path in protected_paths
    }

    print()
    print("===== MODEL METADATA VALIDATION =====")
    print("Models verified:", len(models))
    print("Training observation scale: 600")
    print("Metadata validation: PASS")

    loaded_models = {}

    for key, path in models.items():

        model = MaskablePPO.load(
            path,
            device="cpu",
        )

        assert model.observation_space.shape == (98,)
        assert model.action_space.n == 7

        loaded_models[key] = model

    episode_rows = []

    comparison_rows = []

    counter = 0

    print()
    print("===== DIAGNOSTIC EPISODES =====")

    for case, reward_scale, observation_scale in CASES:

        for model_seed in MODEL_SEEDS:

            model = loaded_models[
                (reward_scale, model_seed)
            ]

            for eval_seed in EVAL_SEEDS:

                counter += 1

                result = evaluate_one(
                    model=model,
                    scale=reward_scale,
                    seed=eval_seed,
                    observation_scale=observation_scale,
                )

                old = historical[
                    (
                        reward_scale,
                        600,
                        model_seed,
                        eval_seed,
                    )
                ]

                row = {
                    "case": case,
                    "reward_scale": reward_scale,
                    "training_observation_scale": 600,
                    "evaluation_observation_scale":
                        observation_scale,
                    "model_seed": model_seed,
                    "eval_seed": eval_seed,
                }

                matches = 0

                for metric in METRICS:

                    actual = float(result[metric])
                    expected = float(old[metric])

                    assert math.isfinite(actual)

                    equal = math.isclose(
                        actual,
                        expected,
                        rel_tol=1e-9,
                        abs_tol=1e-8,
                    )

                    matches += int(equal)

                    row[metric] = actual

                    comparison_rows.append({
                        "case": case,
                        "model_seed": model_seed,
                        "eval_seed": eval_seed,
                        "metric": metric,
                        "historical_value": expected,
                        "current_value": actual,
                        "difference": actual - expected,
                        "matches": equal,
                    })

                row["historical_metrics_matched"] = matches

                episode_rows.append(row)

                print(
                    f"[{counter:03d}/300] "
                    f"{case} | "
                    f"seed={model_seed}/{eval_seed} | "
                    f"Avg={row['avg_waiting_time_s']:.2f} | "
                    f"P95={row['p95_waiting_time_s']:.2f} | "
                    f"Matches={matches}/7"
                )

    assert len(episode_rows) == 300
    assert len(comparison_rows) == 2100

    summary_rows = []

    print()
    print("===== DIAGNOSTIC SUMMARY =====")

    for case, reward_scale, observation_scale in CASES:

        rows = [
            row
            for row in episode_rows
            if row["case"] == case
        ]

        assert len(rows) == 150

        summary = {
            "case": case,
            "reward_scale": reward_scale,
            "evaluation_observation_scale":
                observation_scale,
            "episodes": len(rows),
        }

        for metric in METRICS:

            summary[metric] = mean(
                row[metric]
                for row in rows
            )

        summary["historical_metrics_matched"] = sum(
            row["historical_metrics_matched"]
            for row in rows
        )

        summary_rows.append(summary)

        print()
        print("Case:", case)

        for metric in METRICS:
            print(f"{metric}: {summary[metric]:.8f}")

        print(
            "Historical metrics matched:",
            f"{summary['historical_metrics_matched']}/1050",
        )

    after_hashes = {
        str(path): sha256(path)
        for path in protected_paths
    }

    assert before_hashes == after_hashes

    validate_environment()

    OUTPUT.mkdir(
        parents=True,
        exist_ok=False,
    )

    def write_csv(name, rows):

        with (OUTPUT / name).open(
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

    write_csv(
        "episode_results.csv",
        episode_rows,
    )

    write_csv(
        "historical_comparison.csv",
        comparison_rows,
    )

    write_csv(
        "summary.csv",
        summary_rows,
    )

    with (OUTPUT / "diagnostic_metadata.json").open(
        "x",
        encoding="utf-8",
    ) as f:

        json.dump(
            {
                "experiment": "reward_scale_full_reproduction",
                "model_seeds": MODEL_SEEDS,
                "evaluation_seeds": EVAL_SEEDS,
                "cases": CASES,
                "fleet": [2, 2, 3],
                "workload": 4.0,
                "battery_enabled": True,
                "episodes": len(episode_rows),
                "model_retrained": False,
                "source_sha256": before_hashes,
            },
            f,
            indent=2,
        )

    print()
    print("===== FINAL DIAGNOSTIC CHECK =====")
    print("Episodes:", len(episode_rows))
    print("Compared metric values:", len(comparison_rows))
    print("Protected file integrity: PASS")
    print("Historical files modified: NO")
    print("Model retrained: NO")
    print("Output:", OUTPUT)
    print("REWARD SCALE FULL REPRODUCTION: COMPLETE")


if __name__ == "__main__":
    main()
