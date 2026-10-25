# -*- coding: utf-8 -*-
import random, string, fcntl, struct, subprocess, os
from PIL import Image, ImageDraw, ImageFont

CODE = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
W, H, BPP = 1024, 768, 32

FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
f_big  = ImageFont.truetype(FONT, 26)
f_mid  = ImageFont.truetype(FONT, 20)
f_small= ImageFont.truetype(FONT, 16)

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)

rows = [
    ("EO INVISIBLE SYSTEMS V2  CODE " + CODE, f_big),
    ("", None),
    ("M1 mutation unique    v1 1of20   v2 20of20", f_mid),
    ("M2 energyA after40x   v1 23737.6 v2 160.0", f_mid),
    ("M2 gap A minus B      v1 23637.6 v2 72.0", f_mid),
    ("M3 distinct emotions  v1 3of5    v2 4of5", f_mid),
    ("M4 trauma hit rate    v1 1of6    v2 5of7", f_mid),
    ("M5 trauma fire t501   v1 True    v2 False", f_mid),
    ("M6 liar selfreport0.0 v1 KEEP    v2 PURGE", f_mid),
    ("M7 solo no peers      v1 KEEP    v2 UNVERIFIABLE", f_mid),
    ("", None),
    ("NEW SAT I INTRODUCED clamp A_MIN angry equals sad 40.0", f_small),
    ("NEW SAT II HTTP429 TooManyRequests still missed", f_small),
]

y = 40
for text, fo in rows:
    if text:
        d.text((50, y), text, fill=(0, 0, 0, 255), font=fo)
    y += 44 if fo is f_small else 50

img.save("render.png")

# ---- write to real framebuffer (RGBA, 32bpp) ----
fb = open("/dev/fb0", "wb")
raw = img.convert("RGBA").tobytes()
assert len(raw) == W * H * 4, (len(raw), W * H * 4)
fb.write(raw)
fb.flush()
os.system("sync")

# ---- read back from the real device ----
with open("/dev/fb0", "rb") as f:
    back = f.read(W * H * 4)
back_img = Image.frombytes("RGBA", (W, H), back).convert("RGB")
back_img.save("captured.png")

# ---- OCR the captured image, not the render ----
txt = subprocess.run(["tesseract", "captured.png", "stdout", "-l", "eng", "--psm", "6"],
                     capture_output=True, text=True).stdout
open("ocr.txt", "w").write(txt)
print("CODE:", CODE)
print("---- OCR (from captured.png) ----")
print(txt)
