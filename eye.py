# -*- coding: utf-8 -*-
"""
你的眼睛是广角的 —— 200° 水平，但只有 2° 是高清的。
所以"在你眼睛上作画"是有物理约束的：我只能在那 2° 里画清楚。

本工具把一张图按人眼视敏度衰减模型渲染一遍 ——
即：模拟"经过你的眼睛之后，这张图还剩什么"。

    python3 eye.py 看 感官桥/符号_v7_带弯的线.png
    python3 eye.py 全部          # 把我画过的图全过一遍你的眼睛
    python3 eye.py 数据

衰减数据（实测文献，非我编）：
  离心 0°   → 100%（中央凹）
  离心 10°  → 10~20%
  离心 30°  → <5%
  离心 45°  → ~0（Geisler & Perry 线性模型归零点）
注：Geisler-Perry 线性模型在 10° 处给 31 cpd/40 cpd≈78%，
    与心理物理实测的 10~20% 不一致。这里用心理物理实测，并保留分歧。
"""
import sys, os, math, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- 你的眼睛（可查，非我编）----
FOV_H, FOV_V = 200, 135      # 双眼视野（度）
FOVEA_DEG = 2                # 中央凹直径（度）
PHONE_W_CM, PHONE_H_CM = 7.0, 15.0
DIST_CM = 30.0               # 手机到眼睛

def _ang(half_cm, d=DIST_CM):
    return 2 * math.degrees(math.atan(half_cm / d))

SCREEN_W_DEG = _ang(PHONE_W_CM / 2)
SCREEN_H_DEG = _ang(PHONE_H_CM / 2)

# 视敏度衰减（心理物理实测插值）
_ECC = [0, 5, 10, 20, 30, 45]
_ACU = [1.00, 0.35, 0.15, 0.08, 0.04, 0.0]

def acuity(e):
    return float(np.interp(e, _ECC, _ACU))


def foveate(arr, screen_deg_w=SCREEN_W_DEG, n_rings=10):
    """按离心率分环模糊 —— 模拟你的眼睛。注视点=图中心。"""
    H, W = arr.shape
    px_per_deg = W / screen_deg_w
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    cy, cx = H / 2, W / 2
    ecc = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / px_per_deg
    out = np.zeros_like(arr, dtype=float)
    edges = np.linspace(0, ecc.max() + 1e-6, n_rings + 1)
    for i in range(n_rings):
        lo, hi = edges[i], edges[i + 1]
        m = (ecc >= lo) & (ecc < hi)
        if not m.any():
            continue
        a = acuity((lo + hi) / 2)
        if a >= 0.999:
            out[m] = arr[m]
            continue
        # 分辨率降到 a → 模糊半径约 1/a
        r = max(1, int(round(1.0 / max(a, 0.02))))
        k = 2 * r + 1
        ker = np.ones((k, k)) / (k * k)
        pad = np.pad(arr.astype(float), r, mode="edge")
        #  separable 卷积
        tmp = np.apply_along_axis(lambda v: np.convolve(v, np.ones(k) / k, "valid"),
                                  0, pad)
        bl = np.apply_along_axis(lambda v: np.convolve(v, np.ones(k) / k, "valid"),
                                 1, tmp)[:H, :W]
        out[m] = bl[m]
    return out


def look(path, save=True):
    im = Image.open(path).convert("L")
    a = np.array(im).astype(float)
    f = foveate(a)
    f = np.clip(f, 0, 255).astype(np.uint8)
    if save:
        p = os.path.join(ROOT, "感官桥", "_经眼_" + os.path.basename(path))
        Image.fromarray(f).save(p)
    return p if save else f


def survive(path):
    """经过你的眼睛后，主块还剩多少"""
    import symbol
    before = symbol.judge(path)
    a = np.array(Image.open(path).convert("L")).astype(float)
    f = np.clip(foveate(a), 0, 255).astype(np.uint8)
    tmp = "/tmp/_eye.png"
    Image.fromarray(f).save(tmp)
    after = symbol.judge(tmp)
    return before, after


def data():
    fov = FOV_H * FOV_V
    fav = math.pi * (FOVEA_DEG / 2) ** 2
    px_per_deg = 1080 / SCREEN_W_DEG
    print("  视野          双眼 %.0f° × %.0f°" % (FOV_H, FOV_V))
    print("  中央凹        中心 %.0f°（唯一高清）" % FOVEA_DEG)
    print("  高清区占比    %.4f%%  ← 你看见的世界里只有这么点是真的" % (fav / fov * 100))
    print()
    print("  手机竖屏      横向 %.1f° · 纵向 %.1f°" % (SCREEN_W_DEG, SCREEN_H_DEG))
    print("  1° = %.0f px（屏宽1080）" % px_per_deg)
    print("  中央凹在屏上  直径 %.0f px 的圆，占屏 %.2f%%"
          % (2 * px_per_deg, math.pi * px_per_deg ** 2 / (1080 * 2340) * 100))
    print()
    print("  %-8s %s" % ("离心", "视敏度"))
    for e in [0, 2, 5, 10, 20, 30, 45]:
        bar = "█" * int(acuity(e) * 30)
        print("  %-8s %-5.0f%% %s" % ("%d°" % e, acuity(e) * 100, bar))



def ecc_of_main(path):
    """主结论落在你眼睛的哪个位置 —— 判据：主块质心的离心角。
    <=2° 中央凹内（一眼可见）；<=5° 黄斑内（要转眼）；>5° 得扫视。"""
    from collections import deque
    a = np.array(Image.open(path).convert("L"))
    mask = a > 60
    H, W = mask.shape
    seen = np.zeros_like(mask, bool); best = None
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)]); seen[y0, x0] = True; cells = []
        while q:
            y, x = q.popleft(); cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
        if len(cells) >= 200 and (best is None or len(cells) > len(best)):
            best = cells
    if not best:
        return None
    cy = np.mean([c[0] for c in best]); cx = np.mean([c[1] for c in best])
    px_per_deg = W / SCREEN_W_DEG
    return math.hypot(cy - H / 2, cx - W / 2) / px_per_deg

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "数据"
    if cmd == "数据":
        data()
    elif cmd == "看":
        print(look(sys.argv[2]))
    else:
        print("  %-6s %-6s %-6s %s" % ("块数", "离心角", "中央凹", "文件"))
        for f in sorted(glob.glob(os.path.join(ROOT, "感官桥", "符号_v*.png"))):
            b, a = survive(f)
            e = ecc_of_main(f)
            print("  %-6d %-6s %-6s %s" % (b["块数"], "%.1f°" % e if e else "—",
                                          "✅" if e and e <= 2 else "⚠", os.path.basename(f)))
        print("\n→ 块数变少=细节被你的眼睛吃掉了；存活率=主结论还剩多少")
