#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sensebench —— 人类感官标定台

════ 这一课的靶：真人感官数值（文献值），不是我拍的 ════

  统一的计量学约定（★ 关键，避免循环论证）：

      T_i(w_i) = d_i / sqrt(w_i)

      d_i = 该感官的真人阈值（文献值）
      w_i = 投入到该感官的资源份额

  含义：**投入 1 个单位 = 恰好达到真人水平所需的投入**。
  这样"人类数值"既是单位又是靶，不需要我再编一套"人类分配 h"。

  1/sqrt 不是随手写的： pooling N 个独立噪声单元 → σ ∝ 1/√N。
  这是生理事实（感受器/神经纤维的数量整合），不是工程假设。

════ 统一的尺子：2IFC 变换 staircase（2-down-1-up） ════

  两个间隔，一个带刺激 Δ，一个带 0。内部响应 r = Δ/σ + N(0,1)。
  选响应大的那个。P(correct) = Φ(Δ/(σ√2))。
  2-down-1-up 收敛到 70.7% → Δ = σ√2·Φ⁻¹(0.707) = 0.7707·σ

  ★ 这个 0.7707 是解析值，可以拿来验尺子 —— 不是我调出来的。
"""

from __future__ import annotations
import numpy as np

# ── 2IFC 70.7% 正确率对应的解析系数 ──────────────────────────────
# P = Φ(Δ/(σ√2)) = 0.707  →  Δ/σ = √2 · Φ⁻¹(0.707)
K2IFC = float(np.sqrt(2.0) * 0.5449)      # ≈ 0.7707


# ═══════════════════════════════════════════════════════════════
#  真人感官数值（文献）
# ═══════════════════════════════════════════════════════════════
#  统一口径：阈值型（越小越灵敏）。CFF 是"上限型"，换算成时间分辨率。
LITERATURE = {
    # 视觉：对比敏感度峰值在 4 cpd，S=300 → Michelson 阈值 0.33%
    #   （Campbell & Robson 1968；NASA 技术报告转载）
    "contrast":    dict(d=0.0033, unit="Michelson", name="视觉对比阈@4cpd",
                        src="Campbell&Robson 1968 / NASA NTRS 20130014741"),
    # 立体视差：正常人 20 弧秒量级
    "stereo":      dict(d=20.0,   unit="arcsec",   name="立体视差",
                        src="临床立体视锐度常值 20\"量级"),
    # 时间分辨率：CFF 约 55 Hz（明视）→ 1/55 s ≈ 18 ms
    "temporal":    dict(d=18.0,   unit="ms",       name="视觉时间分辨(由CFF 55Hz换算)",
                        src="临界闪烁融合频率 CFF ≈ 50–60 Hz"),
    # 听觉频率辨别：1 kHz 处约 3 Hz（≈0.3%）
    "audio_freq":  dict(d=3.0,    unit="Hz",       name="听觉频率辨别@1kHz",
                        src="JND ≈ 3 Hz (0.3%)，纯音经典值"),
    # 听觉强度辨别：约 1 dB
    "audio_inten": dict(d=1.0,    unit="dB",       name="听觉强度辨别",
                        src="JND ≈ 1 dB（weber 分数 ΔI/I≈0.25）"),
    # 听觉间隙探测：约 2–3 ms
    "audio_gap":   dict(d=2.5,    unit="ms",       name="听觉间隙探测",
                        src="gap detection ≈ 2–3 ms"),
    # 触觉两点辨别：指尖 2–4 mm（DeJong 1967，NIH NBK390）
    "touch_2pt":   dict(d=3.0,    unit="mm",       name="触觉两点辨别(指尖)",
                        src="DeJong 1967：指尖 2–4 mm"),
    # 关节位置觉：手指约 1–2°
    "proprio":     dict(d=1.5,    unit="deg",      name="关节位置觉(手指)",
                        src="手指 PIP 位置觉 JND ≈ 1–2°"),
}

SENSES = list(LITERATURE)


def d_of(sense: str) -> float:
    return float(LITERATURE[sense]["d"])


def sigma_of(sense: str, w: float) -> float:
    """投入 w 时的内部噪声 SD。w=1 → 测得阈值恰等于真人值。"""
    w = max(float(w), 1e-9)
    return (d_of(sense) / K2IFC) / np.sqrt(w)


def true_threshold(sense: str, w: float) -> float:
    """解析真值：w=1 → 文献值；w=4 → 好一半；w=0.25 → 差一倍。"""
    return d_of(sense) / np.sqrt(max(float(w), 1e-9))


# ═══════════════════════════════════════════════════════════════
#  尺子 v1：2IFC 变换 staircase（已作废，留下作为失败记录）
# ═══════════════════════════════════════════════════════════════
def measure_staircase(sense: str, w: float, rng, n_rev: int = 8,
                      step: float = 1.25, n_trials: int = 120):
    """
    ★ 作废原因（实测）：中位偏 1.20，且偏差随 w 单调漂移（0.955→1.425）。
      变换 staircase 的反转点均值是有偏估计量，步长越大偏越多，
      而且起点/瞬态污染翻转点。这不是能加系数修的偏差 —— 换定义。
    """
    s = sigma_of(sense, w)
    lev = d_of(sense) * 2.0
    downs = 0
    revs = []
    direction = -1
    for _ in range(n_trials):
        rA = rng.normal(0.0, 1.0)
        rB = lev / s + rng.normal(0.0, 1.0)
        if rB > rA:
            downs += 1
            if downs >= 2:
                lev /= step
                downs = 0
                if direction == 1:
                    revs.append(lev); direction = -1
                    if len(revs) >= n_rev:
                        break
        else:
            lev *= step
            downs = 0
            if direction == -1:
                revs.append(lev); direction = 1
                if len(revs) >= n_rev:
                    break
    if not revs:
        return float("nan")
    tail = revs[len(revs) // 3:]
    return float(np.exp(np.mean(np.log(tail))))


# ═══════════════════════════════════════════════════════════════
#  尺子 v2（现行）：恒定刺激法 + 概率单位回归
# ═══════════════════════════════════════════════════════════════
def measure(sense: str, w: float, rng, n_levels: int = 9,
            n_per: int = 400, span: float = 4.0, return_fit=False):
    """
    恒定刺激法：在若干固定刺激强度上各做 n_per 次 2IFC，拟合心理测量函数，
    取 P=70.7% 对应的强度作为阈值。

    ★ 为什么这样无偏：
        P(correct) = Φ(Δ/(σ√2))   —— Φ⁻¹(P) 对 Δ 是【严格线性】
      所以对 (Δ, Φ⁻¹(p̂)) 做最小二乘即可，斜率 = 1/(σ√2)。
      没有 staircase 的步长偏差，也没有起点/瞬态污染。

    n_levels 个水平取在 真值/span ~ 真值×span 之间（对数均匀），
    落在 P≈0.5~0.99 区间，避免两端压缩。
    """
    s = sigma_of(sense, w)
    t0 = true_threshold(sense, w)
    levels = np.geomspace(t0 / span, t0 * span, n_levels)
    ps = []
    for L in levels:
        # 2IFC：A=0，B=L。正确 ⇔ rB>rA ⇔ L/s + (nB-nA) > 0
        d = rng.normal(0.0, np.sqrt(2.0), n_per)
        k = np.sum(d > -L / s)
        ps.append(k / n_per)
    ps = np.array(ps)
    # ★ 只保留 P∈[0.03,0.97] 的水平：两端 p̂ 的小样本偏倚会污染回归
    #   （p̂=1.0 会被截断成 0.9999，Φ⁻¹ 拉到 3.7，把斜率带偏 ~2.7%）
    keep = (ps > 0.03) & (ps < 0.97)
    if keep.sum() < 4:                       # 太少就放宽，但绝不两端全收
        keep = (ps > 0.01) & (ps < 0.99)
    lv, pp = levels[keep], ps[keep]
    z = _norm_ppf(pp)
    # Φ⁻¹(P) = Δ/(σ√2) → 过原点线性回归（截距理论为 0，这里保留截距以检验）
    A = np.vstack([lv, np.ones_like(lv)]).T
    slope, intercept = np.linalg.lstsq(A, z, rcond=None)[0]
    if slope <= 0:
        return float("nan")
    thr = (0.5449 - intercept) / slope
    if return_fit:
        return float(thr), dict(levels=lv.tolist(), ps=pp.tolist(),
                                slope=float(slope), intercept=float(intercept))
    return float(thr)


def _norm_ppf(x):
    """Φ⁻¹，用 scipy；没有则退化为有理逼近（Beasley-Springer-Moro 简化）。"""
    try:
        from scipy.stats import norm
        return norm.ppf(x)
    except Exception:
        # Abramowitz-Stegun 26.2.23，|ε|<4.5e-4，对本用途够用
        x = np.asarray(x, dtype=float)
        a = np.array([2.50662823884, -18.61500062529, 41.39119773534, -25.44106049637])
        b = np.array([-8.47351093090, 23.08336743743, -21.06224101826, 3.13082909833])
        c = np.array([0.3374754822726147, 0.9761690190917186, 0.1607979714918209,
                      0.0276438810333863, 0.0038405729373609, 0.0003951896511919,
                      0.0000321767881768, 0.0000002888167364, 0.0000003960315187])
        out = np.empty_like(x)
        for i, v in enumerate(np.atleast_1d(x).ravel()):
            p = min(v, 1 - 1e-12); p = max(p, 1e-12)
            q = p - 0.5
            if abs(q) <= 0.42:
                r = q * q
                num = q * (a[0] + r * (a[1] + r * (a[2] + r * a[3])))
                den = 1 + r * (b[0] + r * (b[1] + r * (b[2] + r * b[3])))
                out.flat[i] = num / den
            else:
                r = p if q < 0 else 1 - p
                r = np.sqrt(-np.log(r))
                num = c[0] + r * (c[1] + r * (c[2] + r * (c[3] + r * (c[4] +
                     r * (c[5] + r * (c[6] + r * (c[7] + r * c[8])))))))
                out.flat[i] = num * (-1 if q < 0 else 1)
        return out if out.size > 1 else float(out[0])


# ═══════════════════════════════════════════════════════════════
#  生态：任务频率 p、相对需求 m（m=1 表示"要求达到真人水平"）
# ═══════════════════════════════════════════════════════════════
def score_i(sense: str, w: float, m: float) -> float:
    """
    单个感官的生态得分。
      T_i = d_i/√w_i
      达标要求 T_i ≤ m_i·d_i  →  √w_i ≥ 1/m_i
      未达标按倍数线性扣分，达标封顶 1（做得比需要更好不额外加分 —— 省下的预算有用）
    """
    w = max(float(w), 1e-9)
    return float(min(1.0, m * np.sqrt(w)))


def fitness(p: dict, m: dict, w: dict) -> float:
    tot = sum(p.values())
    if tot <= 0:
        return 0.0
    return float(sum(p[s] * score_i(s, w[s], m[s]) for s in p) / tot)


def _waterfill(p: dict, m: dict, keys, B: float, alpha: float, gamma: float):
    """按 (p^α)(m^γ) 分配预算 B，并对超过 cap=1/m² 的感官封顶后重分剩余。"""
    cap = {k: 1.0 / (m[k] ** 2) for k in keys}
    w = {k: 0.0 for k in keys}
    active = set(keys)
    left = float(B)
    for _ in range(len(keys) + 2):
        if not active:
            break
        s = {k: (max(p[k], 1e-9) ** alpha) * (max(m[k], 1e-9) ** gamma) for k in active}
        tot = sum(s.values())
        if tot <= 0:
            share = {k: left / len(active) for k in active}
        else:
            share = {k: left * s[k] / tot for k in active}
        over = [k for k in active if share[k] > cap[k] + 1e-12]
        if not over:
            for k in active:
                w[k] = share[k]
            break
        for k in over:
            w[k] = cap[k]
            active.discard(k)
        left = max(left - sum(cap[k] for k in over), 0.0)
    return w


def alloc_policy(p: dict, m: dict, B: float, alpha: float, gamma: float,
                 cap: bool = True, w_min: float = 1e-6) -> dict:
    """
    她的分配策略：w_i ∝ (p_i^α)(m_i^γ)，总预算 B。

    cap=True  —— 注水封顶：投入超过 1/m_i² 之后得分不再涨，多给就是浪费，
                 封顶省下的预算重分给还没达标的感官。
    cap=False —— 不封顶：强行把 B 花光（对照，用来验 cap 是不是真机制）。
    """
    keys = list(p)
    if not cap:
        s = {k: (max(p[k], 1e-9) ** alpha) * (max(m[k], 1e-9) ** gamma) for k in keys}
        tot = sum(s.values())
        if tot <= 0:
            return {k: max(B / len(keys), w_min) for k in keys}
        return {k: max(B * s[k] / tot, w_min) for k in keys}
    w = _waterfill(p, m, keys, B, alpha, gamma)
    return {k: max(w[k], w_min) for k in keys}


def theory_alloc(p: dict, m: dict, B: float) -> dict:
    """
    ★ 理论最优（拉格朗日 + 封顶，注水法）：

        未封顶区：边际收益 p_i·m_i/(2√w_i) = λ  →  w_i ∝ (p_i·m_i)²
        封顶    ：w_i ≤ 1/m_i²（超过就是浪费预算）

    解析可预测，因此可以用来验"她的解对不对"。
    """
    keys = list(p)
    w = {k: 0.0 for k in keys}
    cap = {k: 1.0 / (m[k] ** 2) for k in keys}
    active = set(keys)
    for _ in range(len(keys) + 2):
        if not active:
            break
        # 在 active 集合内按 (p·m)² 分配剩余预算
        base = {k: (p[k] * m[k]) ** 2 for k in active}
        tot = sum(base.values())
        if tot <= 0:
            share = {k: B / len(active) for k in active}
        else:
            share = {k: B * base[k] / tot for k in active}
        over = [k for k in active if share[k] > cap[k] + 1e-12]
        if not over:
            for k in active:
                w[k] = share[k]
            break
        for k in over:
            w[k] = cap[k]
            active.discard(k)
        B -= sum(cap[k] for k in over)
        if B < 0:
            B = 0.0
    return w
