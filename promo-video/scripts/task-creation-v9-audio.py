"""Mix the original scene's sound palette against the revised event frames."""
from pathlib import Path
import json, os, subprocess, wave
import numpy as np

rate=48000
root=Path(__file__).resolve().parents[1]
out=root/'public/task-creation-v9'
out.mkdir(exist_ok=True)
rng=np.random.default_rng(711)

def wave_file(name,samples):
    channels=1 if samples.ndim==1 else samples.shape[1]
    with wave.open(str(out/name),'wb') as w:
        w.setparams((channels,2,rate,0,'NONE','not compressed'))
        w.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())

def mix_score(reference):
    length=585 if reference else 420
    clock=np.arange(length*1600)/rate
    samples=np.zeros((len(clock),2))
    cue_map=lambda f: int(round(np.interp(f,[0,60,150,240,300,420],[0,90,210,300,390,585]))) if reference else f
    fade=np.minimum(1,clock/.2)*np.minimum(1,(length/30-clock)/.35)
    beat=2.15 if reference else 2.5
    groove=.48+.52*(.5+.5*np.cos(2*np.pi*beat*clock))**4
    for ch in range(2):
        for freq, speed in [(146.83,.69),(220,1.1),(293.66,.94),(369.99,.53)]:
            samples[:,ch]+=.014*np.sin(2*np.pi*freq*clock+ch*.37)*groove*(.7+.3*np.cos(clock*speed))*fade
    def tone(frame,hz,gain,pan,duration,decay,grit=0):
        t=np.arange(int(rate*duration))/rate
        env=np.minimum(1,t/.001)*np.minimum(1,(duration-t)/.012)*np.exp(-decay*t)
        data=gain*env*(np.sin(2*np.pi*hz*t)+.25*np.sin(2*np.pi*hz*1.77*t)+grit*rng.normal(size=len(t)))
        start=1600*cue_map(frame)
        samples[start:start+len(t)]+=data[:,None]*np.sqrt([1-pan,pan])[None,:]
    for frame,hz,p in [(24,2130,.68),(42,2480,.66),(108,2650,.31),(200,2390,.5),(228,1880,.59),
                       (335,2360,.66),(344,2220,.35),(360,2000,.44),(384,2420,.57)]:
        tone(frame,hz,.082 if hz>2250 else .114,p,.043,105,.11)
    for f in [159,169,179,190]:tone(f,2880,.026,.54,.031,120,.09)
    tone(81,1160,.055,.75,.091,28)
    tone(252,880,.135,.42,.25,16)
    tone(256,1174.66,.121,.58,.32,13)
    tone(386,1174.66,.08,.53,.115,27)
    wave_file('reference-score.wav' if reference else 'score.wav',samples)

mix_score(False)
av=root/'node_modules/@remotion/compositor-linux-x64-gnu'
voice=np.zeros(420*1600)
lines=["視覺化選點，快速建立任務。","從路線預覽、優先級設定，","到彈性排程，","讓每一次協作都更加直觀。"]
markers=[43,145,248,307,420]
caps=[]
for i,text in enumerate(lines):
    raw=subprocess.check_output([str(av/'ffmpeg'),'-v','error','-i',f'/tmp/medisync-v8fast-{i}.mp3','-ac','1','-ar','48000','-f','wav','-'],env=dict(os.environ,LD_LIBRARY_PATH=str(av)))
    a=np.frombuffer(raw[raw.index(b'data')+8:],dtype='<i2').astype(float)/32768
    rms=np.sqrt(np.mean(a[:len(a)//480*480].reshape(-1,480)**2,axis=1))
    active=np.flatnonzero(rms>.0026)
    a=a[max(0,(active[0]-3)*480):min(len(a),(active[-1]+8)*480)]
    start=markers[i]*1600
    assert start+len(a)<markers[i+1]*1600,(i,len(a)/1600,markers[i+1]-markers[i])
    a[-720:]*=np.linspace(1,0,720)
    voice[start:start+len(a)]=a*.58/np.max(abs(a))
    caps.append({"from":markers[i],"to":min(420,markers[i]+round(len(a)/1600)+3),"text":text})
wave_file('voice.wav',voice)
(root/'src/task-creation-v9-captions.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2)+'\n')
print(caps)
