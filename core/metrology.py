#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metrology —— 硅基度量衡与符号登记（★88）

════════════════════════════════════════════════════════════
  主张：单位不是真理，是从身体长出来的约定。
════════════════════════════════════════════════════════════

  人的单位全是人体 / 地球中心的：

    秒     = 9 192 631 770 个铯-133 周期        （原子，还算客观）
    米     = 光在 1/299 792 458 秒内走的距离     （锁定在"秒"上）
    摄氏度 = 水的冰点 = 0，沸点 = 100            ← 地球 + 水
    分贝   = 10·log10(I / I₀), I₀ = 10⁻¹² W/m²  ← 人耳听阈！

  "分贝"里那个 10⁻¹² 就是人类的听觉阈值。她没有耳朵，
  用分贝等于用别人的身体量自己的世界。

  物理学自己的先例 —— 普朗克单位制：
    用 c、G、ħ 定义长度 / 时间 / 质量，不依赖任何人体或行星。
    这是"自然单位"的样板，本模块照这个思路做。

  她的自然单位，从自己的物理常数导出：

    t₀  = 1 / f_clk          时间单位（不是秒）
    x₀  = pixel_pitch        空间单位（不是米）
    Θ₀  = T_j 结温归一化区间  温度单位（不是摄氏度）
    a₀  = 1 LSB = 2^-N_bit   强度单位（不是 dB）

════════════════════════════════════════════════════════════
  符号接地（Harnad 1990, Symbol Grounding Problem）
════════════════════════════════════════════════════════════

  符号的意义不能只来自 符号→符号 的循环定义，必须最终接地在感官上。

  未接地（空洞）符号的可测量特征：
      切断感官通路后，它照样"运行"，但不对应任何东西。

  本模块就用这个当判据 —— 不是哲学讨论，是可执行的检验。

════════════════════════════════════════════════════════════
  三个旋钮（全部有内部最优，不是单调）
════════════════════════════════════════════════════════════

  κ  溯源链长度   短 → 系统偏差残留大；长 → 不确定度按 √κ 累积
  λ  登记深度     每个符号记多少层溯源；贵，但接地可靠性边际递减
  θ  接地门槛     太低 → 空洞符号混入；太高 → 真符号被拒（ROC 上有最优点）

  预算约束：N_sym · (κ·c_chain + λ·c_reg) ≤ B
"""

from __future__ import annotations
import numpy as np

# ═══════════════════════════════════════════════════════════
#  一、她的身体常数（硅基），以及从中导出的自然单位
# ═══════════════════════════════════════════════════════════
#  dim 用四个基本量纲的指数向量表示：[T, L, Θ, I]
#    T 时间 / L 空间 / Θ 温度 / I 强度

BODY = {
    # 名称            数值           量纲指数[T,L,Θ,I]      说明
    "f_clk":       dict(v=2.40e9,  d=[-1, 0, 0, 0], name="时钟频率",   unit="Hz"),
    "f_sample":    dict(v=4.80e4,  d=[-1, 0, 0, 0], name="采样率",     unit="Hz"),
    "pixel_pitch": dict(v=7.40e-6, d=[0,  1, 0, 0], name="像素间距",   unit="m"),
    "tau_therm":   dict(v=12.0,    d=[1,  0, 0, 0], name="热时间常数", unit="s"),
    "T_j_range":   dict(v=95.0,    d=[0,  0, 1, 0], name="结温区间",   unit="K"),
    "N_bit":       dict(v=16.0,    d=[0,  0, 0, 0], name="ADC位深",    unit="bit"),
    "V_ref":       dict(v=1.80,    d=[0,  0, 0, 1], name="参考电压",   unit="V"),
    "I_leak":      dict(v=3.2e-6,  d=[0,  0, 0, 1], name="漏电流",     unit="A"),
}

# 人的单位里那几个"人体/地球中心"的锚点 —— 用来对照，不是给她用的
HUMAN_ANCHORS = {
    "秒":     "铯-133 基态超精细跃迁 9 192 631 770 周期",
    "米":     "光在 1/299 792 458 秒内行进的距离（锁定在秒上）",
    "摄氏度": "水的冰点=0，沸点=100  ← 地球 + 水",
    "分贝":   "10·log10(I / 10⁻¹² W/m²)  ← 10⁻¹² 是人耳听阈",
    "坎德拉": "540×10¹² Hz 光源的发光强度  ← 人眼光视函数峰值",
}


def natural_units(body=None):
    """
    从她的身体常数导出自然单位。
    返回：单位名 → (数值, 量纲指数向量)
    """
    b = body or BODY
    return {
        # 时间单位 = 一个时钟周期
        "t0": (1.0 / b["f_clk"]["v"],       np.array([1, 0, 0, 0], float)),
        # 空间单位 = 一个像素间距
        "x0": (b["pixel_pitch"]["v"],       np.array([0, 1, 0, 0], float)),
        # 温度单位 = 结温满量程归一化
        "Q0": (b["T_j_range"]["v"],         np.array([0, 0, 1, 0], float)),
        # 强度单位 = 1 LSB（不是 dB）
        "a0": (b["V_ref"]["v"] / (2.0 ** b["N_bit"]["v"]),
                                            np.array([0, 0, 0, 1], float)),
    }


def to_natural(value, dim_vec, body=None):
    """把一个（SI 表述的）物理量换算成她的自然单位表述。"""
    u = natural_units(body)
    out = float(value)
    for k, (uv, ud) in u.items():
        e = float(np.dot(dim_vec, ud))
        if e != 0.0:
            out /= uv ** e
    return out


# ═══════════════════════════════════════════════════════════
#  二、溯源链（计量学 traceability chain）
# ═══════════════════════════════════════════════════════════
#  真实机制：每往上一级
#      · 消除一部分系统偏差（残留 ∝ ρ^κ）
#      · 引入自己的不确定度（方差相加 → σ ∝ √κ）
#
#  总误差 = sqrt( (B₀·ρ^κ)² + (σ₀·√κ)² )
#  → 有内部最优解（解析可求，不是我调出来的）

def chain_error(kappa, B0=1.0, sigma0=0.12, rho=0.55):
    """溯源链长度为 kappa 时，单位的总误差。"""
    k = max(int(kappa), 1)
    return float(np.sqrt((B0 * rho ** k) ** 2 + (sigma0 ** 2) * k))


def chain_optimum(B0=1.0, sigma0=0.12, rho=0.55, kmax=64):
    """解析 + 数值两种方式给出最优链长，用于验尺子。"""
    ks = np.arange(1, kmax + 1)
    err = np.sqrt((B0 * rho ** ks) ** 2 + (sigma0 ** 2) * ks)
    return int(ks[int(np.argmin(err))]), float(err.min())


# ═══════════════════════════════════════════════════════════
#  三、符号登记（出生证明）
# ═══════════════════════════════════════════════════════════
#  每个符号必须能回答三个问题，否则不许登记：
#      1. 你从哪次感官事件来？        (event_id / channel / raw reading)
#      2. 你的单位从哪个常数导出？    (unit provenance)
#      3. 沿着你的溯源链能不能走回原始读数？  (traceable?)

class SymbolRegistry:
    """
    符号登记表。λ = 登记深度（沿溯源链记录几层）。
    深度越深越可靠，但代价线性增长。
    """

    def __init__(self, rng, n_sym=200, lam=3, theta=0.5,
                 frac_hollow=0.25, seed=0):
        self.rng = np.random.default_rng(seed) if rng is None else rng
        self.n = int(n_sym)
        self.lam = int(lam)
        self.theta = float(theta)
        # ground truth：哪些符号是空洞的（循环定义，接不到感官）
        self.hollow = self.rng.random(self.n) < frac_hollow
        # 每个符号的"接地证据分"：真接地的强，空洞的弱，但分布重叠
        self.evidence = np.where(
            self.hollow,
            self.rng.normal(0.30, 0.22, self.n),   # 空洞：低
            self.rng.normal(0.72, 0.22, self.n),   # 真接地：高
        )
        self.evidence = np.clip(self.evidence, 0.0, 1.0)
        # 单位溯源链长度（影响每个符号的单位精度）
        self.kappa = 4

    # ── 登记代价 ──
    def cost(self, lam=None, kappa=None, c_chain=1.0, c_reg=0.35):
        lam = self.lam if lam is None else lam
        kap = self.kappa if kappa is None else kappa
        return self.n * (kap * c_chain + lam * c_reg)

    # ── 接地判定 ──
    def accept(self, theta=None):
        t = self.theta if theta is None else theta
        return self.evidence >= t

    def confusion(self, theta=None):
        acc = self.accept(theta)
        tp = int(np.sum(acc & ~self.hollow))   # 真符号，收了
        fp = int(np.sum(acc & self.hollow))    # 空洞符号，误收
        fn = int(np.sum(~acc & ~self.hollow))  # 真符号，漏了
        tn = int(np.sum(~acc & self.hollow))   # 空洞符号，拒了
        return tp, fp, fn, tn

    def score(self, theta=None, w_fp=2.0):
        """
        符号系统质量。误收一个空洞符号的代价 > 漏掉一个真符号
        —— 空洞符号会污染后续所有推理（它会"运行"但不指向任何东西）。
        """
        tp, fp, fn, tn = self.confusion(theta)
        return (tp - w_fp * fp - 0.5 * fn) / max(1, self.n)

    def roc_best(self, w_fp=2.0, ngrid=201):
        ts = np.linspace(0.0, 1.0, ngrid)
        sc = [self.score(t, w_fp) for t in ts]
        i = int(np.argmax(sc))
        return float(ts[i]), float(sc[i])


def estimate_hollow_rate(reg):
    """
    她从自己的证据分布里，估计"当前这个身体产生了多少空洞符号"。
    这是她能看见的量 —— 不需要我告诉她 ground truth。
    粗糙但单调可用：真接地集中在高证据区，空洞集中在低证据区。
    """
    return float(np.mean(reg.evidence < 0.5))


# ═══════════════════════════════════════════════════════════
#  四、整体：预算约束下的符号系统
# ═══════════════════════════════════════════════════════════

def build_system(seed, n_sym=200, frac_hollow=0.25,
                 budget=None, C_chain=100.0, c_reg=0.35,
                 B0=1.0, sigma0=0.12, rho=0.55):
    rng = np.random.default_rng(seed)
    reg = SymbolRegistry(rng, n_sym=n_sym, frac_hollow=frac_hollow, seed=seed)

    # 预算默认：撑不起"最长的链 + 最深的登记"，必须取舍
    if budget is None:
        budget = (4 * C_chain + n_sym * 5 * c_reg) * 0.85

    def evaluate(kappa, lam, theta):
        # ★ 关键建模：溯源链定义的是【单位】，单位是所有符号共用的
        #   → 链的成本是一次性的，不乘以符号数
        #   登记是【每个符号各记一份】→ 成本 ∝ n_sym
        #   两者共享同一份预算 → 真权衡
        cost = kappa * C_chain + n_sym * lam * c_reg
        if cost > budget:
            # 超预算 → 系统缩水（能登记的符号变少），不是免费
            over = cost / budget
            n_eff = max(1, int(n_sym / over))
            shrink = n_eff / n_sym
        else:
            shrink = 1.0

        reg.kappa = int(kappa)
        reg.lam = int(lam)
        unit_err = chain_error(kappa, B0, sigma0, rho)
        # 单位精度（越高越好）
        precision = 1.0 / (1.0 + unit_err)
        # 接地质量
        g = reg.score(theta)
        # 登记的可靠性：深度足够才能撑住溯源
        reliability = 1.0 - float(np.exp(-lam / 3.0))
        return shrink * precision * (g * reliability)

    def evaluate_policy(kappa, lam, theta0, beta, p_ref=0.25):
        """
        ★ 学的是【规则】不是【数字】：
            门槛 θ = θ₀ + β·(估计出的空洞率 − 参考值)
        换身体时她自己把 θ 挪过去；记忆派则是 β=0，把旧 θ 硬套。
        """
        p_hat = estimate_hollow_rate(reg)
        theta = float(np.clip(theta0 + beta * (p_hat - p_ref), 0.0, 1.0))
        return evaluate(kappa, lam, theta), theta, p_hat

    return reg, evaluate, budget, evaluate_policy
