"""Extract six verified native DOM rectangles from the capture."""
import json
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[1]
directory = root / "public/dashboard-v3"
layout_path = directory / "native-layout.json"
layout = json.loads(layout_path.read_text())
overview_path = directory / "native-overview.png"
base_path = directory / "native-base.png"
with Image.open(overview_path) as original:
    overview = original.convert("RGB")

supplement = directory / "native-chart-supplement.png"
if supplement.exists():
    box = layout["battery"]
    with Image.open(supplement) as crop:
        overview.paste(crop.convert("RGB").resize((box["width"], box["height"])), (box["x"], box["y"]))

# Remove the development-tool button outside the product DOM.
overview.paste(overview.crop((745, 874, 783, 900)), (781, 874))
overview.save(overview_path)
for name, box in layout.items():
    x, y, w, h = (box[key] for key in ("x", "y", "width", "height"))
    overview.crop((x, y, x + w, y + h)).save(directory / (name + ".png"))

if base_path.exists():
    with Image.open(base_path) as original:
        base = original.convert("RGB")
    base.paste(base.crop((745, 874, 783, 900)), (781, 874))
else:
    base = overview.copy()
    for box in layout.values():
        x, y, w, h = (box[key] for key in ("x", "y", "width", "height"))
        base.paste((230, 234, 237), (x, y, x + w, y + h))
base.save(base_path)
(root / "src/dashboard-v3-layout.json").write_text(json.dumps(layout, indent=2) + "\n")
