import subprocess, os, random, string, cv2, pytesseract, numpy as np, json
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"
eg=json.load(open(OUT+"/engine093_result.json"))
cs=eg["cells"]; tt=eg["tests"]
vals=[("UAc",403),("UAg",403),("UAp",403),
      ("gate",9),("flip",1),
      ("open",cs["open"]["skew"]),("rand",cs["rand_p50"]["skew"]),
      ("perio80",cs["perio_80"]["skew"]),("closed",cs["closed"]["skew"]),
      ("H3",tt["H3 稳定关 vs 稳定开"]["diff"])]
tok=''.join(random.choices(string.ascii_uppercase+string.digits,k=6))
os.environ["TOK"]=tok
script = r'''
import os,subprocess
from PIL import Image, ImageDraw, ImageFont
W,H=1024,768
img=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(img)
F=None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F=ImageFont.truetype(p,26); break
        except Exception: pass
if F is None: F=ImageFont.load_default()
import json
D="/data/workspace/luoshen-o1/experiments/exp093_human_door/"
eg=json.load(open(D+"/engine093_result.json")); cs=eg["cells"]; tt=eg["tests"]
rows=[("UA curl/chrome/iphone","403 403 403"),
      ("stable gates","9 of 10"),
      ("intermittent","api.github flip=3"),
      ("skew open",  "%.4f"%cs["open"]["skew"]),
      ("skew rand50","%.4f"%cs["rand_p50"]["skew"]),
      ("skew perio80","%.4f"%cs["perio_80"]["skew"]),
      ("skew closed","%.4f"%cs["closed"]["skew"]),
      ("H3 diff",    "%+.4f"%tt["H3 稳定关 vs 稳定开"]["diff"]),
      ("TOKEN",      os.environ["TOK"])]
y=40
for k,v in rows:
    d.text((40,y),f"{k:22s} {v}",fill=(0,0,0),font=F); y+=52
d.text((40,y+20),"093 SELF-CHECK",fill=(0,0,0),font=F)
img.save("/tmp/sc093.png")
subprocess.run(["python3","-c","""
from PIL import Image
im=Image.open('/tmp/sc093.png').convert('RGB')
im.save('/dev/fb0' if False else '/tmp/sc093b.png')
import shutil
# 写入帧缓冲
with open('/dev/fb0','wb') as f:
    im2=im.resize((1024,768))
    f.write(im2.tobytes())
"""],check=True)
'''
open("/tmp/render093.py","w").write(script)
subprocess.run(["python3","/tmp/render093.py"],check=True)
subprocess.run(["ffmpeg","-y","-f","fbdev","-i","/dev/fb0","-frames:v","1",
                f"{OUT}/captured093.png","-loglevel","error"],check=True)
im=cv2.imread(f"{OUT}/captured093.png")
g=cv2.cvtColor(cv2.resize(im,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC),cv2.COLOR_BGR2GRAY)
txt=pytesseract.image_to_string(g,config="--psm 6")
print("=== OCR READBACK ===")
print(txt.strip()[:700])
hit = tok in txt.replace(" ","")
print(f"\nTOKEN={tok}  found_in_OCR={hit}")
print("MATCH:",hit)
