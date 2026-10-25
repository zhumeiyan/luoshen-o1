# -*- coding: utf-8 -*-
"""125 上屏自检：渲染 → 写 /dev/fb0 → 真实采集 → OCR 回读"""
import os, json, random, string, subprocess
from PIL import Image, ImageDraw, ImageFont
import numpy as np, cv2, pytesseract

OUT = "/data/workspace/luoshen-o1/experiments/exp125_wean"
r1 = json.load(open(OUT+"/result125.json")); r2 = json.load(open(OUT+"/result125b.json"))
tok = ''.join(random.choices(string.ascii_uppercase+string.digits, k=6))
# 去掉易混淆字符
tok = ''.join(c for c in tok if c not in "O0I1")

rows = [
    ("fg dead zone",  "fg=0.007  0 of 24 alive"),
    ("fg alive zone", "fg=0.008 11 of 24 alive"),
    ("drip sustain",  "16 of 16 alive"),
    ("forage sustain","13 of 16 alive"),
    ("cut fg=0",      "0 of 12  last 235"),
    ("cut fg=0.030",  "8 of 12  last 1117"),
    ("cap7 decay",    "1.000 -> 0.229"),
    ("skew delta",    "%+.4f CI cross0" % r2["delta"]),
    ("TOKEN",         tok),
]

W, H = 1024, 768
img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
F = None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F = ImageFont.truetype(p, 30); break
        except Exception: pass
if F is None: F = ImageFont.load_default()
y = 40
for k, v in rows:
    d.text((40, y), f"{k:16s} {v}", fill=(0, 0, 0), font=F); y += 62
d.text((40, y+20), "125 WEAN SELF-CHECK", fill=(0, 0, 0), font=F)
img.save(OUT+"/render.png")

# 写帧缓冲：32bpp → RGBA
rgba = img.convert("RGBA").resize((1024, 768))
with open("/dev/fb0", "wb") as f:
    f.write(rgba.tobytes())
print("written bytes:", len(rgba.tobytes()))

# 真实采集（直读 fb0，避免 ffmpeg fbdev 超时）
with open("/dev/fb0", "rb") as f:
    raw = f.read()
print("captured bytes:", len(raw))
arr = np.frombuffer(raw, dtype=np.uint8).reshape(768, 1024, 4)
cap = Image.fromarray(arr[:, :, :3], "RGB")
cap.save(OUT+"/captured.png")

g = cv2.cvtColor(cv2.resize(cv2.imread(OUT+"/captured.png"), None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2GRAY)
txt = pytesseract.image_to_string(g, config="--psm 6")
open(OUT+"/ocr.txt", "w").write(txt)
clean = txt.replace(" ", "").upper()
print("=== OCR READBACK ==="); print(txt.strip()[:800])
print(f"\nTOKEN={tok}  found={tok in clean}  香农校验")
for probe in ["0.007", "0.008", "235", "1117", "0.229"]:
    print(f"  probe {probe:8s} -> {probe in txt}")
