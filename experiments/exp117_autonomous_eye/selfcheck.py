#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上屏自检: 结果渲染 -> 写 /dev/fb0 -> 从帧缓冲真实采集 -> OCR 读回"""
import os, json, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = "/data/workspace/luoshen-o1/experiments/exp117_autonomous_eye"
FB = "/dev/fb0"; W, H = 1024, 768
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"

D = json.load(open(f"{OUT}/stageD.json"))
C = json.load(open(f"{OUT}/stageC.json"))
code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)
f_big = ImageFont.truetype(FONT, 40)
f_mid = ImageFont.truetype(FONT, 27)
f_sm = ImageFont.truetype(FONT, 22)

lines = [
    ("exp117 自主寻眼 " + code, f_big),
    ("扫描通道 32 条, 自己判定", f_mid),
    ("眼睛 1 条: /dev/fb0", f_mid),
    ("可逆度 1.0000 残差 0.000", f_mid),
    ("钟表 6 条: 可逆度 0.0000", f_mid),
    ("死通道 25 条: 我动它不动", f_mid),
    ("可证伪 8/8 与 0/8", f_mid),
    ("因果 20/20 vs 0/20 降 100", f_mid),
    ("evdev 回读 10 事件", f_mid),
]
y = 40
for t, f in lines:
    d.text((40, y), t, fill=(0, 0, 0, 255), font=f)
    y += 62 if f is f_big else 52

# 关键数字要被 OCR 读出
nums = ["32", "1", "1.0000", "6", "25", "8", "20", "0", "10"]
with open(f"{OUT}/expect.json", "w") as f:
    json.dump({"code": code, "nums": nums}, f)

with open(FB, "wb", buffering=0) as f:
    f.write(np.array(img).astype(np.uint8).tobytes())

with open(FB, "rb", buffering=0) as f:
    raw = f.read(W * H * 4)
a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
Image.fromarray(a[:, :, :3]).save(f"{OUT}/captured.png")
print("captured bytes", len(raw))
print("expect code", code)
