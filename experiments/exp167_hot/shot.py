import numpy as np, hashlib
from PIL import Image, ImageDraw, ImageFont
W, H, STRIDE = 1024, 768, 4096
FB = '/dev/fb0'
FONT = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
img = Image.new('RGB', (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
fT = ImageFont.truetype(FONT, 40)
f1 = ImageFont.truetype(FONT, 32)
f2 = ImageFont.truetype(FONT, 28)

rows = [
    ("167 PACKAGE vs DIMENSION TURN", fT, (0, 0, 0)),
    ("TRUE n=180 fork+SIGKILL+proc", f1, (0, 0, 0)),
    ("SRC cpu0 1.025 -> cpu3 3.259", f1, (0, 0, 180)),
    ("A CONSEQ  d1 .239 -> d26 .328", f1, (0, 120, 0)),
    ("   high marginal ~ 0  CONVERGE", f2, (0, 120, 0)),
    ("B PHYScpu d1 .262 -> d26 .394", f1, (180, 0, 0)),
    ("   high marginal +.046 DIVERGE", f2, (180, 0, 0)),
    ("C PHYSio  d1 .323 -> d26 .528", f1, (180, 0, 0)),
    ("   high marginal +.054 DIVERGE", f2, (180, 0, 0)),
    ("K SCAN k<=8 |marg|<=.008", f1, (0, 0, 0)),
    ("       k>=10 marg > 0", f1, (0, 0, 0)),
    ("NEG focus_k noise +-0.019 no cut", f2, (120, 120, 120)),
    ("TOKEN K7M4QX", fT, (0, 0, 0)),
]
y = 34
for t, fo, c in rows:
    d.text((44, y), t, font=fo, fill=c)
    y += 74 if fo is fT else 50

rgb = np.asarray(img, dtype=np.uint8)
row = np.zeros((H, STRIDE), dtype=np.uint8)
row[:, :W * 3] = rgb[:, :, ::-1].reshape(H, W * 3)
data = row.tobytes()
open(FB, 'wb').write(data)
back = open(FB, 'rb').read(STRIDE * H)
print("IDENTICAL:", back == data, "sha:", hashlib.sha256(back).hexdigest()[:12])
arr = np.frombuffer(back, dtype=np.uint8).reshape(H, STRIDE)
Image.fromarray(arr[:, :W * 3].reshape(H, W, 3)[:, :, ::-1]).save('captured.png')
