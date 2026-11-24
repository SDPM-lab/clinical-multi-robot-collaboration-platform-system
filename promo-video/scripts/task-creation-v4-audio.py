"""Build the 510-frame product film stereo bed and event cues."""
from pathlib import Path
import wave

import numpy as np

rate = 48_000
seconds = 17
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
air(91,.48,.049,.58)
air(160,1.25,.044,.61)
for f, pitches, gain, pan in [
    (39,[750,1450],.082,.69),(64,[840,1430],.073,.69),
    (126,[494,738],.055,.82),(152,[604,902],.067,.34),
    (233,[743,1370],.076,.51),(283,[315,816],.104,.62),
    (415,[638,1260],.064,.53),(425,[769,1170],.057,.52),
    (439,[569,980],.065,.56),(458,[705,1080],.071,.59),
]:
    tone(f,pitches,.11,gain,pan,24)
tone(300,[783.99,1174.66],.5,.152,.68,7)
tone(480,[700,1340],.105,.06,.56,26)
tone(490,[740,1100],.08,.047,.64,25)
tone(482,[523.25,783.99],.34,.085,.56,10)

out = Path(__file__).resolve().parents[1] / "public/task-creation-v4/score.wav"
with wave.open(str(out),"wb") as wf:
    wf.setparams((2,2,rate,0,"NONE","not compressed"))
    wf.writeframes((np.clip(mix,-1,1)*32767).astype("<i2").tobytes())
