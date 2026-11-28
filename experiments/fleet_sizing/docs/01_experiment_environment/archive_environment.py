from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import subprocess
import sys

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]
FLEET = ROOT / "experiments/fleet_sizing"

sys.path.insert(0, str(FLEET))

import config


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


# ============================================================
# 1. Verify formal Nav2 calibration identity
# ============================================================

expected_hashes = {
    Path(config.BATCH_ROUTE_RESULTS_PATH): (
        "2afdbdf57e8f5f0ffe6d318ec689c10b8"
        "b638477476ea63e56483b3ef6377b4a"
    ),
    Path(config.BATCH_ROUTE_SUMMARY_PATH): (
        "0baf6a695bacd2dac8f99a9e1b540dbb3"
        "0901dfff0086afb93a0666acf030399"
    ),
    Path(config.NAV_GRAPH_PATH): (
        "91c491b860ce97036ecceba4cf2460085"
        "baf9169d22484c1328cd722dc94bf79"
    ),
}

for path, expected in expected_hashes.items():

    assert path.is_file(), path

    assert sha(path) == expected, (
        path, sha(path), expected
    )

    print(path.name, "| SHA256 PASS")


# ============================================================
# 2. Archive plan
# ============================================================

plan = [
    (
        Path(config.TASK_PROFILES_PATH),
        DOC / "data/task_profiles.yaml",
    ),
    (
        Path(config.NAV_GRAPH_PATH),
        DOC / "data/nav2_calibration/nav_graph.yaml",
    ),
    (
        Path(config.BATCH_ROUTE_RESULTS_PATH),
        DOC / "data/nav2_calibration/batch_route_results_nav2.csv",
    ),
    (
        Path(config.BATCH_ROUTE_SUMMARY_PATH),
        DOC / "data/nav2_calibration/batch_route_summary_nav2.csv",
    ),
]

source_files = [
    "config.py",
    "models.py",
    "task_generator.py",
    "service_time.py",
    "nav_graph.py",
    "travel_time.py",
    "simulator.py",
    "scheduling_simulator.py",
    "metrics.py",
    "baseline/common.py",
    "rl/environment.py",
    "rl/observation.py",
    "rl/action_mask.py",
    "rl/reward.py",
    "rl/evaluate_reward_tuned_workload_robustness.py",
]

for name in source_files:

    plan.append((
        FLEET / name,
        DOC / "scripts" / name,
    ))

# Preflight all files before copying.

for source, target in plan:

    assert source.is_file(), source

    if target.exists():

        assert sha(source) == sha(target), (
            "Existing archive differs",
            target,
        )


# ============================================================
# 3. Export configuration values
# ============================================================

def convert(value):

    if isinstance(value, Path):

        try:
            return str(value.relative_to(ROOT))
        except ValueError:
            return str(value)

    if isinstance(value, dict):

        return {
            str(key): convert(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):

        return [
            convert(item)
            for item in value
        ]

    if isinstance(value, set):

        return [
            convert(item)
            for item in sorted(value)
        ]

    return value


settings = {}

for name in sorted(dir(config)):

    if not name.isupper():
        continue

    value = getattr(config, name)

    if isinstance(
        value,
        (str, int, float, bool, list, tuple,
         dict, set, Path),
    ):

        settings[name] = convert(value)

assert settings["REFERENCE_FLEET"] == [2, 2, 3]

assert settings["REFERENCE_TOTAL_ROBOTS"] == 7

assert settings["SIMULATION_DAYS"] == 7

assert settings["EXPECTED_TOTAL_TASKS_PER_DAY"] == 58

assert settings["BATTERY_MIN_RESERVE_SOC"] == 0.15

assert settings["BATTERY_CHARGE_TRIGGER_SOC"] == 0.25

assert settings["BATTERY_RESUME_SOC"] == 0.80

assert settings["ENABLE_BATTERY_MODEL"] is False

settings_path = DOC / "data/environment_config.json"

settings_content = json.dumps(
    settings,
    indent=2,
    ensure_ascii=False,
) + "\n"

if settings_path.exists():

    assert settings_path.read_text(
        encoding="utf-8"
    ) == settings_content


# ============================================================
# 4. Copy verified sources
# ============================================================

records = []

for source, target in plan:

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not target.exists():

        shutil.copy2(source, target)

    assert sha(source) == sha(target)

    records.append({
        "source": str(source.relative_to(ROOT)),
        "archive": str(target.relative_to(DOC)),
        "sha256": sha(target),
        "size_bytes": target.stat().st_size,
    })

    print(
        target.relative_to(DOC),
        "| PASS",
    )

settings_path.write_text(
    settings_content,
    encoding="utf-8",
)


# ============================================================
# 5. Manifest
# ============================================================

def git(*args):

    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
    ).strip()


manifest = {
    "created_at": (
        datetime.now().astimezone().isoformat()
    ),
    "archive_type": "Current environment source snapshot",
    "historical_training_snapshot": False,
    "git_branch": git("branch", "--show-current"),
    "git_commit": git("rev-parse", "HEAD"),
    "git_status": git("status", "--short"),
    "configuration_count": len(settings),
    "configuration_sha256": sha(settings_path),
    "file_count": len(records),
    "files": records,
    "historical_fleet_sizing": {
        "battery_enabled": False,
        "completion_rate": "within seven-day horizon",
        "utilization_denominator": "seven-day horizon",
    },
    "formal_evaluation": {
        "battery_enabled": True,
        "fleet": [2, 2, 3],
        "workloads": [3, 3.5, 4, 4.5, 5],
        "completion_rate": "final completed tasks",
        "utilization_denominator": "makespan",
    },
}

manifest_path = (
    DOC / "data/environment_manifest.json"
)

if manifest_path.exists():

    previous = json.loads(
        manifest_path.read_text()
    )

    assert previous["files"] == records

    assert previous[
        "configuration_sha256"
    ] == sha(settings_path)

else:

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

print()
print("===== ENVIRONMENT ARCHIVE REPORT =====")
print("Archived source files:", len(records))
print("Configuration values:", len(settings))
print("Nav2 source identity: PASS")
print("Archive integrity: PASS")
print("Original files modified: NO")
print("New simulations: 0")
print("Environment archive: COMPLETE")
