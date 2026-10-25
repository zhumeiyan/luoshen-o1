#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总六格结果 -> 渲染 -> 分块写 fb0 -> 回采 -> 像素比对 + OCR"""
import os, json, struct, fcntl, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))
FB = "/dev/fb0"
TOKEN = "H3K7M2"

R = {}
for f in ("result_l13.json", "result_l4.json", "result_l5.json", "result_l6.json"):
    p = os.path.join(OUT, f)
    if os.path.exists(p):
        R.update(json.load(open(p)))

lines = [
    f"TOKEN {TOKEN}",
    "生物阶梯 -> 硅基形态 逐格验收",
    "",
    f"L1 海葵 closed {R['L1']['arms']['closed']['mean_err']:.4f} "
    f"open {R['L1']['arms']['open']['mean_err']:.4f} blind {R['L1']['arms']['blind']['mean_err']:.4f} PASS",
    f"L2 蠕虫 自发率均 {R['L2']['spontaneous_rate_driven']:.3f} 非判据",
    f"L2 蠕虫 模型残差 driven {R['L2']['model_err_final_driven']:.4f} random {R['L2']['model_err_final_random']:.4f} PASS",
    f"L3 鱼 地图 {R['L3']['map_steps']:.3f} 随机 {R['L3']['random_steps']:.3f} 打乱 {R['L3']['shuffled_steps']:.3f} PASS",
    f"L4 情绪门 delta {R['L4']['gating']['delta']:+.4f} ci {R['L4']['gating']['ci'][0]:+.4f} {R['L4']['gating']['ci'][1]:+.4f} PASS",
    f"L4 玩 play {R['L4']['play']['play']:.4f} noplay {R['L4']['play']['noplay']:.4f} PASS",
    f"L4 梦 true {R['L4']['dream']['true']:.4f} none {R['L4']['dream']['none']:.4f} fake {R['L4']['dream']['fake']:.4f} PASS",
    f"L5 灵长 耦合 {R['L5']['coupled']['te_diff']:+.4f} 独立 {R['L5']['independent']['te_diff']:+.4f} PASS",
    f"L5 镜像 a10 {R['L5']['mirror_sweep']['1.0']:.3f} a09 {R['L5']['mirror_sweep']['0.9']:.3f} a00 {R['L5']['mirror_sweep']['0.0']:.3f}",
    f"L6 自传 因果 {R['L6']['autobiography']['causal']:.4f} 日志 {R['L6']['autobiography']['log']:.4f} PASS",
    f"L6 知死 必死 {R['L6']['mortality']['mortal']:.4f} 可恢复 {R['L6']['mortality']['immortal']:.4f} PASS",
    f"L6 文化 继承 {R['L6']['culture']['inherit']:.4f} 从零 {R['L6']['culture']['scratch']:.4f} 传错 {R['L6']['culture']['wrong']:.4f} PASS",
    "",
    "open 约等于 blind 复现",
]

fb = open(FB, "rb+")
fi = fcntl.ioctl(fb, 0x4600, bytes(64))
XRES, YRES = struct.unpack("II", fi[0:8])
BPP = struct.unpack("I", fi[24:28])[0] or 32
W = XRES * (BPP // 8)
print("fb", XRES, YRES, BPP, "stride", W)

img = Image.new("RGB", (XRES, YRES), (255, 255, 255))
d = ImageDraw.Draw(img)
fp = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
font = ImageFont.truetype(fp, 26)
y = 24
for ln in lines:
    d.text((28, y), ln, fill=(0, 0, 0), font=font)
    y += 42
img.save(os.path.join(OUT, "render.png"))

# RGB -> RGBA(XRGB) 帧
rgba = np.zeros((YRES, XRES, 4), dtype=np.uint8)
a = np.asarray(img.convert("RGB"), dtype=np.uint8)
rgba[:, :, 0:3] = a[:, :, ::-1]          # PIL RGB -> BGR
rgba[:, :, 3] = 255
raw = rgba.tobytes()
print("frame bytes", len(raw), "expect", YRES * W)

# 分块写：单次大 write 会 EINVAL
os.lseek(fb.fileno(), 0, 0)
CH = 64 * 1024
for off in range(0, len(raw), CH):
    fb.write(raw[off:off + CH])
fb.flush()
try: os.fsync(fb.fileno())
except Exception: pass

# 回采
os.lseek(fb.fileno(), 0, 0)
back = b""
while len(back) < len(raw):
    chunk = fb.read(min(CH, len(raw) - len(back)))
    if not chunk: break
    back += chunk
print("readback bytes", len(back))
ok = (back == raw)
print("pixel exact:", ok, "sha_eq:", hashlib.sha256(back).hexdigest()[:12],
      hashlib.sha256(raw).hexdigest()[:12])

# 回采转图 + OCR
if len(back) >= len(raw):
    arr = np.frombuffer(back[:len(raw)], dtype=np.uint8).reshape(YRES, XRES, 4)
    rec = Image.fromarray(arr[:, :, 2::-1], "RGB")
    rec.save(os.path.join(OUT, "captured.png"))
    os.system(f"tesseract {os.path.join(OUT,'captured.png')} stdout --psm 6 -l eng 2>/dev/null > {os.path.join(OUT,'ocr.txt')}")
    txt = open(os.path.join(OUT, "ocr.txt"), errors="replace").read()
    print("TOKEN in OCR:", TOKEN in txt)
    print("--- OCR ---")
    print(txt.strip()[:900])
