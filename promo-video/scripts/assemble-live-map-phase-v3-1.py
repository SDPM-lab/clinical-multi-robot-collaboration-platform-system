"""Encode the 120 original WebGL fleet frames and preserve their data timeline."""
import json
import math
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
source = Path(os.environ.get("MEDISYNC_LIVE_FRAMES", "/tmp/medisync-live-v31-dispatch"))
capture = json.loads((source / "metadata.json").read_text())
frames = capture["states"][420:]
assert len(frames) == 120 and capture["meta"]["buffer"] == [1920, 1080]
assert all(len(f["fleet"]) == 7 and len(f["routes"]) == 3 for f in frames)
assert frames[64]["progress"] < 1 and frames[65]["progress"] == 1
assert all(0 < route["progress"] < 1 for route in frames[-1]["routes"][1:])
for i in range(3):
    assert all(a["routes"][i]["progress"] <= b["routes"][i]["progress"] for a,b in zip(frames,frames[1:]))
assert len({tuple(r["ids"]) for r in frames[-1]["routes"]}) == 3
old = json.loads((root/"src/live-map-phase-v3-capture.json").read_text())["frames"]
assert math.dist(old[419]["camera"],frames[0]["camera"]) < .4
assert math.dist(old[419]["target"],frames[0]["target"]) < .4
for f in frames:
    assert math.dist(old[f["frame"]]["position"], f["position"]) < .001

ffmpeg = root/"node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
cmd = [str(ffmpeg),"-v","error","-y","-f","image2pipe","-framerate","30","-c:v","mjpeg","-i","-",
       "-an","-c:v","libx264","-crf","14","-pix_fmt","yuv420p",str(root/"public/live-map-phase-v3-1/fleet.mp4")]
with subprocess.Popen(cmd,stdin=subprocess.PIPE,env=dict(os.environ,LD_LIBRARY_PATH=str(ffmpeg.parent))) as pipe:
    assert pipe.stdin
    for frame in frames:
        pipe.stdin.write((source/f'{frame["frame"]}.jpg').read_bytes())
    pipe.stdin.close()
    assert pipe.wait() == 0
(root/"src/live-map-phase-v3-1-capture.json").write_text(json.dumps({"frames":frames},separators=(",",":"))+"\n")
for route in frames[-1]["routes"]:
    print(route["id"],"→".join(route["ids"]),route["progress"])
