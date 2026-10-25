#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染 L7 结果 -> 写 /dev/fb0 -> 回采比对 -> OCR"""
import os, json, hashlib, subprocess, struct, fcntl
OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 1024, 768

def fb_info():
    for p in ("/sys/class/graphics/fb0/virtual_size",
              "/sys/class/graphics/fb0/bits_per_pixel"):
        try:
            with open(p) as f: yield f.read().strip()
        except Exception:
            yield None

def load_font(sz):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except Exception: pass
    return ImageFont.load_default()

def main():
    from PIL import Image, ImageDraw
    r7a = json.load(open(os.path.join(OUT, "result_l7v2.json")))
    r7  = json.load(open(os.path.join(OUT, "result_l7.json")))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    fh = load_font(26); fs = load_font(21); ft = load_font(30)
    y = 24
    def line(t, f=None, pad=34):
        nonlocal y
        d.text((40, y), t, fill="black", font=f or fs); y += pad
    d.text((40, y), "L7 RELATION RUNG", fill="black", font=ft); y += 46
    line("general=can cooperate | specific=fits MY history", fs); y += 8

    line("L7a old       gen %.4f  spec %.4f" % (
        r7a["l7a2"]["old"]["general"]["mean"], r7a["l7a2"]["old"]["specific"]["mean"]))
    line("L7a stranger  gen %.4f  spec %.4f" % (
        r7a["l7a2"]["stranger"]["general"]["mean"], r7a["l7a2"]["stranger"]["specific"]["mean"]))
    line("L7a clone     gen %.4f  spec %.4f" % (
        r7a["l7a2"]["clone"]["general"]["mean"], r7a["l7a2"]["clone"]["specific"]["mean"]))
    line("clone general matches old -> ability is FORGEABLE", fs); y += 6
    line("clone specific BELOW random -> history is NOT", fs); y += 14

    line("L7b old        match_B %.4f  match_truth %.4f" % (
        r7a["l7b2"]["old"]["match_B"]["mean"], r7a["l7b2"]["old"]["match_truth"]["mean"]))
    line("L7b clone      match_B %.4f  match_truth %.4f" % (
        r7a["l7b2"]["clone"]["match_B"]["mean"], r7a["l7b2"]["clone"]["match_truth"]["mean"]))
    line("L7b clone_fed  match_B %.4f  match_truth %.4f" % (
        r7a["l7b2"]["clone_fed"]["match_B"]["mean"], r7a["l7b2"]["clone_fed"]["match_truth"]["mean"]))
    line("forgery WINS match_B 0.8115 > 0.6958", fs); y += 6
    line("but match_truth 1.0000 perfect = FORGED", fs); y += 14

    line("L7c debt ledger %.4f  no_ledger %.4f" % (
        r7["l7c"]["ledger"]["mean"], r7["l7c"]["no_ledger"]["mean"]), fs)
    line("L7d lived %.4f  fed %.4f  delta %+.4f CI[%+.4f,%+.4f]" % (
        r7["l7d"]["lived"]["mean"], r7["l7d"]["fed"]["mean"],
        r7["l7d"]["delta"]["mean"], r7["l7d"]["delta"]["lo"], r7["l7d"]["delta"]["hi"]), fs)
    line("L7d time NOT better than data (CI crosses 0)", fs); y += 10
    line("REAL udp loss %.4f  observed %.4f" % (
        r7a["real_loss"]["loss"], r7a["real_loss"]["observed"]), fs)
    line("modeled P_LOSS 0.20 -> modeled channel was PESSIMISTIC", fs); y += 10

    import random, string
    tok = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    d.text((40, y), "TOKEN " + tok, fill="black", font=ft)

    img.save(os.path.join(OUT, "render_l7.png"))
    rgba = img.convert("RGBA")
    raw = rgba.tobytes()
    sh = hashlib.sha256(raw).hexdigest()[:12]
    try:
        with open("/dev/fb0", "wb") as f:
            f.write(raw); f.flush()
        with open("/dev/fb0", "rb") as f:
            cap = f.read(len(raw))
        ok = (cap == raw)
        print("WRITE bytes", len(raw), "CAPTURE bytes", len(cap), "IDENTICAL", ok)
    except Exception as ex:
        print("FB ERR", ex); ok = False; cap = b""
    print("RENDER_SHA", sh)
    print("TOKEN", tok)
    open(os.path.join(OUT, "captured_l7.png"), "wb").write(cap)
    json.dump(dict(sha=sh, token=tok, identical=bool(ok)),
              open(os.path.join(OUT, "l7_screen.json"), "w"))

main()
