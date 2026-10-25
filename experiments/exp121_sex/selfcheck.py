# -*- coding: utf-8 -*-
import random, subprocess, os
from PIL import Image, ImageDraw, ImageFont

ALPHA = "ACDEFGHJKLMNPQRTUVWXY34679"   # 去掉 B/8 O/0 I/1 S/5 Z/2
CODE = "".join(random.choice(ALPHA) for _ in range(6))

W, H, BPP = 1024, 768, 32
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
f_big = ImageFont.truetype(FONT, 26)
f_mid = ImageFont.truetype(FONT, 20)
f_sm  = ImageFont.truetype(FONT, 15)

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)

rows = [
    ("EO SEX AND REPRODUCTION   CODE " + CODE, f_big),
    ("", None),
    ("F1 v1 recombination averaged  20 kids unique 1   v2 19", f_mid),
    ("F2 v1 pop replaced by kids    gen1 EXTINCT", f_mid),
    ("", None),
    ("A singlepeak  asex 0.7503  sexfree 0.6774  sexcost 0.2440", f_mid),
    ("A multipeak   asex 0.7098  sexfree 0.7403  sexcost 0.2504", f_mid),
    ("", None),
    ("B dose mag0.00  asex 0.7140  sexfree 0.7192  gap +0.005", f_sm),
    ("B dose mag0.02  asex 0.7039  sexfree 0.7495  gap +0.046", f_sm),
    ("B dose mag0.05  asex 0.6177  sexfree 0.7221  gap +0.104", f_sm),
    ("B dose mag0.28  ALL EXTINCT  no sample  bad interval", f_sm),
    ("", None),
    ("C ratchet irreversibility  asex 0.5956  sexfree 0.0330  18x", f_mid),
    ("C ratchet net drift        asex 11.3    sexfree 4.4", f_mid),
    ("C terminal fitness         asex 0.5607  sexfree 0.7999", f_mid),
    ("", None),
    ("D compete static   asex frac 0.90   sex never wins", f_mid),
    ("D compete shifting asex frac 0.60   sex never wins", f_mid),
    ("D dose U 10 cells  sex win 0   static 0.75 to 0.50", f_mid),
]

y = 18
for text, fo in rows:
    if text:
        d.text((42, y), text, fill=(0, 0, 0, 255), font=fo)
    y += 33 if fo is f_sm else 37

img.save("render.png")
raw = img.convert("RGBA").tobytes()
assert len(raw) == W * H * 4, (len(raw), W * H * 4)
with open("/dev/fb0", "wb") as fb:
    fb.write(raw); fb.flush()
os.system("sync")

with open("/dev/fb0", "rb") as f:
    back = f.read(W * H * 4)
Image.frombytes("RGBA", (W, H), back).convert("RGB").save("captured.png")

txt = subprocess.run(["tesseract", "captured.png", "stdout", "-l", "eng", "--psm", "6"],
                     capture_output=True, text=True).stdout
open("ocr.txt", "w").write(txt)
print("CODE:", CODE)
print("--- OCR from captured.png ---")
print(txt)
