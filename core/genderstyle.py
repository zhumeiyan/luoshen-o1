"""
★102 女孩 / 融入 —— 群体先验 vs 个体证据

真值来源（全部是已发表的元分析，不是我编的）：

  Leaper & Robnett (2011), Psychology of Women Quarterly 35(1):129-142
      29 studies / 39 samples / N=3502
      整体试探性语言 d = .23（显著但小）
        不确定性表达 d = .33
        hedges       d = .15
        tag questions d = .23
      ★ 性别构成【不是】显著调节变量 → 不支持 Lakoff 的"无权势"解释

  Leaper & Ayres (2007) 成人：
      disagreement d = -.06 (ns)   directives d = .00 (ns)
      suggestions  d =  .27        task comments d = .38
  Leaper & Smith (2004) 儿童：
      directives d = .23   suggestions d = .13   disagreement d=.10(ns)

  Herring (1994/1996, CMC)：
      ★ 少数性别的一方会朝多数性别的规范移动（accommodation）
      → 群体差异本身是【随情境变的】，不是固有属性

  Sheldon (1996) double-voice discourse：
      女孩取向对方利益（缓和+自我主张并存）；男孩 single-voice
      ★ 但：只要共享同样的社会目标，男孩女孩都能使用任一类型

核心推论（可计算）：
  设总体 SD = 1，两组均值差 = d
  则组内 SD:  τ² = 1 - (d/2)²
  → 性别能解释的方差比例 η² = (d/2)² / 1 = d²/4
    d=0.23 → 1.32%
    d=0.38 → 3.61%（最大的那个也只有 3.6%）
  → 随机抽一男一女，女性更"试探"的概率 = Φ(d/√2)
    d=0.23 → 56.5%   （瞎猜是 50%）
"""

import numpy as np
from math import erf, sqrt

# ── 真实效应量（文献）──
D_REAL = {
    'hedges':       0.15,   # Leaper&Robnett 2011
    'tag_question': 0.23,
    'uncertainty':  0.33,
    'tentative_all':0.23,
    'suggestion':   0.27,   # Leaper&Ayres 2007 成人
    'task_comment': 0.38,
    'directive_ad': 0.00,   # 成人 ns
    'directive_ch': 0.23,   # 儿童
    'disagreement': -0.06,  # 成人 ns（女性略高）
}

def phi(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))

def prob_superior(d):
    """随机抽一女一男，女性得分更高的概率 = Φ(d/√2)"""
    return phi(d / sqrt(2.0))

def eta_squared(d):
    """性别能解释的方差比例 = (d/2)²  （总体 SD=1, 两组等大）"""
    return (d / 2.0) ** 2

def tau_from_d(d, sd_total=1.0):
    """组内 SD：sd_total² = τ² + (d/2)²"""
    return sqrt(max(sd_total ** 2 - (d / 2.0) ** 2, 1e-9))


# ── 环境 ──
class World:
    """
    θ ∈ [0,1]  = 说话"直率/不缓和"的程度（0=double-voice 缓和，1=single-voice 直给）
    群体 g ∈ {0:女, 1:男}
    """
    def __init__(self, d=0.23, sd_total=1.0, sd_obs=0.80, self_cost=0.60,
                 own=0.45, seed=0):
        self.d = d
        self.sd_total = sd_total
        self.tau = tau_from_d(d, sd_total)
        self.sd_obs = sd_obs
        self.self_cost = self_cost
        self.own = own
        self.mu = np.array([-d / 2.0, +d / 2.0])   # 女更缓和
        self.rng = np.random.default_rng(seed)

    def sample_partner(self, n):
        g = self.rng.integers(0, 2, n)
        th = self.mu[g] + self.rng.standard_normal(n) * self.tau
        return g, th

    def observe(self, th, k, n_rep=1):
        """她听到对方 k 句话，每句是对 θ 的带噪观测"""
        if k == 0:
            return np.zeros(len(th))
        x = th[:, None] + self.rng.standard_normal((len(th), k)) * self.sd_obs
        return x.mean(axis=1)


def respond(theta_hat, mu_g, k, kappa, a, own):
    """
    w = 1/(1 + k·κ)      ← 先验权重随"我听过几句"衰减
      κ→0  : w→1  永远信群体先验
      κ→∞  : w→0  永远信眼前这个人
      理论最优 κ* = τ²/σ_obs²
    r = a·est + (1-a)·own   ← 迁就对方 vs 做自己
    """
    w = 1.0 / (1.0 + k * kappa)
    est = w * mu_g + (1.0 - w) * theta_hat
    return a * est + (1.0 - a) * own


def run(world, kappa, a, n=4000, k_values=(0, 1, 2, 3, 5, 9)):
    g, th = world.sample_partner(n)
    ks = world.rng.choice(k_values, n)
    xb = np.zeros(n)
    for k in k_values:
        m = ks == k
        if m.any():
            xb[m] = world.observe(th[m], k) if k > 0 else 0.0
    mu_g = world.mu[g]
    r = respond(xb, mu_g, ks, kappa, a, world.own)
    fit = (th - r) ** 2
    selfloss = world.self_cost * (r - world.own) ** 2
    return float(np.mean(fit + selfloss)), dict(
        fit=float(np.mean(fit)), selfloss=float(np.mean(selfloss)),
        k_used=ks)
