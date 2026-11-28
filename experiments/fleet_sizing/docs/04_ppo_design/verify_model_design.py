from pathlib import Path
from datetime import datetime
import hashlib
import json
import csv
import re
import xml.etree.ElementTree as ET

import numpy as np

from PIL import Image

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]
DATA = DOC / "data"
FIG = DOC / "figures"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads(
        (DATA / name).read_text(encoding="utf-8")
    )


def rows(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


manifest = read("model_design_manifest.json")
integrity = read("model_integrity.json")
metadata = read("final_model_metadata.json")
architecture = read("model_architecture.json")
training = read("ppo_hyperparameters.json")
reward = read("reward_config.json")
decision = read("example_decision.json")

# ============================================================
# 1. Formal model identity
# ============================================================

EXPECTED_SHA = (
    "1972295e176e6907d3bee4d01b301fa"
    "10526dac40dca38a5e867fe1a63825d07"
)

model = ROOT / integrity["model_path"]

assert sha(model) == EXPECTED_SHA
assert integrity["model_sha256"] == EXPECTED_SHA
assert manifest["model_sha256"] == EXPECTED_SHA
assert decision["model_sha256"] == EXPECTED_SHA

assert sha(DATA / "final_model_metadata.json") == (
    integrity["historical_metadata_sha256"]
)

assert metadata["model_seed"] == 7101
assert training["model_seed"] == 7101
assert training["actual_timesteps"] == 200192

print("Formal PPO model identity: PASS")
print("Model metadata identity: PASS")

# ============================================================
# 2. Archived data, figures and scripts
# ============================================================

assert manifest["file_count"] == 22
assert len(manifest["files"]) == 22

for item in manifest["files"]:

    path = DOC / item["file"]

    assert path.is_file(), path
    assert sha(path) == item["sha256"], path
    assert path.stat().st_size == item["size_bytes"]

for name, expected in manifest["scripts"].items():

    assert sha(DOC / name) == expected, name

assert len(manifest["scripts"]) == 3

for entry in integrity["navigation_source_sha256"].values():

    assert sha(ROOT / entry["path"]) == entry["sha256"]

print("Archived data and figures: 22/22 PASS")
print("Generation scripts: 3/3 PASS")
print("Nav2 source identity: PASS")

# ============================================================
# 3. Observation, actions and architecture
# ============================================================

layout = rows("observation_layout.csv")
observation = rows("example_observation.csv")
mapping = rows("action_mapping.csv")
parameters = rows("model_parameters.csv")

assert len(layout) == 98
assert len(observation) == 98
assert len(mapping) == 7
assert len(parameters) == 12

assert [int(r["index"]) for r in layout] == list(range(98))

assert architecture["observation_shape"] == [98]
assert architecture["action_count"] == 7
assert architecture["actor_parameters"] == 10951
assert architecture["critic_parameters"] == 10561
assert architecture["total_parameters"] == 21512

assert sum(
    int(r["parameter_count"])
    for r in parameters
) == 21512

values = np.array([
    float(r["value"])
    for r in observation
])

assert np.all(np.isfinite(values))
assert np.all((values >= 0) & (values <= 1))

print("Observation layout: 98/98 PASS")
print("Action mapping: 7/7 PASS")
print("Model parameters: 21512 PASS")

# ============================================================
# 4. Reward configuration
# ============================================================

assert reward == metadata["reward_config"]

weights = [
    reward["waiting_weight"],
    reward["approach_weight"],
    reward["queue_weight"],
    reward["imbalance_weight"],
]

assert weights == [0.40, 0.35, 0.15, 0.10]
assert np.isclose(sum(weights), 1)

assert reward["waiting_scale_s"] == 600
assert reward["approach_scale_s"] == 600
assert reward["tasks_ahead_scale"] == 10

print("Reward configuration: PASS")

# ============================================================
# 5. Actual inference
# ============================================================

mask = np.array(
    decision["action_mask"], dtype=bool
)

raw = np.array(
    decision["unmasked_action_probabilities"]
)

masked = np.array(
    decision["masked_action_probabilities"]
)

assert mask.tolist() == [
    False, False, True, True, False, False, False
]

assert raw.shape == masked.shape == (7,)
assert np.isclose(raw.sum(), 1)
assert np.isclose(masked.sum(), 1)

assert np.allclose(masked[~mask], 0)

expected_masked = raw * mask
expected_masked /= expected_masked.sum()

assert np.allclose(
    masked,
    expected_masked,
    atol=1e-6,
)

assert decision["selected_action"] == 2
assert decision["selected_robot_id"] == "M01"
assert masked.argmax() == 2

assert np.isclose(
    masked[2],
    0.8139893412590027,
)

assert np.isfinite(
    decision["critic_state_value"]
)

assert decision["environment_step_executed"] is False
assert decision["model_training_performed"] is False

print("Actual action probabilities: PASS")
print("Masked probability normalization: PASS")
print("Selected robot M01: PASS")

# ============================================================
# 6. Figures
# ============================================================

pngs = sorted(FIG.glob("*.png"))
svgs = sorted(FIG.glob("*.svg"))

assert len(pngs) == len(svgs) == 6

assert {p.stem for p in pngs} == {
    p.stem for p in svgs
}

for path in pngs:

    with Image.open(path) as im:

        assert all(
            abs(v - 300) < 1
            for v in im.info["dpi"]
        )

        im.verify()

for path in svgs:

    assert ET.parse(
        path
    ).getroot().tag.endswith("svg")

print("Figure groups: 6/6 PASS")
print("Figure files: 12/12 PASS")

# ============================================================
# 7. Historical backup
# ============================================================

backup = DOC / manifest["historical_backup"]

assert backup.is_dir()
assert (backup / "README.md").is_file()

assert len(list(
    (backup / "data").iterdir()
)) == 10

assert len(list(
    (backup / "figures").glob("*.png")
)) == 5

assert len(list(
    (backup / "figures").glob("*.svg")
)) == 5

print("Historical backup presence: PASS")

# ============================================================
# 8. README structure and links
# ============================================================

readme = DOC / "README.md"
content = readme.read_text(encoding="utf-8")

sections = re.findall(
    r"^## (\d+)\.",
    content,
    flags=re.MULTILINE,
)

assert sections == [
    str(i) for i in range(1, 18)
]

images = re.findall(
    r"!\[[^\]]*\]\(([^)]+)\)",
    content,
)

assert len(images) == 6

assert set(images) == {
    str(p.relative_to(DOC))
    for p in pngs
}

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

    raise AssertionError("Unresolved README links")

assert content.count("```") % 2 == 0
assert content.count("$$") % 2 == 0

for value in [
    "Nav2 Sweep 12",
    "7101",
    "200192",
    "21512",
    "Selected action: 2",
    "Selected robot: M01",
    "-0.96",
    EXPECTED_SHA,
]:

    assert value in content, value

print("README sections: 17/17 PASS")
print("README embedded figures: 6/6 PASS")
print("README links checked:", len(links))
print("README missing links:", len(missing))
print("README lines:", len(content.splitlines()))

# ============================================================
# 9. README manifest
# ============================================================

readme_manifest = {
    "verified_at": datetime.now().astimezone().isoformat(),
    "readme_sha256": sha(readme),
    "model_design_manifest_sha256": sha(
        DATA / "model_design_manifest.json"
    ),
    "verification_script_sha256": sha(Path(__file__)),
    "model_sha256": EXPECTED_SHA,
    "model_seed": 7101,
    "sections": len(sections),
    "lines": len(content.splitlines()),
    "embedded_figures": len(images),
    "links_checked": len(links),
    "missing_links": missing,
    "archived_files": 22,
    "verification_status": "PASS",
    "deployment_verified": False,
    "verification_scope": (
        "File integrity, model identity, exported inference data, "
        "figure formats, README structure and local links."
    ),
}

(DATA / "readme_manifest.json").write_text(
    json.dumps(
        readme_manifest,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print()
print("===== SECTION 04 FINAL VERIFICATION =====")
print("Formal model: PASS")
print("Model architecture: PASS")
print("Reward configuration: PASS")
print("Observation and action mapping: PASS")
print("Actual inference: PASS")
print("Historical backup presence: PASS")
print("Archived files: 22/22 PASS")
print("Figures: PASS")
print("README: PASS")
print("README SHA256:", sha(readme))
print("README manifest: COMPLETE")
print("Model retrained: NO")
print("New full evaluation episodes: 0")
print("Deployment verified: False")
print("SECTION 04: COMPLETE")
