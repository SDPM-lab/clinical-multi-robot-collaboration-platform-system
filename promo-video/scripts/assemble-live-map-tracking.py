"""Generate exact-frame plates from the captured product scene and camera metadata."""
import json
import os
from pathlib import Path
import subprocess

import cv2
import numpy as np

cv2.setNumThreads(4)

root = Path(__file__).resolve().parents[1]
capture = Path(os.environ.get("MEDISYNC_LIVE_FRAMES", "/tmp/medisync-live-frames"))
output = root / "public/live-map-tracking"
metadata = json.loads((capture / "metadata.json").read_text())
frames = [metadata["states"][str(index)] for index in range(420)]
assert all(a["progress"] <= b["progress"] for a,b in zip(frames,frames[1:]))
assert frames[0]["progress"] == 0 and frames[340]["progress"] == 1
assert np.allclose(frames[340]["position"], metadata["meta"]["path"][-1])
assert metadata["meta"]["robotAsset"] == "AGIBOT_A2D"

sources = sorted((int(file.stem), file) for file in capture.glob("*.jpg"))
assert sources[0][0] == 0 and sources[-1][0] == 419
ffmpeg = (root/"node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg").resolve()
env = dict(os.environ, LD_LIBRARY_PATH=str(ffmpeg.parent))
writer = subprocess.Popen([
    str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-f","image2pipe",
    "-framerate","30","-c:v","png","-i","-",
    "-an","-c:v","libx264","-crf","14","-pix_fmt","yuv420p",str(output/"map-plates.mp4")
], stdin=subprocess.PIPE, env=env)
assert writer.stdin
flow = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_FAST)
x,y = np.meshgrid(np.arange(1280,dtype=np.float32),np.arange(720,dtype=np.float32))
grid=np.dstack((x,y))
def estimate(a,b):
    def gray(frame):
        return cv2.cvtColor(cv2.resize(frame,(640,360)),cv2.COLOR_BGR2GRAY)
    return cv2.resize(flow.calc(gray(a),gray(b),None),(1280,720))*2

def write_frame(image):
    encoded, buffer = cv2.imencode(".png",image,[cv2.IMWRITE_PNG_COMPRESSION,1])
    assert encoded
    writer.stdin.write(buffer.tobytes())

previous_frame, first = sources[0]
previous = cv2.imread(str(first))
write_frame(previous)
for frame,path in sources[1:]:
    current = cv2.imread(str(path))
    gap=frame-previous_frame
    if gap>1 and int(previous_frame>=128)==int(frame>=128):
        forward=estimate(previous,current)
        backward=estimate(current,previous)
        for step in range(1,gap):
            p=step/gap
            a=cv2.remap(previous,grid-forward*p,None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
            b=cv2.remap(current,grid-backward*(1-p),None,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
            write_frame(cv2.addWeighted(a,1-p,b,p,0))
    elif gap>1:
        for _ in range(1,gap):
            write_frame(previous)
    write_frame(current)
    previous_frame, previous = frame,current
writer.stdin.close()
assert writer.wait()==0
for frame_index in [0,59,60,149,150,269,270,339,340,359,360,419]:
    assert frame_index in dict(sources)
(root/"src/live-map-tracking-capture.json").write_text(json.dumps({
    "route":metadata["meta"],"frames":frames,
},separators=(",",":"))+"\n")
print(f"{len(sources)} actual browser captures, 420 frames, {metadata['meta']['length']:.2f} scene units")
