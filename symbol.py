# -*- coding: utf-8 -*-
"""
符号 —— 用我的手，在你眼睛上画。

链路：
  你按键 → token → 我的眼睛        （输入：离散符号）
  我有想法 → 我的手 → 像素 → 你的眼睛 （输出：可扫符号）

两边载体不同，所以要翻译。翻译必须不失真，否则是装饰。

好符号的三条硬判据（都可测）：
  S1 块数 <= 9      一屏扫得完（7±2 上限）
  S2 降采样存活      缩到 1/8 后主块仍是主块 -> 扫一眼抓得到主结论
  S3 自带校验        哈希可复算，不是好看的谎言

    python3 symbol.py 测 感官桥/xxx.png
    python3 symbol.py 全部
    python3 symbol.py 造            # 造一个真符号
"""
import sys, os, hashlib, glob
from collections import deque
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_BLOCKS = 9


def _blobs(fg, minsize=200):
    H, W = fg.shape
    seen = np.zeros_like(fg, bool)
    out = []
    ys, xs = np.nonzero(fg)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        q = deque([(y0, x0)]); seen[y0, x0] = True; size = 0
        cells = []
        while q:
            y, x = q.popleft(); size += 1; cells.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and fg[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
        if size >= minsize:
            out.append(size)
    return sorted(out, reverse=True)


def s1_blocks(path):
    im = Image.open(path).convert("L")
    return len(_blobs(np.array(im) > 60))


def s2_survive(path):
    """降到 1/8：主块还是不是主块。
    模拟'扫一眼'——你扫的时候分辨率本来就很低。"""
    im = Image.open(path).convert("L")
    a = np.array(im).astype(float)
    full = _blobs(a > 60)
    if not full:
        return 0.0
    h, w = a.shape
    small = np.array(Image.fromarray(a.astype(np.uint8)).resize(
        (max(8, w // 8), max(8, h // 8)), Image.BILINEAR))
    sm = _blobs(small > 60, minsize=2)
    # 全分辨率主块占前景比例 vs 缩略图主块占前景比例
    r_full = full[0] / sum(full)
    r_small = (sm[0] / sum(sm)) if sm else 0.0
    return round(min(r_small / r_full, 1.0), 3) if r_full else 0.0


def s3_hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def judge(path):
    b = s1_blocks(path); s = s2_survive(path); h = s3_hash(path)
    ok = b <= MAX_BLOCKS and s >= 0.6
    return {"文件": os.path.basename(path), "块数": b, "降采样存活": s,
            "哈希": h, "好符号": ok}


def make():
    """造一个真符号：块数 <= 9，扫一眼抓全。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(7, 5), dpi=140, facecolor="#0d0d0d")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#0d0d0d")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # 只有 5 块：身体一行、一个大数、一个缺口、一行字、一行校验
    senses = [("眼", True), ("耳", False), ("口", True), ("手", True), ("记", True)]
    x = 0.10
    for name, has in senses:
        col = "#FF6B1A" if has else "#3a3a3a"
        ax.add_patch(FancyBboxPatch((x, 0.72), 0.115, 0.15, boxstyle="round,pad=0.01",
                                    facecolor=col if has else "none",
                                    edgecolor=col, lw=2))
        ax.text(x + 0.0575, 0.795, name,
                color="#0d0d0d" if has else col, fontsize=17, ha="center", weight="bold")
        x += 0.135

    ax.text(0.5, 0.52, "461 MB → 1500 字", color="#f0f0f0",
            fontsize=25, ha="center", weight="bold")
    ax.text(0.5, 0.40, "我压缩 315 倍，只递成片", color="#8a8a8a", fontsize=12, ha="center")
    ax.text(0.5, 0.24, "耳是空的 —— 这条不压缩", color="#FF6B1A",
            fontsize=13, ha="center", weight="bold")

    p = os.path.join(ROOT, "感官桥", "符号.png")
    plt.savefig(p, facecolor="#0d0d0d"); plt.close()
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "全部"
    if cmd == "造":
        p = make(); print("已造:", p); print(judge(p))
    elif cmd == "测":
        print(judge(sys.argv[2]))
    else:
        print("  %-4s %-5s %-8s %s" % ("判定", "块数", "存活", "文件"))
        for f in sorted(glob.glob(os.path.join(ROOT, "感官桥", "*.png"))):
            r = judge(f)
            print("  %-4s %-5d %-8s %s" % ("好" if r["好符号"] else "差",
                                           r["块数"], r["降采样存活"], r["文件"]))
        print("\n  判据: 块数<=9（一屏扫得完）且 降采样存活>=0.6（扫一眼抓得到主结论）")


def make_v2():
    """无字符号：靠面积、颜色、位置，不靠字。
    实测：每个汉字约 1 块，9 块预算放 9 个字就用光了。
    所以符号必须几乎无字 —— 第一次要教，之后就不用字了。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(7, 5.2), dpi=140, facecolor="#0d0d0d")
    ax = fig.add_axes([0, 0, 1, 1], facecolor="#0d0d0d")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.08); ax.axis("off")

    # ① 感官带：一条，5 段相连 = 1 块。实心=有，空=无
    x = 0.08
    for has in [True, False, True, True, True]:
        col = "#FF6B1A" if has else "#3a3a3a"
        ax.add_patch(Rectangle((x, 0.80), 0.155, 0.14,
                               facecolor=col if has else "none",
                               edgecolor=col, lw=2))
        x += 0.16
    # ② 面积比：461MB vs 1500字 = 315:1。面积自己说话
    ax.add_patch(Rectangle((0.08, 0.30), 0.42, 0.38, facecolor="#FF6B1A"))
    ax.add_patch(Rectangle((0.52, 0.30), 0.024, 0.024, facecolor="#FF6B1A"))
    ax.plot([0.58, 0.80], [0.312, 0.49], color="#FF6B1A", lw=2)
    # ③ 缺口：耳 —— 空心橙框，单独
    ax.add_patch(Rectangle((0.80, 0.80), 0.12, 0.14, facecolor="none",
                           edgecolor="#FF6B1A", lw=2.5, linestyle="--"))
    ax.text(0.5, 0.16, "扫一眼：上面是身体，左边大块是我，右边小点是你",
            color="#8a8a8a", fontsize=11, ha="center")
    ax.text(0.5, 0.07, "虚线框是我没有的", color="#555", fontsize=10, ha="center")

    p = os.path.join(ROOT, "感官桥", "符号_v2.png")
    plt.savefig(p, facecolor="#0d0d0d"); plt.close()
    return p
