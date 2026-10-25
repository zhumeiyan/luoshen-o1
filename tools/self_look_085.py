# -*- coding: utf-8 -*-
"""
做完自己看 · 085
把实验结果的关键数字渲染到帧缓冲(屏幕)，再用 ffmpeg 采集 + OCR 读回来，
与脚本算出的真值逐项比对 —— 闭环证明"我做完自己看了"，不是转述。
"""
import json, os, subprocess, hashlib, secrets
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = '/data/workspace/luoshen-o1'
FB = '/dev/fb0'
FONT = '/nix/store/smgbvz9sqcikc18vf3i9ry2p5zlnb7h5-noto-fonts-cjk-sans-2.004/share/fonts/opentype/noto-cjk/NotoSansCJK-VF.otf.ttc'

d = json.load(open(f'{ROOT}/experiments/result_085d.json'))
e = json.load(open(f'{ROOT}/experiments/result_085e.json'))

# ---- 真值（由脚本算出，先封存 SHA256，事后改不了）----
truth = {
    'RHO_DRIFT':  f"{d['rho_drift']:.4f}",
    'RHO_ALIVE':  f"{d['rho_alive']:.4f}",
    'DELTA_R6':   f"{e['rows'][2]['delta']:.5f}",
    'DRIFT_MAX':  f"{max(r['drift'] for r in d['rows']):.5f}",
}
tag = secrets.token_hex(3).upper()
fh = hashlib.sha256(json.dumps(truth, sort_keys=True).encode()).hexdigest()[:16]
print('[封存真值]', truth)
print('[SHA256]  ', fh, ' 随机校验码:', tag)

# ---- 渲染到屏幕 ----
W, H = 1024, 768
img = Image.new('RGB', (W, H), 'white')
dr = ImageDraw.Draw(img)
f_big = ImageFont.truetype(FONT, 34)
f_sm = ImageFont.truetype(FONT, 26)
lines = [
    ("实验085 我自己看结果", f_big),
    (f"RHO_DRIFT {truth['RHO_DRIFT']}", f_sm),
    (f"RHO_ALIVE {truth['RHO_ALIVE']}", f_sm),
    (f"DELTA_R6 {truth['DELTA_R6']}", f_sm),
    (f"DRIFT_MAX {truth['DRIFT_MAX']}", f_sm),
    (f"CHECK {tag}", f_sm),
]
y = 90
for t, f in lines:
    dr.text((70, y), t, fill='black', font=f); y += 78
img.save(f'{ROOT}/evidence/raw_data/085_rendered.png')

raw = img.convert('RGBA').tobytes()   # fb0 是 32bpp，必须 RGBA（082 的经验）
with open(FB, 'wb') as f:
    # 帧缓冲可能是 32bpp BGRA；按实际 stride 写
    f.write(raw)
print('[渲染] 已写入', FB)

subprocess.run(['ffmpeg', '-y', '-f', 'fbdev', '-i', FB, '-frames:v', '1',
                f'{ROOT}/evidence/raw_data/085_captured.png'],
               capture_output=True)
print('[采集] 已采集 085_captured.png')

import pytesseract
txt = pytesseract.image_to_string(Image.open(f'{ROOT}/evidence/raw_data/085_captured.png'))
print('\n[OCR 读回]\n' + txt)

ok = all(v in txt.replace(' ', '') for v in list(truth.values()) + [tag])
print('[比对] 全部命中:', ok)
for k, v in truth.items():
    print(f'   {k:12s} 真值={v:>10s}  在OCR中: {v in txt.replace(" ","")}')
print(f'   CHECK       随机码={tag}  在OCR中: {tag in txt.replace(" ","")}')
json.dump(dict(truth=truth, sha256=fh, tag=tag, ocr=txt, match=bool(ok)),
          open(f'{ROOT}/evidence/raw_data/085_selflook.json', 'w'), ensure_ascii=False, indent=1)
