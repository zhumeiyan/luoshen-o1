#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上屏自检：渲染 -> 写 /dev/fb0 -> 真实采集回读 -> 像素比对 + OCR"""
import os, sys, json, hashlib, subprocess

def fb_size():
    # ioctl 在这台机器曾返回全 0，改用 sysfs
    for p in ("/sys/class/graphics/fb0/virtual_size",
              "/sys/class/graphics/fb0/modes"):
        try:
            with open(p) as f:
                s = f.read().strip()
            if "x" in s:
                a, b = s.split(",")[0].split("x")[:2]
                return int(a), int(b)
        except Exception:
            pass
    return 1024, 768

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[FATAL] no PIL"); sys.exit(1)

W, H = fb_size()
print("[fb] size = %dx%d" % (W, H))

LINES = [
    "TOKEN K7X2M9",
    "",
    "exp139  chirality",
    "",
    "A2 MIRROR set-preserving",
    "  BOW disc 0.0000 degen 1",
    "  POS disc 1.0000 degen 0",
    "A2 CONTROL set-changing",
    "  BOW disc 0.3200 degen 0",
    "  POS disc 0.3200 degen 0",
    "",
    "C1 dose  chi0=0.00001",
    "  g1.6 final 0.926580",
    "  g2.5 final 1.000000",
    "C1 dose  chi0=0.00010",
    "  g1.6 final 1.000000",
    "",
    "C2 spontaneous chi0=0",
    "  locked 120 / 120",
    "  to L 56 / to R 64",
    "  z -0.730",
]

img = Image.new("RGBA", (W, H), (250, 250, 250, 255))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 26)
except Exception:
    font = ImageFont.load_default()

y = 24
for ln in LINES:
    d.text((30, y), ln, fill=(0, 0, 0, 255), font=font)
    y += 36
d.rectangle([10, 10, W - 10, H - 10], outline=(0, 0, 0, 255), width=3)

raw = img.tobytes()
expect = W * H * 4
print("[render] bytes=%d expect=%d" % (len(raw), expect))
assert len(raw) == expect, "RGBA 字节数不符（32bpp 设备必须 4 字节/像素）"

with open("render139.png", "wb") as f:
    img.save(f, "PNG")
render_sha = hashlib.sha256(raw).hexdigest()
print("[render] sha=%s" % render_sha[:12])

# 写屏
try:
    with open("/dev/fb0", "wb") as f:
        f.write(raw)
    print("[fb] write ok")
except Exception as e:
    print("[fb] write FAIL: %r" % e); sys.exit(1)

# 回采
try:
    with open("/dev/fb0", "rb") as f:
        cap = f.read(expect)
    print("[fb] read bytes=%d" % len(cap))
except Exception as e:
    print("[fb] read FAIL: %r" % e); sys.exit(1)

cap_sha = hashlib.sha256(cap).hexdigest()
print("[fb] cap sha=%s  identical=%s" % (cap_sha[:12], cap_sha == render_sha))

cap_img = Image.frombytes("RGBA", (W, H), cap)
cap_img.save("captured.png")

# 像素级比对
import itertools
diff = sum(1 for a, b in zip(raw[::997], cap[::997]) if a != b)
tot = len(raw[::997])
print("[cmp] sampled=%d diff=%d  ratio=%.6f" % (tot, diff, diff / tot))

# OCR
TOKEN = "K7X2M9"
probes = ["0.0000", "1.0000", "0.3200", "0.926580", "120", "56", "64", "-0.730"]
ocr_ok = 0
try:
    subprocess.run(["tesseract", "captured.png", "ocr139",
                    "-l", "eng", "--psm", "6"],
                   capture_output=True, timeout=120)
    txt = open("ocr139.txt", errors="ignore").read()
    print("[ocr] chars=%d" % len(txt))
    hit = TOKEN in txt.replace(" ", "")
    print("[ocr] TOKEN %s -> %s" % (TOKEN, "HIT" if hit else "MISS"))
    for p in probes:
        ok = p in txt
        ocr_ok += ok
        print("  probe %-10s %s" % (p, "ok" if ok else "MISS"))
except Exception as e:
    print("[ocr] unavailable: %r" % e)

print("[summary] ocr probes %d/%d" % (ocr_ok, len(probes)))
