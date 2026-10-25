#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染 144 结果 -> 写 /dev/fb0 -> 回采比对 -> OCR"""
import os, json, hashlib, random
OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 1024, 768


def load_font(sz):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    from PIL import Image, ImageDraw
    dose = json.load(open(os.path.join(OUT, "result_144.json")))
    shape = json.load(open(os.path.join(OUT, "result_144_shape.json")))
    real = json.load(open(os.path.join(OUT, "result_144_real.json")))

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    ft = load_font(30); fs = load_font(21); fb = load_font(23)
    y = 22

    def line(t, f=None, pad=26):
        nonlocal y
        d.text((38, y), t, fill="black", font=f or fs); y += pad

    d.text((38, y), "144 TIME: ORDER ASSET OR LIABILITY", fill="black", font=ft); y += 44
    line("d_order = shuffled - lived  (>0 = keeping time order is an ASSET)", fs); y += 4

    line("== DOSE: does order effect grow with world drift? ==", fb); y += 2
    for r in dose["dose"]:
        m, lo, hi = r["d_order"]["mean"], *r["d_order"]["ci"]
        line("drift %.1f  d_order %+.4f  [%+.4f,%+.4f]" % (r["drift_scale"], m, lo, hi))
    line("monotone in drift: %s" % dose["verdict"]["monotone"], fs); y += 5

    line("== SHAPE OF WORLD TIME-STRUCTURE ==", fb); y += 2
    for sh in ["stationary", "monotone", "sine", "square"]:
        r = shape["shapes"][sh]
        m, lo, hi = r["d_order"]["mean"], *r["d_order"]["ci"]
        line("%-10s d_order %+.4f [%+.4f,%+.4f]  %s" % (sh, m, lo, hi, r["sign"]))
    line("square world: order is a LIABILITY", fs); y += 5

    line("== REAL ARM: real CPU load square-wave jitter ==", fb); y += 2
    line("real d_order %+.6f  [%+.6f,%+.6f]" % (
        real["arms"]["d_order"]["mean"], *real["arms"]["d_order"]["ci"]))
    line("sim  square  %+.4f  -> reproduced %s" % (
        shape["shapes"]["square"]["d_order"]["mean"],
        shape["real_cross_check"]["reproduced"]), fs); y += 5

    line("== VALUE OF FORGETTING depends on world shape ==", fb); y += 2
    for w in ["stationary", "drift", "cyclic"]:
        r = dose["worlds"][w]
        line("%-10s lived %.4f batch %.4f recent %.4f" % (
            w, r["lived"]["mean"], r["fed_batch"]["mean"], r["fed_recent"]["mean"]))
    line("stationary: remember ALL wins | cyclic: forgetting HURTS", fs); y += 4

    tok = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    d.text((38, y), "TOKEN " + tok, fill="black", font=ft)

    img.save(os.path.join(OUT, "render144.png"))
    raw = img.convert("RGBA").tobytes()
    sh = hashlib.sha256(raw).hexdigest()[:12]
    try:
        with open("/dev/fb0", "wb") as f:
            f.write(raw); f.flush()
        with open("/dev/fb0", "rb") as f:
            cap = f.read(len(raw))
        ok = (cap == raw)
    except Exception as ex:
        print("FB ERR", ex); ok = False; cap = b""
    print("WRITE", len(raw), "CAPTURE", len(cap), "IDENTICAL", ok)
    print("RENDER_SHA", sh); print("TOKEN", tok)
    open(os.path.join(OUT, "captured.png"), "wb").write(cap)
    json.dump(dict(sha=sh, token=tok, identical=bool(ok)),
              open(os.path.join(OUT, "screen.json"), "w"))


main()
