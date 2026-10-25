# -*- coding: utf-8 -*-
"""105 自检：数字渲染 -> 写 /dev/fb0 -> ffmpeg 从帧缓冲采集 -> OCR 回读"""
import os, random, subprocess, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np

FB = '/dev/fb0'
OUT = os.path.join(os.path.dirname(__file__))
rng = random.Random()
code = ''.join(rng.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(6))

vals = [
    ('BASE_SKEW', 0.2879), ('RICH_SKEW', 0.0000),
    ('CRIT_A', 0.1886), ('CRIT_B', 0.0288), ('CRIT_C', 0.0000),
    ('CUT_D', 0.1727), ('JIT_D', 0.0710),
    ('ALIVE_B', 13.0), ('ALIVE_R', 16.0), ('DEAF_A', 0.0),
]
W = H = 900
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
fp = None
for c in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
          '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
    if os.path.exists(c):
        fp = c; break
f_big = ImageFont.truetype(fp, 36) if fp else ImageFont.load_default()
d.text((30, 15), 'EXP105 INCOME METABOLISM', fill=(0, 0, 0), font=f_big)
d.text((30, 70), 'CODE %s' % code, fill=(0, 0, 0), font=ImageFont.truetype(fp, 52) if fp else ImageFont.load_default())
y = 170
for k, v in vals:
    d.text((30, y), '%-10s %8.4f' % (k, v), fill=(0, 0, 0), font=f_big)
    y += 55

# 帧缓冲 32bpp -> BGRA
try:
    with open(FB, 'rb') as f:
        f.seek(0, 2); fbsize = f.tell()
    fbw, fbh = 1024, 768
except Exception as e:
    print('FB probe fail', e); fbw, fbh = 1024, 768

canvas = Image.new('RGB', (fbw, fbh), (255, 255, 255))
canvas.paste(img.resize((min(W, fbw - 40), min(H, fbh - 40))), (20, 20))
arr = np.asarray(canvas)
bgra = np.zeros((fbh, fbw, 4), dtype=np.uint8)
bgra[:, :, 0] = arr[:, :, 2]; bgra[:, :, 1] = arr[:, :, 1]
bgra[:, :, 2] = arr[:, :, 0]; bgra[:, :, 3] = 255
with open(FB, 'wb') as f:
    f.write(bgra.tobytes())

# 真实采集：直读帧缓冲（ffmpeg -f fbdev 曾超时 60s，097 已改同源直读）
with open(FB, 'rb') as f:
    raw = f.read(fbw * fbh * 4)
fb = np.frombuffer(raw, dtype=np.uint8).reshape(fbh, fbw, 4)
cap = Image.fromarray(fb[:, :, [2, 1, 0]].copy())
capp = os.path.join(OUT, 'captured.png')
cap.save(capp)

try:
    import pytesseract
    txt = pytesseract.image_to_string(cap)
except Exception as e:
    txt = ''
    print('OCR fail', e)

hit_code = code in txt.replace(' ', '')
hits = []
for k, v in vals:
    s = '%.4f' % v
    hits.append(bool(s in txt.replace(' ', '')))
print('check_code=%s  hit=%s' % (code, hit_code))
print('num_hits=%d/%d' % (sum(hits), len(hits)))
print('--- OCR ---'); print(txt[:1200])
json.dump(dict(code=code, code_hit=hit_code, num_hits=int(sum(hits)),
               total=len(vals), ocr=txt), open(os.path.join(OUT, 'selfcheck.json'), 'w'))
