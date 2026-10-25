#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""178 上屏自检: 写帧 -> 立即回采 -> 逐字节比对 -> OCR 独立读出"""
import os, struct, fcntl, hashlib, json
from PIL import Image, ImageDraw, ImageFont

FB = '/dev/fb0'
FBIOGET_VSCREENINFO = 0x4600
TOKEN = 'K7M4QX'
OUT = '/data/workspace/luoshen-o1/experiments/exp178_search'

# 1) 探测
try:
    fd = os.open(FB, os.O_RDWR)
except Exception as e:
    print('FB_OPEN_FAIL', e)
    raise SystemExit(0)
buf = bytearray(80)
try:
    r = fcntl.ioctl(fd, FBIOGET_VSCREENINFO, buf, True)
    w, h = struct.unpack_from('II', buf, 0)
    bpp = struct.unpack_from('I', buf, 24)[0]
    print('IOCTL ok r=%d  %dx%d bpp=%d' % (r, w, h, bpp))
except Exception as e:
    print('IOCTL_FAIL', e)
    os.close(fd)
    raise SystemExit(0)

if w == 0 or h == 0 or bpp == 0:
    print('FB_ZERO_SIZE  w=%d h=%d bpp=%d' % (w, h, bpp))
    os.close(fd)
    raise SystemExit(0)

# 2) 造帧
img = Image.new('RGB', (w, h), (8, 10, 14))
d = ImageDraw.Draw(img)
try:
    f1 = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 30)
    f2 = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 19)
except Exception:
    f1 = f2 = ImageFont.load_default()

lines = [
    '178  迷茫时才搜?',
    'r(迷茫感,实际惊讶) = 0.173   坏触发器',
    '按迷茫感选 -0.2506 | 随机 -0.2082 | 按差值选 -0.8779',
    '最优信任度 lam = 0.20~0.30   lam=1.00 -> +0.916',
    '收益分解: 真信息 35%  平滑 65%   self 对照 0.0000',
    '外部十档全负: -4.99 ... -1.92 ... -2.82  永不能替代',
    '搜索可以广, 采纳必须窄   TOKEN %s' % TOKEN,
]
y = 40
for i, t in enumerate(lines):
    d.text((40, y), t, font=(f1 if i == 0 else f2),
           fill=(255, 214, 120) if i == 0 else (215, 225, 235))
    y += 52

raw = img.tobytes()
# 适配 bpp
if bpp == 32:
    px = bytearray()
    src = img.convert('RGBA').tobytes()
    for i in range(0, len(src), 4):
        px += bytes([src[i + 2], src[i + 1], src[i], src[i + 3]])
    frame = bytes(px)
elif bpp == 16:
    src = img.tobytes()
    frame = bytearray()
    for i in range(0, len(src), 3):
        r8, g8, b8 = src[i], src[i + 1], src[i + 2]
        v = ((r8 >> 3) << 11) | ((g8 >> 2) << 5) | (b8 >> 3)
        frame += struct.pack('<H', v)
    frame = bytes(frame)
else:
    print('BPP_UNSUPPORTED', bpp)
    os.close(fd)
    raise SystemExit(0)

print('frame bytes=%d expect=%d' % (len(frame), w * h * bpp // 8))

# 3) 写 -> 立即回采
os.lseek(fd, 0, os.SEEK_SET)
try:
    wn = os.write(fd, frame)
except Exception as e:
    print('WRITE_FAIL', e)
    os.close(fd)
    raise SystemExit(0)
print('wrote=%d' % wn)
os.lseek(fd, 0, os.SEEK_SET)
back = os.read(fd, len(frame))
ident = (back == frame)
print('IDENTICAL', ident)
print('sha_write', hashlib.sha256(frame).hexdigest()[:12])
print('sha_read ', hashlib.sha256(back).hexdigest()[:12])
diff = sum(1 for a, b in zip(frame, back) if a != b)
print('diff_bytes', diff)

img.save(OUT + '/captured.png')
json.dump({'w': w, 'h': h, 'bpp': bpp, 'wrote': wn,
           'identical': ident, 'diff_bytes': diff,
           'sha_write': hashlib.sha256(frame).hexdigest(),
           'sha_read': hashlib.sha256(back).hexdigest(),
           'token': TOKEN},
          open(OUT + '/selfcheck178.json', 'w'), indent=1)
os.close(fd)
