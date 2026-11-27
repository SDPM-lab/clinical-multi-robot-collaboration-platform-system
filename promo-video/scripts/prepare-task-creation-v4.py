"""Prepare transparent pins from original captures with and without native markers."""
from pathlib import Path
import json
import sys
from PIL import Image
import numpy as np

root = Path(__file__).resolve().parents[1]
version = "phase-vnext" if "--phase-vnext" in sys.argv else "v4"
scale = 2 if version == "phase-vnext" else 1
output = root / f"public/task-creation-{version}"

def read(name):
    return np.asarray(Image.open(output / f"{name}.png").convert("RGB"))

def isolate(before, after, bounds, name):
    x0,y0,x1,y1=(coordinate*scale for coordinate in bounds)
    a,b=before[y0:y1,x0:x1],after[y0:y1,x0:x1]
    alpha=(np.abs(a.astype(np.int16)-b).max(axis=2)>3).astype(np.uint8)*255
    y,x=np.where(alpha>0)
    assert 250*scale**2<len(x)<7500*scale**2, name
    xlo,xhi,ylo,yhi=int(x.min()),int(x.max())+1,int(y.min()),int(y.max())+1
    rgba=np.dstack((b,alpha))[ylo:yhi,xlo:xhi]
    Image.fromarray(rgba).save(output / f"pin-{name}.png")
    return {"x":(x0+xlo)/scale,"y":(y0+ylo)/scale,"width":(xhi-xlo)/scale,"height":(yhi-ylo)/scale}

base, source, both=map(read,("map-clean","map-source","map-both"))
layers={
    "source":isolate(base,source,(1265,530,1440,636),"source"),
    "destination":isolate(source,both,(634,104,792,204),"destination"),
}
(root/f"src/task-creation-{version}-layers.json").write_text(json.dumps(layers,indent=2)+"\n")
