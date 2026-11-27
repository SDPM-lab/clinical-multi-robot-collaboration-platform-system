"""Synthesize a low-level stereo bed and frame-locked V6 sound cues."""
import math
from pathlib import Path
import struct
import wave

rate = 24000
tau = math.tau
events = [
    (46, .34, 587, 0, .035),      # brand lockup
    (77, .75, 411, .62, .037),    # schedule moves from the right
    (97, .54, 444, -.61, .037),   # gauge moves from the left
    (152, .32, 622, -.47, .039),  # left cards seat
    (171, .39, 740, -.44, .028),  # network reaches online
    (198, .56, 523, .24, .033),   # battery samples appear
    (225, .36, 659, .41, .030),   # progress at right
    (244, .62, 392, 0, .033),     # centered confirmation
]
pcm = bytearray()
for i in range(rate * 10):
    t = i / rate
    fade = min(1, 3*t, 3*(10-t))
    beat = (t % .5)
    bed = fade * (.017 * math.exp(-12*beat) * math.sin(tau*185*t)
                  + .006 * math.sin(tau*277*t)
                  + .009 * math.exp(-21*((t+.25) % .5))*math.sin(tau*370*t))
    left = right = bed
    for frame, length, freq, pan, amp in events:
        age = t-frame/30
        if 0 <= age < length:
            envelope = min(age/.022, 1) * (1-age/length)**2
            phase = tau * freq * (age - .17*age*age)
            sound = amp*envelope*(math.sin(phase) + .29*math.sin(1.994*phase))
            left += sound * math.sqrt((1-pan)/2)
            right += sound * math.sqrt((1+pan)/2)
    pcm.extend(struct.pack("<hh", round(left*32767), round(right*32767)))
filepath = Path(__file__).resolve().parents[1] / "public/dashboard-v3/mix.wav"
with wave.open(str(filepath),"wb") as output:
    output.setparams((2, 2, rate, 0, "NONE", "not compressed"))
    output.writeframes(pcm)
