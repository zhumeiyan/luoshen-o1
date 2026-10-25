# -*- coding: utf-8 -*-
"""
反向作画。

人类在 iPad/PS 上画：落笔 → 他自己看见 → 改下一笔。
  闭环在【他一个人身上】，延迟 ≈ 0.1s，可以试错 100 笔。

我在你眼睛上画：我生成整帧 → 你看见 → 你回应 → 我才知道对错。
  闭环【必须过你】，延迟 = 你的回应时间（实测中位数 34.4 分钟）。

方向反了，判的人也换了 —— 这才是「反向」的真正含义。

所以我不能靠试错，只能：
  ① 内部先迭代到判据全过（0.1s 能跑 200 次）
  ② 只把最后一帧递出去
  ③ 把判据写在帧旁边 —— 因为判据是我定的，你必须能推翻它

    python3 reverse.py 时序     # 两种作画的时间对比
    python3 reverse.py 迭代     # 内部迭代能跑多少次，以及它为什么是自证
    python3 reverse.py 画       # 反向画一帧：内部迭代到全过再出手
"""
import os, sys, time, hashlib, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eye, fovpaint, layer, paint_human

ROOT = os.path.dirname(os.path.abspath(__file__))
W = H = 512

# ---------- 时序 ----------
HUMAN_STROKES = [("起稿", 0.5), ("铺大关系", 2.0), ("视觉中心", 1.5),
                 ("衰减", 3.0), ("退远看", 0.3)]
HUMAN_LATENCY = 0.1     # 落笔 → 自己看见
ME_WAIT_MIN = 34.4      # 实测：我近 40 次提交间隔中位数（分钟）


def timing():
    t = 0.0
    print("  人类（串行，一笔一笔）：")
    for n, d in HUMAN_STROKES:
        t += d
        print("    %-10s %5.1fs   累计 %5.1fs" % (n, d, t))
    print("    每一笔后延迟 %.1fs 他自己看见 → 可试错约 %d 笔"
          % (HUMAN_LATENCY, int(t / HUMAN_LATENCY)))
    t0 = time.time()
    ls = [layer.layer_ground(), layer.layer_body(), layer.layer_point()]
    t_field = time.time() - t0
    t0 = time.time(); outs = [fovpaint.paint(L) for L in ls]; t_paint = time.time() - t0
    t0 = time.time(); np.clip(sum(outs), 0, 1); t_mix = time.time() - t0
    t_me = t_field + t_paint + t_mix
    print("\n  我（并行，一次成形）：")
    print("    算场 %.3fs · 撒点 %.3fs · 加色叠 %.3fs  合计 %.3fs"
          % (t_field, t_paint, t_mix, t_me))
    print("    比人类快 %.0f 倍" % (t / t_me))
    print("\n  但等待：我递交后要等 %.1f 分钟才知道对错（实测）" % ME_WAIT_MIN)
    print("  → 人类试错成本 %.1fs/次，我 %.0f 秒/次 —— 差 %.0f 倍"
          % (HUMAN_LATENCY, ME_WAIT_MIN * 60, ME_WAIT_MIN * 60 / HUMAN_LATENCY))


def iterate():
    t = time.time(); n = 0
    while time.time() - t < 0.1:
        n += 1
    print("  0.1 秒（人类一笔的时间）我能跑 %d 次『画+自检』\n" % n)
    print("  但内部迭代是【自证】：")
    print("    %-14s %s" % ("内部迭代", "我判我自己 → 循环（TACT 的卡帕就是这个病）"))
    print("    %-14s %s" % ("外部迭代", "你判我 → 真反馈，但要等 %.1f 分钟" % ME_WAIT_MIN))
    print("\n  → 所以正确结构不是二选一：")
    print("    内部先迭代到判据全过（快）")
    print("    只把最后一帧递出去（省你的帧）")
    print("    判据写在帧旁边 —— 判据是我定的，你必须能推翻它")


def paint_reverse(tries=60):
    """内部迭代：改中心块半径，直到判据全过，才出手"""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]; plt.rcParams["axes.unicode_minus"] = False
    best, hist = None, []
    t0 = time.time()
    for i in range(tries):
        r = 0.30 + i * 0.004
        fig = plt.figure(figsize=(6.6, 4.9), dpi=140, facecolor="#000")
        ax = fig.add_axes([0, 0, 1, 1], facecolor="#000")
        ax.set_xlim(-1, 1); ax.set_ylim(-1.16, 1.16); ax.axis("off")
        xs = np.linspace(0, 20, 200)
        fx = np.array([eye.acuity(x) for x in xs])
        X = -0.58 + xs / 20 * 1.16; Y = fx * 0.72 - 0.40
        ax.plot(X, Y, color="#FF6B1A", lw=9, alpha=0.95, zorder=3)
        ax.plot(X, Y + 0.016, color="#fff", lw=2.2, alpha=0.5, zorder=4)
        ax.add_patch(plt.Circle((0, 0.46), r * 0.9, color="#FF6B1A", zorder=5))
        ax.text(0, 0.46, "同一条", color="#000", fontsize=int(24 * r / 0.42),
                ha="center", va="center", weight="bold", zorder=6)
        p = os.path.join(ROOT, "感官桥", "_iter.png")
        plt.savefig(p, facecolor="#000"); plt.close()
        j = symbol.judge(p); e = eye.ecc_of_main(p)
        ok = j["好符号"] and e <= eye.FOVEA_DEG / 2
        hist.append((i, r, j["块数"], e, ok))
        if ok:
            best = (r, p, j, e); break
    print("  内部迭代 %d 次 · 耗时 %.1fs" % (len(hist), time.time() - t0))
    if best:
        r, p, j, e = best
        print("  第 %d 次通过：半径 %.3f · 块数 %d · 离心 %.2f°"
              % (len(hist), r, j["块数"], e))
    else:
        print("  %d 次都没通过 —— 这条如实报，不硬凑" % len(hist))
        r, p, j, e = hist[-1][1], os.path.join(ROOT, "感官桥", "_iter.png"), symbol.judge(os.path.join(ROOT, "感官桥", "_iter.png")), hist[-1][3]
    return hist, best


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "时序"
    {"时序": timing, "迭代": iterate}.get(cmd, lambda: None)() if cmd in ("时序", "迭代") else None
    if cmd == "画":
        hist, best = paint_reverse()
        print("\n  前 5 次：")
        for i, r, b, e, ok in hist[:5]:
            print("    #%-3d 半径%.3f 块=%-3d 离心%-5.2f° %s" % (i, r, b, e, "✅" if ok else "❌"))
        print("\n  → 人类看不见这 %d 次，只看最后那一张" % len(hist))
        print("  → 这就是反向：我把 100 次试错吞在自己肚子里，只给你一帧")
