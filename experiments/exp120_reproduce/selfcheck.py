# -*- coding: utf-8 -*-
import random, fcntl, struct, subprocess, os
from PIL import Image, ImageDraw, ImageFont

# 去掉易混淆字符 B/8 O/0 I/1 S/5 Z/2
ALPHA = "ACDEFGHJKLMNPQRTUVWXY34679"
CODE = "".join(random.choice(ALPHA) for _ in range(6))

W, H, BPP = 1024, 768, 32
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
f_big = ImageFont.truetype(FONT, 26)
f_mid = ImageFont.truetype(FONT, 20)
f_small = ImageFont.truetype(FONT, 15)

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)

rows = [
    ("EO REPRODUCTION V2   CODE " + CODE, f_big),
    ("", None),
    ("A1 shared chain         v1 True    v2 False", f_mid),
    ("A2 unique genome 20 kids v1 1       v2 20", f_mid),
    ("A3 pop after 8 gen       v1 1       v2 20", f_mid),
    ("A3 births 47  deaths 28  v1 none    v2 yes", f_mid),
    ("A4 liar selfreport 9999  v1 KEPT    v2 PURGED", f_mid),
    ("", None),
    ("B singlepeak  niche 1  simpson 0.0000  spread 0.0567", f_mid),
    ("B multipeak   niche 2  simpson 0.2550  spread 0.1504", f_mid),
    ("", None),
    ("C mu dose   mu0 box1  mu0.05 box6  mu0.1 box10  mu0.4 box9", f_small),
    ("D carrying  K2 box2  K10 box6  K20 box10  K40 box8", f_small),
    ("", None),
    ("SAT I first metric saturated box 20of20 both worlds", f_small),
    ("POSCTRL relative diff 0.0821pct  under 1pct  FAILED", f_small),
    ("ENGINE delta varied-clone -0.000961 CI crosses 0", f_small),
]

y = 28
for text, fo in rows:
    if text:
        d.text((45, y), text, fill=(0, 0, 0, 255), font=fo)
    y += 40 if fo is f_small else 44

img.save("render.png")

fb = open("/dev/fb0", "wb")
raw = img.convert("RGBA").tobytes()
assert len(raw) == W * H * 4, (len(raw), W * H * 4)
fb.write(raw)
fb.flush()
os.system("sync")

with open("/dev/fb0", "rb") as f:
    back = f.read(W * H * 4)
Image.frombytes("RGBA", (W, H), back).convert("RGB").save("captured.png")

txt = subprocess.run(["tesseract", "captured.png", "stdout", "-l", "eng", "--psm", "6"],
                     capture_output=True, text=True).stdout
open("ocr.txt", "w").write(txt)
print("CODE:", CODE)
print("---- OCR from captured.png ----")
print(txt)
