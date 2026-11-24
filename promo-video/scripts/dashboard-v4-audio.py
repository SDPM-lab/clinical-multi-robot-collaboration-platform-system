"""Original chord bed and quiet, non-pitched stereo UI accents."""
from pathlib import Path
from math import exp, sin, sqrt, tau
from random import Random
import struct
import sys
import wave

rate = 24000
rng = Random(604)
piano = [0.0] * (rate * 10)
v5 = "--v5" in sys.argv
accents = ([(20, 0), (92, .48), (99, -.46), (121, .24), (172, 0), (231, -.28), (284, .25)]
           if v5 else [(20, 0), (119, .48), (133, -.46), (172, .32), (234, 0)])
chords = [(130.81, 164.81, 196.00, 293.66), (110, 130.81, 164.81, 261.63),
          (87.31, 130.81, 174.61, 220.00), (98, 146.83, 196.00, 246.94)]
for beat in range(16):
    start = int(beat * .56 * rate)
    chord = chords[(beat // 4) % len(chords)]
    f = chord[beat % len(chord)]
    for i in range(min(rate * 2, len(piano) - start)):
        age = i / rate
        env = min(1, age/.04) * exp(-3.2*age)
        piano[start+i] += .025 * env * (sin(tau*f*age) + .14*sin(tau*2*f*age))

pcm=bytearray()
noise=0.0
for i, key in enumerate(piano):
    t=i/rate
    noise=.92*noise+.08*rng.uniform(-1,1)
    fade=min(1, t*3, (10-t)*2)
    left=right=key*fade
    for frame,pan in accents:
        age=t-frame/30
        if 0<=age<.24:
            amp=.026*min(1,age/.025)*(1-age/.24)**2
            left += amp*noise*sqrt((1-pan)/2)
            right += amp*noise*sqrt((1+pan)/2)
    pcm.extend(struct.pack("<hh",round(left*32767),round(right*32767)))
version = "dashboard-v5" if v5 else "dashboard-v4"
with wave.open(str(Path(__file__).resolve().parents[1]/"public"/version/"mix.wav"),"wb") as output:
    output.setparams((2,2,rate,0,"NONE","not compressed"))
    output.writeframes(pcm)
