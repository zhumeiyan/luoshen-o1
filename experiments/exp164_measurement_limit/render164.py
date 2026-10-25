#!/usr/bin/env python3
"""exp164 上屏自检: 渲染 -> 写 /dev/fb0 -> 同进程立即回采 -> 逐字节比对 -> OCR"""
import os, glob, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = "/data/workspace/luoshen-o1/experiments/exp164_measurement_limit"
FB = "/dev/fb0"
W, H = 1024, 768
NB = W*H*4
TOKEN = "T9K2MZ"

cands = ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
         "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
         "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"]
font_path = None
for c in cands:
    if os.path.exists(c):
        font_path = c
        break
if font_path is None:
    g = sorted(glob.glob("/usr/share/fonts/truetype/wqy/*") +
               glob.glob("/usr/share/fonts/opentype/noto/*CJK*"))
    if g:
        font_path = g[0]
assert font_path, "未找到中文字体(禁止静默降级)"
print("font =", font_path)

img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
d = ImageDraw.Draw(img)
f = ImageFont.truetype(font_path, 23)
fb = ImageFont.truetype(font_path, 30)

LINES = [
    "164 测量极限: 灵敏度的终点是坍缩",
    "",
    "A 单分支互信息 I(A;X)=0.00000  I(B;X)=0.00001",
    "A 关联 A^B 恢复 X 准确率 = 1.0000",
    "A 观测扰动 p: 0.00->1.0000  0.20->0.7990  0.35->0.6537",
    "A p=0.50 -> 0.4996  完全坍缩 (单分支互信息始终为0)",
    "",
    "A2 经典关联可复制 -> 多数投票纠错 (m=21,p=0.20 -> 0.9990)",
    "A2 相变点 p=0.50: m=1..21 恒 0.50  多堆关联无效",
    "",
    "C2 CPU降频: 连续 5842 ns  sleep后首次 40388 ns  比值 6.913",
    "C3 观测强度 k=4..256 漂移无单调趋势 (经典扰动是机制依赖)",
    "",
    "量子: SQL 1/sqrt(N) -> HL 1/N (纠缠, 提升 sqrt(N) 倍)",
    "量子: 纠缠不可克隆 -> 越大越难保护 -> 观测即坍缩",
    "",
    "TOKEN " + TOKEN,
]

# 固定行位表(避免末行越出画布)
y0, lh = 55, 40
for i, t in enumerate(LINES):
    y = y0 + i*lh
    assert y + lh <= H - 10, f"行 {i} 越出画布: y={y}"
    d.text((45, y), t, font=(fb if i == 0 else f), fill=(0, 0, 0, 255))

img.convert("RGB").save(os.path.join(OUT, "render164.png"))

raw = img.tobytes()
assert len(raw) == NB, f"字节数不符 {len(raw)} != {NB}"
with open(FB, "wb") as g:
    g.write(raw)
with open(FB, "rb") as g:          # 同进程立即回采(避开 fbcon 0.2s 覆盖)
    cap = g.read(NB)

identical = (raw == cap)
print("写入字节 =", len(raw))
print("IDENTICAL =", identical, " diff_px =", int((np.frombuffer(raw, np.uint8) != np.frombuffer(cap, np.uint8)).sum()))
print("raw sha =", hashlib.sha256(raw).hexdigest()[:16])
print("cap sha =", hashlib.sha256(cap).hexdigest()[:16])

ci = Image.frombytes("RGBA", (W, H), cap).convert("RGB")
ci.save(os.path.join(OUT, "captured.png"))
print("saved captured.png")

# OCR 独立读出
try:
    import pytesseract
    txt = pytesseract.image_to_string(ci, lang="chi_sim")
    with open(os.path.join(OUT, "ocr164.txt"), "w") as g:
        g.write(txt)
    hit = TOKEN in txt.replace(" ", "")
    print("OCR 字符数 =", len(txt), " TOKEN 命中 =", hit)
    print("---- OCR ----")
    print(txt.strip()[:900])
except Exception as e:
    print("OCR 不可用:", e)
