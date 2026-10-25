import pathlib, struct, subprocess
W,H = 1024,768
def dims():
    try:
        v = pathlib.Path("/sys/class/graphics/fb0/virtual_size").read_text().split(",")
        return int(v[0]), int(v[1])
    except Exception:
        return W,H
W,H = dims()
from PIL import Image, ImageDraw, ImageFont
fp = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
try: f = ImageFont.truetype(fp, 26)
except Exception: f = ImageFont.load_default()
f2 = ImageFont.truetype(fp, 19) if True else f
img = Image.new("RGB", (W,H), "white")
d = ImageDraw.Draw(img)
lines = [
 "TOKEN 6K4QX7",
 "exp133 anchor spec audit",
 "anchor proof 22 of 24 = 91.7 pct",
 "strict precision all 10 of 24 = 41.7",
 "present 10 of 15 = 66.7  gate 60",
 "absent 0 of 9 = 0.0 structural",
 "EG011 pinned to continue 3 of 3",
 "metrics substring bug 12 to 2",
 "recall planted 12 of 12 pro 14 of 14",
 "saturated keys EG006 EGP08",
 "VERDICT DO NOT SHIP SPLIT NOT PREREGISTERED",
]
y = 60
for i,t in enumerate(lines):
    d.text((60,y), t, fill="black", font=f if i<2 else f2)
    y += 52
img.save("render133.png")
raw = img.convert("RGBA").tobytes()
pathlib.Path("/dev/fb0").write_bytes(raw)
cap = pathlib.Path("/dev/fb0").read_bytes()[:len(raw)]
print("wrote", len(raw), "read", len(cap), "equal:", raw==cap)
