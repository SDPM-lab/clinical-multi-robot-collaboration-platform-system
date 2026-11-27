"""Generate the offline scratch voice and original transition mix."""
import ctypes
import json
import math
from pathlib import Path
import struct
import tempfile
import wave

root = Path(__file__).resolve().parent.parent
assets = root / "public" / "dashboard-v2"
assets.mkdir(parents=True, exist_ok=True)
flite = ctypes.CDLL("libflite.so.1", mode=ctypes.RTLD_GLOBAL)
voice_library = ctypes.CDLL("libflite_cmu_us_slt.so.1")
flite.flite_init()
voice_library.register_cmu_us_slt.argtypes = [ctypes.c_char_p]
voice_library.register_cmu_us_slt.restype = ctypes.c_void_p
voice = voice_library.register_cmu_us_slt(None)
flite.flite_text_to_speech.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_char_p]
flite.flite_text_to_speech.restype = ctypes.c_float

lines = [
    ("Meet MediSync.", "Meet Medi Sync.", 18),
    ("One intelligent platform connecting", "One intelligent platform connecting", 66),
    ("every task, every robot, and every decision.", "every task, every robot, and every decision.", 145),
]
cues = []
with tempfile.TemporaryDirectory() as directory:
    mix = None
    for index, (subtitle, pronunciation, start) in enumerate(lines):
        part = Path(directory) / f"{index}.wav"
        flite.flite_text_to_speech(pronunciation.encode(), voice, str(part).encode())
        with wave.open(str(part), "rb") as stream:
            rate = stream.getframerate()
            signal = list(struct.unpack(f"<{stream.getnframes()}h", stream.readframes(stream.getnframes())))
        audible = [i for i, sample in enumerate(signal) if abs(sample) > 150]
        signal = signal[max(0, audible[0] - rate // 30):audible[-1] + rate // 15]
        if mix is None:
            mix = [0] * (rate * 10)
        offset = round(start * rate / 30)
        mix[offset:offset + len(signal)] = signal
        cues.append(dict(text=subtitle, start=start, end=start + math.ceil(len(signal) * 30 / rate) + 4))
    with wave.open(str(assets / "voice.wav"), "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(struct.pack(f"<{len(mix)}h", *mix))

(root / "src" / "dashboard-v2-captions.json").write_text(json.dumps(cues, indent=2) + "\n")

rate = 24000
events = [(53, .34, 520, .033), (144, .58, 329.6, .045), (216, .35, 440, .035)]
samples = []
for index in range(rate * 10):
    time = index / rate
    bed = .013 * min(1, time * 2, (10 - time) * 2) * (
        math.sin(math.tau * 220 * time) + .32 * math.sin(math.tau * 329.6 * time)
    )
    for frame, duration, frequency, volume in events:
        age = time - frame / 30
        if 0 <= age < duration:
            envelope = min(age / .033, 1) * (1 - age / duration) ** 2
            bed += volume * envelope * (math.sin(math.tau * frequency * age)
                                       + .24 * math.sin(math.tau * frequency * 2 * age))
    samples.append(round(32767 * bed))
with wave.open(str(assets / "sound.wav"), "wb") as stream:
    stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
    stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
