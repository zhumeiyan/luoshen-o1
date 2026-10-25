"""exp138 — render three-way split, write to /dev/fb0, read back, OCR."""
import os, hashlib
from PIL import Image, ImageDraw, ImageFont

FB = "/dev/fb0"
OUT = "/data/workspace/luoshen-o1/experiments/exp138_trisplit"

def geom():
    vs = open("/sys/class/graphics/fb0/virtual_size").read().strip()
    w, h = (int(x) for x in vs.split(","))
    bpp = int(open("/sys/class/graphics/fb0/bits_per_pixel").read().strip())
    return w, h, bpp

W, H, BPP = geom()
TOKEN = "T4K7RN"          # no O/0, no 1/I, no 8/B, no 5/S
PROBES = ["4/4", "2/6", "4/6", "0.938", "0.034", "0.000",
          "1.000", "0.08194", "0.10368", "3/5", "15", "13"]

img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
try:
    f_t = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 30)
    f_b = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 21)
    f_s = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 17)
except Exception:
    f_t = f_b = f_s = ImageFont.load_default()

y = 16
d.text((36, y), "exp138  three-way split: computer / agent / silicon life",
       font=f_t, fill=(0, 0, 0)); y += 46
d.text((36, y), "TOKEN " + TOKEN, font=f_b, fill=(0, 0, 0)); y += 42

rows = [
    ("L1 computer / AI", "13 readings", "precision 0.938 / 0.034"),
    ("L2 Agent", "13 readings", "closed 1.000 vs open 0.000"),
    ("L3 silicon life", "15 readings", "fg 0.000, wean 0/12"),
    ("separator", "", ""),
    ("H1 cross-layer flip", "4/4", "same number, opposite verdict"),
    ("H1b control: not flipped", "4/6", "framework is falsifiable"),
    ("H1b control: flipped", "2/6", "PASS"),
    ("H2 layer mismatch", "3/5", "my 'failed' calls were mis-gauged"),
    ("separator", "", ""),
    ("syntax layer precision", "0.938", "L1 verdict: ship"),
    ("methodology layer", "0.034", "L1 verdict: kill"),
    ("infusion survival", "1.000", "L1: perfect / L3: mirror state"),
    ("self-feeding fg", "0.000", "L1: scrap / L3: feeds on negentropy"),
    ("contingent practice fg", "0.10368", "vs non-contingent 0.00149"),
    ("hippocampus knockout dev", "0.08194", "rank 1 of 31 systems"),
    ("separator", "", ""),
    ("VERDICT", "3 datasets, 3 rulers", "do not mix the rulers"),
]

for a, b, c in rows:
    if a == "separator":
        y += 10
        continue
    d.text((36, y), a, font=f_s, fill=(0, 0, 0))
    d.text((330, y), b, font=f_s, fill=(0, 0, 0))
    d.text((520, y), c, font=f_s, fill=(110, 110, 110))
    y += 25

img.save(os.path.join(OUT, "render138.png"))

# ---- write to real framebuffer (RGBA, 4 bytes per pixel) ----
rgba = img.convert("RGBA").tobytes()
with open(FB, "wb") as f:
    f.write(rgba)
print(f"[fb] wrote {len(rgba)} bytes -> {FB} ({W}x{H}x{BPP})")
print(f"[sha] render {hashlib.sha256(rgba).hexdigest()[:16]}")

# ---- read back ----
with open(FB, "rb") as f:
    cap = f.read(len(rgba))
print(f"[fb] read  {len(cap)} bytes")
print(f"[sha] capture {hashlib.sha256(cap).hexdigest()[:16]}")
print(f"[cmp] identical = {cap == rgba}")

# save capture as png for OCR
Image.frombytes("RGBA", (W, H), cap).convert("RGB").save(
    os.path.join(OUT, "captured.png"))
print("[ok] captured.png saved")
