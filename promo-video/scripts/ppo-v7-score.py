"""Mix frame-locked information cues and the original-speed synthetic narration."""
from pathlib import Path
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
directory = root / "public/ppo-v7"
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
    (121,659,.08,.035,.40),(155,880,.14,.049,.61),
    (216,523,.21,.028,.31),(242,659,.24,.031,.58),(252,784,.21,.039,.64),
    (281,587,.15,.035,.34),(292,698,.15,.036,.44),(308,784,.16,.035,.55),
    (327,880,.15,.044,.67),(351,659,.19,.038,.51),(386,988,.18,.030,.62),(403,587,.22,.036,.51),
    (450,698,.19,.038,.52),(483,880,.16,.036,.54),(546,1046,.25,.062,.55),(551,1318,.28,.043,.62),
]:
    t = np.arange(round(d*rate))/rate
    env = np.minimum(1,t/.008)*np.minimum(1,(d-t)/.035)*np.exp(-7*t)
    tone = level*env*(np.sin(2*np.pi*hz*t)+.30*np.sin(2*np.pi*hz*1.5*t))
    start = frame*1600
    score[start:start+len(t)] += tone[:,None]*np.sqrt([1-pan,pan])[None,:]
save("score.wav", score)
