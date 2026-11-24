"""Interpolate camera plates between sampled 3D frames; never interpolate across cuts."""
from pathlib import Path
import json
import cv2
import numpy as np

src=Path("/tmp/medisync-ppo-plates")
root=Path(__file__).resolve().parents[1]
out=root/"public/ppo-spatial/plates"
out.mkdir(exist_ok=True)
points=json.loads((src/"points.json").read_text())
sections=[(0,58,90),(90,148,180),(180,231,300),(300,368,390),(390,433,450)]
result=[]
def load(i):
    return cv2.imread(str(src/f"{i}.png"),cv2.IMREAD_UNCHANGED)
def write(i,a):
    assert cv2.imwrite(str(out/f"{i}.png"),a,[cv2.IMWRITE_PNG_COMPRESSION,2])

for begin,stop,end in sections:
    keys=sorted(int(k) for k in points if begin<=int(k)<=stop)
    assert keys[0]==begin and keys[-1]==stop,keys
    for left,right in zip(keys,keys[1:]):
        a,b=load(left),load(right)
        write(left,a)
        if right-left>1:
            h,w=a.shape[:2]; width,height=w//2,h//2
            gray=lambda im: cv2.cvtColor(cv2.resize(im,(width,height)),cv2.COLOR_BGRA2GRAY)
            fa=cv2.calcOpticalFlowFarneback(gray(a),gray(b),None,.5,3,15,3,5,1.2,0)
            fb=cv2.calcOpticalFlowFarneback(gray(b),gray(a),None,.5,3,15,3,5,1.2,0)
            fa=cv2.resize(fa,(w,h))*2;fb=cv2.resize(fb,(w,h))*2
            xx,yy=np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32))
        for f in range(left,right):
            t=(f-left)/(right-left)
            if f!=left:
                u=cv2.remap(a,xx-fa[:,:,0]*t,yy-fa[:,:,1]*t,cv2.INTER_LINEAR)
                v=cv2.remap(b,xx-fb[:,:,0]*(1-t),yy-fb[:,:,1]*(1-t),cv2.INTER_LINEAR)
                write(f,cv2.addWeighted(u,1-t,v,t,0))
            origin=points[str(left)]
            dest=points[str(right)]
            locations={key:[x+(y-x)*t for x,y in zip(p,dest.get(key,p))] for key,p in origin.items()}
            result.append([f,locations])
    write(stop,load(stop))
    result.extend([[stop,points[str(stop)]] for _ in range(stop,end)])
assert len(result)==450
(root/"src/ppo-spatial-plates.json").write_text(json.dumps(result,separators=(",",":")))
