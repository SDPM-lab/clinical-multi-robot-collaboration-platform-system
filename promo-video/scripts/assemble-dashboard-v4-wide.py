"""Place the original panel captures at their measured DOM coordinates."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
assets = root / "public"
wide = assets / "dashboard-v4"
native = assets / "dashboard-v3"
layout = json.loads((root / "src/dashboard-v3-layout.json").read_text())
with Image.open(wide / "wide-capture.png") as source:
    base = source.convert("RGB")
assert base.size == (1600, 900), base.size
# Remove the local devtools control outside the product.
base.paste(base.crop((745, 874, 783, 900)), (781, 874))
base.save(wide / "wide-base.png")
hero = base.copy()
for name, rect in layout.items():
    size = (rect["width"], rect["height"])
    source = (wide if name == "battery" else native) / (name + ".png")
    with Image.open(source) as panel:
        panel = panel.convert("RGB")
        if panel.size != size:
            panel = panel.resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius=6, fill=255)
    hero.paste(panel, (rect["x"], rect["y"]), mask)
hero.save(wide / "wide-hero.png")
