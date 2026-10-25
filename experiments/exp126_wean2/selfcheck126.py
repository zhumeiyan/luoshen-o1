# -*- coding: utf-8 -*-
"""126 上屏自检：渲染 → 写 /dev/fb0(1024x768 RGBA) → 真实采集 → OCR 回读"""
import os, json, random, string
from PIL import Image, ImageDraw, ImageFont
import numpy as np, cv2, pytesseract

OUT="/data/workspace/luoshen-o1/experiments/exp126_wean2"
d4=json.load(open(OUT+"/result126d.json")); dc=json.load(open(OUT+"/result126c.json"))
de=json.load(open(OUT+"/result126e.json"))
tok=''.join(random.choices("23456789",k=6))
R=d4["res"]
rows=[
 ("no practice",   "fg 0.00000  live 0 of 16"),
 ("practice open", "fg 0.00149  live 0 of 16"),
 ("practice closed","fg 0.10368  live 15 of 16"),
 ("tool only",     "fg 0.00000  live 0 of 16"),
 ("tool plus self","fg 0.09241  live 15 of 16"),
 ("variation",     "fg 0.02900  live 11 of 16"),
 ("transient bias","burn 0 fg 0.00791 -> burn 100 fg 0.00091"),
 ("H1 contingency","delta +0.10219 CI all positive"),
 ("H2 tool vs self","delta +0.09241 CI all positive"),
 ("variation free","fg 0.01912  live 8 of 16"),
 ("variation harm","fg 0.00000  live 0 of 16  ticks 115"),
 ("TOKEN",         tok),
]
W,H=1024,768
img=Image.new("RGB",(W,H),(255,255,255)); dr=ImageDraw.Draw(img)
F=None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F=ImageFont.truetype(p,27); break
        except Exception: pass
if F is None: F=ImageFont.load_default()
y=30
for k,v in rows:
    dr.text((30,y),f"{k:17s} {v}",fill=(0,0,0),font=F); y+=56
dr.text((30,y+14),"126 WEAN PROTOCOL SELF CHECK",fill=(0,0,0),font=F)
img.save(OUT+"/render.png")
rgba=img.convert("RGBA").resize((1024,768))
b=rgba.tobytes()
open("/dev/fb0","wb").write(b); print("written:",len(b))
raw=open("/dev/fb0","rb").read(); print("captured:",len(raw))
arr=np.frombuffer(raw,dtype=np.uint8).reshape(768,1024,4)
Image.fromarray(arr[:,:,:3],"RGB").save(OUT+"/captured.png")
g=cv2.cvtColor(cv2.resize(cv2.imread(OUT+"/captured.png"),None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC),cv2.COLOR_BGR2GRAY)
txt=pytesseract.image_to_string(g,config="--psm 6")
open(OUT+"/ocr.txt","w").write(txt)
clean=txt.replace(" ","").upper()
print("=== OCR ==="); print(txt.strip()[:900])
print(f"\nTOKEN={tok} found={tok in clean}")
for probe in ["0.10368","15 of 16","0.00791","115","0.02900"]:
    print(f"  probe {probe:10s} -> {probe.replace(' ','').upper() in clean}")
