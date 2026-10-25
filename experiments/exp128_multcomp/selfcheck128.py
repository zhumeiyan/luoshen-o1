# -*- coding: utf-8 -*-
"""128 上屏自检：渲染 → 写 /dev/fb0(1024x768 RGBA, ioctl实测) → 真实采集 → OCR 回读"""
import os, json, random, hashlib
from PIL import Image, ImageDraw, ImageFont
import numpy as np, cv2, pytesseract

OUT = "/data/workspace/luoshen-o1/experiments/exp128_multcomp"
os.chdir(OUT)
raw_d = json.load(open("claims_raw.json", encoding="utf-8"))
gated = json.load(open("claim_log_gated.json", encoding="utf-8"))

n_all = 110
n_no_ci = sum(1 for u in raw_d["unparsed_reports"] if u["reason"] == "no_parsable_CI")
n_claim = len(raw_d["claims"])
nom = sum(1 for c in raw_d["claims"] if c["ci_excludes_zero"])
bh = sum(1 for c in raw_d["claims"] if c.get("reject_bh", False))
bonf = sum(1 for c in raw_d["claims"] if c.get("reject_bonf", False))
npass = sum(1 for c in gated if c["PASS"])
nbh2 = sum(1 for c in gated if c["reject_bh"])
nnom2 = sum(1 for c in gated if c.get("ci_lo") is not None and (c["ci_lo"] > 0 or c["ci_hi"] < 0))

# 校验码只用无易混淆字符（082 起 O/0、I/1 反复撞）
tok = "".join(random.choices("346789", k=6))

rows = [
    ("TRACK GAP", "reports 110  no CI %d  claims %d" % (n_no_ci, n_claim)),
    ("RETRO FDR", "nominal %d  bh %d  bonf %d" % (nom, bh, bonf)),
    ("RETRO GATE", "three gate pass 0 of %d" % n_claim),
    ("FWD LOG", "claims %d  nominal %d  bh %d" % (len(gated), nnom2, nbh2)),
    ("FWD GATE", "three gate pass %d of %d" % (npass, len(gated))),
    ("G1 CATCH", "116 delta 9.8e-09 blocked"),
    ("G1 PASS",  "112 delta 0.1535 allowed"),
    ("G4 CLOSED", "burn 0 fg 0.16410  burn 100 0.10368"),
    ("G4 OPEN",  "burn 0 fg 0.00791  burn 100 0.00091"),
    ("G4 KEEP",  "closed 0.632  open 0.115"),
    ("TOKEN", tok),
]

W, H = 1024, 768
img = Image.new("RGB", (W, H), (255, 255, 255))
dr = ImageDraw.Draw(img)
F = None
for p in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    if os.path.exists(p):
        try:
            F = ImageFont.truetype(p, 24)
            break
        except Exception:
            pass
if F is None:
    F = ImageFont.load_default()
y = 24
for k, v in rows:
    dr.text((26, y), "%-11s %s" % (k, v), fill=(0, 0, 0), font=F)
    y += 52
dr.text((26, y + 10), "128 MULTIPLE COMPARISON SELF CHECK", fill=(0, 0, 0), font=F)
img.save(OUT + "/render.png")

rgba = img.convert("RGBA").resize((1024, 768))
b = rgba.tobytes()
open("/dev/fb0", "wb").write(b)
print("written :", len(b))
raw = open("/dev/fb0", "rb").read()
print("captured:", len(raw))
arr = np.frombuffer(raw, dtype=np.uint8).reshape(768, 1024, 4)
Image.fromarray(arr[:, :, :3], "RGB").save(OUT + "/captured.png")
print("render sha ", hashlib.sha256(open(OUT + "/render.png", "rb").read()).hexdigest()[:12],
      " capture sha", hashlib.sha256(open(OUT + "/captured.png", "rb").read()).hexdigest()[:12])

g = cv2.cvtColor(cv2.resize(cv2.imread(OUT + "/captured.png"), None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2GRAY)
txt = pytesseract.image_to_string(g, config="--psm 6")
open(OUT + "/ocr.txt", "w").write(txt)
clean = txt.replace(" ", "").upper()
loose = (clean.replace("O", "0").replace("I", "1").replace("L", "1")
              .replace("S", "5").replace("B", "8").replace("Z", "2"))
print("=== OCR ===")
print(txt.strip()[:900])

probes = ["110", "101", "14", "0", "22", "17", "9.8e-09", "0.1535",
          "0.16410", "0.10368", "0.00791", "0.00091", "0.632", "0.115"]
hit = 0
for p in probes:
    k = p.replace(" ", "").upper()
    ok = (k in clean) or (k in loose)
    hit += bool(ok)
    print("  probe %-10s -> %s" % (p, ok))
tk = tok in clean or tok in loose
print("\nTOKEN=%s hit=%s" % (tok, tk))
print("probes hit %d/%d" % (hit, len(probes)))
json.dump(dict(token=tok, token_hit=tk, hits=hit, n=len(probes),
               written=len(b), captured=len(raw)),
          open(OUT + "/selfcheck128.json", "w"), indent=1)
