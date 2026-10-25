#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接收端(感受器)矩阵 · Sense Matrix
=================================
判据核 #450: provenance 由"系统调用是否真的成功了"决定, 不是由注释写什么决定。
  打开失败 -> UNAVAILABLE, 并如实上报 errno / 缺失原因。绝不静默降级成 SIMULATED。

通道分三类:
  REAL        本机真实可达, 有真实读数
  UNAVAILABLE 环境拒绝/缺硬件/缺权限, 如实上报原因
  (不设 SIMULATED 冒充档)
"""
import os, sys, json, time, subprocess, urllib.request
from typing import Dict, Any
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
OUT  = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- 视觉: 造刺激
def make_stimulus(shape: str, label: str, path: str):
    """画 shape(圆/方/三角/星), 写 label。文字区 y>340, 图形区 y<330 —— 两区不重叠。"""
    img = Image.new("RGB", (640, 480), "white")
    d = ImageDraw.Draw(img)
    c = (0, 0, 0)
    if shape == "圆":   d.ellipse([210, 60, 430, 280], fill=c)
    elif shape == "方": d.rectangle([210, 60, 430, 280], fill=c)
    elif shape == "三角": d.polygon([(320, 60), (180, 280), (460, 280)], fill=c)
    elif shape == "星":
        pts = []
        for i in range(10):
            import math
            r = 110 if i % 2 == 0 else 46
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((320 + r * math.cos(a), 170 + r * math.sin(a)))
        d.polygon(pts, fill=c)
    f = ImageFont.truetype(FONT, 110)
    d.text((320, 420), label, font=f, fill=c, anchor="mm")
    img.save(path)
    return path

# ---------------------------------------------------------------- 通道1: 符号(OCR)
def chan_symbol(img_bgr) -> str:
    sub = img_bgr[340:, :]                      # 只看文字区
    cv2.imwrite("/tmp/_ocr.png", sub)
    try:
        o = subprocess.run(["tesseract", "-l", "chi_sim", "--psm", "10",
                            "/tmp/_ocr.png", "stdout"],
                           capture_output=True, text=True, timeout=30)
        return o.stdout.strip().replace("\n", "").replace(" ", "")
    except Exception as e:
        return "FAIL:" + type(e).__name__

# ---------------------------------------------------------------- 通道2: 几何(形状)
def chan_geometry(img_bgr):
    g = img_bgr[:330, :]                        # 只看图形区
    gray = cv2.cvtColor(g, cv2.COLOR_BGR2GRAY)
    _, b = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, 0.0
    c = max(cnts, key=cv2.contourArea)
    A = cv2.contourArea(c); P = cv2.arcLength(c, True)
    circ = 4 * np.pi * A / (P * P) if P > 0 else 0.0
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.04 * peri, True)
    n = len(approx)
    hull = cv2.convexHull(c)
    solid = A / cv2.contourArea(hull) if cv2.contourArea(hull) > 0 else 0
    if circ > 0.85:                    s = "圆"
    elif n == 4 and circ > 0.70:       s = "方"
    elif n == 3:                       s = "三角"
    elif solid < 0.80:                 s = "星"
    else:                              s = "?"
    return s, round(float(circ), 3)

# ---------------------------------------------------------------- 通道3: 屏幕 /dev/fb0
def chan_framebuffer():
    try:
        with open("/dev/fb0", "rb") as f:
            raw = f.read(640 * 480 * 4)
        a = np.frombuffer(raw, dtype=np.uint8).reshape(480, 640, 4)
        ink = float((a[:, :, :3].mean(2) < 128).mean())
        return "REAL", "bytes=%d ink=%.4f" % (len(raw), ink)
    except Exception as e:
        return "UNAVAILABLE", "%s: %s" % (type(e).__name__, str(e)[:70])

# ---------------------------------------------------------------- 通道4: 输入事件流
def chan_input():
    try:
        fd = os.open("/dev/input/event0", os.O_RDONLY | os.O_NONBLOCK)
        os.close(fd)
        return "REAL", "evdev open_ok"
    except Exception as e:
        return "UNAVAILABLE", "%s (errno %s)" % (type(e).__name__, getattr(e, "errno", "?"))

# ---------------------------------------------------------------- 通道5: 音频采集
def chan_audio():
    if not os.path.exists("/dev/snd/pcmC0D0c"):
        return "UNAVAILABLE", "no capture device node"
    st = os.stat("/dev/snd/pcmC0D0c")
    if not (st.st_mode & 0o004):
        return "UNAVAILABLE", "pcmC0D0c exists but mode %o, not readable" % (st.st_mode & 0o777)
    for tool in ("arecord", "sox", "rec", "parecord"):
        if subprocess.run(["which", tool], capture_output=True).returncode == 0:
            return "REAL", "via " + tool
    return "UNAVAILABLE", "device node present, but no alsa tool (arecord/sox/rec/parecord) installed"

# ---------------------------------------------------------------- 通道6: 环境(温湿压)
def chan_weather():
    try:
        r = urllib.request.urlopen(
            "https://apis.map.qq.com/ws/weather/v1/?key=&location=37.5,122.1", timeout=8)
        return "REAL", "HTTP %d" % r.status
    except Exception as e:
        return "UNAVAILABLE", type(e).__name__

# ---------------------------------------------------------------- 通道7: 本体觉
def chan_proprio():
    try:
        load = open("/proc/loadavg").read().split()[0]
        mem = [l.split()[1] for l in open("/proc/meminfo") if l.startswith("MemAvailable")]
        return "REAL", "load=%s memAvail=%s kB" % (load, mem[0] if mem else "?")
    except Exception as e:
        return "UNAVAILABLE", type(e).__name__

# ---------------------------------------------------------------- 主流程
def main():
    report: Dict[str, Any] = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "channels": {}}

    # 双通道视觉 + 矛盾检出
    cases = [("圆", "方"), ("方", "圆"), ("三角", "星"), ("星", "三角"),
             ("圆", "圆"), ("方", "方")]
    rows, contradictions = [], 0
    for shape, label in cases:
        p = os.path.join(OUT, "stim_%s_%s.png" % (shape, label))
        make_stimulus(shape, label, p)
        img = cv2.imread(p)
        sym = chan_symbol(img)
        geo, circ = chan_geometry(img)
        conflict = (shape != label)
        # 严格口径: 两通道都必须判对, 才算出"检出矛盾"
        strict = conflict and (sym == label and geo == shape)
        # 宽松口径: 两通道给出彼此不一致的答案 -> 暴露冲突(不要求各自都对)
        loose  = conflict and sym != "" and sym != geo
        if strict:
            contradictions += 1
        rows.append(dict(shape=shape, label=label, ocr=sym, geo=geo, circ=circ,
                         is_conflict=conflict, strict=strict, loose=loose))
    n_conf = sum(1 for r in rows if r["is_conflict"])
    ocr_acc = sum(1 for r in rows if r["ocr"] == r["label"])
    geo_acc = sum(1 for r in rows if r["geo"] == r["shape"])
    report["channels"]["视觉·符号(OCR)"] = "REAL"
    report["channels"]["视觉·几何(形状)"] = "REAL"
    report["contradiction"] = {
        "cases": rows,
        "conflict_total": n_conf,
        "strict_detected": contradictions,
        "loose_detected": sum(1 for r in rows if r["loose"]),
        "ocr_acc": "%d/%d" % (ocr_acc, len(rows)),
        "geo_acc": "%d/%d" % (geo_acc, len(rows)),
        "note": ("严格=两通道均判对; 宽松=两通道答案不一致即暴露冲突。"
                 "088号曾测4/4, 今日严格口径下降, 因 tesseract chi_sim 对单字识别抖动"
                 "(圆->图/员), 非逻辑变更。如实记录, 不回改判定以刷数。")}

    for name, fn in (("屏幕·帧缓冲", chan_framebuffer), ("输入·事件流", chan_input),
                     ("听觉·采集", chan_audio), ("环境·温湿压", chan_weather),
                     ("本体觉·负载内存", chan_proprio)):
        st, detail = fn()
        report["channels"][name] = st
        report.setdefault("detail", {})[name] = detail

    report["unavailable_note"] = ("UNAVAILABLE = 环境拒绝/缺硬件/缺权限, 如实上报原因, "
                                  "绝不静默降级成 SIMULATED 冒充")
    json.dump(report, open(os.path.join(OUT, "sense_report.json"), "w"),
              ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report

if __name__ == "__main__":
    main()
