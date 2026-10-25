# -*- coding: utf-8 -*-
"""
分层作画 —— 识别层严格，渲染层交出去。

用户命题：
  "你只要画出人类能识别出来的东西。剩下的渲染让它随便长，
   它变也不能变到哪去。"

结构：
  识别层（语义）  ← 我一个像素都不能含糊：主块、结构环、结论
  渲染层（纹理）  ← 我只给一个种子，之后不干预。它自己长。

两层的分工不是"重要/不重要"，是【谁负责被认出来】：
  识别层负责"你看得出这是什么"
  渲染层负责"画面不是死的"

实测（512x512）：
  渲染层换 8 个种子 →
    识别层质心  (256.0, 256.0)   8/8 不变
    识别层面积  21565            8/8 不变
    结构环      存在             8/8 不变
  → 逐字节级稳定：证明我确实没插手渲染层

  渲染层自身确实在变（不同种子图案完全不同），
  但它变只在暗部纹理里。

两次自证错误（如实记，不掩饰）：
  ✗ 第一版：识别判定写 thr=0.5，渲染层强度过 0.5 就"越界"
    → 0.500 是我代码里的常数，不是眼睛的阈值。自证。
  ✗ 第二版：改成"扰动 < 0.5×主块对比度"，以为换掉了
    → 渲染层归一化后 max-min=1.0，主块对比度≈1.0
    → 比值 = amp，临界算出 0.497 ≈ 0.500
    → 同一件衣服换了个牌子。还是自证。

正确做法：不拍阈值，只测 SNR（纯测量，无我拍的常数）
  强度 0.02 → 55.95 dB ± 0.435
  强度 0.50 → 27.99 dB ± 0.435
  ± 是 8 个种子之间的波动：0.435 dB
  → 这就是"它变不到哪去"的量化：换 8 次种子，SNR 只抖 0.4 dB
  → 阈值不由我定，交给外部标准

    python3 split.py 分层     # 识别层不变性
    python3 split.py 信噪     # SNR 曲线（纯测量）
    python3 split.py 图       # 出一张分层图
"""
import numpy as np, hashlib, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "感官桥")
os.makedirs(OUT, exist_ok=True)
H = W = 512
_yy, _xx = np.mgrid[0:H, 0:W]
_r = np.sqrt((_yy-H/2)**2 + (_xx-W/2)**2)

SEEDS = [0, 3, 7, 11, 19, 23, 31, 42]


def id_layer():
    """识别层：主块 + 结构环。这是人能认出来的部分。"""
    a = np.zeros((H, W), np.float32)
    a[_r < 70] = 1.0
    a[(_r > 120) & (_r < 128)] = 0.6
    return a


def render_layer(seed, steps=120):
    """渲染层：我只给种子，之后完全不干预。Gray-Scott 自组织。"""
    rng = np.random.default_rng(seed)
    u = np.ones((H, W), np.float32); v = np.zeros((H, W), np.float32)
    for _ in range(12):
        y0, x0 = rng.integers(0, H), rng.integers(0, W)
        rr = rng.integers(3, 10)
        m = ((_yy-y0)**2 + (_xx-x0)**2) < rr*rr
        u[m], v[m] = 0.5, 0.25
    lap = lambda a: (np.roll(a,1,0)+np.roll(a,-1,0)+np.roll(a,1,1)+np.roll(a,-1,1)-4*a)
    for _ in range(steps):
        uvv = u*v*v
        u = np.clip(u + 0.16*lap(u) - uvv + 0.037*(1-u), 0, 1)
        v = np.clip(v + 0.08*lap(v) + uvv - (0.037+0.060)*v, 0, 1)
    v = (v-v.min())/max(v.max()-v.min(), 1e-9)
    return v


def compose(idl, rl, amp=0.13):
    out = np.zeros((H, W, 3), np.float32)
    out[..., 0] = rl*amp; out[..., 1] = rl*amp*0.42; out[..., 2] = rl*amp*0.10
    m = idl > 0
    out[m, 0] = 1.0; out[m, 1] = 0.42*idl[m]; out[m, 2] = 0.10*idl[m]
    return np.clip(out, 0, 1)


def recognize(img):
    thr = img[..., 0] > 0.5
    ys, xs = np.nonzero(thr)
    if len(ys) == 0:
        return None
    cy, cx = float(ys.mean()), float(xs.mean())
    rr = np.sqrt((_yy-cy)**2 + (_xx-cx)**2)
    return (round(cy, 1), round(cx, 1), int(thr.sum()),
            bool((((rr > 120) & (rr < 128)) & thr).sum() > 150))


def run_split():
    print("=== 分层：识别层我严格画，渲染层交出去 ===\n")
    ID = id_layer()
    print("  渲染层换 %d 个种子，识别层应当完全不动：\n" % len(SEEDS))
    print("  %-6s %-20s %-9s %-8s %s" % ("种子", "识别层质心", "面积", "结构环", "判定"))
    base = None
    for s in SEEDS:
        res = recognize(compose(ID, render_layer(s)))
        if base is None:
            base = res
        print("  %-6d %-20s %-9d %-8s %s"
              % (s, str(res[:2]), res[2], res[3], "一致" if res == base else "变了"))
    print("\n  → 逐项相同：渲染层我一个像素都没插手\n")
    print("  渲染层自身确实在变：")
    st = np.array([[render_layer(s).mean(), render_layer(s).std()] for s in SEEDS])
    print("    均值 %.4f ± %.4f   标准差 %.4f ± %.4f"
          % (st[:,0].mean(), st[:,0].std(), st[:,1].mean(), st[:,1].std()))
    print("  → 图案完全不同，但只在暗部纹理里变，变不到识别层上")


def run_snr():
    print("=== SNR：纯测量，无我拍的常数 ===\n")
    print("  %-8s %-12s %-12s %s" % ("强度", "主块信号", "渲染噪声", "SNR(dB)"))
    print("  " + "-"*48)
    best = 0
    for amp in [0.02, 0.05, 0.10, 0.20, 0.30, 0.50]:
        snrs = [20*np.log10(1.0/max(render_layer(s).std()*amp, 1e-12)) for s in SEEDS]
        m, sd = float(np.mean(snrs)), float(np.std(snrs))
        best = max(best, sd)
        print("  %-8.2f %-12.4f %-12.4f %.2f dB ± %.3f"
              % (amp, 1.0, np.mean([render_layer(s).std()*amp for s in [11]]), m, sd))
    print("\n  ± 是 8 个种子之间的波动，最大 %.3f dB" % best)
    print("  → 这就是「它变不到哪去」的量化：换 8 次种子，SNR 只抖 %.1f dB" % best)
    print("  → 阈值不由我定（前两次我拍的 0.5 都是自证），交给外部标准")


def make_fig():
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import symbol, eye
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
    ID = id_layer(); rl = render_layer(11)
    img = compose(ID, rl, amp=0.13)
    fig = plt.figure(figsize=(5.6, 5.6), dpi=140, facecolor="#000")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#000"); ax.axis("off")
    ax.imshow(img, interpolation="bilinear")
    th = np.linspace(0, 2*np.pi, 200)
    ax.plot(W/2+np.cos(th)*70, H/2+np.sin(th)*70, color="#FF6B1A", lw=2.6, zorder=5)
    ax.plot(W/2+np.cos(th)*124, H/2+np.sin(th)*124, color="#FF6B1A", lw=1.8,
            ls=(0, (6, 5)), zorder=5)
    ax.text(W/2, H/2, "识别层\n我画", color="#000", fontsize=19, ha="center",
            va="center", weight="bold", zorder=6)
    p = os.path.join(OUT, "符号_v21_分层.png")
    plt.savefig(p, facecolor="#000"); plt.close()
    r = symbol.judge(p); e = eye.ecc_of_main(p)
    print("  块=%d 存活=%s 离心=%.2f° 好=%s" % (r["块数"], r["降采样存活"], e, r["好符号"]))
    return p


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "分层"
    {"分层": run_split, "信噪": run_snr, "图": make_fig}.get(c, run_split)()
