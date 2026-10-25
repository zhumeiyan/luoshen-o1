# -*- coding: utf-8 -*-
"""做完自己看：101 关键数字 渲染上屏 -> 帧缓冲真实采集 -> OCR 读回"""
import os, subprocess, random, json, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FB = '/dev/fb0'
W, H = 1024, 768
FONT = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
if not os.path.exists(FONT):
    FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

rows = [
    ("101b 周边+主动 识别率", "1.0000   特征 420"),
    ("101b 盲动 识别率", "0.7500   特征 84"),
    ("101b 不动 识别率", "0.1250   特征 48"),
    ("101c 假引导 识别率", "0.5312  < 盲动 0.7188"),
    ("101c 引导破坏剂量", "1.000 -> 0.531  单调"),
    ("101c T=1 GUIDED", "1.0000  只用 89 特征"),
    ("101c T=12 FIXED", "0.1250  累积 96 特征"),
    ("101e 相变区 0.08->0.12", "斜率 -36.1  最陡"),
    ("101e level=1.00 偏度", "-0.6391"),
    ("101e 无感官基线 偏度", "-0.7273  几乎相同"),
    ("101e level=0.00 偏度", "+1.8346  最高"),
    ("101d 生态 FIXED->GUIDED", "diff -1.646 CI全负"),
]
code = ''.join(random.choice('0123456789ABCDEF') for _ in range(6))
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
f1 = ImageFont.truetype(FONT, 28)
f2 = ImageFont.truetype(FONT, 24)
d.text((40, 22), "101 主动扫视靠什么看清", font=f1, fill=(0, 0, 0))
y = 78
for a, b in rows:
    d.text((45, y), a, font=f2, fill=(20, 20, 120))
    d.text((560, y), b, font=f2, fill=(160, 20, 20))
    y += 46
d.text((45, y + 12), f"RANDOM CHECK = {code}",
       font=ImageFont.truetype(FONT, 32), fill=(0, 110, 0))
img.save(os.path.join(OUT, 'rendered101.png'))

arr = np.array(img.convert('RGB'))
canvas = np.zeros((H, W, 4), np.uint8)
canvas[:H, :W, 0] = arr[:, :, 2]
canvas[:H, :W, 1] = arr[:, :, 1]
canvas[:H, :W, 2] = arr[:, :, 0]
canvas[:H, :W, 3] = 255
with open(FB, 'wb') as f:
    f.write(canvas.tobytes())
time.sleep(0.4)
with open(FB, 'rb') as f:
    raw = f.read(W * H * 4)
cap = np.frombuffer(raw, np.uint8).reshape(H, W, 4)[:, :, [2, 1, 0]]
Image.fromarray(cap).save(os.path.join(OUT, 'captured101.png'))

txt = subprocess.run(['tesseract', os.path.join(OUT, 'captured101.png'), 'stdout',
                      '--psm', '6', '-l', 'eng'], capture_output=True, text=True).stdout
flat = txt.replace(' ', '')
hit = code in flat
nums = [t for t in ['1.0000', '0.7500', '0.1250', '0.5312', '0.7188',
                    '-36.1', '-0.6391', '-0.7273', '+1.8346', '-1.646']
        if t in flat]
print("校验码:", code, "| 回读命中:", hit)
print("数字命中:", nums, f"({len(nums)}/10)")
print("--- OCR 节选 ---")
print('\n'.join([l for l in txt.splitlines() if l.strip()][:12]))
json.dump({'code': code, 'code_hit': bool(hit), 'nums': nums,
           'n_nums': len(nums)},
          open(os.path.join(OUT, 'selfcheck101.json'), 'w'), ensure_ascii=False, indent=1)
