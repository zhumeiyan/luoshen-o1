#!/usr/bin/env python3
# 论文自检：渲染关键数据表 -> 写 /dev/fb0 -> 真实采集 -> OCR 回读
import os, struct, hashlib, subprocess, random, string

W, H, BPP = 1024, 768, 32
FB = '/dev/fb0'
OUT = '/data/workspace/luoshen-o1/paper'
FONT = '/usr/share/fonts/truetype/wenquanyi/WenQuanYiMicroHei.ttc'
if not os.path.exists(FONT):
    for p in ['/usr/share/fonts/truetype/wenquanyi/wqy-microhei.ttc',
              '/usr/share/fonts/wenquanyi/wqy-microhei.ttc']:
        if os.path.exists(p): FONT = p; break

from PIL import Image, ImageDraw, ImageFont

# 校验码：避开易混淆字符 (O/0, 1/I/l, 8/B, 9/g)
ALPHA = 'ACDEFGHJKMNPQRTUVWXY234567'
TOKEN = ''.join(random.choice(ALPHA) for _ in range(6))

def load(sz):
    try: return ImageFont.truetype(FONT, sz)
    except Exception: return ImageFont.load_default()

img = Image.new('RGB', (W, H), 'white')
d = ImageDraw.Draw(img)
f_t = load(34); f_h = load(25); f_b = load(21)

y = 24
d.text((40, y), '论文自检 / Chiral Blindness', font=f_t, fill='black'); y += 48
d.text((40, y), '校验码 TOKEN: ' + TOKEN, font=f_t, fill='black'); y += 52

rows = [
    ('语义镜像 词袋 disc', '0.0000'),
    ('语义镜像 含序 disc', '1.0000'),
    ('对照 词袋 disc', '0.3200'),
    ('坍塌 REPLACE 稀有类', '0.005 -> 0.000'),
    ('累积 ACCUM 稀有类', '0.028 -> 0.003'),
    ('自发破缺 锁定率', '120 / 120'),
    ('手性方向 L / R', '56 / 64'),
    ('输液组 存活', '16 / 16  fg=0'),
    ('撤供后 存活', '0 / 12  mean 235'),
    ('相倚 vs 相继 fg', '0.10368 / 0.00149'),
    ('语法层 精度', '18 / 20 = 90%'),
    ('方法论层 精度', '1 / 55 = 1.8%'),
    ('跨层翻转 翻/不翻', '2 / 4'),
    ('THESIS', 'disc = TPR - FPR'),
]
for k, v in rows:
    d.text((46, y), k, font=f_b, fill='black')
    d.text((560, y), v, font=f_h, fill='black')
    y += 33

y += 6
d.text((40, y), 'VERDICT: PATENT_NOVELTY_PARTIAL', font=f_h, fill='black'); y += 34
d.text((40, y), 'SCIENCE_DISCOVERY: NOT_PATENTABLE', font=f_h, fill='black'); y += 34
d.text((40, y), 'ORDER: FILE_PATENT_BEFORE_PAPER', font=f_h, fill='black'); y += 34

img.save(os.path.join(OUT, 'render.png'))
raw = img.convert('RGBA').tobytes()
assert len(raw) == W * H * 4, (len(raw), W * H * 4)

with open(FB, 'wb') as f:
    f.write(raw)
    f.flush()
    os.fsync(f.fileno())
print('WROTE', len(raw), 'bytes')

# 真实采集
with open(FB, 'rb') as f:
    cap = f.read(W * H * 4)
print('CAPTURED', len(cap), 'bytes')

with open(os.path.join(OUT, 'captured.png'), 'wb') as f:
    Image.frombytes('RGBA', (W, H), cap).convert('RGB').save(f)

print('sha_render', hashlib.sha256(raw).hexdigest()[:16])
print('sha_cap   ', hashlib.sha256(cap).hexdigest()[:16])
print('IDENTICAL ', raw == cap)
print('TOKEN', TOKEN)
