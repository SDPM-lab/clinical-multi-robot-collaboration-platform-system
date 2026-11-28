from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil

import pandas as pd

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]
FLEET = ROOT / "experiments/fleet_sizing"

RESULT = (
    FLEET / "results_rl"
    / "final_nav2_calibrated_baselines_sweep12_seed7101"
)

CAL = FLEET / "results/battery_baseline_calibration_v2"

MANIFEST = DOC / "data/archive_manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(path, expected):
    assert path.is_file(), path
    assert sha(path) == expected, path


evaluation_path = RESULT / "full/experiment_metadata.json"
primary_path = RESULT / "analysis/analysis_metadata.json"
secondary_path = (
    RESULT / "secondary_analysis/secondary_analysis_metadata.json"
)

evaluation = read(evaluation_path)
primary = read(primary_path)
secondary = read(secondary_path)

assert evaluation["status"] == "complete"
assert evaluation["completed_episodes"] == 750
assert evaluation["summary_groups"] == 25
assert evaluation["runtime_travel_checks"] == 750
assert evaluation["minimum_completion_rate"] == 1.0
assert evaluation["fleet"] == [2, 2, 3]
assert evaluation["model_seed"] == 7101

assert evaluation["baseline_parameters"] == {
    "static_alpha": 0.6,
    "dynamic_alpha_min": 0.4,
    "dynamic_alpha_max": 0.9,
}

assert primary["bootstrap_counts"] == {
    "ppo_better": 91,
    "ppo_worse": 16,
    "ci_crosses_zero": 13,
}

assert secondary["bootstrap_counts"] == {
    "ppo_better": 93,
    "ppo_worse": 16,
    "ci_includes_zero": 31,
}

assert secondary["secondary_metric_count"] == 15
assert secondary["derived_metric_count"] == 4
assert secondary["comparison_count"] == 140

print("===== METADATA VERIFICATION: PASS =====")

# Verify links between experiment and analysis.

verify(
    evaluation_path,
    primary["source_metadata_sha256"],
)

for metadata in (primary, secondary):

    verify(
        RESULT / "full/comparison_runs.csv",
        metadata["source_runs_sha256"],
    )

    verify(
        RESULT / "full/comparison_summary.csv",
        metadata["source_summary_sha256"],
    )

verify(
    primary_path,
    secondary["primary_analysis_metadata_sha256"],
)

model = ROOT / evaluation["model_path"]
verify(model, evaluation["model_sha256"])

assert sha(model) == (
    "1972295e176e6907d3bee4d01b301fa105"
    "26dac40dca38a5e867fe1a63825d07"
)

print("Formal model: PASS")

# Archive plan.

plan = []

for source_dir, target_dir, metadata, metadata_name in [
    (
        "full", "evaluation", evaluation,
        "experiment_metadata.json",
    ),
    (
        "analysis", "analysis", primary,
        "analysis_metadata.json",
    ),
    (
        "secondary_analysis", "secondary_analysis", secondary,
        "secondary_analysis_metadata.json",
    ),
]:

    for name, expected in metadata["output_sha256"].items():

        source = RESULT / source_dir / name

        verify(source, expected)

        plan.append((
            source,
            DOC / "data" / target_dir / name,
        ))

    plan.append((
        RESULT / source_dir / metadata_name,
        DOC / "data" / target_dir / metadata_name,
    ))

# Selected baseline configurations.

for method in ("static", "dynamic"):

    source = CAL / method / "selected_parameters.json"

    verify(
        source,
        evaluation[f"{method}_selection_sha256"],
    )

    plan.append((
        source,
        DOC / "data/configuration"
        / f"{method}_selected_parameters.json",
    ))

# Analysis and evaluation source scripts.

scripts = [
    "evaluate_final_nav2_calibrated_baselines.py",
    "analyze_final_nav2_calibrated_baselines.py",
    "analyze_secondary_metrics_nav2.py",
]

for name in scripts:

    source = FLEET / "rl" / name

    assert source.is_file(), source

    if name == scripts[0]:

        verify(
            source,
            evaluation["source_sha256"][
                str(source.relative_to(ROOT))
            ],
        )

    elif name == scripts[1]:

        verify(source, primary["analysis_script_sha256"])

    else:

        verify(source, secondary["analysis_script_sha256"])

    plan.append((
        source,
        DOC / "scripts" / name,
    ))

assert len(plan) == 25

# Verify statistical outcomes.

stats = pd.read_csv(
    RESULT / "analysis/paired_bootstrap_results.csv"
)

aux = pd.read_csv(
    RESULT / "secondary_analysis/secondary_paired_bootstrap.csv"
)

assert len(stats) == 120
assert len(aux) == 140

for table in (stats, aux):

    assert not table.duplicated([
        "workload", "baseline", "metric",
    ]).any()

    assert (table["paired_seeds"] == 30).all()

assert stats["bootstrap_verdict"].value_counts().to_dict() == (
    primary["bootstrap_counts"]
)

assert aux["bootstrap_verdict"].value_counts().to_dict() == (
    secondary["bootstrap_counts"]
)

for column in (
    "holm_t_p_verdict",
    "holm_wilcoxon_p_verdict",
):

    assert stats[column].value_counts().to_dict() == {
        "ppo_better": 85,
        "ppo_worse": 15,
        "not_significant": 20,
    }

assert aux["holm_t_verdict"].value_counts().to_dict() == {
    "ppo_better": 67,
    "ppo_worse": 15,
    "not_significant": 58,
}

t = stats["holm_t_p_verdict"] == "ppo_better"
w = stats["holm_wilcoxon_p_verdict"] == "ppo_better"
b = stats["bootstrap_verdict"] == "ppo_better"

agreement = {
    "both_holm_better": int((t & w).sum()),
    "all_three_better": int((t & w & b).sum()),
}

# Verify battery and travel conclusions.

battery = pd.read_csv(
    RESULT / "secondary_analysis/battery_charging_summary.csv"
)

travel = pd.read_csv(
    RESULT / "secondary_analysis/travel_decomposition.csv"
)

assert len(battery) == 25
assert len(travel) == 20

assert battery["episodes_below_reserve"].sum() == 0
assert travel["identical_task_travel_seeds"].sum() == 600

assert battery["lowest_observed_soc"].min() >= 0.15

# Preflight: no conflicting archive files.

records = []

for source, target in plan:

    assert source.is_file(), source

    if target.exists():
        assert sha(source) == sha(target), target

    records.append({
        "source": str(source.relative_to(ROOT)),
        "archive": str(target.relative_to(DOC)),
        "sha256": sha(source),
        "size_bytes": source.stat().st_size,
    })

manifest = {
    "created_at": datetime.now().astimezone().isoformat(),
    "experiment": "Final Nav2 PPO vs Calibrated Baselines",
    "evaluation_episodes": 750,
    "summary_groups": 25,
    "primary_metric_count": 7,
    "secondary_metric_count": 15,
    "derived_metric_count": 4,
    "primary_comparisons": 120,
    "secondary_comparisons": 140,
    "fleet": [2, 2, 3],
    "baseline_parameters": evaluation["baseline_parameters"],
    "formal_model": {
        "config": "sweep12",
        "model_seed": 7101,
        "path": str(model.relative_to(ROOT)),
        "sha256": sha(model),
        "deployment_verified": False,
    },
    "primary_bootstrap_counts": primary["bootstrap_counts"],
    "secondary_bootstrap_counts": secondary["bootstrap_counts"],
    "statistical_agreement": agreement,
    "battery": {
        "lowest_observed_soc": float(
            battery["lowest_observed_soc"].min()
        ),
        "episodes_below_reserve": 0,
    },
    "identical_task_travel_pairs": 600,
    "nav2_summary_sha256": evaluation["nav2_summary_sha256"],
    "file_count": len(records),
    "files": records,
}

if MANIFEST.exists():

    existing = read(MANIFEST)

    assert existing["files"] == records, (
        "Existing manifest differs. Preserve it before updating."
    )

# Copy and independently verify archive files.

for (source, target), record in zip(plan, records):

    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        shutil.copy2(source, target)

    verify(target, record["sha256"])

    print(record["archive"], "| PASS")

if not MANIFEST.exists():

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

print()
print("===== FINAL ARCHIVE REPORT =====")
print("Archived files:", len(records))
print("Primary comparisons: 120")
print("Secondary comparisons: 140")
print("Primary bootstrap:", primary["bootstrap_counts"])
print("Secondary bootstrap:", secondary["bootstrap_counts"])
print("Statistical agreement:", agreement)
print("Identical task travel pairs: 600/600")
print("Episodes below battery reserve: 0/750")
print("Archive integrity: PASS")
print("Original files modified: NO")
print("New simulations: 0")
print("Archive: COMPLETE")
