"""Build the 585-frame product film stereo bed and event cues."""
from pathlib import Path
import wave

import numpy as np

rate = 48_000
seconds = 19.5
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
def click_sound(pitch, variant):
    duration={"tick":.031,"mouse":.038,"tap":.044}[variant]
    t=np.arange(round(duration*rate))/rate
    env=np.minimum(1,t/.00065)*np.exp(-120*t)*np.minimum(1,(duration-t)/.007)
    wavelets=np.sin(2*np.pi*pitch*t)+.22*np.sin(2*np.pi*pitch*1.73*t)
    grit=noise.normal(size=t.size)
    if variant=="mouse":
        wavelets+=.24*np.sin(2*np.pi*3300*t)*np.exp(-180*t)
        wavelets+=.13*grit*np.exp(-60*t)
    if variant=="tap":
        env=np.minimum(1,t/.002)*np.exp(-86*t)*np.minimum(1,(duration-t)/.01)
    return wavelets*env

for frame,pitch,gain,pan,variant in [
    (39,2350,.100,.69,"tick"),(64,2640,.112,.69,"mouse"),
    (152,2680,.097,.34,"tick"),(233,2520,.103,.50,"tick"),(283,1840,.135,.58,"mouse"),
    (465,2400,.091,.64,"mouse"),(480,2320,.078,.36,"tap"),
    (513,1970,.091,.42,"mouse"),(538,2450,.092,.56,"tick"),
]:
    add(frame,click_sound(pitch,variant)*gain,pan)

tone(126,[1080,1620],.105,.062,.79,22)
tone(308,[880,1320,1760],.29,.113,.43,12)
tone(318,[1174.66,1761.99,2349.32],.36,.104,.57,11)
tone(541,[1174.66,1761.99],.115,.077,.54,25)

out = Path(__file__).resolve().parents[1] / "public/task-creation-v7/score.wav"
with wave.open(str(out),"wb") as wf:
    wf.setparams((2,2,rate,0,"NONE","not compressed"))
    wf.writeframes((np.clip(mix,-1,1)*32767).astype("<i2").tobytes())

