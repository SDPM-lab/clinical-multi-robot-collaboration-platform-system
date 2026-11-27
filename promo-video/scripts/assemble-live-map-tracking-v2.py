"""Use original per-frame JPEGs; repeat only explicitly locked camera holds."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
source = Path(os.environ.get("MEDISYNC_LIVE_FRAMES", "/tmp/medisync-live-v2-buffer"))
target = root / "public/live-map-tracking-v2"
capture = json.loads((source / "metadata.json").read_text())
frames = capture["states"]
assert len(frames) == 450 and capture["meta"]["buffer"] == [1920,1080]
assert [row["frame"] for row in frames] == list(range(450))
assert all(a["progress"] <= b["progress"] for a,b in zip(frames,frames[1:]))
assert frames[397]["progress"] == 1
assert math.dist(frames[397]["position"], capture["meta"]["path"][-1]) < .001
assert capture["meta"]["robotAsset"] == "AGIBOT_A2D"

ffmpeg = root/"node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
env = dict(os.environ, LD_LIBRARY_PATH=str(ffmpeg.parent))

def encode(images, output):
    with subprocess.Popen([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe",
        "-framerate", "30", "-c:v", "mjpeg", "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", str(target/output),
    ], stdin=subprocess.PIPE, env=env) as writer:
        assert writer.stdin
        for file in images:
            writer.stdin.write(file.read_bytes())
        writer.stdin.close()
        assert writer.wait() == 0

def main_frame(f):
    if 25 <= f < 108:
        f = 24
    elif 159 <= f < 197:
        f = 158
    elif 402 <= f < 449:
        f = 401
    return source/f"{f}.jpg"

encode([main_frame(f) for f in range(450)], "map.mp4")
encode([source/f"local-{f}.jpg" for f in range(270,322)], "local.mp4")
shutil.copy2(source/"203.jpg", target/"overhead-handoff.jpg")
shutil.copy2(source/"359.jpg", target/"follow-handoff.jpg")
(root/"src/live-map-tracking-v2-capture.json").write_text(json.dumps({
    "route":capture["meta"],"frames":frames,
},separators=(",",":"))+"\n")
print("450 main frames, 52 synchronized alternate frames; no blending or optical flow")
