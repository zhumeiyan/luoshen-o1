import subprocess, random, struct, zlib, os
from PIL import Image, ImageDraw, ImageFont

FONTS = ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
         "/usr/share/fonts/truetype/wqy/wenquanyi/wqy-microhei.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
f = None
for p in FONTS:
    if os.path.exists(p):
        try: f = ImageFont.truetype(p, 34); break
        except Exception: pass
if f is None: f = ImageFont.load_default()

code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
vals = [("canon entries", 368), ("exec rules", 10), ("planted caught", 9),
        ("planted total", 10), ("clean blocker", 0), ("clean warn", 0),
        ("actionable", 144), ("tier1 usd", 29), ("tier2 usd", 99), ("tier3 usd", 499)]

W, H = 1024, 768
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
d.text((40, 30), f"evalguard selfcheck   code {code}", font=f, fill="black")
y = 100
for k, v in vals:
    d.text((40, y), f"{k:16s} {v}", font=f, fill="black"); y += 52
d.text((40, y+20), "render -> /dev/fb0 -> capture -> OCR", font=f, fill="black")
img.save("experiments/exp104/rendered.png")

# 写帧缓冲（32bpp BGRA）
raw = img.tobytes()
bgra = bytearray()
for i in range(0, len(raw), 3):
    r, g, b = raw[i], raw[i+1], raw[i+2]
    bgra += bytes([b, g, r, 255])
fb = open("/dev/fb0", "wb")
try:
    fb.write(bytes(bgra)); fb.flush()
except Exception as e:
    print("fb write:", e)
fb.close()

# 采集
subprocess.run(["python3", "-c", """
import sys
data = open('/dev/fb0','rb').read(1024*768*4)
from PIL import Image
im = Image.frombytes('RGB', (1024,768), data, 'raw', 'BGRX', 0, 1)
im.save('experiments/exp104/captured.png')
print('captured bytes', len(data))
"""], check=False)

print("CODE", code)
print("EXPECT", vals)
