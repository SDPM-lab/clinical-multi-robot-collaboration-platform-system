from __future__ import annotations

import csv
import hashlib
import json
import math

from collections import Counter
from statistics import mean

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)

from experiments.fleet_sizing.battery_calibration.evaluation import (
    validate_environment,
    calculate_unified_metrics,
    run_baseline_episode,
)

from experiments.fleet_sizing.baseline.dynamic_weighted import (
    DynamicWeightedScheduler,
)

from experiments.fleet_sizing.scheduling_simulator import (
    SchedulingSimulator,
)


DIAGNOSTIC_RANGES = (
    (0.0, 0.4),
    (0.0, 1.0),
    (0.4, 0.8),
    (0.4, 1.0),
    (0.6, 0.8),
    (0.6, 1.0),
    (0.9, 1.0),
)

DIAGNOSTIC_SEEDS = (3001, 3002, 3003)

OUTPUT = cfg.RESULTS_ROOT / "diagnostics" / "dynamic_behavior"

TOL = 1e-10


def close(a, b):

    return math.isclose(
        a, b,
        rel_tol=TOL,
        abs_tol=TOL,
    )


# ============================================================
# Diagnostic wrapper
# ============================================================

class DiagnosticDynamicScheduler(
    DynamicWeightedScheduler
):

    def __init__(self, alpha_min, alpha_max):

        super().__init__(
            alpha_min=alpha_min,
            alpha_max=alpha_max,
        )

        self.decision_records = []

    def decide(self, *args, **kwargs):

        # Execute original scheduler without changing it.
        decision = super().decide(
            *args,
            **kwargs,
        )

        count = decision.candidate_count
        alpha = float(decision.dynamic_alpha)
        imbalance = float(decision.load_imbalance)

        assert decision.alpha_min == self.alpha_min
        assert decision.alpha_max == self.alpha_max

        assert (
            self.alpha_min - TOL
            <= alpha
            <= self.alpha_max + TOL
        )

        record = {
            "decision_index":
                len(self.decision_records) + 1,

            "task_id": decision.task_id,

            "current_time_s":
                kwargs.get("current_time_s"),

            "status": decision.decision_status,

            "selected_robot_id":
                decision.selected_robot_id,

            "candidate_count": count,

            "candidate_robot_ids":
                "|".join(decision.candidate_robot_ids),

            "load_imbalance": imbalance,

            "dynamic_alpha": alpha,

            "alpha_min": self.alpha_min,
            "alpha_max": self.alpha_max,

            "candidate_loads": "",
            "candidate_approaches": "",

            "load_values_equal": False,

            "alpha_position": "not_applicable",

            "released_task_count":
                len(decision.released_task_ids),
        }

        if count > 0:

            candidates = decision.all_candidates

            assert len(candidates) == count

            loads = [
                c.observable_load
                for c in candidates
            ]

            normalized_loads = [
                c.normalized_load
                for c in candidates
            ]

            approaches = [
                c.placement_evaluation
                .projected_approach_time_s
                for c in candidates
            ]

            expected_imbalance = (
                max(normalized_loads)
                - min(normalized_loads)
            )

            expected_alpha = (
                self.alpha_max
                - (
                    self.alpha_max
                    - self.alpha_min
                ) * expected_imbalance
            )

            assert close(
                imbalance,
                expected_imbalance,
            )

            assert close(alpha, expected_alpha)

            # Independently verify every weighted cost.
            for candidate in candidates:

                expected_cost = (
                    alpha * candidate.normalized_approach
                    + (1.0 - alpha)
                    * candidate.normalized_load
                )

                assert close(
                    expected_cost,
                    candidate.weighted_cost,
                )

            # Verify original tie-breaking and selection.
            expected_robot = min(
                candidates,
                key=lambda c: (
                    c.weighted_cost,
                    c.placement_evaluation
                    .projected_approach_time_s,
                    c.observable_load,
                    c.robot_id,
                ),
            )

            assert (
                expected_robot.robot_id
                == decision.selected_robot_id
            )

            record["candidate_loads"] = "|".join(
                str(v) for v in loads
            )

            record["candidate_approaches"] = "|".join(
                f"{v:.9f}" for v in approaches
            )

            record["load_values_equal"] = (
                len(set(loads)) == 1
            )

            if close(alpha, self.alpha_min):
                position = "minimum"

            elif close(alpha, self.alpha_max):
                position = "maximum"

            else:
                position = "intermediate"

            record["alpha_position"] = position

        self.decision_records.append(record)

        # Return original, unmodified decision.
        return decision


# ============================================================
# Save results
# ============================================================

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


def hash_records(records):

    encoded = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


# ============================================================
# Summarize decision behavior
# ============================================================

def summarize_decisions(records):

    assigned = [
        r for r in records
        if r["candidate_count"] > 0
    ]

    multiple = [
        r for r in assigned
        if r["candidate_count"] >= 2
    ]

    different_load = [
        r for r in multiple
        if not r["load_values_equal"]
    ]

    positions = Counter(
        r["alpha_position"]
        for r in multiple
    )

    def pct(count, total):
        return 100.0 * count / total if total else 0.0

    return {
        "total_decisions": len(records),

        "no_feasible_decisions":
            len(records) - len(assigned),

        "assigned_decisions": len(assigned),

        "single_candidate_decisions":
            len(assigned) - len(multiple),

        "multiple_candidate_decisions":
            len(multiple),

        "multiple_candidate_pct":
            pct(len(multiple), len(assigned)),

        "equal_load_multi_pct":
            pct(
                len(multiple) - len(different_load),
                len(multiple),
            ),

        "different_load_multi_pct":
            pct(
                len(different_load),
                len(multiple),
            ),

        "alpha_min_multi_pct":
            pct(positions["minimum"], len(multiple)),

        "alpha_max_multi_pct":
            pct(positions["maximum"], len(multiple)),

        "alpha_intermediate_multi_pct":
            pct(
                positions["intermediate"],
                len(multiple),
            ),

        "mean_alpha_assigned":
            mean(
                r["dynamic_alpha"]
                for r in assigned
            ) if assigned else 0.0,

        "mean_alpha_multiple":
            mean(
                r["dynamic_alpha"]
                for r in multiple
            ) if multiple else 0.0,

        "mean_imbalance_multiple":
            mean(
                r["load_imbalance"]
                for r in multiple
            ) if multiple else 0.0,
    }


# ============================================================
# Run diagnostic simulations
# ============================================================

def main():

    validate_environment()

    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT}"
        )

    OUTPUT.mkdir(parents=True)

    summaries = []
    episode_rows = []
    all_decisions = []

    expected_runs = (
        len(DIAGNOSTIC_RANGES)
        * len(DIAGNOSTIC_SEEDS)
    )

    index = 0

    for lo, hi in DIAGNOSTIC_RANGES:

        for seed in DIAGNOSTIC_SEEDS:

            index += 1

            scheduler = DiagnosticDynamicScheduler(
                alpha_min=lo,
                alpha_max=hi,
            )

            simulator = SchedulingSimulator(
                fleet_configuration=cfg.FLEET_CONFIGURATION,
                seed=seed,
                scheduler=scheduler,
                workload_multiplier=cfg.WORKLOAD_MULTIPLIER,
                enable_battery_model=True,
            )

            result = simulator.run()

            records = scheduler.decision_records

            assert records

            metrics = calculate_unified_metrics(
                method="dynamic_weighted",
                seed=seed,
                tasks=result.tasks,
                robots=result.robots,
                assignments=result.assignments,
            )

            # Compare wrapper results with the ordinary scheduler.
            reference = run_baseline_episode(
                method="dynamic_weighted",
                seed=seed,
                alpha_min=lo,
                alpha_max=hi,
            )

            for field in (
                *cfg.PRIMARY_METRICS,
                "completion_rate",
                "jain_utilization_fairness",
                "minimum_robot_soc",
                "total_charging_count",
            ):

                assert close(
                    float(metrics[field]),
                    float(reference[field]),
                ), (
                    lo, hi, seed, field
                )

            # Hash decision sequence without alpha-related
            # fields, for cross-configuration comparison.
            decision_sequence = [
                {
                    "task_id": r["task_id"],
                    "time": r["current_time_s"],
                    "robot_id": r["selected_robot_id"],
                    "status": r["status"],
                }
                for r in records
            ]

            dispatch_hash = hash_records(
                decision_sequence
            )

            behavior = summarize_decisions(records)

            summary = {
                "alpha_min": lo,
                "alpha_max": hi,
                "seed": seed,

                **behavior,

                "dispatch_sequence_sha256":
                    dispatch_hash,

                "wrapper_metric_check": "PASS",
            }

            summaries.append(summary)

            episode_rows.append({
                "alpha_min": lo,
                "alpha_max": hi,
                **metrics,
            })

            all_decisions.extend(
                {
                    "seed": seed,
                    **record,
                }
                for record in records
            )

            print(
                f"[{index:02d}/{expected_runs}] "
                f"range=[{lo:.1f},{hi:.1f}] "
                f"seed={seed} | "
                f"decisions={behavior['total_decisions']} | "
                f"multi={behavior['multiple_candidate_pct']:.2f}% | "
                f"equal_load={behavior['equal_load_multi_pct']:.2f}% | "
                f"min={behavior['alpha_min_multi_pct']:.2f}% | "
                f"max={behavior['alpha_max_multi_pct']:.2f}% | "
                f"mid={behavior['alpha_intermediate_multi_pct']:.2f}% | "
                f"mean_alpha={behavior['mean_alpha_multiple']:.4f} | "
                "PASS",
                flush=True,
            )

    write_csv(
        OUTPUT / "decision_records.csv",
        all_decisions,
    )

    write_csv(
        OUTPUT / "behavior_summary.csv",
        summaries,
    )

    write_csv(
        OUTPUT / "episode_metrics.csv",
        episode_rows,
    )

    print()
    print("=" * 100)
    print("DYNAMIC BEHAVIOR SUMMARY")
    print("=" * 100)

    fields = (
        "multiple_candidate_pct",
        "equal_load_multi_pct",
        "alpha_min_multi_pct",
        "alpha_max_multi_pct",
        "alpha_intermediate_multi_pct",
        "mean_alpha_multiple",
    )

    print(
        "Range       "
        "Multi%  EqualLoad%   Min%    Max%    Mid%   MeanAlpha"
    )

    for lo, hi in DIAGNOSTIC_RANGES:

        group = [
            r for r in summaries
            if r["alpha_min"] == lo
            and r["alpha_max"] == hi
        ]

        values = [
            mean(r[field] for r in group)
            for field in fields
        ]

        print(
            f"[{lo:.1f},{hi:.1f}]  "
            + " ".join(
                f"{v:9.3f}"
                for v in values
            )
        )

    print()
    print("===== DISPATCH SEQUENCE EQUIVALENCE =====")

    for seed in DIAGNOSTIC_SEEDS:

        groups = {}

        for row in summaries:

            if row["seed"] != seed:
                continue

            digest = row[
                "dispatch_sequence_sha256"
            ]

            groups.setdefault(
                digest, []
            ).append(
                (
                    row["alpha_min"],
                    row["alpha_max"],
                )
            )

        print()
        print("Seed:", seed)
        print("Unique decision sequences:", len(groups))

        for i, ranges in enumerate(
            groups.values(), 1
        ):
            print(
                f"Sequence {i}:",
                ranges,
            )

    print()
    print("===== FINAL DIAGNOSTIC CHECK =====")
    print("Diagnostic runs:", len(summaries))
    print("Reference runs:", len(summaries))
    print("Decision records:", len(all_decisions))
    print("Dynamic alpha formula: PASS")
    print("Weighted cost formula: PASS")
    print("Robot selection rule: PASS")
    print("Wrapper metric equivalence: PASS")

    validate_environment()

    print("DYNAMIC DIAGNOSTICS: COMPLETE")
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
