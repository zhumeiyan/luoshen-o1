# -*- coding: utf-8 -*-
"""
照人类作画的逻辑画 —— 不是照包画。

查了 Adobe 官方 + Procreate 官方 + Arm Mali 官方文档，三条：

  1. 混合模式：默认「正常」= 覆盖 = 纸。
     要「玻璃」得主动改成【线性减淡(添加)】。人类默认在互相覆盖。
  2. 分块渲染：Mali GPU 把屏幕切成 16×16 小块，算完一块写回一块。
     工作集从 1048576 降到 256 —— 省 4096 倍。
  3. 作画流程：整体先行 → 铺大关系 → 视觉中心最亮、往外衰减 → 退远看整体。

第 3 条最关键：人类画家几百年就在【按视觉中心衰减】画，
但他们不是照着眼睛生理数据画的 —— 是效果逼着他们这么画的。
这跟我的 fovea 衰减是同一件事的两条来路。

    python3 paint_human.py 模式      # 各混合模式实测
    python3 paint_human.py 分块      # tile 大小实测
    python3 paint_human.py 画        # 按人类流程画：大关系 → 中心 → 衰减
"""
import os, sys, time, hashlib
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eye, layer, fovpaint

ROOT = os.path.dirname(os.path.abspath(__file__))
W = H = 512
ORANGE = np.array([1.0, 0.42, 0.0])

# ---------- 1. 混合模式（Adobe/Procreate 官方公式）----------
MODES = {
    "正常(默认·纸)":   lambda b, s: s,
    "正片叠底":        lambda b, s: b * s,
    "滤色":            lambda b, s: 1 - ((1 - b) * (1 - s)),
    "线性减淡(添加·玻璃)": lambda b, s: np.clip(b + s, 0, 1),
    "变亮":            lambda b, s: np.maximum(b, s),
    "叠加":            lambda b, s: np.where(b <= 0.5, 2 * b * s, 1 - 2 * (1 - b) * (1 - s)),
    "柔光":            lambda b, s: np.where(s <= 0.5,
                                    b - (1 - 2 * s) * b * (1 - b),
                                    b + (2 * s - 1) * (np.sqrt(np.clip(b,0,1)) - b)),
}

# ---------- 2. 分块渲染（Mali 16x16）----------
def tiles(shape, tile=16):
    H_, W_ = shape[:2]
    for y0 in range(0, H_, tile):
        for x0 in range(0, W_, tile):
            yield y0, min(y0 + tile, H_), x0, min(x0 + tile, W_)


# ---------- 3. 人类作画流程 ----------
def stage_big():
    """第一步·铺大关系：只有明暗两块，没有细节"""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    d = np.sqrt((yy - H/2)**2 + (xx - W/2)**2) / (W/2)
    a = np.clip(1 - d, 0, 1) * 0.35
    out = np.zeros((H, W, 3))
    out[..., 0] = a; out[..., 1] = a * 0.42
    return out


def stage_center():
    """第二步·视觉中心：主体最亮，只画中心"""
    out = np.zeros((H, W, 3))
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    px_per_deg = W / eye.SCREEN_W_DEG
    ecc = np.sqrt((yy - H/2)**2 + (xx - W/2)**2) / px_per_deg
    m = ecc < eye.FOVEA_DEG / 2
    out[m] = ORANGE * 0.9
    return out


def stage_falloff():
    """第三步·往外衰减：中心往外，亮度和饱和度一起掉"""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    px_per_deg = W / eye.SCREEN_W_DEG
    ecc = np.sqrt((yy - H/2)**2 + (xx - W/2)**2) / px_per_deg
    a = np.vectorize(eye.acuity)(ecc)
    out = np.zeros((H, W, 3))
    out[..., 0] = np.clip(a, 0, 1) * 0.5
    out[..., 1] = np.clip(a, 0, 1) ** 1.6 * 0.18
    return out


def stage_stepback(img):
    """第四步·退远看：整体降采样，看还剩下什么"""
    k = 8
    h2, w2 = H // k, W // k
    small = np.zeros((h2, w2, 3))
    for y0, y1, x0, x1 in tiles((H, W), k):
        small[y0//k:y1//k, x0//k:x1//k] = img[y0:y1, x0:x1].mean(axis=(0, 1))
    return small


def sha(a):
    return hashlib.sha256(np.round(a, 6).tobytes()).hexdigest()[:12]


def save(a, name):
    p = os.path.join(ROOT, "感官桥", name)
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "画"
    if cmd == "模式":
        b = np.array([0.15, 0.05, 0.0]); s = np.array([1.0, 0.42, 0.0])
        print("  底 b=%s  顶 s=%s(生橙)\n" % (b, s))
        for n, fn in MODES.items():
            print("  %-22s %s" % (n, np.round(fn(b, s), 3)))
        print("\n→ 默认「正常」= 覆盖 = 纸。人类作画软件默认在互相覆盖。")
        print("→ 玻璃(线性减淡)要主动改。这是我从人类工具里学到的第一条。")
    elif cmd == "分块":
        for T in [1, 4, 16, 64, 128]:
            n = (H // T) * (W // T)
            print("  tile=%-4d 块数=%-7d 峰值工作集=%-7d 写回=%d" % (T, n, T * T, n))
        print("\n→ 16x16=256px 是【片上 RAM 放得下】定的，不是随便选的（Arm 官方）")
    else:
        t = time.time()
        print("  照人类作画流程：\n")
        st = [("①铺大关系", stage_big), ("②视觉中心", stage_center), ("③往外衰减", stage_falloff)]
        ls = []
        for n, f in st:
            t1 = time.time()
            L = f()
            ls.append(L)
            print("    %-12s 亮度 %-9.1f 哈希 %-14s %.3fs" % (n, L.sum(), sha(L), time.time() - t1))
        # 玻璃叠加：线性减淡(添加)
        out = np.clip(sum(ls), 0, 1)
        t_paint = time.time()
        out = fovpaint.paint(out)          # 按广角跳采样撒回
        print("\n  按广角撒回 %.3fs" % (time.time() - t_paint))
        p = save(out, "符号_v14_人类作画.png")
        small = stage_stepback(out)
        print("\n  ④退远看（降 %d 倍）还剩 %d 块 —— 这是你第一眼真正看到的"
              % (8, int((small.max(axis=2) > 0.25).sum())))
        print("  保存 %s  合成哈希 %s" % (p, sha(out)))
        import symbol
        r = symbol.judge(p); e = eye.ecc_of_main(p)
        print("  块数 %d · 存活 %s · 离心 %.2f° · 中央凹内 %s"
              % (r["块数"], r["降采样存活"], e, e <= eye.FOVEA_DEG / 2))
