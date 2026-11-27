"""Mix frame-locked information cues and the original-speed synthetic narration."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/ppo-v5"
directory.mkdir(exist_ok=True)
rate = 48000
length = 540 * 1600
time = np.arange(length) / rate

def save(name, audio):
    with wave.open(str(directory / name), "wb") as handle:
        handle.setparams((1 if audio.ndim == 1 else 2, 2, rate, 0, "NONE", "not compressed"))
        handle.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())

score = np.zeros((length, 2))
fade = np.minimum(1, time/.35) * np.minimum(1, (18-time)/.55)
for ch in range(2):
    for hz, pace in [(146.83,.77),(220,1.06),(293.66,.82),(369.99,.66)]:
        score[:,ch] += .012*np.sin(2*np.pi*hz*time+ch*.27)*fade*(.72+.28*np.cos(pace*time+ch*.33))

for frame, hz, d, level, pan in [
    (22,784,.15,.038,.40),(31,1046,.19,.046,.52),
    (105,659,.080,.037,.32),(122,880,.14,.046,.61),
    (168,523,.21,.026,.32),(197,659,.24,.032,.58),(215,784,.21,.040,.65),
    (251,587,.15,.037,.34),(272,659,.16,.037,.55),(292,784,.18,.043,.67),(319,880,.20,.040,.51),
    (352,587,.10,.025,.44),(401,659,.22,.037,.42),(476,1046,.25,.061,.55),(488,1318,.28,.047,.62),
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
av = (root / "node_modules/@remotion/compositor-linux-x64-gnu").resolve()
lines=["近端策略優化。","先篩選合適的機器人。","整合為九十八維狀態。","演員決策，評論家估值。","回饋更新策略。","排程時，已訓練的策略依當前狀態完成指派。"]
clips = []
for i in range(6):
    raw = subprocess.check_output([str(av/"ffmpeg"),"-v","error","-i",f"/tmp/medisync-v5-{i}.mp3","-ac","1","-ar","48000","-f","wav","-"],env=dict(os.environ, LD_LIBRARY_PATH=str(av)))
    samples = np.frombuffer(raw[raw.index(b"data")+8:], dtype="<i2").astype(float)/32768
    blocks = samples[:len(samples)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt(np.mean(blocks**2,axis=1))>.0022)
    clip = samples[max(0,(active[0]-3)*480):min(len(samples),(active[-1]+7)*480)]
    clip[-600:] *= np.linspace(1,0,600)
    clips.append(clip*.59/np.max(abs(clip)))

voice = np.zeros(length)
captions = []
for line, clip, step, limit in zip(lines, clips, [3, 75, 150, 240, 335, 390], [75, 150, 240, 335, 390, 540]):
    start = step * 1600
    end = step + int(np.ceil(len(clip)/1600))
    assert end <= limit, (line, step, end, limit)
    voice[start:start+len(clip)] = clip
    captions.append({"from":step,"to":min(limit,end+2),"text":line})
save("voice.wav",voice)
(root/"src/ppo-v5-captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2)+"\n")
print(captions)
