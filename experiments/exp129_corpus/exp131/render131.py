"""exp131 self-check: render results, write to /dev/fb0, read back, OCR.

Two independent probes of the device geometry:
  ioctl FBIOGET_VSCREENINFO -> returns all zeros on this sandbox (unimplemented)
  /sys/class/graphics/fb0/{virtual_size,bits_per_pixel} -> 1024x768, 32
exp127 wrote 1920x1080 from memory and got OSError before measuring. Measure
first, and when two probes disagree record which one is dead.
"""
import pathlib, subprocess, hashlib

W, H, BPP = 1024, 768, 32          # from sysfs, see docstring
BYTES = W * H * BPP // 8

TOKEN = "K3N7QW"
ROWS = [
    "EO EXP131 EVALGUARD STATEMENT-LEVEL",
    "",
    f"TOKEN {TOKEN}",
    "",
    "REAL CORPUS 27 FILES, 17 FINDINGS",
    "  STRICT  1/17 =  5.9 PCT",
    "  LOOSE  10/17 = 58.8 PCT",
    "  GATE 60 PCT -> NEITHER PASSES",
    "",
    "AFTER G-ROLE (DEMO FILES DEMOTED)",
    "  ACTIONABLE 17 -> 15",
    "  STRICT  1/15 =  6.7 PCT",
    "  LOOSE  10/15 = 66.7 PCT",
    "  GATE USES STRICT -> FAIL",
    "",
    "SEPARATORS",
    "  ANCHOR CORRECT  6/17 = 35.3 PCT",
    "  ANCHOR-CORRECT PRECISION 5/6 = 83.3 PCT",
    "  ANCHOR-WRONG   PRECISION 5/11 = 45.5 PCT",
    "  DEMO FILES  0/2 TRUE, BOTH STANDARDS",
    "",
    "RECALL HELD  12/12 AND 14/14",
    "RULE CRASHES 0",
    "VERDICT DO NOT SHIP",
]

from PIL import Image, ImageDraw, ImageFont
# exp106/exp130: dark-on-light at a real font size is what OCR can actually
# read. Tiny default bitmaps on a dark ground produce confident garbage.
FONT = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
FONTB = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 22)
img = Image.new("RGBA", (W, H), (252, 252, 250, 255))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W - 1, 44], fill=(20, 45, 90, 255))
y = 10
d.text((14, y), "evalguard v0.4  /  exp131  /  NOT FOR SALE",
       font=FONTB, fill=(255, 255, 255, 255))
y = 62
for r in ROWS:
    if r:
        col = (0, 90, 190, 255) if r.startswith("TOKEN") else \
              (190, 20, 20, 255) if "FAIL" in r or "DO NOT" in r else \
              (10, 110, 30, 255) if ("PCT" in r or "/1" in r) else \
              (25, 25, 30, 255)
        d.text((16, y), r, font=FONTB if r.isupper() else FONT, fill=col)
    y += 30

D = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp131")
img.save(D / "render131.png")
raw = img.tobytes()
assert len(raw) == BYTES, (len(raw), BYTES)

with open("/dev/fb0", "r+b") as fb:
    fb.seek(0)
    fb.write(raw)

with open("/dev/fb0", "rb") as fb:
    back = fb.read(BYTES)
print(f"wrote {len(raw)}  read back {len(back)}  identical={raw == back}")
print("render sha", hashlib.sha256(raw).hexdigest()[:12],
      "capture sha", hashlib.sha256(back).hexdigest()[:12])

Image.frombytes("RGBA", (W, H), back).save(D / "captured.png")
(D / "token.txt").write_text(TOKEN)

# probe: the numbers must survive the round trip as pixels, not as variables
dark = sum(1 for i in range(0, BYTES, 4) if back[i] < 40)
print(f"dark-pixel fraction {dark/(BYTES//4):.4f}")
