from pathlib import Path
from collections import Counter
import hashlib
import json
import csv
import re
import xml.etree.ElementTree as ET

from PIL import Image

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]
DATA = DOC / "data"


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


archive_path = DATA / "reward_selection_manifest.json"

analysis_path = (
    DATA / "reward_selection_analysis_manifest.json"
)

figure_path = (
    DATA / "reward_selection_figure_manifest.json"
)

archive = read_json(archive_path)
analysis = read_json(analysis_path)
figures = read_json(figure_path)


# ============================================================
# 1. Archived sources
# ============================================================

print("===== 1. SOURCE ARCHIVE =====")

assert len(archive["files"]) == 161

counts = Counter()

for record in archive["files"]:

    source = ROOT / record["source"]

    target = DOC / record["archive"]

    assert source.is_file(), source
    assert target.is_file(), target

    assert sha256(source) == record["sha256"], source
    assert sha256(target) == record["sha256"], target

    counts[record["stage"]] += 1

assert counts["stage1_metadata"] == 33
assert counts["stage2_metadata"] == 75
assert counts["stage3_metadata"] == 35

print("Original archived files: 161")
print("Training metadata: 143")
print("Archive integrity: PASS")


# ============================================================
# 2. Analysis data
# ============================================================

print()
print("===== 2. ANALYSIS DATA =====")

assert sha256(archive_path) == (
    analysis["archive_manifest_sha256"]
)

assert sha256(
    DOC / "analyze_reward_selection.py"
) == analysis["analysis_script_sha256"]

assert len(analysis["generated_files"]) == 7

total_rows = 0

for name, record in analysis["generated_files"].items():

    path = DOC / name

    assert path.is_file(), path

    assert sha256(path) == record["sha256"], path

    with path.open(
        newline="", encoding="utf-8-sig"
    ) as f:

        rows = list(csv.DictReader(f))

    assert len(rows) == record["rows"]

    total_rows += len(rows)

assert total_rows == 106

print("Analysis CSV files: 7")
print("Analysis rows: 106")
print("Analysis integrity: PASS")


# ============================================================
# 3. Figure integrity
# ============================================================

print()
print("===== 3. FIGURE INTEGRITY =====")

assert sha256(analysis_path) == (
    figures["analysis_manifest_sha256"]
)

assert sha256(
    DOC / "plot_reward_selection.py"
) == figures["plot_script_sha256"]

counts = Counter()

for record in figures["files"]:

    path = DOC / record["file"]

    assert path.is_file(), path

    assert sha256(path) == record["sha256"], path

    counts[path.suffix] += 1

    if path.suffix == ".png":

        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:

            dpi = image.info.get("dpi")

            assert dpi is not None

            assert all(
                abs(x - 300) < 1
                for x in dpi
            )

    elif path.suffix == ".svg":

        assert ET.parse(
            path
        ).getroot().tag.endswith("svg")

assert counts[".png"] == 13
assert counts[".svg"] == 13

print("PNG files: 13")
print("SVG files: 13")
print("Figure integrity: PASS")


# ============================================================
# 4. README structure and links
# ============================================================

print()
print("===== 4. README VERIFICATION =====")

readme = DOC / "README.md"

content = readme.read_text(encoding="utf-8")

headings = re.findall(
    r"^## (\d+)\.",
    content,
    flags=re.MULTILINE,
)

assert headings == [
    str(i) for i in range(1, 17)
], headings

images = re.findall(
    r"!\[[^\]]*\]\(([^)]+)\)",
    content
)

assert len(images) == 13
assert len(set(images)) == 13

links = re.findall(
    r"\]\(([^)]+)\)",
    content
)

missing = []

for link in links:

    if link.startswith((
        "https://",
        "http://",
        "#"
    )):
        continue

    if not (DOC / link).exists():

        missing.append(link)

assert not missing, missing

for required in [
    "Sweep 12",
    "7101",
    "24.71%",
    "3,210",
]:

    assert required in content, required

print("Main sections:", len(headings))
print("Embedded figures:", len(images))
print("Links checked:", len(links))
print("Missing links:", missing)
print("README SHA256:", sha256(readme))
print("README structure and links: PASS")


# ============================================================
# 5. Scale archive preservation
# ============================================================

print()
print("===== 5. SCALE ARCHIVE =====")

scale = DATA / "scale_selection"

scale_figures = DOC / "figures/scale_selection"

assert (scale / "README.md").is_file()

assert len(list(
    (scale / "training_metadata").glob("*.json")
)) == 29

assert len(list(
    scale_figures.glob("*.png")
)) == 8

assert len(list(
    scale_figures.glob("*.svg")
)) == 8

print("Scale metadata: 29")
print("Scale figure groups: 8")
print("Scale inventory: PASS")


# ============================================================
# 6. Formal model identity
# ============================================================

print()
print("===== 6. FORMAL MODEL =====")

model = archive["formal_model"]

assert model["config"] == "sweep12"
assert model["model_seed"] == 7101

model_path = ROOT / model["path"]

assert model_path.is_file()

assert sha256(model_path) == model["sha256"]

print("Configuration:", model["config"])
print("Model seed:", model["model_seed"])
print("Model identity: PASS")
print("Deployment verified:", model["deployment_verified"])


# ============================================================
# Final report
# ============================================================

print()
print("===== REWARD SELECTION FINAL VERIFICATION =====")

print("Source archive: PASS")
print("Analysis data: PASS")
print("Figure integrity: PASS")
print("README structure and links: PASS")
print("Scale inventory: PASS")
print("Formal model identity: PASS")

print()
print("All verification checks: PASS")
print("05 Reward Weight Selection archive: COMPLETE")

