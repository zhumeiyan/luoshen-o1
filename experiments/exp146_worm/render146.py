#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""exp146 上屏自检：渲染 -> 写 /dev/fb0 -> 回采 -> 比对"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 768
TOKEN = "W7K3QZ"
HERE = os.path.dirname(os.path.abspath(__file__))

img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
try:
    fp = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    f_big = ImageFont.truetype(fp, 34)
    f_mid = ImageFont.truetype(fp, 26)
    f_sm = ImageFont.truetype(fp, 21)
except Exception:
    f_big = f_mid = f_sm = ImageFont.load_default()

lines = [
    ("EXP146 WORM STAGE", f_big),
    ("self-initiated scheduler", f_sm),
    ("", f_sm),
    ("G1 no_drive spont_rate = 0.000  PASS", f_mid),
    ("", f_sm),
    ("TERRAIN A real / no structure", f_mid),
    ("  pretest ratio 1.0936  learnable NO", f_sm),
    ("  curiosity - random = +0.1504  WORSE", f_sm),
    ("", f_sm),
    ("TERRAIN B real / structured", f_mid),
    ("  pretest ratio 0.6582  learnable YES", f_sm),
    ("  curiosity - random = -0.0447  BETTER", f_sm),
    ("  anti 1.4177 > random 1.2551 > curi 1.2104", f_sm),
    ("", f_sm),
    ("INTERACTION B - A = +0.1950", f_mid),
    ("  CI [+0.1221 +0.2679]  no zero", f_sm),
    ("", f_sm),
    ("DAEMON no instruction, 18 sec", f_mid),
    ("  curiosity 32 actions / 766 ticks", f_sm),
    ("  no_drive   0 actions / 858 ticks", f_sm),
    ("", f_sm),
    (f"TOKEN {TOKEN}", f_big),
]

# 固定行位，避免末行越界（144 号同病第 2 次复发）
YS = [16, 54, 84, 116, 150, 184, 218, 252, 286, 320, 346, 380, 414, 450, 484, 516, 552, 586, 620, 656, 690, 712]
assert len(YS) == len(lines), (len(YS), len(lines))
for (txt, fnt), yy in zip(lines, YS):
    d.text((40, yy), txt, fill=(0, 0, 0), font=fnt)
print("last line y =", YS[-1], "canvas H =", H, "fits =", YS[-1] + 44 <= H)

png = os.path.join(HERE, "render146.png")
img.save(png)

FB = "/dev/fb0"
raw = img.convert("RGB").tobytes()
with open(FB, "wb") as f:
    f.write(raw)
with open(FB, "rb") as f:
    cap = f.read(len(raw))
identical = (cap == raw)
print("wrote", len(raw), "captured", len(cap), "IDENTICAL", identical)

subprocess.run(["python3", "-c", """
from PIL import Image
im = Image.open('%s')
im.save('%s')
""" % (png, os.path.join(HERE, "expect146.png"))], check=False)

# 把帧缓冲原始字节存成 PNG 供 OCR
Image.frombytes("RGB", (W, H), cap).save(os.path.join(HERE, "captured.png"))
print("saved captured.png")
