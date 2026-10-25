"""exp135 — render results, write to /dev/fb0, read back, OCR."""
import os, sys, time, hashlib, subprocess, json
from PIL import Image, ImageDraw, ImageFont

FB = "/dev/fb0"
OUT = "/data/workspace/luoshen-o1/experiments/exp129_corpus/exp135"

# framebuffer geometry read from sysfs (ioctl returns zeros on this box)
def geom():
    for p in ("/sys/class/graphics/fb0/virtual_size",
              "/sys/class/graphics/fb0/bits_per_pixel"):
        pass
    vs = open("/sys/class/graphics/fb0/virtual_size").read().strip()
    w, h = (int(x) for x in vs.split(","))
    bpp = int(open("/sys/class/graphics/fb0/bits_per_pixel").read().strip())
    return w, h, bpp

W, H, BPP = geom()
TOKEN = "M4K2P9"          # no O/0, no 1/I, no 8/B, no 5/S
PROBES = ["0.750", "18/20", "1/55", "0.900", "0.020", "9/12", "3/4", "0/26"]

img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
try:
    f_t = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 30)
    f_b = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 21)
    f_s = ImageFont.truetype(
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 17)
except Exception:
    f_t = f_b = f_s = ImageFont.load_default()

y = 16
d.text((36, y), "exp135  third independent corpus  (7 new repos, 12 files)",
       font=f_t, fill=(0, 0, 0)); y += 46
d.text((36, y), "TOKEN " + TOKEN, font=f_b, fill=(0, 0, 0)); y += 40

rows = [
    ("G3 syntax strict on corpus4", "3/4 = 0.750", "PASS (>=0.60), CI wide"),
    ("G4 methodology on corpus4", "0/26 = 0.000", "PASS (<=0.20)"),
    ("syntax pooled c3+c4", "18/20 = 0.900", "CI [0.699, 0.972]"),
    ("methodology pooled c3+c4", "1/55 = 0.018", "CI [0.003, 0.096]"),
    ("recall EG005 / EG006 / EGP01", "3/3  2/2  1/1", "PASS, needs --pro"),
    ("clean file findings", "0", "PASS"),
    ("rule crashes", "0", "PASS"),
    ("coverage c1 / c3 / c4", "0.024 / 0.031 / 0.020", "per KB"),
    ("silent on corpus4 files", "9/12", "the real limit"),
    ("EGP04 denominator", "0 hits", "stays experimental"),
    ("DECISION", "SHIP v0.5.0", "3 rules, 23 off"),
]
d.text((36, y), "gate                                  measured            note",
       font=f_s, fill=(90, 90, 90)); y += 26
for a, b, c in rows:
    d.text((36, y), a, font=f_s, fill=(0, 0, 0))
    d.text((430, y), b, font=f_s, fill=(0, 0, 0))
    d.text((640, y), c, font=f_s, fill=(110, 110, 110))
    y += 25

y += 10
d.text((36, y), "the gate was single-sided: 6 rounds gated on precision, never on coverage",
       font=f_b, fill=(160, 0, 0)); y += 32
d.text((36, y), "90% precise and silent on 9 of 12 professional files is also not a product",
       font=f_b, fill=(160, 0, 0)); y += 32
d.text((36, y), "shipped set: EG005 unguarded division  EG006 bare except  EGP01 silent handler",
       font=f_s, fill=(0, 0, 0))

img.save(OUT + "/render135.png")
raw = img.convert("RGBA").tobytes()
assert len(raw) == W * H * 4, (len(raw), W * H * 4)
with open(FB, "wb") as f:
    f.write(raw)
    f.flush()
    os.fsync(f.fileno())
time.sleep(0.4)

# read back from the real device
with open(FB, "rb") as f:
    cap = f.read(W * H * 4)
print("wrote", len(raw), "read", len(cap), "identical", raw == cap)
open(OUT + "/capture135.raw", "wb").write(cap)
Image.frombytes("RGBA", (W, H), cap).convert("RGB").save(OUT + "/captured.png")
json.dump({"token": TOKEN, "probes": PROBES, "w": W, "h": H, "bpp": BPP,
           "identical": raw == cap}, open(OUT + "/shot135.json", "w"), indent=1)
print("TOKEN", TOKEN)
print("probes", " ".join(PROBES))
