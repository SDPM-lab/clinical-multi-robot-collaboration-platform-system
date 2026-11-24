"""Isolate the real WebGL route and native success toast for frame-based motion."""
from collections import deque
import json
from pathlib import Path
from PIL import Image
import numpy as np

root = Path(__file__).resolve().parents[1]
assets = root / "public/task-creation"
capture = json.loads((root / "src/task-creation-capture.json").read_text())
points = capture["points"]
# Reproducible click offset from the actual Ward A marker interaction.
points["ward"]["x"] = round(points["ward"]["box"]["x"] + 10)
points["ward"]["y"] = round(points["ward"]["box"]["y"] + 28)
(root / "src/task-creation-capture.json").write_text(json.dumps(capture, indent=2)+"\n")
for name in ("initial","type-options","source-fixed","route","priority","loading","success","notification","schedule","edit","new-time","confirm","saved"):
    path=assets/(name+".png")
    with Image.open(path) as capture_frame:
        frame=capture_frame.convert("RGB")
    frame.paste(frame.crop((743,875,781,900)),(781,875))
    frame.save(path)
with Image.open(assets/"initial.png") as source:
    opening=source.convert("RGB")
    strip=opening.crop((12,98,22,722)).resize((422,624), Image.Resampling.BILINEAR)
    opening.paste(strip,(21,98))
    opening.save(assets/"opening-map.png")
before = Image.open(assets / "source-fixed.png").convert("RGB")
after = Image.open(assets / "route.png").convert("RGB")
original = np.asarray(before).astype(np.int16)
selected = np.asarray(after).astype(np.int16)
r, g, b = selected.transpose(2, 0, 1)
mask = ((abs(original - selected).max(axis=2) > 9)
        & (r > 145) & (r - g > 25) & (r - b > 35))
mask[:, :450] = False
mask[790:, :] = False
pixels = set(map(tuple, np.argwhere(mask)))
assert len(pixels) > 100, "No route overlay was detected in the native WebGL capture"
source = points["pharmacy"]
neighbors = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
def flood(start, available):
    distance = {start: 0}
    front = deque([start])
    while front:
        y, x = front.popleft()
        for dy, dx in neighbors:
            neighbor = (y+dy,x+dx)
            if neighbor in available and neighbor not in distance:
                distance[neighbor] = distance[y,x]+1
                front.append(neighbor)
    return distance

available = pixels.copy()
largest = {}
while available:
    fragment = flood(next(iter(available)), available)
    if len(fragment) > len(largest):
        largest = fragment
    available.difference_update(fragment)
assert len(largest) > 100, "No connected WebGL route was found"
start = min(largest, key=lambda p: (p[0]-source["y"])**2+(p[1]-source["x"])**2)
distance = flood(start, largest)
ys, xs = np.where(mask)
x0,y0,x1,y1 = int(min(xs)),int(min(ys)),int(max(xs))+1,int(max(ys))+1
width,height = x1-x0,y1-y0
cut = selected[y0:y1,x0:x1].astype(np.uint8)
thresholds = np.full((height,width), np.inf)
longest = max(distance.values())
for (y,x),value in distance.items(): thresholds[y-y0,x-x0] = value
steps=24
for i in range(steps):
    if i==0: alpha=np.zeros((height,width),dtype=np.uint8)
    elif i==steps-1: alpha=mask[y0:y1,x0:x1].astype(np.uint8)*255
    else: alpha=(thresholds<=longest*i/(steps-1)).astype(np.uint8)*255
    rgb = np.where(alpha[:, :, None] > 0, cut, 0).astype(np.uint8)
    Image.fromarray(np.dstack((rgb,alpha)), "RGBA").save(assets / f"route-{i}.png")
before.save(assets / "route-base.png")

toast = points["toast"]["box"]
box=tuple(round(a) for a in (toast["x"],toast["y"],toast["x"]+toast["width"],toast["y"]+toast["height"]))
with Image.open(assets/"success.png") as screenshot,Image.open(assets/"loading.png") as loading:
    img=screenshot.convert("RGB")
    img.paste(loading.crop(box),box[:2])
    img.save(assets/"success-base.png")
(root/"src/task-creation-route.json").write_text(json.dumps(dict(x=x0,y=y0,width=width,height=height,count=steps),indent=2)+"\n")
print(f"Isolated native route with {len(pixels)} pixels and {steps} frame-driven path stages.")
