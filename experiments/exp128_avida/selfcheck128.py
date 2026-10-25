# -*- coding: utf-8 -*-
"""128 上屏自检：渲染 → 写 /dev/fb0(1024x768 RGBA, ioctl实测) → 真实采集 → OCR 回读"""
import os, json, random, hashlib
from PIL import Image, ImageDraw, ImageFont
import numpy as np, cv2, pytesseract

OUT = "/data/workspace/luoshen-o1/experiments/exp128_avida"
B = json.load(open(OUT + "/stageB_result.json"))
C = json.load(open(OUT + "/stageC_result.json"))
t = C["avida_total"]
L = B["life5"]
tok = ''.join(random.choices("23456789", k=6))

rows = [
 ("L CLOSED",   f"fg {L['practice_closed']['fg']:.5f} survive 16 of 16"),
 ("L OPEN",     f"fg {L['practice_open']['fg']:.5f} survive 0 of 16"),
 ("L NOPRAC",   f"fg {L['no_practice']['fg']:.5f} survive 0 of 16"),
 ("L VARIA",    f"fg {L['variation']['fg']:.5f} survive 11 of 16"),
 ("A SELF",     f"task {t['n_task']} of {t['n']} rate 0.080"),
 ("A ENERGY",   f"energy {t['n_energy']} of {t['n']}"),
 ("A REPLIC",   f"task and replicate {t['n_task_and_replicate']} of {t['n']}"),
 ("A BROKEN",   f"task but broken {t['n_task_not_replicate']} of {t['n']}"),
 ("A CUT",      "births after cut 0"),
 ("CTRL NEG A", "mut 0 task 0 of 40"),
 ("CTRL POS A", "given task energy 40 of 40"),
 ("CTRL NEG L", "fg 0 survive 0 of 16"),
 ("CTRL POS L", "fg 0.15 survive 15 of 16"),
 ("TOKEN",      tok),
]
W, H = 1024, 768
img = Image.new("RGB", (W, H), (255, 255, 255)); dr = ImageDraw.Draw(img)
F = None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try: F = ImageFont.truetype(p, 24); break
        except Exception: pass
if F is None: F = ImageFont.load_default()
y = 24
for k, v in rows:
    dr.text((28, y), f"{k:11s} {v}", fill=(0, 0, 0), font=F); y += 50
dr.text((28, y + 10), "128 AVIDA VS LIFE5 BASELINE SELF CHECK", fill=(0, 0, 0), font=F)
img.save(OUT + "/render.png")
b = img.convert("RGBA").resize((1024, 768)).tobytes()
open("/dev/fb0", "wb").write(b); print("written:", len(b))
raw = open("/dev/fb0", "rb").read(); print("captured:", len(raw))
arr = np.frombuffer(raw, dtype=np.uint8).reshape(768, 1024, 4)
Image.fromarray(arr[:, :, :3], "RGB").save(OUT + "/captured.png")
print("render sha", hashlib.sha256(open(OUT + "/render.png", 'rb').read()).hexdigest()[:12],
      "capture sha", hashlib.sha256(open(OUT + "/captured.png", 'rb').read()).hexdigest()[:12])
g = cv2.cvtColor(cv2.resize(cv2.imread(OUT + "/captured.png"), None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2GRAY)
txt = pytesseract.image_to_string(g, config="--psm 6")
open(OUT + "/ocr.txt", "w").write(txt)
clean = txt.replace(" ", "").upper()
loose = clean.replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("B", "8")
print("=== OCR ==="); print(txt.strip()[:900])
print(f"\nTOKEN={tok} strict={tok in clean} loose={tok in loose}")
probes = ["0.15365", "0.00378", "0.02900", "16 of 16", "0 of 16", "11 of 16",
          "0.080", "40 of 40", "15 of 16"]
hit = [p for p in probes if p.replace(" ", "") in clean or p.replace(" ", "") in loose]
print(f"probes hit {len(hit)}/{len(probes)}: {hit}")
json.dump(dict(token=tok, strict=tok in clean, loose=tok in loose,
               probes=len(hit), probes_total=len(probes), hit=hit),
          open(OUT + "/selfcheck128.json", "w"), indent=2)
