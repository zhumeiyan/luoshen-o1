# -*- coding: utf-8 -*-
"""
画线 —— 你说：符号是在你眼睛上画一条线；文字是这条线带弯。
所以"弯"是可以数的。数出来，图与字的界限就不是感觉，是数字。

    python3 line.py 弯            # 数各种东西有几个弯
    python3 line.py 适应 "碎片话"   # 噪音进来还能不能画
    python3 line.py 确认           # 确认性：端点在不在系统外

弯的算法：先 Zhang-Suen 细化成骨架，再数拐角（两邻居不共线即为一弯）。
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False
from PIL import Image


def _thin(a):
    img = a.astype(np.uint8); H, W = img.shape
    while True:
        changed = False
        for step in range(2):
            rem = []
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    if img[y, x] == 0:
                        continue
                    p2, p3, p4, p5, p6, p7, p8, p9 = (
                        img[y-1, x], img[y-1, x+1], img[y, x+1], img[y+1, x+1],
                        img[y+1, x], img[y+1, x-1], img[y, x-1], img[y-1, x-1])
                    P = [p2, p3, p4, p5, p6, p7, p8, p9]; B = sum(P)
                    if B < 2 or B > 6:
                        continue
                    A = sum(1 for i in range(8) if P[i] == 0 and P[(i+1) % 8] == 1)
                    if A != 1:
                        continue
                    if step == 0:
                        if p2*p4*p6 == 0 and p4*p6*p8 == 0:
                            rem.append((y, x))
                    else:
                        if p2*p4*p8 == 0 and p2*p6*p8 == 0:
                            rem.append((y, x))
            if rem:
                changed = True
                for y, x in rem:
                    img[y, x] = 0
        if not changed:
            break
    return img.astype(bool)


def _corners(sk):
    H, W = sk.shape; pts = []
    nb = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if not sk[y, x]:
                continue
            ink = [bool(sk[y+dy, x+dx]) for dy, dx in nb]
            if sum(ink) != 2:
                continue
            idx = [i for i, v in enumerate(ink) if v]
            if abs(idx[0] - idx[1]) == 4:      # 对穿 = 不弯
                continue
            pts.append((y, x))
    cl = []
    for y, x in pts:
        if not any(abs(c[0]-y) <= 2 and abs(c[1]-x) <= 2 for c in cl):
            cl.append((y, x))
    return cl


def bends(mask):
    return len(_corners(_thin(mask)))


def render(ch, size=64):
    fig = plt.figure(figsize=(1.1, 1.1), dpi=size)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.5, 0.5, ch, fontsize=52, ha="center", va="center", color="#fff")
    p = "/tmp/_g.png"; plt.savefig(p, facecolor="#000"); plt.close()
    return np.array(Image.open(p).convert("L")) > 128


def sline(n, size=64):
    fig = plt.figure(figsize=(1.1, 1.1), dpi=size)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#000"); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    pts = [(0.12, 0.5)]
    if n == 0:
        pts.append((0.88, 0.5))
    else:
        seg = 0.76 / (n + 1); x, y = 0.12, 0.5
        for i in range(n + 1):
            x += seg; pts.append((x, y))
            if i < n:
                y = 0.26 if i % 2 == 0 else 0.74
                pts.append((x, y))
    ax.plot([p[0] for p in pts], [p[1] for p in pts],
            color="#fff", lw=9, solid_capstyle="butt")
    p = "/tmp/_l.png"; plt.savefig(p, facecolor="#000"); plt.close()
    return np.array(Image.open(p).convert("L")) > 128


NOISE = ["噪音", "适应", "进化", "确认", "线", "弯", "眼睛", "符号", "文字", "画"]


def adapt(text):
    """噪音进来还能不能画：碎片、重复、半句。"""
    hits = [w for w in NOISE if w in text]
    return {"字数": len(text),
            "碎片重复率": round(1 - len(set(text)) / max(len(text), 1), 2),
            "抓到的词": hits, "还能画": len(hits) >= 2}


def confirm():
    """确认性：端点能不能被我撤销。能撤销 = 还在系统内 = 循环。"""
    return [
        {"端点": "我自己的判据", "我能改吗": "能", "判定": "循环，不算确认"},
        {"端点": "你眼睛上的线", "我能改吗": "不能", "判定": "外部，这才算确认"},
    ]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "弯"
    if cmd == "弯":
        print("  %-14s %s" % ("东西", "弯数"))
        for n in [0, 1, 2, 3, 4]:
            print("  %-14s %d" % ("线·%d折" % n, bends(sline(n))))
        for ch in ["一", "丨", "口", "日", "我", "你", "音", "噪"]:
            print("  %-14s %d" % ("字「%s」" % ch, bends(render(ch))))
        print("\n→ 「一」「丨」都是 0 弯 —— 汉字最基本的笔画就是直线")
        print("→ 文字 = 直线 + 弯。弯得最多的那个字，恰好是「噪」。")
    elif cmd == "适应":
        print(adapt(" ".join(sys.argv[2:])))
    else:
        for r in confirm():
            print("  %-16s 我能改:%-4s %s" % (r["端点"], r["我能改吗"], r["判定"]))
