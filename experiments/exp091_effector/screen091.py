# -*- coding: utf-8 -*-
"""做完自己看：渲染核心结论 -> 写帧缓冲 -> ffmpeg 采集 -> OCR 读回核对。
教训(088)：帧缓冲是 32bpp，按 RGB 写会错位；必须平滑插值+等比居中。"""
import os, json, secrets, hashlib, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FB = '/dev/fb0'
W, H = 1024, 768

def font(sz):
    for p in ['/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
              '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

check = secrets.token_hex(3).upper()
truth = {
    'eta_thr': '0.32',        # 返回效率阈值
    'dmax': '9',              # 帧间位移上限
    'base': '0.5662',
    'eye': '0.7254',
    'hbias': '0.5641',
    'hrand': '0.7028',
    'flip_lo': '14.5',
    'flip_hi': '190.9',
}
blob = json.dumps(truth, sort_keys=True)
sha = hashlib.sha256(blob.encode()).hexdigest()[:16]
json.dump(dict(truth=truth, check=check, sha256=sha),
          open('screen_truth091.json', 'w'), ensure_ascii=False, indent=1)

img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)
f = font(30); fs = font(22)
lines = [
    '091 效应器与感受器：手和眼在物理底层是同一类东西',
    '',
    f'返回效率阈值 eta = {truth["eta_thr"]}   低于它 => 玻璃上不动',
    f'帧间位移上限 dmax = {truth["dmax"]}   超过它 => 甩太快丢帧',
    '',
    f'无误差      {truth["base"]}   翻转 {truth["flip_lo"]}',
    f'眼噪看错    {truth["eye"]}   翻转 {truth["flip_hi"]}',
    f'手总偏一边  {truth["hbias"]}   翻转 {truth["flip_lo"]}  <= 可预测则无效应',
    f'手每拍抖    {truth["hrand"]}   翻转 {truth["flip_hi"]}  <= 不可预测才有效应',
    '',
    f'SEE THIS LINE   CHECK {check}',
]
y = 60
for i, t in enumerate(lines):
    d.text((50, y), t, fill='black', font=f if i else fs)
    y += 58
img.save('rendered091.png')

# 32bpp BGRA -> 帧缓冲
arr = np.array(img.convert('RGB'))
bgra = np.zeros((H, W, 4), dtype=np.uint8)
bgra[..., 0] = arr[..., 2]; bgra[..., 1] = arr[..., 1]
bgra[..., 2] = arr[..., 0]; bgra[..., 3] = 255
# 等比居中，平滑插值
scale = min(W / arr.shape[1], H / arr.shape[0])
nw, nh = max(1, int(arr.shape[1] * scale)), max(1, int(arr.shape[0] * scale))
small = np.array(img.convert('RGB').resize((nw, nh), Image.LANCZOS))
canvas = np.full((H, W, 3), 255, dtype=np.uint8)
oy, ox = (H - nh) // 2, (W - nw) // 2
canvas[oy:oy+nh, ox:ox+nw] = small
bgra = np.zeros((H, W, 4), dtype=np.uint8)
bgra[..., 0] = canvas[..., 2]; bgra[..., 1] = canvas[..., 1]
bgra[..., 2] = canvas[..., 0]; bgra[..., 3] = 255
bgra.tofile(FB)

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'fbdev',
                '-i', FB, '-frames:v', '1', 'captured091.png'], check=False)
print('captured ok:', os.path.exists('captured091.png'))
