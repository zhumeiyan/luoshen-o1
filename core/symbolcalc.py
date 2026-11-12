#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
symbolcalc —— 符号演算与不确定度传播（★89）

════════════════════════════════════════════════════════════
  上一课（★88）给了她单位和符号登记。
  这一课：符号拿去做演算时，误差会怎么长大。
════════════════════════════════════════════════════════════

  ══ 硬定律 1：误差传播（一阶）══
      σ_f² = Σ_i (∂f/∂x_i)² σ_i²
             + 2 Σ_{i<j} (∂f/∂x_i)(∂f/∂x_j) Cov(x_i, x_j)

      第二项是协方差项。**大多数工程代码里它被省略了。**

  ══ 硬定律 2：协方差会沿推导链传递 ══
      z_k = f(z_{k-1}, x_new)
      Cov(z_{k-1}, x_new) ≠ 0
      因为 z_{k-1} 里含着更早的叶子，若与 x_new 共用噪声源就相关。
      → 误差不是独立地 √k 累加，是**带着相关性往下传**。

  ══ 硬定律 3：共用基准 ⇒ 误差相关 ══
      用同一个时钟/同一个参考电压读出来的两个数，
      它们的误差不是独立的 —— 基准漂了，两个一起漂。

  ══ 符号漂移 ══
      感官会老化/温漂。不重新标定，噪声按 √(1 + drift·τ) 放大。

════════════════════════════════════════════════════════════
  三个旋钮（全部应当有内部最优）
════════════════════════════════════════════════════════════

  λ  协方差记录密度  记全(贵, ∝节点对数) / 不记(省, 但误差估计有偏)
  τ  重标定周期      太频繁贵 / 太久漂移累积
  θ  接受阈值        太松→收下不可信的答案 / 太紧→把好答案也拒了

  预算共享：cov_vs_cal 二选一地花同一份钱 → 真权衡。
"""

from __future__ import annotations
import numpy as np

# ═══════════════════════════════════════════════════════════
#  一、尺子自检：一阶传播 vs 蒙特卡洛
# ═══════════════════════════════════════════════════════════

def first_order(f, x, sigma, cov):
    """
    一阶误差传播。x: 变量均值, sigma: 标准差, cov: 协方差矩阵
    """
    x = np.asarray(x, float)
    n = len(x)
    g = np.zeros(n)
    h = 1e-6
    for i in range(n):
        xp = x.copy(); xp[i] += h
        xm = x.copy(); xm[i] -= h
        g[i] = (f(xp) - f(xm)) / (2 * h)
    S = np.outer(sigma, sigma) * cov if cov.ndim == 2 else np.diag(sigma ** 2)
    return float(np.sqrt(max(g @ S @ g, 0.0)))


def monte_carlo(f, x, sigma, cov, rng, n=200000):
    x = np.asarray(x, float)
    S = np.outer(sigma, sigma) * cov
    X = rng.multivariate_normal(x, S, size=n)
    return float(np.std([f(v) for v in X[:20000]]))


def ruler_selfcheck(rng, verbose=False):
    """一阶传播 对 蒙特卡洛 —— 相差应远小于 1%"""
    out = []
    cases = [
        ("x+y", lambda v: v[0] + v[1], [2.0, 3.0], [0.10, 0.20], 0.6),
        ("x*y", lambda v: v[0] * v[1], [2.0, 3.0], [0.10, 0.20], 0.6),
        ("x/y", lambda v: v[0] / v[1], [2.0, 3.0], [0.10, 0.20], 0.6),
        ("x-y", lambda v: v[0] - v[1], [5.0, 1.0], [0.15, 0.25], -0.5),
    ]
    for name, f, x, s, r in cases:
        cov = np.array([[1.0, r], [r, 1.0]])
        a = first_order(f, x, np.array(s), cov)
        m = monte_carlo(f, x, np.array(s), cov, rng)
        rel = abs(a - m) / max(m, 1e-12)
        no = first_order(f, x, np.array(s), np.eye(2))   # 忽略协方差
        out.append(dict(name=name, first=a, mc=m, rel=rel,
                        no_cov=no, bias=(no - a) / a))
        if verbose:
            print(f"   {name:4s} 一阶={a:.5f} MC={m:.5f} 相对差={rel:.2%} "
                  f"忽略协方差={no:.5f} 偏差={ (no-a)/a:+.1%}")
    return out


# ═══════════════════════════════════════════════════════════
#  二、她的符号系统
# ═══════════════════════════════════════════════════════════

class SymbolSystem:
    """
    N 个基础符号（来自感官），部分共用噪声源 ⇒ 真实协方差非对角。
    推导链：z_k = op(z_{k-1}, x_new)，误差沿链传播，协方差跟着传。
    """

    def __init__(self, rng, n_sym=48, n_share=0, rho=0.55,
                 base_sigma=0.09, drift=0.010, n_query=40,
                 chain_len=8, seed=0, cm_frac=0.65):
        self.rng = rng
        self.N = int(n_sym)
        self.rho = float(rho)              # 共用噪声源产生的相关强度
        self.drift = float(drift)
        self.L = int(chain_len)
        self.Q = int(n_query)
        self._rng_build = np.random.default_rng(seed + 7777)

        # 真值
        self.true = self._rng_build.normal(1.0, 0.4, self.N)
        self.true = np.where(np.abs(self.true) < 0.25, 0.35, self.true)
        # 基础噪声
        self.sigma0 = np.abs(self._rng_build.normal(base_sigma, base_sigma * 0.3, self.N)) + 1e-3
        # ★ 共享因子（latent factor）：x_i = true_i + b·p_i·c + e_i
        #       Cov(x_i, x_j) = b² · p_i · p_j · σ_i σ_j     (i≠j)
        #   p_i = +1 / −1 是通道对这个共享因子的【极性】
        #
        #   物理事实：
        #     p 同号 → 共模。同一个 ADC / 同一参考源，源漂了所有通道一起漂。
        #     p 异号 → 竞争。共享有限资源（功耗预算 / 带宽），
        #              一个拿多了另一个就少 → 负相关。
        #
        #   ★ 关键：所以"忽略协方差"的后果【方向不定】——
        #     差分同号通道会消掉噪声（以为独立 ⇒ 高估误差 ⇒ 过度保守）
        #     求和异号通道也会消掉（同样 ⇒ 高估）
        #     但同号求和 / 异号相减会【放大】噪声（以为独立 ⇒ 低估 ⇒ 误收）
        #     这正是尺子自检里看到的：x+y −17.8%（低估），x/y +53.6%（高估）
        self.cm_frac = float(cm_frac)
        self.pol = self._rng_build.choice([-1.0, 1.0], self.N)
        self.share = np.zeros(self.N, int)
        P = np.outer(self.pol, self.pol)
        C = self.cm_frac * P
        np.fill_diagonal(C, 1.0)
        self.C = C
        self.Sigma = np.outer(self.sigma0, self.sigma0) * C

        # 查询链：每层一个运算 + 引用一个新叶子
        # ★ 查询链长随机（2..L）：不同问题需要不同深度的推导。
        #   这使真相对误差分布【宽】—— 否则 θ 的 ROC 无从谈起（★84 教训）。
        self.chains = []
        for _ in range(self.Q):
            L = int(self._rng_build.integers(2, self.L + 1))
            ops = [int(self._rng_build.integers(0, 4))]
            leaves = [(int(self._rng_build.integers(0, self.N)),
                       int(self._rng_build.integers(0, self.N)))]
            for _ in range(1, L):
                ops.append(int(self._rng_build.integers(0, 4)))
                leaves.append(int(self._rng_build.integers(0, self.N)))
            self.chains.append((ops, leaves))

    # ── 运算 ──
    @staticmethod
    def _apply(op, a, b):
        if op == 0:  return a + b
        if op == 1:  return a - b
        if op == 2:  return a * b
        b = b if abs(b) > 1e-6 else (1e-6 if b >= 0 else -1e-6)
        return a / b

    @staticmethod
    def _deriv(op, a, b):
        """返回 [∂f/∂a, ∂f/∂b]"""
        if op == 0:  return 1.0, 1.0
        if op == 1:  return 1.0, -1.0
        if op == 2:  return b, a
        bb = b if abs(b) > 1e-6 else (1e-6 if b >= 0 else -1e-6)
        return 1.0 / bb, -a / (bb * bb)

    def run(self, lam, tau, theta, drift=None, correlated=True, tol=0.15):
        """
        ★ 正确的传播方式：维护【梯度向量】 g_j = ∂z/∂x_j
            Var(z)      = gᵀ Σ g          ← 自动包含全部协方差项
            Cov(z, x_i) = (Σ g)_i
        梯度只由运算和值决定，与 λ 无关；
        λ 只影响她用的协方差矩阵：Σ_λ = 对角 + λ·非对角。

        λ=1 → 她知道所有通道共享参考源 ⇒ 误差估计准确
        λ=0 → 她以为各通道独立       ⇒ 系统性地算错误差
        真误差始终是 gᵀ Σ g，不因她记不记而改变。
        """
        d = self.drift if drift is None else drift
        amp = float(np.sqrt(1.0 + d * float(tau)))     # 不标定 ⇒ 噪声放大
        Sigma = self.Sigma * (amp ** 2)
        if not correlated:
            Sigma = np.diag(np.diag(Sigma))
        lam = float(np.clip(lam, 0.0, 1.0))
        # 她用的协方差矩阵：只记得住 λ 比例的"通道间相关"
        off = Sigma - np.diag(np.diag(Sigma))
        Sigma_est = np.diag(np.diag(Sigma)) + lam * off

        accepted = correct = wrong = rejected = 0
        est_rel = []; true_rel = []

        for ops, leaves in self.chains:
            L = len(ops)
            i0, j0 = leaves[0]
            val = self._apply(ops[0], self.true[i0], self.true[j0])
            g = np.zeros(self.N)
            da, db = self._deriv(ops[0], self.true[i0], self.true[j0])
            g[i0] = da; g[j0] = db

            for k in range(1, L):
                op = ops[k]; li = leaves[k]
                da, db = self._deriv(op, val, self.true[li])
                # 链式的梯度：z_new = f(z, x_li)
                #   ∂z_new/∂x_j = da · ∂z/∂x_j  (j 已有)
                #   ∂z_new/∂x_li = db
                g_new = da * g
                g_new[li] += db
                val = self._apply(op, val, self.true[li])
                g = g_new

            var_true = float(max(g @ Sigma @ g, 1e-18))
            var_est = float(max(g @ Sigma_est @ g, 1e-18))
            denom = max(abs(val), 1e-9)
            rel_t = float(np.sqrt(var_true) / denom)
            rel_e = float(np.sqrt(var_est) / denom)
            true_rel.append(rel_t); est_rel.append(rel_e)

            # ★ 正确性由【外部容差 tol】判定，不是由她的门槛 θ 判定。
            #   用 θ 判正确 = 她自己给自己打分 —— 那样 θ 越大"正确"越多，
            #   永远单调，测不出权衡。（★55/72/75/77/78/88 同一族错误）
            if rel_e <= theta:
                accepted += 1
                if rel_t <= tol: correct += 1
                else: wrong += 1
            else:
                rejected += 1

        n = self.Q
        w_wrong = 3.0
        gain = (correct * 1.0 - wrong * w_wrong - rejected * 0.15) / n
        bias = float(np.mean(np.array(est_rel) / np.maximum(np.array(true_rel), 1e-12) - 1.0))
        return gain, dict(accepted=accepted, correct=correct, wrong=wrong,
                          rejected=rejected, bias=bias,
                          est_rel=float(np.mean(est_rel)),
                          true_rel=float(np.mean(true_rel)))

    def common_mode_note(self):
        """共模噪声占比 —— 这个量她能自己测出来（同时读多个通道看它们是否一起抖）"""
        return self.cm_frac


# ═══════════════════════════════════════════════════════════
#  三、预算约束下的整体
# ═══════════════════════════════════════════════════════════

def build(seed, budget=None, c_cov=90.0, c_cal=260.0,
          n_sym=48, n_share=0, rho=0.55, drift=0.010,
          chain_len=8, n_query=40, correlated=True, cm_frac=0.65,
          sigma0=0.09):
    """
    成本模型（★ 关键，吸取 ★88 教训：共享 vs 每份要分清）
      协方差记录：定义的是【符号间关系】，记一次全系统共用 → ∝ 节点对数(≈L²)
      重标定：    【每个符号各来一次】          → ∝ N / τ
      两者共享同一份预算 → 真权衡
    """
    rng = np.random.default_rng(seed)
    sysm = SymbolSystem(rng, n_sym=n_sym, n_share=n_share, rho=rho,
                        drift=drift, n_query=n_query, chain_len=chain_len,
                        seed=seed, cm_frac=cm_frac, base_sigma=sigma0)
    L = chain_len
    if budget is None:
        budget = (c_cov * (L * (L - 1) / 2) * 0.55 + c_cal * n_sym / 12.0) * 0.9

    def evaluate(lam, tau, theta, corr=None, tol=0.15):
        corr = correlated if corr is None else corr
        tol = float(tol)
        cost = c_cov * lam * (L * (L - 1) / 2) + c_cal * n_sym / max(float(tau), 0.5)
        if cost > budget:
            # 超预算 ⇒ 能维护的符号数缩水（系统变小），不是免费
            shrink = max(0.05, budget / cost)
        else:
            shrink = 1.0
        g, st = sysm.run(lam, tau, theta, correlated=corr, tol=tol)
        return float(shrink * g), st

    return sysm, evaluate, budget


def estimate_noise(sysm, tau=8.0):
    """
    她从自己的读数里估计噪声水平 —— 她能看见的量，不需要 ground truth。
    方法：反复读同一个符号，看它抖多少。
    """
    diffs = []
    for _ in range(24):
        a = sysm.true + sysm.rng.normal(0, sysm.sigma0 * np.sqrt(1 + sysm.drift * tau), sysm.N)
        b = sysm.true + sysm.rng.normal(0, sysm.sigma0 * np.sqrt(1 + sysm.drift * tau), sysm.N)
        diffs.append(np.std(a - b) / np.sqrt(2))
    return float(np.mean(diffs))
