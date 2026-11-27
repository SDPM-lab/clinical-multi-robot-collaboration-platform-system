"""Mix frame-locked information cues and the original-speed synthetic narration."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/ppo-spatial"
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
    (28,880,.13,.051,.35),(37,987.77,.14,.052,.46),(46,1108.73,.14,.052,.56),
    (121,698.46,.19,.052,.52),(143,880,.21,.065,.62),
    (182,587.33,.29,.038,.29),(204,659.25,.32,.045,.42),
    (238,783.99,.31,.053,.59),(268,987.77,.25,.071,.69),
    (300,1174.66,.27,.122,.65),(390,659.25,.35,.038,.76),
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
av = (root / "node_modules/@remotion/compositor-linux-x64-gnu").resolve()
lines = ["從任務需求，到車隊的能力與狀態。","將調度負載整合為九十八維狀態。","訓練從回饋學習。派工使用既有策略。","從合格車隊，完成指派。"]
clips = []
for i in range(4):
    raw = subprocess.check_output([str(av/"ffmpeg"),"-v","error","-i",f"/tmp/medisync-spatial-{i}.mp3","-ac","1","-ar","48000","-f","wav","-"],env=dict(os.environ, LD_LIBRARY_PATH=str(av)))
    samples = np.frombuffer(raw[raw.index(b"data")+8:], dtype="<i2").astype(float)/32768
    blocks = samples[:len(samples)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt(np.mean(blocks**2,axis=1))>.0022)
    clip = samples[max(0,(active[0]-3)*480):min(len(samples),(active[-1]+7)*480)]
    clip[-600:] *= np.linspace(1,0,600)
    clips.append(clip*.59/np.max(abs(clip)))

voice = np.zeros(length)
captions = []
step = 5
for i,(line,clip) in enumerate(zip(lines,clips)):
    if i == 2:
        step = max(step,178)
    start = step*1600
    assert start+len(clip)<=len(voice), (i,step,len(clip))
    voice[start:start+len(clip)] = clip
    end = step+int(np.ceil(len(clip)/1600))
    captions.append({"from":step,"to":min(450,end+2),"text":line})
    step=end+4
save("voice.wav",voice)
(root/"src/ppo-spatial-captions.json").write_text(json.dumps(captions,ensure_ascii=False,indent=2)+"\n")
print(captions)
