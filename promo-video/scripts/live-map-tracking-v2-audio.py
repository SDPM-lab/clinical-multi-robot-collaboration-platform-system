"""Mix frame-locked information cues and the original-speed synthetic narration."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/live-map-tracking-v2"
directory.mkdir(exist_ok=True)
rate = 48000
length = 450 * 1600
time = np.arange(length) / rate

def save(name, audio):
    with wave.open(str(directory / name), "wb") as handle:
        handle.setparams((1 if audio.ndim == 1 else 2, 2, rate, 0, "NONE", "not compressed"))
        handle.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())

score = np.zeros((length, 2))
fade = np.minimum(1, time/.35) * np.minimum(1, (15-time)/.55)
for ch in range(2):
    for hz, pace in [(146.83,.77),(220,1.06),(293.66,.82),(369.99,.66)]:
        score[:,ch] += .012*np.sin(2*np.pi*hz*time+ch*.27)*fade*(.72+.28*np.cos(pace*time+ch*.33))

for frame, hz, d, level, pan in [
 (18,523,.30,.035,.49),(100,659,.14,.04,.39),(120,784,.15,.044,.61),
 (154,587,.18,.029,.49),(196,880,.13,.042,.55),(217,523,.30,.031,.50),
 (282,698,.16,.04,.57),(322,784,.16,.037,.65),(371,523,.27,.026,.53),
 (397,1047,.22,.052,.53),(412,1319,.27,.028,.61)
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
av = (root / "node_modules/@remotion/compositor-linux-x64-gnu").resolve()
lines=["三維即時地圖。","任務與進度，一目了然。","近距離跟隨機器人。","切換視角，掌握動態。","一個平台，掌握每次任務。"]
clips = []
for i in range(5):
    raw = subprocess.check_output([str(av/"ffmpeg"),"-v","error","-i",f"/tmp/medisync-live-v2-{i}.mp3","-ac","1","-ar","48000","-f","wav","-"],env=dict(os.environ, LD_LIBRARY_PATH=str(av)))
    samples = np.frombuffer(raw[raw.index(b"data")+8:], dtype="<i2").astype(float)/32768
    blocks = samples[:len(samples)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt(np.mean(blocks**2,axis=1))>.0022)
    clip = samples[max(0,(active[0]-3)*480):min(len(samples),(active[-1]+7)*480)]
    clip[-600:] *= np.linspace(1,0,600)
    clips.append(clip*.59/np.max(abs(clip)))

voice = np.zeros(length)
captions = []
for line, clip, step, limit in zip(lines, clips, [0,90,180,270,360], [90,180,270,360,450]):
    start = step * 1600
    end = step + int(np.ceil(len(clip)/1600))
    assert end <= limit, (line, step, end, limit)
    voice[start:start+len(clip)] = clip
    captions.append({"from":step,"to":min(limit,end+2),"text":line})
save("voice.wav",voice)
(root/"src/live-map-tracking-v2-captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2)+"\n")
print(captions)
