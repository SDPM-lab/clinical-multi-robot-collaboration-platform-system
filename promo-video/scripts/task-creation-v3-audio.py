"""Build the 480-frame product film stereo bed and event cues."""
from pathlib import Path
import wave

import numpy as np

rate = 48_000
seconds = 16
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

air(9,.72,.082,.38)
air(136,.32,.049,.58)
air(202,1.27,.044,.61)
for f, pitches, gain, pan in [
    (89,[750,1450],.082,.69),(112,[840,1430],.073,.69),
    (165,[494,738],.055,.82),(197,[604,902],.067,.34),
    (270,[743,1370],.076,.51),(297,[315,816],.104,.62),
    (410,[638,1260],.064,.53),(422,[769,1170],.057,.52),
    (438,[569,980],.065,.56),(454,[705,1080],.071,.59),
]:
    tone(f,pitches,.11,gain,pan,24)
tone(315,[783.99,1174.66],.5,.152,.68,7)
tone(457,[523.25,783.99],.34,.085,.56,10)

out = Path(__file__).resolve().parents[1] / "public/task-creation/v3-score.wav"
with wave.open(str(out),"wb") as wf:
    wf.setparams((2,2,rate,0,"NONE","not compressed"))
    wf.writeframes((np.clip(mix,-1,1)*32767).astype("<i2").tobytes())
