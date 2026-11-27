"""Build the 540-frame product film stereo bed and event cues."""
from pathlib import Path
import wave

import numpy as np

rate = 48_000
seconds = 18
clock = np.arange(rate * seconds) / rate
mix = np.zeros((len(clock), 2))
noise = np.random.default_rng(773)

def add(f, data, pan):
    start = f * 1600
    data = data[:len(clock) - start]
    mix[start:start + len(data)] += data[:, None] * np.sqrt([1-pan, pan])

def tone(f, pitches, duration, level, pan, release):
    t = np.arange(round(duration * rate)) / rate
    env = np.minimum(1, t / .008) * np.minimum(1, (duration-t)/.035) * np.exp(-release*t)
    sound = sum(np.sin(2*np.pi*hz*t)/(i+1) for i,hz in enumerate(pitches))
    add(f, sound*env*level, pan)

def air(f, duration, level, pan):
    count = round(rate*duration)
    t = np.arange(count)/rate
    data = np.convolve(noise.normal(0,1,count),np.ones(21)/21,mode="same")
    add(f, data*np.sin(np.pi*t/duration)**2*level,pan)

fade = np.clip(clock / .42,0,1) * np.clip((seconds-clock)/.7,0,1)
for channel in range(2):
    phase = channel*.38
    for f, speed in [(146.83, 1.55), (220, 2.3), (293.66, .77), (369.99, 1.1)]:
        mix[:, channel] += .011*np.sin(2*np.pi*f*clock+phase)*(.6+.4*np.sin(2*np.pi*speed*clock+phase))*fade

air(4,.72,.075,.52)
air(91,.48,.041,.58)
air(160,1.25,.044,.61)
def click(frame, pitch, gain, pan):
    t=np.arange(round(.048*rate))/rate
    env=np.minimum(1,t/.0015)*np.exp(-110*t)*np.minimum(1,(.048-t)/.008)
    metal=sum(np.sin(2*np.pi*hz*t)*level for hz,level in
              [(pitch,1),(pitch*1.56,.36),(pitch*2.28,.15)])
    add(frame,(metal+.11*noise.normal(size=t.size))*env*gain,pan)

for frame,pitch,gain,pan in [
    (39,1810,.105,.69),(64,2010,.116,.69),
    (152,2370,.111,.34),(233,1910,.108,.50),(283,1440,.142,.58),
    (444,1940,.085,.54),(458,2110,.069,.45),(477,1700,.090,.55),
    (499,1920,.094,.56),(509,1730,.071,.57),
]:
    click(frame,pitch,gain,pan)

tone(126,[1080,1620],.105,.062,.79,22)
tone(308,[880,1320,1760],.29,.113,.43,12)
tone(318,[1174.66,1761.99,2349.32],.36,.104,.57,11)
tone(501,[659.25,987.77],.27,.081,.54,13)

out = Path(__file__).resolve().parents[1] / "public/task-creation-v5/score.wav"
with wave.open(str(out),"wb") as wf:
    wf.setparams((2,2,rate,0,"NONE","not compressed"))
    wf.writeframes((np.clip(mix,-1,1)*32767).astype("<i2").tobytes())
