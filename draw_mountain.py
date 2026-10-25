# -*- coding: utf-8 -*-
"""山。不解释，直接画。"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W,H = 1400, 880
PAPER = np.array([244,239,230],dtype=np.float32)

def fbm(x,seed,oct=6):
    rng=np.random.default_rng(seed); y=np.zeros_like(x); a=1.0
    for o in range(oct):
        y += a*np.sin(2*np.pi*(2.0**o)*x + rng.uniform(0,2*np.pi)*4)
        a*=0.52
    return y

def ridge(x,seed,sharp=1.0):
    n=fbm(x,seed)
    r=1.0-np.abs(n)/np.max(np.abs(n))
    return r**sharp

X=np.linspace(0,1,W)
YY=np.arange(H,dtype=np.float32)[:,None]

canvas=np.tile(PAPER,(H,W,1))

# 远→近。峰位、墨色、浓度
layers=[
  dict(seed=11, peak=0.16, amp=105, ink=(180,175,166), a=0.55, fall=0.070, sharp=1.8),
  dict(seed=29, peak=0.33, amp=160, ink=(116,112,104), a=0.80, fall=0.088, sharp=1.4),
  dict(seed=47, peak=0.50, amp=205, ink=( 46, 44, 39), a=0.95, fall=0.082, sharp=1.1),
]

for L in layers:
    r=ridge(X,L["seed"],L["sharp"])
    rn=(r-r.min())/(r.max()-r.min())
    base=(L["peak"]*H) + L["amp"]*(1.0-rn)          # 山脊线：峰高谷低
    d=YY-base[None,:]
    m=(d>0)
    alpha=np.where(m, L["a"]*np.exp(-np.maximum(d,0)/(L["fall"]*H))**1.15, 0.0)
    alpha=np.clip(alpha,0,1)[...,None]
    ink=np.tile(np.array(L["ink"],dtype=np.float32),(H,W,1))
    canvas = canvas*(1-alpha) + ink*alpha

# 留白：山脚藏进云里（三条横带）
fog=np.zeros((H,W),dtype=np.float32)
for yp,wid in [(0.50,0.18),(0.64,0.16),(0.76,0.36)]:
    y0=int(yp*H)
    for k in range(min(int(H*wid), H-y0)):
        fog[y0+k,:] = np.maximum(fog[y0+k,:], 235*np.exp(-(k/(H*wid*0.38))**1.6))
canvas = canvas*(1-(fog/255)[...,None]) + PAPER*(fog/255)[...,None]

img=Image.fromarray(np.clip(canvas,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
img.save("感官桥/符号_v48_山.png")

a=np.array(img.convert("L")).astype(np.float32)/255
print("墨占比 %.1f%%   质心 y=%.0f/%d"%((a<0.88).mean()*100, np.nonzero(a<0.88)[0].mean(), H))
