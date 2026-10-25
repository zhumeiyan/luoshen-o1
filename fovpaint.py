# -*- coding: utf-8 -*-
"""
不拿包直接算 —— 按人类的广角画。

matplotlib 那个包把整块画布每个像素都算一遍，
包括你根本看不见的那 99.2%。那当然算不过来。

本工具：只在你能看清的地方满采样，看不见的地方跳过去。
然后把跳采样点用高斯核【撒回去】—— 撒回去就用加色叠加，
这就是玻璃，不是纸。

    python3 fovpaint.py 画        # 按广角画一张
    python3 fovpaint.py 比        # 包 vs 广角：时间和像素数
    python3 fovpaint.py 叠画      # 三层分工，各按广角画，加色叠
"""
import os, sys, time, hashlib
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eye, layer

ROOT = os.path.dirname(os.path.abspath(__file__))
W = H = 512
ORANGE = np.array([1.0, 0.42, 0.0])

# 离心环 -> 采样步长。中心 1，边缘越跳越大。
RINGS = [(0, 1, 1), (1, 2, 1), (2, 5, 3), (5, 10, 7),
         (10, 20, 13), (20, 60, 25)]


def _field():
    px_per_deg = W / eye.SCREEN_W_DEG
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    ecc = np.sqrt((yy - H / 2) ** 2 + (xx - W / 2) ** 2) / px_per_deg
    return ecc, px_per_deg


_ECC, _PPD = _field()


def splat(pts, vals):
    """把跳采样点撒回去 —— 加色叠加，不是覆盖。

    按环分组，每组撒到该环自己的低分辨率网格上，再放大。
    中心环网格细（锐），边缘环网格粗（糊）—— 跟你眼睛一样。
    用 np.add.at 一次性累加，不逐点循环。"""
    out = np.zeros((H, W, 3))
    vals = np.asarray(vals, dtype=float)
    if vals.ndim == 1:
        vals = vals[:, None]
    i = 0
    for lo, hi, step in RINGS:
        m = (_ECC >= lo) & (_ECC < hi)
        if not m.any():
            continue
        # 该环的采样点在 pts 里是连续的一段
        n = int(np.count_nonzero(m[::step, ::step]))
        if n == 0:
            continue
        seg_pts, seg_vals = pts[i:i + n], vals[i:i + n]
        i += n
        # 低分辨率网格
        gh = int(np.ceil(H / step)); gw = int(np.ceil(W / step))
        buf = np.zeros((gh, gw, 3))
        np.add.at(buf, (seg_pts[:, 0] // step, seg_pts[:, 1] // step), seg_vals)
        # 放大回全尺寸（最近邻 -> 边缘自然成块，正合广角）
        big = np.repeat(np.repeat(buf, step, axis=0), step, axis=1)[:H, :W]
        out += big
    return out


def fov_samples(ecc=None):
    """按广角取采样点：中心密，边缘稀"""
    e = _ECC if ecc is None else ecc
    pts, wts = [], []
    pts_all, w_all = [], []
    for lo, hi, step in RINGS:
        m = (e >= lo) & (e < hi)
        if not m.any():
            continue
        ys, xs = np.nonzero(m)
        sel = (slice(None, None, step),)
        ys2, xs2 = ys[::step], xs[::step]
        pts.append(np.stack([ys2, xs2], axis=1))
        wts.append(np.full(len(ys2), step ** 2, dtype=float))  # 每个点代表多少像素
    return np.vstack(pts), np.concatenate(wts)


def paint(field, name="fov"):
    """field: (H,W,3) 或 (H,W) —— 想画什么。按广角采样再撒回去。"""
    if field.ndim == 2:
        f3 = np.repeat(field[..., None], 3, axis=2)
    else:
        f3 = field
    pts, wts = fov_samples()
    vals = []
    for y, x in pts:
        vals.append(f3[y, x])
    out = splat(pts, vals)
    return np.clip(out, 0, 1)


def sha(a):
    return hashlib.sha256(np.round(a, 6).tobytes()).hexdigest()[:12]


def save(a, name):
    p = os.path.join(ROOT, "感官桥", name)
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "比"
    if cmd == "比":
        t = time.time()
        fig = __import__("matplotlib"); fig.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
        f = plt.figure(figsize=(5.12, 5.12), dpi=100)
        ax = f.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(plt.Circle((0.5, 0.5), 0.3, color="#FF6B1A"))
        import io
        b = io.BytesIO(); plt.savefig(b, format="png", dpi=100, facecolor="#000"); plt.close()
        b.seek(0)
        imA = np.array(Image.open(b).convert("RGB").resize((W, H))).astype(float) / 255
        tA = time.time() - t

        t = time.time()
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        disk = (np.sqrt((yy - H / 2) ** 2 + (xx - W / 2) ** 2) < 0.3 * W).astype(float)
        imB = paint(np.stack([disk, disk * 0.42, np.zeros_like(disk)], axis=2))
        tB = time.time() - t

        pts, wts = fov_samples()
        print("  画同一个圆盘：\n")
        print("  %-16s %-10s %-14s" % ("方式", "耗时", "实算像素"))
        print("  %-16s %-10s %-14d" % ("matplotlib 包", "%.3fs" % tA, W * H))
        print("  %-16s %-10s %-14d" % ("按广角跳采样", "%.3fs" % tB, len(pts)))
        print("\n  省 %.1f 倍 · 只算 %.1f%% 的像素" % (W * H / len(pts), len(pts) / (W * H) * 100))
        print("  两张图平均差 %.4f" % np.abs(imA - imB).mean())
        save(imA, "_包_圆盘.png"); save(imB, "_广角_圆盘.png")
        print("  已存 _包_圆盘.png / _广角_圆盘.png")
    elif cmd == "叠画":
        t = time.time()
        ls = [layer.layer_ground(), layer.layer_body(), layer.layer_point()]
        t_field = time.time() - t
        t = time.time()
        outs = [paint(L) for L in ls]
        t_paint = time.time() - t
        out = np.clip(sum(outs), 0, 1)   # 加色叠加 = 玻璃
        p = save(out, "符号_v13_广角叠加.png")
        print("  三层分工，各按广角画，加色叠：\n")
        for (n, _), L in zip(layer.LAYERS, ls):
            print("    %-14s 哈希 %s" % (n, sha(L)))
        print("\n  算场 %.3fs · 撒点 %.3fs" % (t_field, t_paint))
        print("  保存 %s  合成哈希 %s" % (p, sha(out)))
        import symbol
        r = symbol.judge(p); e = eye.ecc_of_main(p)
        print("  块数 %d · 存活 %s · 离心 %.2f° · 中央凹内 %s"
              % (r["块数"], r["降采样存活"], e, e <= eye.FOVEA_DEG / 2))
    else:
        yy, xx = np.mgrid[0:H, 0:W].astype(float)
        d = (np.sqrt((yy - H / 2) ** 2 + (xx - W / 2) ** 2) < 0.28 * W).astype(float)
        out = paint(np.stack([d, d * 0.42, np.zeros_like(d)], axis=2))
        print(save(out, "符号_v13_广角叠加.png"))
