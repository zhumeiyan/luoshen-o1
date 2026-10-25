"""exp136 — render, write /dev/fb0, read back, OCR-verify."""
import os, time, hashlib, subprocess, json
from PIL import Image, ImageDraw, ImageFont

FB="/dev/fb0"; OUT="/data/workspace/luoshen-o1/experiments/exp129_corpus/exp136"
vs=open("/sys/class/graphics/fb0/virtual_size").read().strip()
W,H=(int(x) for x in vs.split(","))
BPP=int(open("/sys/class/graphics/fb0/bits_per_pixel").read().strip())
TOKEN="Q3N7WV"   # no O/0 1/I 8/B 5/S
PROBES=["0.0093","0.0164","0.0240","0.2376","13 of 14","13 of 15",
        "2 of 3","1 of 29","3 of 3"]

img=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(img)
try:
    fp="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    f_t=ImageFont.truetype(fp,29); f_b=ImageFont.truetype(fp,21); f_s=ImageFont.truetype(fp,17)
except Exception:
    f_t=f_b=f_s=ImageFont.load_default()

y=14
d.text((30,y),"exp136  is the tool mute, or is the code clean?",font=f_t,fill=(0,0,0)); y+=44
d.text((30,y),"TOKEN "+TOKEN+"   (7 mature repos vs 8 low-star repos)",font=f_b,fill=(0,0,0)); y+=38

rows=[
 ("H1 non-eval fires >=0.05 per KB","REJECTED","was 0.05, got 0.0093"),
 ("H2 strict precision >=0.60 (CI)","FAIL","2 of 3 point, lower bound 0.21"),
 ("H3 recall on minefield","PASS","3 of 3, 2 of 2, 1 of 1, clean 0"),
 ("","",""),
 ("corpus5 mature  14 files 108KB","1 hit","0.0093 per KB, 13 of 14 silent"),
 ("corpus6 lowstar 15 files 122KB","2 hits","0.0164 per KB, 13 of 15 silent"),
 ("eval baseline (exp135)","--","0.0240 per KB"),
 ("","",""),
 ("loose un-pruned, corpus5","10 hits","0.0926 per KB"),
 ("loose un-pruned, corpus6","29 hits","0.2376 per KB"),
 ("loose judged on corpus6","1 of 29","3.4 percent precision"),
 ("","",""),
 ("verdict","","silence is not domain, not pruning"),
 ("","","defect is rare OR its common form is fine"),
]
for a,b,c in rows:
    if a:
        d.text((30,y),a,font=f_s,fill=(0,0,0))
        d.text((430,y),b,font=f_s,fill=(0,0,0))
        d.text((640,y),c,font=f_s,fill=(0,0,0))
    y+=30

y+=6
d.text((30,y),"three errors this round",font=f_b,fill=(0,0,0)); y+=32
for e in ["audit ledger counted as findings (5 phantom hits)",
          "pathlib slash counted as division, 53 to 5",
          "handler that logs counted as silent, 20 to 11",
          "httpie repo renamed, 301 on old name"]:
    d.text((46,y),"- "+e,font=f_s,fill=(0,0,0)); y+=26

d.text((30,H-34),"DO NOT SHIP  precision 2 of 3 n too small, coverage 0.01 per KB",
       font=f_s,fill=(0,0,0))

img.save(OUT+"/render136.png")
raw=img.convert("RGBA").tobytes()
assert len(raw)==W*H*4, (len(raw), W*H*4)
with open(FB,"wb") as f: f.write(raw)
time.sleep(1.2)
with open(FB,"rb") as f: cap=f.read()
open(OUT+"/capture136.raw","wb").write(cap)
print("W,H,BPP",W,H,BPP,"wrote",len(raw),"read",len(cap),"equal",raw==cap)
cimg=Image.frombytes("RGBA",(W,H),cap).convert("RGB")
cimg.save(OUT+"/captured.png")
txt=subprocess.run(["tesseract",OUT+"/captured.png","stdout"],capture_output=True,text=True).stdout
open(OUT+"/ocr.txt","w").write(txt)
norm=lambda s: s.replace(" ","").replace("/","").replace("of","")
flat=norm(txt)
hits=[p for p in PROBES if norm(p) in flat]
print("TOKEN", TOKEN in txt.replace(" ",""))
print("probes", len(hits),"/",len(PROBES), [p for p in PROBES if norm(p) not in flat])
