from __future__ import annotations

import argparse
from pathlib import Path

from sb3_contrib import MaskablePPO

from experiments.fleet_sizing.rl.evaluate_reward_tuned_workload_robustness import (
    run_baseline_episode,
    run_ppo_episode,
    aggregate_method,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1] / "results_rl"

MODEL_PATH = (
    ROOT
    / "models"
    / "reward_confirm_nav2_sweep12_w40_a35_q15_i10_seed7101_200k"
    / "final_model.zip"
)

OUTPUT_DIR = ROOT / "final_policy_vs_baselines_sweep12_seed7101_nav2_final30"

BASELINES = (
    "random_feasible",
    "projected_nearest",
    "static_weighted",
    "dynamic_weighted",
)

WORKLOADS = (
    3.0,
    3.5,
    4.0,
    4.5,
    5.0,
)

EVAL_SEEDS = tuple(range(9601, 9631))

PPO_NAME = "ppo_sweep12_seed7101"


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--limit-seeds",
        type=int,
        default=None,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(MODEL_PATH)

    if args.limit_seeds is not None:
        if not 1 <= args.limit_seeds <= len(EVAL_SEEDS):
            raise ValueError("Invalid --limit-seeds")

    seeds = (
        EVAL_SEEDS[:args.limit_seeds]
        if args.limit_seeds is not None
        else EVAL_SEEDS
    )

    methods = (*BASELINES, PPO_NAME)

    print("=" * 80)
    print("FINAL POLICY VS BASELINES")
    print("PPO:", MODEL_PATH)
    print("Workloads:", WORKLOADS)
    print("Eval seeds:", seeds)
    print("Methods:", methods)
    print(
        "Planned episodes:",
        len(methods) * len(WORKLOADS) * len(seeds),
    )
    print("=" * 80)

    if args.dry_run:
        print("DRY RUN COMPLETE")
        return

    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise RuntimeError(
            f"Output directory is not empty: {OUTPUT_DIR}. "
            "Refusing to overwrite results."
        )

    model = MaskablePPO.load(
        str(MODEL_PATH),
        device="cpu",
    )

    all_rows = []
    summaries = []

    for workload in WORKLOADS:
        for method in methods:
            rows = []

            for seed in seeds:
                if method == PPO_NAME:
                    result = run_ppo_episode(
                        model=model,
                        seed=seed,
                        method_name=method,
                        workload_multiplier=workload,
                    )
                else:
                    result = run_baseline_episode(
                        method=method,
                        seed=seed,
                        workload_multiplier=workload,
                    )

                result["training_seed"] = (
                    7101 if method == PPO_NAME else ""
                )
                result["workload_multiplier"] = workload

                rows.append(result)
                all_rows.append(result)

                print(
                    f"{method:<24}"
                    f" workload={workload:.1f}"
                    f" seed={seed}"
                    f" completion={result['completion_rate']:.4f}"
                    f" wait={result['average_waiting_time_s']:.2f}"
                    f" emergency={result['emergency_waiting_time_s']:.2f}",
                    flush=True,
                )

            summary = aggregate_method(method, rows)
            summary["workload_multiplier"] = workload
            summaries.append(summary)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        OUTPUT_DIR / "comparison_runs.csv",
        all_rows,
    )
    write_csv(
        OUTPUT_DIR / "comparison_summary.csv",
        summaries,
    )

    print("=" * 80)
    print("FINAL EVALUATION COMPLETE")
    print("Episode rows:", len(all_rows))
    print("Summary rows:", len(summaries))
    print("Results:", OUTPUT_DIR)
    print("=" * 80)


if __name__ == "__main__":
    main()
