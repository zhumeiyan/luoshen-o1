import os, json, hashlib
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 768
F = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
def f(sz): return ImageFont.truetype(F, sz)

img = Image.new("RGB", (W, H), (8, 10, 14))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W-1, H-1], outline=(60, 200, 160), width=3)

TITLE = "151  SIX-RUNG INTEGRATION  FIRST JOINT RUN"
d.text((26, 16), TITLE, font=f(27), fill=(80, 230, 180))
d.line([26, 54, W-26, 54], fill=(60, 140, 120), width=2)

R = json.load(open("result151.json"))
c = R["cond"]
base = c["L1"]["mean"]

lines = []
lines.append("G0 STRUCTURE   ORACLE 73.0  RANDOM 15.4  CONST 0.0  -> task has structure")
lines.append("")
lines.append("SINGLE-RUNG GAIN (over L1 baseline %.1f)" % base)
for k in ["L1+L2","L1+L3","L1+L4g","L1+L4d","L1+L4p","L1+L6m","L1+L6a","L1+L6d","L1+L6c"]:
    v = c[k]
    lines.append("  %-9s %6.2f  d=%+6.2f  CI[%5.2f,%5.2f]" % (k, v["mean"], v["mean"]-base, v["lo"], v["hi"]))
lines.append("")
lines.append("ABLATION (from FULL_noL5 %.1f)" % c["FULL_noL5"]["mean"])
for k in ["ABL_-L1","ABL_-L2","ABL_-L3","ABL_-L4d","ABL_-L4p","ABL_-L6a","ABL_-L6c"]:
    v = c[k]
    lines.append("  %-9s %6.2f  d=%+6.2f  CI[%5.2f,%5.2f]" % (k, v["mean"], v["mean"]-c["FULL_noL5"]["mean"], v["lo"], v["hi"]))
lines.append("")
lines.append("KEY  culture L6c is the ONLY large gain  +29.3   ablation -37.3")
lines.append("     it accumulates across generations   first 62.0 -> late 70.5")
lines.append("     stale culture still helps 24.7->37.7 and self-corrects 38.6->58.6")
lines.append("     harmful here: L6a -17.5   L4p -13.2   L4d -4.4   L3 -6.4")
lines.append("")
lines.append("TOKEN K7M4QX   nodes 500 targets 75 deg 10.8 T 150 rep 16")

y = 66
for i, ln in enumerate(lines):
    col = (225, 235, 240)
    if ln.startswith("KEY"): col = (120, 230, 255)
    elif ln.startswith("G0"): col = (150, 255, 190)
    elif "culture L6c" in ln: col = (255, 210, 120)
    d.text((26, y), ln, font=f(19 if i < 3 else 17), fill=col)
    y += 27 if i < 3 else 25

img.save("render151.png")
raw = img.tobytes()
fd = os.open("/dev/fb0", os.O_RDWR)
os.lseek(fd, 0, 0); os.write(fd, raw)
os.lseek(fd, 0, 0); back = os.read(fd, len(raw))
os.close(fd)
open("captured.bin","wb").write(back)
print("render_sha", hashlib.sha256(raw).hexdigest()[:12])
print("capture_sha", hashlib.sha256(back).hexdigest()[:12])
print("IDENTICAL", raw == back)
