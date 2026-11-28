from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from PIL import Image

DOC = Path(__file__).resolve().parent
ROOT = DOC.parents[3]

DATA = DOC / "data"
FIG = DOC / "figures"


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


archive = read(
    DATA / "environment_manifest.json"
)

config = read(
    DATA / "environment_config.json"
)

figures = read(
    FIG / "figure_manifest.json"
)

# Archive

assert archive["file_count"] == 19
assert len(archive["files"]) == 19

for item in archive["files"]:

    for path in [
        ROOT / item["source"],
        DOC / item["archive"],
    ]:

        assert path.is_file(), path
        assert sha(path) == item["sha256"], path
        assert path.stat().st_size == item["size_bytes"]

print("Archived source files: 19/19 PASS")

# Configuration

assert len(config) == 82

assert sha(
    DATA / "environment_config.json"
) == archive["configuration_sha256"]

assert config["SIMULATION_DAYS"] == 7
assert config["SIMULATION_HORIZON_S"] == 604800
assert config["REFERENCE_FLEET"] == [2, 2, 3]
assert config["EXPECTED_TOTAL_TASKS_PER_DAY"] == 58

assert config["ENABLE_BATTERY_MODEL"] is False
assert config["BATTERY_MIN_RESERVE_SOC"] == 0.15
assert config["BATTERY_CHARGE_TRIGGER_SOC"] == 0.25
assert config["BATTERY_RESUME_SOC"] == 0.8

print("Configuration values: 82 PASS")

# Figures

assert figures["figure_count"] == 10
assert len(figures["figures"]) == 10

assert sha(
    DATA / "environment_manifest.json"
) == figures["environment_manifest_sha256"]

assert sha(
    DATA / "environment_config.json"
) == figures["configuration_sha256"]

assert sha(
    DOC / "plot_environment.py"
) == figures["plot_script_sha256"]

verified = 0
source_checks = 0

for figure in figures["figures"]:

    for source in figure["sources"]:

        assert sha(
            DOC / source["file"]
        ) == source["sha256"]

        source_checks += 1

    for item in figure["outputs"]:

        path = DOC / item["file"]

        assert sha(path) == item["sha256"]
        assert path.stat().st_size == item["size_bytes"]

        if path.suffix == ".png":

            with Image.open(path) as im:

                assert all(
                    abs(v-300) < 1
                    for v in im.info["dpi"]
                )

                im.verify()

        elif path.suffix == ".svg":

            assert ET.parse(
                path
            ).getroot().tag.endswith("svg")

        verified += 1

assert verified == 20

assert len(list(FIG.glob("*.png"))) == 10
assert len(list(FIG.glob("*.svg"))) == 10

print("Figure groups: 10/10 PASS")
print("Figure files: 20/20 PASS")
print("Figure source checks:", source_checks)

# README basic structure

readme = DOC / "README.md"

assert readme.is_file()

content = readme.read_text(encoding="utf-8")

sections = re.findall(
    r"^## (\d+)\.",
    content,
    flags=re.MULTILINE,
)

assert sections == [
    str(i) for i in range(1, 18)
]

print("README sections: 17/17 PASS")
print("README lines:", len(content.splitlines()))

print()
print("===== ENVIRONMENT VERIFICATION =====")
print("Archived data: PASS")
print("Configuration: PASS")
print("Figures: PASS")
print("README basic structure: PASS")
print("Full README link integration: PENDING")
print("Visual inspection: PENDING")
