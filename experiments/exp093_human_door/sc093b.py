import os, subprocess, random, string, json, cv2, pytesseract, numpy as np
from PIL import Image, ImageDraw, ImageFont
OUT="/data/workspace/luoshen-o1/experiments/exp093_human_door"
eg=json.load(open(OUT+"/engine093_result.json")); cs=eg["cells"]; tt=eg["tests"]
tok=''.join(random.choices(string.ascii_uppercase+string.digits,k=6))
W,H=1024,768
img=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(img)
F=None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F=ImageFont.truetype(p,28); break
        except Exception: pass
if F is None: F=ImageFont.load_default()
rows=[("UA curl chrome iphone","403 403 403"),
      ("stable gates","9 of 10"),
      ("intermittent","api.github flip 3"),
      ("skew open",   "%.4f"%cs["open"]["skew"]),
      ("skew rand50", "%.4f"%cs["rand_p50"]["skew"]),
      ("skew perio80","%.4f"%cs["perio_80"]["skew"]),
      ("skew closed", "%.4f"%cs["closed"]["skew"]),
      ("H3 diff",     "%+.4f"%tt["H3 稳定关 vs 稳定开"]["diff"]),
      ("TOKEN",       tok)]
y=50
for k,v in rows:
    d.text((50,y),f"{k:22s} {v}",fill=(0,0,0),font=F); y+=56
d.text((50,y+24),"093 SELF CHECK",fill=(0,0,0),font=F)
img.save(f"{OUT}/rendered093.png")
# RGB -> BGRA (32bpp)
a=np.array(img)
bgra=np.dstack([a[:,:,2],a[:,:,1],a[:,:,0],np.full(a.shape[:2],255,np.uint8)])
with open("/dev/fb0","wb") as f: f.write(bgra.tobytes())
subprocess.run(["ffmpeg","-y","-f","fbdev","-i","/dev/fb0","-frames:v","1",
                f"{OUT}/captured093.png","-loglevel","error"],check=True)
im=cv2.imread(f"{OUT}/captured093.png")
big=cv2.resize(im,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
g=cv2.cvtColor(big,cv2.COLOR_BGR2GRAY)
txt=pytesseract.image_to_string(g,config="--psm 6")
print("=== OCR READBACK (from framebuffer capture) ===")
print(txt.strip()[:800])
print(f"\nTOKEN = {tok}   found = {tok in txt.replace(' ','')}")
