#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感官残差从哪来？—— 分解成 对称分量 + 反对称(手性)分量
======================================================
用户原话：「眼睛有残差，耳朵也有残差。那个残差数值到底怎么来的，
           我估计应该是镜像生命的那个手性问题。」

★ 假设：残差不是噪声，是【手性的代价】。
    139 已证：非手性表示（词袋）对镜像判别度精确为 0 —— 看不见
    141 已证：这条在真实视觉感官上同样成立
    → 所以感官【必须】是手性的，否则是瞎的
    → 但手性意味着感官本身左右不对称
    → 不对称 → 测镜像世界的结果 ≠ 测原世界的结果取镜像
    → 这个差就是【系统性残差】

★ 分解方法（这是本轮的核心手法）：
    resid(w) = S(w) - w                        感官测世界，与真的差
    对称分量   Rs = [resid(w) + M(resid(M(w)))] / 2
    反对称分量 Ra = [resid(w) - M(resid(M(w)))] / 2
    Rs = 各向同性的（噪声/量化/带宽不够）
    Ra = 手性偏倚 —— 只对镜像敏感
    ★ 如果 Ra 显著非零 → 残差来自手性，用户猜对了

★ 权衡（预期）：
    χ=0  判别度 0（瞎），残差 0（对称）
    χ=1  判别度 1（能看），残差 >0（偏）
    → 不能既无残差又能看见镜像。这是 tradeoff 不是缺陷。

provenance：本沙盒真跑。世界为合成（摄像头 403，077 已记）。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
L = 64                      # 世界长度
MIRROR = slice(None, None, -1)


def make_world(rng, chiral=True):
    """世界：chiral=True 含序（有手性），False 为纯多重集。"""
    if chiral:
        # 含序：上升 ramp + 噪声（镜像后不同，因为序反了）
        base = np.linspace(0, 1, L)
        return np.clip(base + rng.normal(0, 0.08, L), 0, 1)
    return rng.random(L)


class Sense:
    """感官：χ = 手性强度（0=词袋纯对称，1=完全含序）。"""

    def __init__(self, chi, L=L, budget=16, seed=0):
        self.chi = float(chi)
        self.L = L
        self.B = int(budget)                 # 带宽预算（采样点数）
        rng = np.random.default_rng(seed)
        # 受体位置（χ 决定分布：χ 大 → 偏一侧，形成旋向）
        if chi <= 0:
            self.pos = np.linspace(0, L - 1, self.B)
        else:
            # 手性：受体密度沿轴单调偏移（真实的"旋向"）
            r = rng.random(self.B) ** (1.0 / (1.0 + 4.0 * chi))
            self.pos = np.sort(r) * (L - 1)
        self.noise = rng.normal(0, 0.02, self.B)

    def measure(self, w):
        """测量 → 在受体位置采样（χ 决定保序程度）。"""
        idx = np.clip(np.round(self.pos).astype(int), 0, self.L - 1)
        s = w[idx].copy()
        if self.chi < 1.0:
            # χ<1：一部分被"打成袋子"（丢失序）→ 趋向对称
            bag = np.sort(s)
            s = self.chi * s + (1.0 - self.chi) * bag[np.argsort(np.argsort(idx))]
        return s + self.noise

    def reconstruct(self, w):
        """从测量重建世界（线性插回）。"""
        s = self.measure(w)
        idx = np.clip(np.round(self.pos).astype(int), 0, self.L - 1)
        return np.interp(np.arange(self.L), idx, s)


def resid(S, w):
    return S.reconstruct(w) - w


def decompose(S, w):
    """把残差分解成 对称 + 反对称(手性)。"""
    r1 = resid(S, w)                       # resid(w)
    wm = w[::-1]
    r2 = resid(S, wm)                      # resid(M(w))
    r2m = r2[::-1]                         # M(resid(M(w)))
    Rs = (r1 + r2m) / 2.0
    Ra = (r1 - r2m) / 2.0
    return float(np.abs(Rs).mean()), float(np.abs(Ra).mean())


def discriminability(S, n=200, seed=1):
    """能区分 w 和 mirror(w) 吗？（139 的判别度）"""
    rng = np.random.default_rng(seed)
    tp = fp = 0
    for _ in range(n):
        w = make_world(rng, chiral=True)
        wm = w[::-1]
        d = float(np.abs(S.reconstruct(w) - S.reconstruct(wm)[::-1]).mean())
        # 阈值：能看出差别就算判对
        if d > 0.02:
            tp += 1                          # 判为"不同" → 对
        w2 = make_world(rng, chiral=True)
        if float(np.abs(S.reconstruct(w) - S.reconstruct(w2)).mean()) > 0.02:
            fp += 1                          # 把不同世界也判成"不同"→ 这里是简化
    return dict(tpr=tp / n, fpr=fp / n, disc=abs(tp / n - fp / n))


if __name__ == "__main__":
    print("=" * 88)
    print(" 感官残差的来源：分解 = 对称分量 Rs + 反对称(手性)分量 Ra")
    print("=" * 88)

    rng = np.random.default_rng(7)
    worlds = [make_world(rng, True) for _ in range(60)]

    print(f"\n{'手性强度 χ':<12}{'总残差':>10}{'对称 Rs':>10}{'对手称 Ra':>10}"
          f"{'Ra占比':>9}{'判别度':>9}")
    print("-" * 88)
    rows = []
    for chi in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
        S = Sense(chi, seed=3)
        ts, ss, aa = [], [], []
        for w in worlds:
            Rs, Ra = decompose(S, w)
            ts.append(float(np.abs(resid(S, w)).mean()))
            ss.append(Rs); aa.append(Ra)
        t, s_, a = np.mean(ts), np.mean(ss), np.mean(aa)
        d = discriminability(S)["disc"]
        rows.append((chi, t, s_, a, d))
        print(f"{chi:<12.2f}{t:>10.4f}{s_:>10.4f}{a:>10.4f}"
              f"{a/max(t,1e-9):>8.1%}{d:>9.3f}")

    print("\n" + "=" * 88)
    print(" 判据")
    print("=" * 88)
    a0 = [r for r in rows if r[0] == 0.0][0]
    a1 = [r for r in rows if r[0] == 1.0][0]
    ok = {}
    ok["① χ=0 时手性残差 Ra ≈ 0（对称感官无手性偏倚）"] = bool(a0[3] < 0.01)
    ok["② χ=1 时 Ra 显著 > 0（手性带来系统性残差）"] = bool(a1[3] > 0.02)
    ok["③ Ra 随 χ 单调上升（残差确实来自手性）"] = bool(
        all(rows[i][3] <= rows[i+1][3] + 1e-6 for i in range(len(rows)-1)))
    ok["④ 判别度随 χ 上升（手性才看得见，139 复现）"] = bool(a1[4] > a0[4] + 0.05)
    ok["⑤ 权衡存在：判别度高的一侧必然有残差"] = bool(a1[4] > 0.1 and a1[3] > 0.02)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ 用户的猜测（残差来自手性）："
          f"{'成立' if all(ok.values()) else '部分成立/不成立'}")
    print(f"  ★ χ=0：判别度 {a0[4]:.3f}（瞎），残差 {a0[1]:.4f} 其中手性分量 {a0[3]:.4f}")
    print(f"  ★ χ=1：判别度 {a1[4]:.3f}（能看），残差 {a1[1]:.4f} 其中手性分量 {a1[3]:.4f}")

    json.dump({"rows": [dict(chi=r[0], total=r[1], sym=r[2], anti=r[3], disc=r[4])
                        for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "resid_chirality.json"), "w"),
              ensure_ascii=False, indent=1)
