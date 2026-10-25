#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""145 渲染 -> 写 /dev/fb0 -> 回采比对 -> OCR"""
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
    v1 = json.load(open(os.path.join(OUT, "result_145.json")))
    b = json.load(open(os.path.join(OUT, "result_145b.json")))
    real = json.load(open(os.path.join(OUT, "result_145_real.json")))
    sup = json.load(open(os.path.join(OUT, "result_145_sup.json")))

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    ft = load_font(29); fs = load_font(20); fb = load_font(22)
    y = 20

    def line(t, f=None, pad=25):
        nonlocal y
        d.text((34, y), t, fill="black", font=f or fs); y += pad

    d.text((34, y), "145 ONLINE SHAPE JUDGE: DETECT THEN ADAPT", fill="black", font=ft)
    y += 41

    line("== V1 FAILED: judged the WRONG quantity ==", fb)
    line("judge trend of Y -> drift detected only %.3f (monotone)" %
         v1["worlds"]["monotone"]["ADAPTIVE"]["drift_rate"])
    line("Y std 2.24 comes from random X, w-drift invisible in Y: t=0.14", fs)
    line("no threshold fixes this; V1 abandoned, reported as-is", fs)
    y += 3

    line("== V3 EXPERT: pick ALL or RECENT by recent loss ==", fb)
    for w, tag in [("stationary", "stat"), ("monotone", "mono"),
                   ("sine", "sine"), ("square", "sqr")]:
        r = b["worlds"][w]
        line("%-5s ALL %.3f  RECENT %.3f  V3 %.3f  pick_R %.2f" % (
            tag, r["ALL"]["err"], r["RECENT"]["err"],
            r["V3_EXPERT"]["err"], r["V3_EXPERT"]["recent_rate"]))
    line("V3 beats BOTH fixed policies on sine and square", fs)
    line("V2 residual-trend also failed (pick_R 0.02-0.11)", fs)
    y += 3

    line("== GATES ==", fb)
    line("G1 selectivity %s (stat %.2f -> mono %.2f)" % (
        b["verdict"]["G1_selectivity"], b["verdict"]["rate_stationary"],
        b["verdict"]["rate_monotone"]))
    line("G2 V3 not worse than best fixed: %s" % b["verdict"]["G2"])
    line("G3 random-pick worse %+.4f [%+.4f,%+.4f]  %s" % (
        b["verdict"]["G3_diff"], b["verdict"]["G3_ci"][0],
        b["verdict"]["G3_ci"][1], b["verdict"]["G3"]))
    line("shape switch: mono-half %.2f -> sqr-half %.2f (tracks)" % (
        b["switch"]["first_half_rate"][0], b["switch"]["second_half_rate"][0]))
    y += 3

    line("== REAL ARM: real CPU jitter ==", fb)
    line("sustain pick_R %.2f | cycle pick_R %.2f  distinct=%s" % (
        real["verdict"]["sustain_rate"], real["verdict"]["cycle_rate"],
        real["verdict"]["distinct"]))
    line("sustain: RECENT wins | cycle: ALL wins  (matches 144 sim)", fs)
    line("but all learners LOSE to identity baseline on cycle: %s" %
         sup["cycle"]["3"]["best_beats_ident"])
    line("sustain beats identity: %s" % sup["sustain"]["3"]["best_beats_ident"])
    y += 3

    line("CAVEAT: real arm n=1 trace; 6 reps are pseudo-replication", fs)
    line("absolute values swing between collections; only the", fs)
    line("RELATIVE policy ordering reproduced twice", fs)

    tok = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    d.text((34, y), "TOKEN " + tok, fill="black", font=ft)

    img.save(os.path.join(OUT, "render145.png"))
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
    # 帧缓冲回采的是原始 RGBA 字节, 不是 PNG; 必须按尺寸重建才能给 OCR 与肉眼读
    capimg = Image.frombytes("RGBA", (W, H), cap)
    capimg.save(os.path.join(OUT, "captured.png"))
    cap_sha = hashlib.sha256(cap).hexdigest()[:12]
    print("CAPTURE_SHA", cap_sha, "MATCH", cap_sha == sh)
    json.dump(dict(sha=sh, cap_sha=cap_sha, token=tok, identical=bool(ok)),
              open(os.path.join(OUT, "screen.json"), "w"))


main()
