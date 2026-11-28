from pathlib import Path
from datetime import datetime
from collections import Counter
import hashlib
import json
import shutil
import re
import csv

DOC_ROOT = Path(__file__).resolve().parent
ROOT = DOC_ROOT.parents[3]

RESULTS = (
    ROOT
    / "experiments/fleet_sizing/results_rl"
)

DATA = DOC_ROOT / "data"
METADATA = RESULTS / "metadata"

manifest = []
planned = []


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def plan_copy(source, destination, stage):

    source = Path(source)
    destination = Path(destination)

    if not source.is_file():
        raise FileNotFoundError(source)

    planned.append(
        (source, destination, stage)
    )


def plan_csv_group(source_dir, target_dir, names, stage):

    for name in names:

        plan_copy(
            source_dir / name,
            DATA / target_dir / name,
            stage
        )


CONFIRMATION_FILES = [
    "confirmation_episode_runs.csv",
    "confirmation_model_summary.csv",
    "confirmation_config_summary.csv",
]

# ============================================================
# Stage 1
# ============================================================

plan_csv_group(
    RESULTS / "reward_weight_sweep_validation/50k",
    "stage1_initial_sweep",
    [
        "reward_sweep_validation_runs.csv",
        "reward_sweep_validation_summary.csv",
    ],
    "stage1"
)

# ============================================================
# Stage 2: Combined results
# ============================================================

plan_csv_group(
    RESULTS / "pareto_15_config_validation",
    "stage2_pareto_confirmation",
    CONFIRMATION_FILES,
    "stage2"
)

# Stage 2: Original source batches

plan_csv_group(
    RESULTS / "reward_weight_confirmation_validation",
    "stage2_pareto_confirmation/source_batches/first_5_configs",
    CONFIRMATION_FILES + [
        "confirmation_statistics.csv",
    ],
    "stage2_source_batch"
)

plan_csv_group(
    RESULTS / "pareto_reward_confirmation_validation",
    "stage2_pareto_confirmation/source_batches/remaining_10_configs",
    CONFIRMATION_FILES,
    "stage2_source_batch"
)

# ============================================================
# Stage 3: Nav2 confirmation
# ============================================================

plan_csv_group(
    RESULTS / "pareto_reward_confirmation_nav2_validation",
    "stage3_nav2_confirmation",
    CONFIRMATION_FILES,
    "stage3"
)

# ============================================================
# Stage 4: Historical statistical analysis
# ============================================================

plan_csv_group(
    RESULTS / "nav2_final_reward_candidates",
    "stage4_final_selection",
    ["hierarchical_paired_bootstrap.csv"],
    "stage4"
)

# ============================================================
# Nav2 calibration
# ============================================================

for name in [
    "batch_route_results_nav2.csv",
    "batch_route_summary_nav2.csv",
]:

    plan_copy(
        ROOT / "ros2_ws" / name,
        DATA / "nav2_calibration" / name,
        "nav2_calibration"
    )

# ============================================================
# Training metadata
# ============================================================

metadata_groups = [
    (
        "stage1",
        "stage1_initial_sweep",
        r"reward_sweep_.*_50k\.json",
        33,
    ),
    (
        "stage2",
        "stage2_pareto_confirmation",
        r"reward_confirm_sweep\d+_.*"
        r"_seed(?:7001|710[1-4])_200k\.json",
        75,
    ),
    (
        "stage3",
        "stage3_nav2_confirmation",
        r"reward_confirm_nav2_sweep\d+_.*"
        r"_seed(?:7001|710[1-4])_200k\.json",
        35,
    ),
]

print("===== METADATA COVERAGE =====")

for stage, target, pattern, expected in metadata_groups:

    files = sorted(
        p for p in METADATA.glob("*.json")
        if re.fullmatch(pattern, p.name)
    )

    print(
        stage,
        "expected:", expected,
        "actual:", len(files)
    )

    if len(files) != expected:
        raise RuntimeError(
            f"{stage}: unexpected metadata count"
        )

    for source in files:

        plan_copy(
            source,
            DATA / target / "training_metadata" / source.name,
            stage + "_metadata"
        )

# ============================================================
# Formal evaluation model identity
# ============================================================

model_path = (
    RESULTS
    / "models"
    / "reward_confirm_nav2_sweep12_w40_a35_q15_i10_seed7101_200k"
    / "final_model.zip"
)

expected_model_hash = (
    "1972295e176e6907d3bee4d01b301fa105"
    "26dac40dca38a5e867fe1a63825d07"
)

assert model_path.is_file()

assert sha256(model_path) == expected_model_hash, (
    "Formal model hash mismatch"
)

# ============================================================
# Preflight: No source modification or silent overwrite
# ============================================================

destinations = [
    destination
    for _, destination, _ in planned
]

assert len(destinations) == len(set(destinations))

for source, destination, stage in planned:

    if destination.exists():

        if sha256(source) != sha256(destination):

            raise RuntimeError(
                "Existing file differs:\n"
                f"{destination}"
            )

# ============================================================
# Execute archive
# ============================================================

print()
print("===== ARCHIVING FILES =====")

copied = 0
unchanged = 0

for source, destination, stage in planned:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if destination.exists():
        unchanged += 1

    else:

        shutil.copy2(source, destination)
        copied += 1

    source_hash = sha256(source)
    target_hash = sha256(destination)

    assert source_hash == target_hash

    manifest.append({
        "stage": stage,
        "source": str(source.relative_to(ROOT)),
        "archive": str(destination.relative_to(DOC_ROOT)),
        "sha256": source_hash,
        "size_bytes": destination.stat().st_size,
    })

# ============================================================
# Manifest
# ============================================================

manifest_path = DATA / "reward_selection_manifest.json"

archive_info = {
    "created_at": datetime.now().astimezone().isoformat(),
    "scope": "Reward selection: 33 -> 15 -> 7 -> 2 -> 1",
    "formal_model": {
        "config": "sweep12",
        "model_seed": 7101,
        "path": str(model_path.relative_to(ROOT)),
        "sha256": expected_model_hash,
        "deployment_verified": False,
    },
    "file_count": len(manifest),
    "files": manifest,
}

if manifest_path.exists():

    previous = json.loads(
        manifest_path.read_text()
    )

    if (
        previous["files"] != archive_info["files"]
        or previous["formal_model"] != archive_info["formal_model"]
    ):

        raise RuntimeError(
            "Existing manifest differs. "
            "Refusing to overwrite."
        )

else:

    manifest_path.write_text(
        json.dumps(
            archive_info,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

print()
print("===== ARCHIVE SUMMARY =====")

for stage, count in sorted(Counter(
    r["stage"] for r in manifest
).items()):

    print(stage, count)

print()
print("Copied:", copied)
print("Already identical:", unchanged)
print("Archived files:", len(manifest))
print("SHA256 verification: PASS")
print("Manifest:", manifest_path)

print()
print("===== ARCHIVE CSV INVENTORY =====")

for path in sorted(DATA.rglob("*.csv")):

    if "scale_selection" in path.parts:
        continue

    with path.open(
        newline="", encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)
        rows = list(reader)

    print()
    print("File:", path.relative_to(DOC_ROOT))
    print("Rows:", len(rows))
    print("Fields:", reader.fieldnames)

print()
print("===== REWARD SELECTION ARCHIVE COMPLETE =====")
print("Historical source files modified: NO")
print("Scale archive modified: NO")
print("Models retrained: NO")
print("New simulation runs: 0")
