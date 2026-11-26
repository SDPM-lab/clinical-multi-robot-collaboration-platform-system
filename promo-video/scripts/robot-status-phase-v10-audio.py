"""Mix normal-speed narration with frame-locked interface cues."""
import json
import os
from pathlib import Path
import subprocess
import wave

import numpy as np

root = Path(__file__).resolve().parents[1]
out = root / 'public/robot-status-phase-v10'
rate = 48000
samples = 195 * 1600
av = root / 'node_modules/@remotion/compositor-linux-x64-gnu'
env = dict(os.environ, LD_LIBRARY_PATH=str(av))
lines = [(38, 194, '快速瀏覽不同機器人，並掌握每台設備的運作資訊。')]
voice = np.zeros(samples)
score = np.zeros((samples,2))
captions = []
for i,(start,limit,line) in enumerate(lines):
    data = subprocess.check_output([av/'ffmpeg','-v','error','-i',f'/tmp/robot-status-v10-voice-{i}.mp3',
                                    '-af','anull','-ac','1','-ar',str(rate),'-acodec','pcm_s16le','-f','wav','-'],env=env)
    clip = np.frombuffer(data[data.index(b'data')+8:],'<i2').astype(float)/32768
    blocks = clip[:len(clip)//480*480].reshape(-1,480)
    active = np.flatnonzero(np.sqrt((blocks**2).mean(axis=1))>.0022)
    clip = clip[max(0,active[0]*480-1440):(active[-1]+6)*480]
    end = start+(len(clip)+1599)//1600
    assert end <= limit,(i,start,end,limit)
    voice[start*1600:start*1600+len(clip)] = clip*.58/np.max(abs(clip))
    captions.append({'from':start,'to':end,'text':line})

t = np.arange(samples)/rate
edge = np.minimum(1,t/.44)*np.minimum(1,(6.5-t)/.65)
for ch in range(2):
    for freq,offset in [(130.81,.2),(196,.6),(261.63,1.2),(329.63,1.9)]:
        score[:,ch] += .012*np.sin(2*np.pi*freq*t+ch*.22)*edge*(.76+.24*np.sin(offset+.65*t))
for frame,freq,pan,volume,duration in [
    (59,960,.30,.012,.1),(103,1640,.39,.042,.075),
    (129,1640,.39,.045,.075)
]:
    x = np.arange(round(duration*rate))/rate
    envlope = np.minimum(1,x/.003)*np.minimum(1,(duration-x)/.015)*np.exp(-17*x)
    tick = volume*envlope*(np.sin(2*np.pi*freq*x)+.17*np.sin(2*np.pi*freq*x*1.47))
    start = frame*1600
    score[start:start+len(x)] += tick[:,None]*np.sqrt([1-pan,pan])[None,:]

for name,audio in [('voice',voice),('score',score)]:
    with wave.open(str(out/f'{name}.wav'),'wb') as file:
        file.setparams((1 if audio.ndim==1 else 2,2,rate,0,'NONE','not compressed'))
        file.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
(root/'src/robot-status-phase-v10-captions.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2)+'\n')
print(captions)
