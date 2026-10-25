"""上屏自检：写 /dev/fb0 -> 同进程立即回采 -> 逐位比对 -> OCR 独立读出"""
import os, subprocess, hashlib, json, sys

FB = "/dev/fb0"
W, H, BPP = 1024, 768, 4
SIZE = W * H * BPP
TOKEN = "K7M4QX"

LINES = [
    "EXP171  LEI-PAIN  SELFTEST",
    "",
    "CHANNEL  SELECT   (consequence x10)",
    "  load1   1.36-1.39   BLIND",
    "  ctxt    61660-80589 BLIND",
    "  nivcsw  sat at 5    SATURATED",
    "  dwait   0-76.5 ms   OK = LATENCY",
    "",
    "DEBT  354.18 ms  cum, no rollback",
    "LAT   19.47 -> 7.60 ms  recovered",
    "",
    "HABITUATION (2 reps, identical)",
    "  A hurtful  FIX 1.00  ADAPT 0.33",
    "  B harmless FIX 1.00  ADAPT 0.00",
    "",
    "NEGATIVE: mem dead, io weak",
    f"TOKEN {TOKEN}",
]

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

if HAVE_PIL:
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    fp = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
    if not os.path.exists(fp):
        cands = subprocess.run("fc-list | grep -i -E 'wqy|micro|hei' | head -5",
                               shell=True, capture_output=True, text=True).stdout
        for c in cands.split("\n"):
            if c.strip():
                fp = c.split(":")[0].strip()
                break
    try:
        f = ImageFont.truetype(fp, 26)
    except Exception:
        f = ImageFont.load_default()
    y = 40
    for ln in LINES:
        d.text((40, y), ln, fill=(0, 0, 0), font=f)
        y += 38
    # rgba -> bgra
    raw = bytearray(img.convert("RGBA").tobytes())
    raw[0::4], raw[2::4] = raw[2::4][:], raw[0::4][:]
    raw[0::4] = bytearray(raw[0::4])
    bgra = bytearray()
    px = img.convert("RGBA").tobytes()
    for i in range(0, len(px), 4):
        r, g, b, a = px[i], px[i+1], px[i+2], px[i+3]
        bgra += bytes((b, g, r, 255))
    payload = bytes(bgra)
else:
    payload = b"\xff" * SIZE

assert len(payload) == SIZE, (len(payload), SIZE)

# 关光标
try:
    open("/sys/class/graphics/fbcon/cursor_blink", "w").write("0")
except Exception:
    pass
try:
    open("/dev/tty1", "w").write("\033[?25l")
except Exception:
    pass

with open(FB, "wb") as f:
    f.write(payload)
    os.fsync(f.fileno())

with open(FB, "rb") as f:
    back = f.read(SIZE)

ident = (back == payload)
diff = sum(1 for i in range(0, SIZE, 997) if back[i] != payload[i])
sha = hashlib.sha256(back).hexdigest()[:12]

# OCR
os.makedirs("/data/workspace/luoshen-o1/experiments/exp171_pain", exist_ok=True)
png = "/data/workspace/luoshen-o1/experiments/exp171_pain/captured.png"
if HAVE_PIL:
    img2 = Image.new("RGB", (W, H))
    px2 = bytearray()
    for i in range(0, SIZE, 4):
        b, g, r, a = back[i], back[i+1], back[i+2], back[i+3]
        px2 += bytes((r, g, b))
    img2.frombytes(bytes(px2))
    img2.save(png)

ocr = ""
try:
    r = subprocess.run(["tesseract", png, "stdout", "-l", "chi_sim+eng",
                        "--psm", "6"], capture_output=True, text=True, timeout=120)
    ocr = r.stdout
except Exception as e:
    ocr = f"OCR_FAIL {e}"

hit = TOKEN in ocr.replace(" ", "").replace("\n", "")
res = {"identical": ident, "diff_sample": diff, "sha": sha,
       "bytes": SIZE, "token_hit": hit, "ocr": ocr}
print(json.dumps({k: v for k, v in res.items() if k != "ocr"}, indent=1))
print("--- OCR ---")
print(ocr[:1500])
json.dump(res, open("/data/workspace/luoshen-o1/experiments/exp171_pain/selfcheck.json", "w"))
