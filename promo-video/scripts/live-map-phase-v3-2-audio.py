"""Mix frame-locked information cues and the original-speed synthetic narration."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/live-map-phase-v3-2"
directory.mkdir(exist_ok=True)
rate = 48000
length = 600 * 1600
time = np.arange(length) / rate

def save(name, audio):
    with wave.open(str(directory / name), "wb") as handle:
        handle.setparams((1 if audio.ndim == 1 else 2, 2, rate, 0, "NONE", "not compressed"))
        handle.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())

score = np.zeros((length, 2))
fade = np.minimum(1, time/.35) * np.minimum(1, (20-time)/.55)
for ch in range(2):
    for hz, pace in [(146.83,.77),(220,1.06),(293.66,.82),(369.99,.66)]:
        score[:,ch] += .012*np.sin(2*np.pi*hz*time+ch*.27)*fade*(.72+.28*np.cos(pace*time+ch*.33))

for frame,hz,d,level,pan in [
 (30,523,.26,.036,.52),(69,659,.17,.036,.55),(99,784,.16,.04,.53),
 (150,880,.15,.044,.48),(205,523,.27,.035,.50),(244,659,.15,.037,.50),
 (289,880,.095,.038,.54),(349,880,.095,.038,.54),(444,523,.28,.036,.53),
 (474,784,.22,.038,.59),(485,1047,.23,.048,.54)
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
av = (root / "node_modules/@remotion/compositor-linux-x64-gnu").resolve()
lines=["任務進入地圖。","位置與進度，一目了然。","近距離跟隨機器人。","還能自由切換三種觀察視角，從不同角度追蹤機器人的移動。","一張地圖，掌握整個車隊的多項作業。"]
clips = []
for i in range(len(lines)):
    prefix="v3" if i<3 else "v32"
    raw = subprocess.check_output([str(av/"ffmpeg"),"-v","error","-i",f"/tmp/medisync-live-{prefix}-{i}.mp3","-ac","1","-ar","48000","-f","wav","-"],env=dict(os.environ, LD_LIBRARY_PATH=str(av)))
    samples = np.frombuffer(raw[raw.index(b"data")+8:], dtype="<i2").astype(float)/32768
    blocks = samples[:len(samples)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt(np.mean(blocks**2,axis=1))>.0022)
    clip = samples[max(0,(active[0]-3)*480):min(len(samples),(active[-1]+7)*480)]
    clip[-600:] *= np.linspace(1,0,600)
    clips.append(clip*.59/np.max(abs(clip)))

voice = np.zeros(length)
captions = []
for line, clip, step, limit in zip(lines, clips, [0,60,150,228,425], [60,150,228,425,600]):
    start = step * 1600
    end = step + int(np.ceil(len(clip)/1600))
    assert end <= limit, (line, step, end, limit)
    voice[start:start+len(clip)] = clip
    captions.append({"from":step,"to":min(limit,end+2),"text":line})
save("voice.wav",voice)
(root/"src/live-map-phase-v3-2-captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2)+"\n")
print(captions)
