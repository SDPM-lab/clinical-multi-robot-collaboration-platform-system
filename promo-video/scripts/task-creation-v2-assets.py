"""Prepare native UI cutouts and original stereo cues for Scene 02 V2."""
from pathlib import Path
import wave

import cv2
import numpy as np

assets = Path(__file__).resolve().parents[1] / "public/task-creation"


def read(name):
    return cv2.imread(str(assets / f"{name}.png"))


def write(name, pixels):
    if not cv2.imwrite(str(assets / f"{name}.png"), pixels):
        raise OSError(name)


# Native Leaflet pins. Fill their white center as part of the moving silhouette.
for key, base, x, y in [
    ("source", "source-fixed", 1317, 549),
    ("ward", "route-base", 688, 115),
]:
    scene = read(base)
    crop = scene[y:y+53, x:x+43].copy()
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue, saturation, _ = cv2.split(hsv)
    color = ((hue <= 16) | (hue >= 165)) if key == "source" else ((hue >= 90) & (hue <= 135))
    mask = (color & (saturation > 90)).astype(np.uint8) * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    outline = max(contours, key=cv2.contourArea)
    if cv2.contourArea(outline) < 200:
        raise ValueError(f"Native pin missing: {key}")
    mask[:] = 0
    cv2.drawContours(mask, [outline], -1, 255, cv2.FILLED)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    write(f"v2-{key}-pin", np.dstack((crop, mask)))
    clean = np.zeros(scene.shape[:2], np.uint8)
    clean[y:y+53, x:x+43] = mask
    write(f"v2-{key}-clean", cv2.inpaint(scene, clean, 4, cv2.INPAINT_TELEA))

write("v2-toast", read("success")[73:127, 1256:1578])

rate = 48000
seconds = 19.5
sample_count = int(rate * seconds)
time = np.arange(sample_count) / rate
mix = np.zeros((sample_count, 2))
rng = np.random.default_rng(221)


def add(at, signal, pan):
    start = round(at * rate)
    span = min(len(signal), sample_count - start)
    gains = np.sqrt([1 - pan, pan])
    mix[start:start+span] += signal[:span, None] * gains


def tone(frame, frequencies, length, gain, pan, decay=7):
    t = np.arange(round(rate * length)) / rate
    attack = np.minimum(1, t / 0.006)
    release = np.minimum(1, (length - t) / 0.04)
    signal = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate(frequencies))
    add(frame / 30, signal * attack * release * np.exp(-decay * t) * gain, pan)


def air(frame, length, gain, pan):
    t = np.arange(round(rate * length)) / rate
    noise = rng.standard_normal(len(t)).astype(np.float32)
    soft = cv2.GaussianBlur(noise[None, :], (19, 1), 3)[0]
    add(frame / 30, soft * np.sin(np.pi * t / length) ** 2 * gain, pan)


fade = np.minimum(1, time / 0.65) * np.minimum(1, (seconds - time) / 0.85)
for channel in range(2):
    phase = channel * 0.42
    bed = sum(np.sin(2 * np.pi * f * time + phase) * (0.5 + 0.5 * np.sin(time * w + phase))
              for f, w in [(146.83, .70), (220, .49), (293.66, .91), (329.63, .63)])
    mix[:, channel] += bed * fade * 0.013

for frame, pan in [(77, .26), (106, .26), (217, .50), (315, .29), (353, .33),
                   (456, .33), (478, .32), (499, .24), (529, .30), (548, .63)]:
    tone(frame, [680, 1240], .105, .076, pan, 31)
tone(159, [493.88, 739.99], .2, .037, .8, 17)
air(221, .72, .055, .64)
air(128, .5, .042, .74)
tone(380, [659.25, 987.77], .44, .108, .74, 9)
tone(551, [587.33, 880], .3, .066, .33, 11)

with wave.open(str(assets / "v2-score.wav"), "wb") as output:
    output.setparams((2, 2, rate, 0, "NONE", "not compressed"))
    output.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
