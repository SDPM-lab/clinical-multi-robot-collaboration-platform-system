from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
import xml.etree.ElementTree as ET

import pandas as pd

from PIL import Image

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]

DATA = DOC / "data"
FIG = DOC / "figures"


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


archive = read_json(
    DATA / "archive_manifest.json"
)

figures = read_json(
    FIG / "figure_manifest.json"
)


# ============================================================
# 1. Archived data
# ============================================================

assert archive["file_count"] == 25
assert len(archive["files"]) == 25

for item in archive["files"]:

    for path in [
        ROOT / item["source"],
        DOC / item["archive"],
    ]:

        assert path.is_file(), path
        assert sha(path) == item["sha256"], path
        assert path.stat().st_size == item["size_bytes"]

print("Archived files: 25/25 PASS")


# ============================================================
# 2. Formal PPO model
# ============================================================

model = ROOT / archive["formal_model"]["path"]

assert model.is_file()

assert sha(model) == archive[
    "formal_model"
]["sha256"]

assert archive["formal_model"]["config"] == "sweep12"
assert archive["formal_model"]["model_seed"] == 7101

print("Formal PPO model identity: PASS")


# ============================================================
# 3. CSV coverage
# ============================================================

expected_rows = {
    "evaluation/comparison_runs.csv": 750,
    "evaluation/comparison_summary.csv": 25,
    "evaluation/runtime_nav2_checks.csv": 750,

    "analysis/paired_bootstrap_results.csv": 120,
    "analysis/relative_improvements.csv": 120,
    "analysis/best_baseline_comparison.csv": 30,
    "analysis/bootstrap_summary_by_metric.csv": 6,
    "analysis/historical_reproducibility.csv": 30,

    "secondary_analysis/secondary_descriptive_summary.csv": 475,
    "secondary_analysis/secondary_paired_bootstrap.csv": 140,
    "secondary_analysis/secondary_best_baseline.csv": 35,
    "secondary_analysis/priority_waiting_summary.csv": 100,
    "secondary_analysis/travel_decomposition.csv": 20,
    "secondary_analysis/utilization_summary.csv": 25,
    "secondary_analysis/battery_charging_summary.csv": 25,
    "secondary_analysis/secondary_bootstrap_counts.csv": 7,
    "secondary_analysis/derived_episode_metrics.csv": 750,
}

for name, count in expected_rows.items():

    frame = pd.read_csv(DATA / name)

    assert len(frame) == count, (
        name, len(frame), count
    )

print(
    "CSV row counts:",
    len(expected_rows),
    "files PASS",
)

runs = pd.read_csv(
    DATA / "evaluation/comparison_runs.csv"
)

assert not runs.duplicated([
    "workload_multiplier",
    "method",
    "seed",
]).any()

assert (runs["completion_rate"] == 1).all()

assert (
    runs["generated_tasks"]
    == runs["completed_tasks"]
).all()

assert (
    runs.groupby([
        "workload_multiplier",
        "method",
    ]).size() == 30
).all()

print("Evaluation coverage: PASS")
print("Task completion: 750/750 PASS")


# ============================================================
# 4. Statistical results
# ============================================================

stats = pd.read_csv(
    DATA / "analysis/paired_bootstrap_results.csv"
)

aux = pd.read_csv(
    DATA / "secondary_analysis/secondary_paired_bootstrap.csv"
)

assert stats["bootstrap_verdict"].value_counts().to_dict() == {
    "ppo_better": 91,
    "ppo_worse": 16,
    "ci_crosses_zero": 13,
}

assert aux["bootstrap_verdict"].value_counts().to_dict() == {
    "ppo_better": 93,
    "ppo_worse": 16,
    "ci_includes_zero": 31,
}

t = stats["holm_t_p_verdict"] == "ppo_better"
w = stats["holm_wilcoxon_p_verdict"] == "ppo_better"
b = stats["bootstrap_verdict"] == "ppo_better"

assert t.sum() == 85
assert w.sum() == 85

assert (t & w).sum() == 84
assert (t & w & b).sum() == 84

assert aux[
    "holm_wilcoxon_significant"
].sum() == 82

assert aux["holm_t_verdict"].value_counts().to_dict() == {
    "ppo_better": 67,
    "ppo_worse": 15,
    "not_significant": 58,
}

print("Primary statistical results: PASS")
print("Secondary statistical results: PASS")
print("Statistical agreement: 84/120 PASS")


# ============================================================
# 5. Battery and travel
# ============================================================

battery = pd.read_csv(
    DATA / "secondary_analysis/battery_charging_summary.csv"
)

travel = pd.read_csv(
    DATA / "secondary_analysis/travel_decomposition.csv"
)

assert battery["episodes_below_reserve"].sum() == 0

assert battery["lowest_observed_soc"].min() >= 0.15

assert travel["identical_task_travel_seeds"].sum() == 600

print("Battery reserve analysis: PASS")
print("Task travel decomposition: PASS")


# ============================================================
# 6. Figures
# ============================================================

assert figures["figure_count"] == 23

assert sha(
    DATA / "archive_manifest.json"
) == figures["archive_manifest_sha256"]

assert sha(
    DOC / "plot_final_comparison.py"
) == figures["plot_script_sha256"]

verified = 0

for figure in figures["figures"]:

    for record in figure["sources"]:

        assert sha(
            DOC / record["file"]
        ) == record["sha256"]

    for record in figure["outputs"]:

        path = DOC / record["file"]

        assert path.is_file()

        assert sha(path) == record["sha256"]

        assert path.stat().st_size == (
            record["size_bytes"]
        )

        if path.suffix == ".png":

            with Image.open(path) as im:

                assert all(
                    abs(v - 300) < 1
                    for v in im.info["dpi"]
                )

                im.verify()

        elif path.suffix == ".svg":

            assert ET.parse(
                path
            ).getroot().tag.endswith("svg")

        verified += 1

assert verified == 46

assert len(list(FIG.rglob("*.png"))) == 23
assert len(list(FIG.rglob("*.svg"))) == 23

print("Figure groups: 23/23 PASS")
print("Figure files: 46/46 PASS")


# ============================================================
# 7. Downloaded README
# ============================================================

readme = DOC / "README.md"

assert readme.is_file()

content = readme.read_text(
    encoding="utf-8"
)

sections = re.findall(
    r"^## (\d+)\.",
    content,
    flags=re.MULTILINE,
)

assert sections == [
    str(i) for i in range(1, 19)
]

images = re.findall(
    r"!\[[^\]]*\]\(([^)]+)\)",
    content,
)

expected_images = {
    record["file"]
    for figure in figures["figures"]
    for record in figure["outputs"]
    if record["file"].endswith(".png")
}

actual_images = {
    Path(image).as_posix().removeprefix("./")
    for image in images
}

assert expected_images.issubset(
    actual_images
), (
    expected_images - actual_images
)

links = re.findall(
    r"\[[^\]]*\]\(([^)]+)\)",
    content,
)

missing = []

for link in links:

    if link.startswith((
        "http://",
        "https://",
        "#",
        "mailto:",
    )):
        continue

    if not (DOC / link).exists():
        missing.append(link)

if missing:

    print("Missing README links:")

    for link in missing:
        print(" -", link)

    raise AssertionError(
        "README contains unresolved links."
    )

assert content.count("```") % 2 == 0

assert content.count("$$") % 2 == 0

print("README sections:", len(sections))
print("README lines:", len(content.splitlines()))
print("README embedded figures:", len(images))
print("README links checked:", len(links))
print("README structure: PASS")


# ============================================================
# 8. README provenance
# ============================================================

manifest = {
    "verified_at": (
        datetime.now().astimezone().isoformat()
    ),
    "generation_method": "Downloaded standalone Markdown",
    "readme_sha256": sha(readme),
    "archive_manifest_sha256": sha(
        DATA / "archive_manifest.json"
    ),
    "figure_manifest_sha256": sha(
        FIG / "figure_manifest.json"
    ),
    "verification_script_sha256": sha(
        Path(__file__)
    ),
    "line_count": len(content.splitlines()),
    "section_count": len(sections),
    "embedded_figures": len(images),
    "links_checked": len(links),
    "missing_links": missing,
    "verification_status": "PASS",
    "verification_scope": (
        "File integrity, research result counts, "
        "README structure and local links; "
        "not independent verification of every README statement"
    ),
}

(
    DATA / "readme_manifest.json"
).write_text(
    json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== SECTION 06 FINAL VERIFICATION =====")
print("Archived data: PASS")
print("Formal PPO model identity: PASS")
print("Evaluation results: PASS")
print("Statistical results: PASS")
print("Battery and travel analysis: PASS")
print("Figures: PASS")
print("README structure and links: PASS")
print("README SHA256:", sha(readme))
print(
    "Deployment verified:",
    archive["formal_model"]["deployment_verified"],
)
print("SECTION 06: COMPLETE")
