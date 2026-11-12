#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
counterfactual —— 反事实与后悔（★97）

════════════════════════════════════════════════════════════
  ★96 她学会了「做」：P(Y|X=x) ≠ P(Y|do(X=x))。
  这一课是 Pearl 因果阶梯的最高层 —— **反事实**：

      对于一个已经发生的个体 i，若当时 X 取另一个值，Y 会是多少？

      Y_i(x')   其中  x' ≠ x_i 已观测到的那个

  这跟「干预」完全不同：
      干预   = 对**一群人**做 X=x' 的平均结果      E[Y(x')]
      反事实 = 对**已经发生的这一个**做 x'          Y_i(x')
  后者需要知道「这个个体是哪一类」，即未观测的 U。

════════════════════════════════════════════════════════════
  Pearl 反事实三步骤（硬算法，不是我编的）
════════════════════════════════════════════════════════════
    Abduction   用已观测的证据 (X=x, Y=y, Z=z) 反推未观测的 U 的后验
    Action      把结构方程里 X 的那一行换成 X = x'
    Prediction  在后验上积分，算出 Y_i(x')

════════════════════════════════════════════════════════════
  为什么反事实比干预难（真限定，不是建模选择）
════════════════════════════════════════════════════════════
  1. 干预可以对一群人做一次就验证；**反事实永远验证不了**
     —— 同一个个体、同一时刻，只能发生一次。
     → 这是根本限制 (fundamental problem of causal inference)。
     → 所以「知道自己的不确定度」是唯一诚实的产物。
  2. 结果噪声 ε 是这次实现的一部分，**重复测量消不掉**。
     → U 的后验宽度有不可约下限，再多测量也没用。
  3. 若效应人人相同 (tau=0)，反事实退化为群体 ATE，
     abduction 一文不值。异质性才是它存在的理由。

════════════════════════════════════════════════════════════
  她的四个旋钮
════════════════════════════════════════════════════════════
  n_meas   对这个个体重复测量几次（花钱；能压掉测量噪声，压不掉 ε）
  w0/w1    信不信「个体反事实」 vs 「群体平均」
           w = clip(w0 + w1·(sd_ref − sd_post), 0, 1)
           后验越窄 → 越信个体；后验越宽 → 退回群体平均
           （这就是统计里的 partial pooling / 收缩）
  theta    后验宽到什么程度就说「我说不准」
           —— 反事实不可证伪，abstain 是唯一诚实的选项
"""

import numpy as np
from scipy.stats import norm

B_XY = 1.0          # 基准效应
UG = np.linspace(-4.0, 4.0, 161)     # U 的后验网格
PRIOR = norm.pdf(UG)
C_MEAS = 1.0
MISS_PEN = 1.0      # abstain 的代价（与误差同量级）
LAM_COST = 0.004    # 每次测量的成本权重


def make_world(seed, tau=1.0, sig=0.8, nu=1.0, bu=1.0, au=0.8,
               a_conf=1.0, bx=1.2, mis=0.5):
    """
    tau    效应异质性：b_i = B_XY + tau·U_i     ← 反事实存在的理由
    sig    结果内在噪声 ε（不可通过重复测量消除）
    nu     单次测量噪声（可以靠重复测量压掉）
    mis    她的结构模型错多少（**方向随机，她不知道**）
           tau_hat = tau·(1 + ε_m)，  ε_m ~ U(−mis, +mis)
           → 有的世界她高估异质性，有的低估。单一 w 无法两头兼顾，
             于是「信个体模型」和「退回群体平均」之间出现真 bias-variance 权衡。
    """
    rng = np.random.default_rng(seed)
    em = rng.uniform(-mis, mis)
    return dict(seed=seed, tau=tau, sig=sig, nu=nu, bu=bu, au=au,
                a_conf=a_conf, bx=bx, mis=mis, eps_m=float(em),
                tau_hat=tau * (1.0 + em),
                a_hat=a_conf * (1.0 + 0.15 * em),
                au_hat=au * (1.0 - 0.10 * em))


def gen_cases(w, n, rng):
    """生成 n 个个体，每个都记录真反事实（U 是我造的，所以真值可算）"""
    U = rng.normal(size=n)
    Z = rng.normal(size=n)
    X = (w['bx'] * Z + w['bu'] * U + rng.normal(size=n) > 0).astype(float)
    b = B_XY + w['tau'] * U
    Y = b * X + w['a_conf'] * Z + w['au'] * U + w['sig'] * rng.normal(size=n)
    Xp = 1.0 - X                                   # 反事实：当时选另一个
    Ycf = b * Xp + w['a_conf'] * Z + w['au'] * U   # 真反事实（不含新 ε）
    return dict(U=U, Z=Z, X=X, Y=Y, Xp=Xp, Ycf=Ycf)


def _posterior(w, cs, n_meas, rng):
    """Abduction —— 她用她自己的（可能有误的）模型参数做后验推断"""
    n = len(cs['X'])
    ybar = cs['Y'][:, None] + (w['nu'] / np.sqrt(max(n_meas, 1))) * rng.normal(size=(n, 1))
    s_tot = np.sqrt(w['sig'] ** 2 + w['nu'] ** 2 / max(n_meas, 1))

    # P(X=x | U)  —— probit
    lin = (2 * cs['X'] - 1)[:, None] * (w['bx'] * cs['Z'][:, None] + w['bu'] * UG[None, :])
    llx = norm.logcdf(lin)
    # P(ȳ | U, X=x) —— 她的模型
    mu = ((B_XY + w['tau_hat'] * UG[None, :]) * cs['X'][:, None]
          + w['a_hat'] * cs['Z'][:, None] + w['au_hat'] * UG[None, :])
    lly = -0.5 * ((ybar - mu) / s_tot) ** 2

    lp = np.log(PRIOR)[None, :] + llx + lly
    lp -= lp.max(axis=1, keepdims=True)
    P = np.exp(lp); P /= P.sum(axis=1, keepdims=True)
    return P, ybar


def run(w, p, n_cases=240, rng=None, sd_ref=None, tau_override=None, **kw):
    rng = rng or np.random.default_rng(0)
    if tau_override is not None:
        w = dict(w, tau=tau_override)
    n_meas = int(round(p[0])); w0 = p[1]; w1 = p[2]; theta = p[3]
    cs = gen_cases(w, n_cases, rng)
    P, ybar = _posterior(w, cs, n_meas, rng)

    # Prediction：在后验上积分
    struct = (P * ((B_XY + w['tau_hat'] * UG[None, :]) * cs['Xp'][:, None]
                   + w['a_hat'] * cs['Z'][:, None]
                   + w['au_hat'] * UG[None, :])).sum(axis=1)
    # 群体平均版本：观测到的 y + 群体平均效应差
    pop = ybar[:, 0] + B_XY * (cs['Xp'] - cs['X'])

    sd_post = np.sqrt((P * (UG[None, :] - (P * UG[None, :]).sum(axis=1)[:, None]) ** 2).sum(axis=1))
    # sd_ref 由她自己从这一批里标定（可观测），于是差值有正有负
    ref = float(np.mean(sd_post)) if sd_ref is None else sd_ref
    w0 = min(max(w0, 1e-4), 1 - 1e-4)
    lg = np.log(w0 / (1.0 - w0)) + w1 * (ref - sd_post)
    wt = 1.0 / (1.0 + np.exp(-lg))
    pred = wt * struct + (1.0 - wt) * pop

    abst = sd_post > theta
    err_ind = np.abs(pred - cs['Ycf'])
    err = np.where(abst, MISS_PEN, err_ind)
    cost = LAM_COST * n_meas * C_MEAS
    return dict(err=float(err.mean() + cost), err_ind=float(err_ind.mean()),
                abst=float(abst.mean()), sd=float(sd_post.mean()),
                w=float(wt.mean()),
                err_ans=float(err_ind[~abst].mean()) if (~abst).any() else np.nan,
                err_abst=float(err_ind[abst].mean()) if abst.any() else np.nan)


def evaluate(p, worlds, nseed=10, n_cases=240, **kw):
    ws = [make_world(s) for s in worlds] if not isinstance(worlds[0], dict) else worlds
    es, ab, sd = [], [], []
    for w in ws:
        for k in range(nseed):
            r = run(w, p, n_cases=n_cases, rng=np.random.default_rng(1000 + k), **kw)
            es.append(r['err']); ab.append(r['abst']); sd.append(r['sd'])
    return float(np.mean(es)), float(np.mean(ab)), float(np.mean(sd))
