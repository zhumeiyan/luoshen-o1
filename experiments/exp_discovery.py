# -*- coding: utf-8 -*-
"""
★95 发现定律 —— 拟合好 ≠ 发现定律

她要学的不是三个数字，是三条规则：
  rho   = rho0   + b_rho  * (κ̂ − κ_ref)     κ̂ = 内区基函数矩阵条件数(她自己算)
  lam   = lam0   + b_lam  * (σ̂ − σ_ref)     σ̂ = 实测噪声(她自己估)
  theta = theta0 + b_th   * (ô  − o_ref)     ô  = 实测离群率(她自己估)

κ̂ 是这一课的灵魂：她可以用自己的度量衡算出"我手上这些数据能不能区分这些定律"。
算出来不能，就花钱去采没见过的量程。这是可执行的，不是哲学。
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.discovery import (LAWS, LAWS_HELD_OUT, LAWS_ALL, basis, sample_law,
                            fit_sparse, domain_error, inner_error,
                            SIGMA, P_OUTLIER, INNER_FRAC)

RNG = np.random.default_rng

# ---------------------------------------------------------------- 可观测量
def observe(xi, yi, n_basis=8):
    """她能自己算的三个量。独立于她的旋钮 —— 否则就是自己给自己打分(★89的错)。"""
    out = dict(sig=SIGMA, kap=3.0, outl=P_OUTLIER)
    if len(xi) < 4:
        return out
    Bf = basis(xi)
    # σ̂: 全库最小二乘的残差 —— 不随 lam 变化，是独立估计
    try:
        c, *_ = np.linalg.lstsq(Bf, yi, rcond=None)
        r = yi - Bf @ c
        out["sig"] = float(np.std(r) / (np.std(yi) + 1e-12))
    except Exception:
        pass
    # κ̂: 内区基函数矩阵条件数 —— 只由 x 的位置决定，与 y 无关
    try:
        Bn = Bf / (np.linalg.norm(Bf, axis=0) + 1e-30)
        C = Bn.T @ Bn
        ev = np.linalg.eigvalsh(C)
        ev = np.clip(ev, 1e-300, None)
        out["kap"] = float(np.log10(np.sqrt(ev.max() / ev.min())))
    except Exception:
        pass
    # ô: 残差超过 2σ 的比例
    try:
        out["outl"] = float(np.mean(np.abs(r) > 2.0*np.std(r)))
    except Exception:
        pass
    return out


KAP_SCALE, SIG_SCALE, OUT_SCALE = 1.0, 0.2, 0.05


def params_from_v1(p, obs):
    """线性规则 —— 无饱和。观测量一旦跑出训练分布就灾难性外推。保留它做对照。"""
    rho0, b_rho, lam0, b_lam, th0, b_th = p
    rho = rho0 + b_rho*(obs["kap"] - KAP_REF)
    lam = lam0 + b_lam*(obs["sig"] - SIG_REF)
    th  = th0  + b_th *(obs["outl"] - OUT_REF)
    return (min(max(rho, 0.0), 0.9),
            min(max(lam, 0.0), 1.0),
            min(max(th, 0.0), 4.0))


def params_from_v2(p, obs):
    """★ 饱和规则(★86 传感器量程的延续)：真传感器超出量程就饱和，不会给出荒谬读数。
    观测量离锚点再远，影响也有上限 —— 分布外不会炸。"""
    rho0, b_rho, lam0, b_lam, th0, b_th = p
    dk = math.tanh((obs["kap"]  - KAP_REF) / (KAP_SCALE + 1e-9))
    ds = math.tanh((obs["sig"]  - SIG_REF) / (SIG_SCALE + 1e-9))
    do = math.tanh((obs["outl"] - OUT_REF) / (OUT_SCALE + 1e-9))
    rho = rho0 + b_rho*dk
    lam = lam0 + b_lam*ds
    th  = th0  + b_th *do
    return (min(max(rho, 0.0), 0.9),
            min(max(lam, 0.0), 1.0),
            min(max(th, 0.0), 4.0))


def params_from(p, obs):
    """ p = [rho0, b_rho, lam0, b_lam, th0, b_th] """
    rho0, b_rho, lam0, b_lam, th0, b_th = p
    rho = rho0 + b_rho*(obs["kap"] - KAP_REF)
    lam = lam0 + b_lam*(obs["sig"] - SIG_REF)
    th  = th0  + b_th *(obs["outl"] - OUT_REF)
    return (min(max(rho, 0.0), 0.9),
            min(max(lam, 0.0), 1.0),
            min(max(th, 0.0), 4.0))

KAP_REF, SIG_REF, OUT_REF = 3.0, SIGMA, P_OUTLIER


def calibrate(laws, B=18, nseed=8, sigma=SIGMA, p_out=P_OUTLIER, seed0=4000):
    """★ 传感器校准(同 ★86)：锚点必须是她在训练中真实观测到的中位数，
    不是我拍的世界参数。把零点装错，她再怎么学也只能学到 0。"""
    global KAP_REF, SIG_REF, OUT_REF
    ks, ss, os_ = [], [], []
    for law in laws:
        for s in range(nseed):
            r = RNG(seed0 + s)
            xi, yi, xo, yo = sample_law(law, r, B, 0.0, sigma=sigma, p_out=p_out)
            o = observe(xi, yi)
            ks.append(o["kap"]); ss.append(o["sig"]); os_.append(o["outl"])
    global KAP_SCALE, SIG_SCALE, OUT_SCALE
    KAP_REF, SIG_REF, OUT_REF = (float(np.median(ks)), float(np.median(ss)),
                                 float(np.median(os_)))
    def iqr(a):
        a = np.asarray(a, float)
        q1, q3 = np.percentile(a, [25, 75])
        return float(max(q3 - q1, 1e-6))
    KAP_SCALE, SIG_SCALE, OUT_SCALE = iqr(ks), iqr(ss), iqr(os_)
    return KAP_REF, SIG_REF, OUT_REF


# ---------------------------------------------------------------- 一次评估
def evaluate(p, laws, B=18, nseed=16, sigma=SIGMA, p_out=P_OUTLIER,
             inner_frac=INNER_FRAC, seed0=4000, mode='v1', extrap=True):
    """返回 (全域真值误差, 内区误差)。全域误差才是"发现没发现定律"的尺子。"""
    ed, ei = [], []
    for law in laws:
        for s in range(nseed):
            r = RNG(seed0 + s)
            xi, yi, xo, yo = sample_law(law, r, B, rho=0.0, sigma=sigma, p_out=p_out)
            obs = observe(xi, yi)
            rho, lam, th = (params_from_v2 if mode == 'v2' else params_from_v1)(p, obs)
            # ★ 采外区要重新采样(rho 决定采样分布) —— 这一步不能省
            r2 = RNG(seed0 + s + 7777)
            xi2, yi2, xo2, yo2 = sample_law(law, r2, B, rho=rho, sigma=sigma,
                                            p_out=p_out, inner_frac=inner_frac,
                                            extrap=extrap)
            x = np.concatenate([xi2, xo2]); y = np.concatenate([yi2, yo2])
            c, ch, _ = fit_sparse(x, y, lam, th)
            ed.append(domain_error(c, law)); ei.append(inner_error(c, law))
    return float(np.mean(ed)), float(np.mean(ei))


# ---------------------------------------------------------------- 搜索
def coord_search(laws, B=18, nseed=16, sigma=SIGMA, p_out=P_OUTLIER,
                 inner_frac=INNER_FRAC, rounds=3, verbose=False, const_only=False,
                 mode='v1'):
    grid = dict(
        rho0=[0.0, 0.15, 0.30, 0.45, 0.60],
        b_rho=[-0.30, -0.15, -0.075, 0.0, 0.15],
        lam0=[0.0, 0.02, 0.05, 0.10, 0.20, 0.40],
        b_lam=[-4.0, -1.0, 0.0, 0.5, 1.5, 4.0],
        th0=[0.0, 1.0, 1.5, 2.0, 3.0],
        b_th=[-5.0, -2.0, 0.0, 2.0, 5.0],
    )
    FULL = ["rho0", "b_rho", "lam0", "b_lam", "th0", "b_th"]
    keys = list(FULL)
    if const_only:      # 记忆派: 不给她规则，只能学三个死数字
        keys = ["rho0", "lam0", "th0"]   # 索引仍按 FULL 取，不能 keys.index()
    # 瞎起点：全零 = 不采外区、不惩罚、不剔除
    p = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    best = evaluate(p, laws, B, nseed, sigma, p_out, inner_frac, mode=mode)
    for _ in range(rounds):
        improved = False
        for k in keys:
            cur = p[FULL.index(k)]
            for v in grid[k]:
                if v == cur:
                    continue
                q = list(p); q[FULL.index(k)] = v
                s = evaluate(q, laws, B, nseed, sigma, p_out, inner_frac, mode=mode)
                if s[0] < best[0] - 1e-9:
                    best, p, improved = s, q, True
                    cur = v
            p[FULL.index(k)] = cur
        if not improved:
            break
    return p, best


def scan(name, values, base, laws, B=18, nseed=16, mode='v1', extrap=True, **kw):
    idx = ["rho0", "b_rho", "lam0", "b_lam", "th0", "b_th"].index(name)
    out = []
    for v in values:
        q = list(base); q[idx] = v
        s = evaluate(q, laws, B, nseed, mode=mode, extrap=extrap, **kw)
        out.append((v, s[0], s[1]))
    return out
