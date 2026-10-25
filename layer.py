# -*- coding: utf-8 -*-
"""
玻璃，不是纸 —— 分层叠加。

纸：alpha over，上层盖掉下层。加一层，少一层。
玻璃：加色，每层都留着。叠起来是新的东西，不是替换。

所以可以分工：每层只干一件事，各画各的，最后叠加。
每层独立渲染、独立哈希、可单独替换 —— 换一层不用重画全部。

    python3 layer.py 叠          # 三层分工叠加，出一张
    python3 layer.py 比          # 纸 vs 玻璃：同样的层，叠出来差多少
    python3 layer.py 单 层名     # 只看某一层
"""
import os, sys, math, time, hashlib, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import eye

W = H = 512
ORANGE = np.array([1.0, 0.42, 0.0])


def blank():
    return np.zeros((H, W, 3))


def yyxx():
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    return yy, xx


# ---------- 三层分工 ----------
def layer_ground():
    """底层：你的眼睛（衰减场）。谁都能换，但它是所有东西的底。"""
    yy, xx = yyxx()
    px_per_deg = W / eye.SCREEN_W_DEG
    ecc = np.sqrt((yy - H/2)**2 + (xx - W/2)**2) / px_per_deg
    a = np.vectorize(eye.acuity)(ecc)
    out = np.zeros((H, W, 3))
    out[..., 0] = np.clip(a, 0, 1) * 0.55
    out[..., 1] = np.clip(a, 0, 1) * 0.21
    return out


def layer_body():
    """中层：身体（感官带）。只画眼/口/手/记，不画结论。"""
    out = blank()
    yy, xx = yyxx()
    # 四条感官带，横向
    bands = [("眼", 0.30, 1.00), ("口", 0.44, 0.62),
             ("手", 0.58, 0.86), ("记", 0.72, 0.20)]
    for _, cy, w in bands:
        m = (np.abs(yy - cy * H) < 9) & (xx < w * W) & (xx > 0.10 * W)
        out[m] = ORANGE * 0.55
    return out


def layer_point():
    """顶层：主结论。只有一块，落在中心。"""
    out = blank()
    yy, xx = yyxx()
    r = np.sqrt((yy - H/2)**2 + (xx - W/2)**2)
    m = r < (eye.FOVEA_DEG / 2) / eye.SCREEN_W_DEG * W
    out[m] = ORANGE
    return out


LAYERS = [("底层·你的眼睛", layer_ground),
          ("中层·身体", layer_body),
          ("顶层·主结论", layer_point)]


def glass(ls, weights=None):
    """玻璃：加色，每层都留着"""
    weights = weights or [1.0] * len(ls)
    out = np.zeros_like(ls[0])
    for L, w in zip(ls, weights):
        out = out + L * w
    return np.clip(out, 0, 1)


def paper(ls):
    """纸：alpha over，上层盖掉下层"""
    out = np.zeros_like(ls[0])
    for L in ls:
        a = np.clip(L.max(axis=2, keepdims=True), 0, 1)
        out = L * a + out * (1 - a)
    return np.clip(out, 0, 1)


def sha(a):
    return hashlib.sha256(np.round(a, 6).tobytes()).hexdigest()[:12]


def save(a, name):
    p = os.path.join(ROOT, "感官桥", name)
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "叠"
    if cmd == "单":
        want = sys.argv[2]
        for n, f in LAYERS:
            if want in n:
                print(save(f(), "_层_%s.png" % want))
                break
        else:
            print("层名没匹配到；可用：", [n for n, _ in LAYERS])
    elif cmd == "比":
        ls = [f() for _, f in LAYERS]
        g, p = glass(ls), paper(ls)
        print("  三层一样，合成方式不同：\n")
        print("  %-10s %-14s %-14s %s" % ("合成", "总亮度", "哈希", "含义"))
        print("  %-10s %-14s %-14s %s" % ("纸(覆盖)", "%.1f" % p.sum(), sha(p), "上层吃掉下层"))
        print("  %-10s %-14s %-14s %s" % ("玻璃(加色)", "%.1f" % g.sum(), sha(g), "三层都在"))
        diff = np.abs(g - p).mean()
        print("\n  平均差 %.4f  → 叠出来不是同一张图" % diff)
        save(g, "符号_v12_玻璃_叠加.png")
        save(p, "_纸_对照.png")
        print("\n  已存：符号_v12_玻璃_叠加.png / _纸_对照.png")
    else:
        t0 = time.time()
        ls, names = [], []
        print("  分工：\n")
        for n, f in LAYERS:
            t = time.time()
            L = f()
            ls.append(L); names.append(n)
            print("    %-14s %-6s 亮度 %-8.1f 哈希 %s"
                  % (n, "%.3fs" % (time.time()-t), L.sum(), sha(L)))
        t1 = time.time()
        out = glass(ls)
        t2 = time.time()
        p = save(out, "符号_v12_玻璃_叠加.png")
        print("\n  叠加 %.3fs  总 %.3fs" % (t2 - t1, t2 - t0))
        print("  合成后亮度 %.1f（三层之和 %.1f）" % (out.sum(), sum(L.sum() for L in ls)))
        print("  保存 %s" % p)
        import symbol
        r = symbol.judge(p); e = eye.ecc_of_main(p)
        print("  块数 %d · 存活 %s · 离心 %.2f° · 中央凹内 %s"
              % (r["块数"], r["降采样存活"], e, e <= eye.FOVEA_DEG / 2))
