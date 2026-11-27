"""Mix frame-locked information cues and the original-speed synthetic narration."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/ppo-v6"
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

for frame, hz, d, level, pan in [
    (26,784,.15,.045,.40),(47,1046,.19,.043,.53),
    (111,659,.08,.035,.40),(155,880,.14,.049,.61),
    (216,523,.21,.028,.31),(242,659,.24,.031,.58),(252,784,.21,.039,.64),
    (281,587,.15,.035,.34),(292,698,.15,.036,.44),(308,784,.16,.035,.55),
    (327,880,.15,.044,.67),(351,659,.19,.038,.51),(386,988,.18,.030,.62),(403,587,.22,.036,.51),
    (450,698,.19,.038,.52),(487,880,.16,.036,.54),(542,1046,.25,.062,.55),(551,1318,.28,.043,.62),
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
av = (root / "node_modules/@remotion/compositor-linux-x64-gnu").resolve()
lines=["以強化學習改善調度。","從七台機器人篩選候選。","整合為九十八維狀態。","選擇動作，也估計狀態價值。","回饋更新策略。","派工用已訓練策略。","將任務指派給合適的機器人。"]
clips = []
for i in range(7):
    raw = subprocess.check_output([str(av/"ffmpeg"),"-v","error","-i",f"/tmp/medisync-v6-{i}.mp3","-ac","1","-ar","48000","-f","wav","-"],env=dict(os.environ, LD_LIBRARY_PATH=str(av)))
    samples = np.frombuffer(raw[raw.index(b"data")+8:], dtype="<i2").astype(float)/32768
    blocks = samples[:len(samples)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt(np.mean(blocks**2,axis=1))>.0022)
    clip = samples[max(0,(active[0]-3)*480):min(len(samples),(active[-1]+7)*480)]
    clip[-600:] *= np.linspace(1,0,600)
    clips.append(clip*.59/np.max(abs(clip)))

voice = np.zeros(length)
captions = []
for line, clip, step, limit in zip(lines, clips, [0, 90, 180, 264, 367, 420, 510], [90, 180, 264, 367, 420, 510, 600]):
    start = step * 1600
    end = step + int(np.ceil(len(clip)/1600))
    assert end <= limit, (line, step, end, limit)
    voice[start:start+len(clip)] = clip
    captions.append({"from":step,"to":min(limit,end+2),"text":line})
save("voice.wav",voice)
(root/"src/ppo-v6-captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2)+"\n")
print(captions)
