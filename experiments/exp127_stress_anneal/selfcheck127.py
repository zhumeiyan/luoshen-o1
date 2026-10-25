# -*- coding: utf-8 -*-
"""127 上屏自检：渲染 → 写 /dev/fb0(1024x768 RGBA, ioctl实测) → 真实采集 → OCR 回读"""
import os, json, random, string
from PIL import Image, ImageDraw, ImageFont
import numpy as np, cv2, pytesseract

OUT = "/data/workspace/luoshen-o1/experiments/exp127_stress_anneal"
B = json.load(open(OUT + "/result127B.json"))
C = json.load(open(OUT + "/result127C.json"))
D = json.load(open(OUT + "/result127D.json"))
an = C["anneal"]; cp = D["continue_pair"]
tok = ''.join(random.choices("23456789", k=6))

rows = [
 ("S2 STEEP",    "cost 10 -> 10 of 16  cost 20 -> 0 of 16"),
 ("S1 GRADUAL",  "bleed 0.04 -> 8 of 16  0.05 -> 3 of 16"),
 ("S3 NOT FATAL", "aging 0.10 -> 15 of 16  cut demand survive"),
 ("S2 LC50",     "cost between 10 and 13"),
 ("P2 LEAK",     "orig 0.81318  norm 0.08777  noise 16"),
 ("ANNEAL HOT",  "fg 0.33799  drift 0.00033"),
 ("ANNEAL SLOW", "fg 0.09600  drift 0.00004"),
 ("ANNEAL FAST", "fg 0.01204  too cold too soon"),
 ("CONTINUE",    "good +0.04015  bad +0.00017"),
 ("PRECURSOR",   "1 dead 9 alive  no verdict"),
 ("DOSE",        "tau 0.02 fg 0.01118  tau 3.0 fg 0.26862"),
 ("TOKEN",       tok),
]
W, H = 1024, 768
img = Image.new("RGB", (W, H), (255, 255, 255)); dr = ImageDraw.Draw(img)
F = None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F = ImageFont.truetype(p, 25); break
        except Exception: pass
if F is None: F = ImageFont.load_default()
y = 26
for k, v in rows:
    dr.text((28, y), f"{k:14s} {v}", fill=(0, 0, 0), font=F); y += 55
dr.text((28, y + 12), "127 STRESS AND ANNEAL SELF CHECK", fill=(0, 0, 0), font=F)
img.save(OUT + "/render.png")
rgba = img.convert("RGBA").resize((1024, 768))
b = rgba.tobytes()
open("/dev/fb0", "wb").write(b); print("written:", len(b))
raw = open("/dev/fb0", "rb").read(); print("captured:", len(raw))
arr = np.frombuffer(raw, dtype=np.uint8).reshape(768, 1024, 4)
Image.fromarray(arr[:, :, :3], "RGB").save(OUT + "/captured.png")
print("render sha", __import__('hashlib').sha256(open(OUT+"/render.png",'rb').read()).hexdigest()[:12],
      "capture sha", __import__('hashlib').sha256(open(OUT+"/captured.png",'rb').read()).hexdigest()[:12])
g = cv2.cvtColor(cv2.resize(cv2.imread(OUT + "/captured.png"), None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2GRAY)
txt = pytesseract.image_to_string(g, config="--psm 6")
open(OUT + "/ocr.txt", "w").write(txt)
clean = txt.replace(" ", "").upper()
loose = clean.replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("B", "8")
print("=== OCR ==="); print(txt.strip()[:1000])
print(f"\nTOKEN={tok}  strict={tok in clean}  loose={tok in loose}")
probes = ["0.33799", "0.09600", "0.01204", "0.00033", "0.00004",
          "0.81318", "0.08777", "0.04015", "0.00017", "0.01118", "0.26862",
          "10 of 16", "0 of 16", "15 of 16"]
hit = 0
for p in probes:
    k = p.replace(" ", "").upper()
    ok = (k in clean) or (k in loose)
    hit += ok
    print(f"  probe {p:12s} -> {ok}")
print(f"\nprobes hit {hit}/{len(probes)}   token={tok in clean or tok in loose}")
json.dump(dict(token=tok, strict=tok in clean, loose=tok in loose, hits=hit, n=len(probes)),
          open(OUT + "/selfcheck127.json", "w"), indent=1)
