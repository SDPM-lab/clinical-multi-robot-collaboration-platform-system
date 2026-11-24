"""Original quiet stereo cue sheet for the TaskCreationPrototype."""
from math import sin,tau, exp,sqrt
from pathlib import Path
from random import Random
import struct,wave

rate=24000
# Hover, control changes, map taps, route, submit, success, schedule and save.
events=[
    (61,0.10, 0,-.35,.018),(67,.12,0,-.43,.035),(97,.12,0,-.4,.029),
    (146,.21,485,.45,.028),(184,.18,540,-.10,.035),(187,.62,0,.24,.019),
    (292,.13,0,-.42,.039),(328,.15,0,-.44,.045),
    (353,.38,880,.58,.041),(377,.12,0,.53,.021),(405,.16,0,-.42,.024),
    (427,.13,0,-.4,.023),(451,.09,0,-.33,.022),(474,.13,0,-.25,.028),
    (495,.11,0,0,.036),(505,.36,660,.37,.034),
]
rng=Random(93)
low=0
samples=bytearray()
notes=(130.81,164.81,196,261.63,110,130.81,164.81,220)
for i in range(18*rate):
    t=i/rate
    phase=t%.63
    frequency=notes[int(t/.63)%len(notes)]
    bed=.013*sin(tau*frequency*t)*min(1,phase/.1)*exp(-4.6*phase)*min(1,t*2,(18-t)*1.8)
    left=right=bed
    low=.64*low+.36*rng.uniform(-1,1)
    for frame,length,freq,pan,gain in events:
        age=t-frame/30
        if 0<=age<length:
            shape=min(1,age/.01)*(1-age/length)**2
            signal=(sin(tau*freq*age)+.18*sin(tau*freq*2*age)) if freq else low
            left+=shape*signal*gain*sqrt((1-pan)/2)
            right+=shape*signal*gain*sqrt((1+pan)/2)
    samples.extend(struct.pack("<hh",round(left*32767),round(right*32767)))
with wave.open(str(Path(__file__).resolve().parents[1]/"public/task-creation/score.wav"),"wb") as out:
    out.setparams((2,2,rate,0,"NONE","not compressed")); out.writeframes(samples)
