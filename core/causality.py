#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
causality —— 因果与干预（★96）

════════════════════════════════════════════════════════════
  前几课她学会了从数据里「发现定律」(★95)。但定律是从**看**来的。
  这一课：看 和 做 是两件事。

      P(Y | X=x)      ≠   P(Y | do(X=x))

════════════════════════════════════════════════════════════
  硬定律（全部可算真值，不由我编）
════════════════════════════════════════════════════════════

  1. 后门校正（backdoor adjustment）
     P(Y|do(x)) = Σ_z P(Y|x,z)·P(z)
     控制住混杂子 z，观察关联才等于因果效应。
     → 但只对**混杂子**成立。控制别的东西会更糟。

  2. 对撞机（collider）X → Z ← Y
     边际上 Z 与 X 相关、也与 Y 相关 —— 看起来和混杂子一模一样。
     但控制它会**打开**一条本来不存在的通路，凭空造出偏差。
     （Berkson 悖论：住院病人里肺炎与骨折「相关」）
     → 判据：混杂子在 X 之前，对撞机在 X 之后。**只有时间顺序能分开它们。**

  3. 中介（mediator）X → M → Y
     控制中介会挡掉间接通路 → 得到的是**直接效应**，不是总效应。
     对不对看你要什么；要总效应时它是错的。

  4. 未测混杂（unmeasured confounding）U → X, U → Y
     U 没被观测到 —— 你校正不了它。这是 RCT 存在的唯一理由。
     → 观察性研究无论如何调整，偏差都消不掉。

  5. 随机化消除混杂
     RCT 里 X 与一切前因独立 → 无偏。但每个样本贵得多（c_r ≫ c_o）。
     → 无偏 vs 便宜，是真权衡，不是信仰。

  6. 逆方差合并
     两个独立估计 → w ∝ 1/var。
     但**便宜的那个样本多、方差小，会压过贵的那个** ——
     于是偏差被放大。样本多不是优势，可能是陷阱。

════════════════════════════════════════════════════════════
  她的五个旋钮
════════════════════════════════════════════════════════════
  alpha0 / beta   α = clip(alpha0 + beta·Δ̂, 0, 1)
                  Δ̂ = 试点阶段「观察估计 − RCT 估计」之差
                  → 用一小笔钱做实验，量出观察有多偏，再决定剩下多少钱买实验。
                    这就是「用实验校准观察」，不是猜。
  theta0 / gamma  θ = clip(theta0 + gamma·σ̂²_噪声, 0, 1)
                  纳入协变量的关联强度门槛
                  → 协变量是带噪声读出来的，噪声越大真实关联被压得越低，
                    门槛就得跟着降。（她能自己估噪声：两次独立读数）
  omega           post-X 协变量额外门槛（0=一视同仁，1=永不纳入）
                  → 对撞机/中介都在 X 之后。
"""

import numpy as np

# ── 结构方程（真值，不让她看见）────────────────────────────
B_XY = 1.0      # X → Y 直接效应
B_XM = 1.0      # X → M
B_MY = 1.0      # M → Y
TRUE_TOTAL = B_XY + B_XM * B_MY    # 2.0
TRUE_DIRECT = B_XY                 # 1.0

C_OBS, C_RCT, C_COV = 1.0, 3.0, 120.0
P_PILOT = 0.25


# ──────────────────────────────────────────────────────────
def make_world(seed, nu=0.5, n_noise=6, sig_y=1.0, collider=True, mediator=True,
               late=True, bu=None, au=None, bx=None, cx=None, cy=None):
    """
    真实混杂强度由 bu·au 决定 —— 跨度必须大：
      有的世界观察就够用（bu·au≈0），有的必须做实验。
      这样「买多少实验」才是个真权衡，而不是永远全买。
    """
    rng = np.random.default_rng(seed)
    return dict(
        seed=seed,
        a_conf=rng.uniform(0.3, 1.8),                     # Zc → Y
        a_conf2=rng.uniform(0.6, 2.0),                    # Zc2 → Y  (只在 X 之后被记录!)
        bx2=rng.uniform(0.3, 0.9),                        # Zc2 → X
        bx=rng.uniform(0.8, 2.2) if bx is None else bx,   # Zc → X
        bu=rng.uniform(0.0, 1.8) if bu is None else bu,   # U → X   (未测!)
        au=rng.uniform(0.0, 1.8) if au is None else au,   # U → Y   (未测!)
        nu=nu, n_noise=n_noise, sig_y=sig_y,
        collider=collider, mediator=mediator, late=late,
        cx=rng.uniform(1.2, 2.5) if cx is None else cx,   # X → 对撞机
        cy=rng.uniform(0.2, 2.0) if cy is None else cy,   # Y → 对撞机
    )


def _core(w, n, rng, X, Zc, U, Zc2):
    """给定外生的 X、Zc、Zc2、U，生成下游 M 与 Y"""
    M = B_XM * X + rng.normal(size=n) * 0.6
    Y = (B_XY * X + B_MY * M + w['a_conf'] * Zc + w['a_conf2'] * Zc2
         + w['au'] * U + rng.normal(size=n) * w['sig_y'])
    return M, Y


def gen(w, n, rng, mode='obs'):
    """mode: obs=观察(X 受 Zc,U 影响→有混杂) / rct=随机化 / do=干预"""
    Zc = rng.normal(size=n)
    Zc2 = rng.normal(size=n)     # 第二个混杂子 —— 物理上在 X 之前，但记录得晚
    U = rng.normal(size=n)
    if mode == 'obs':
        X = (w['bx'] * Zc + w['bx2'] * Zc2 + w['bu'] * U
             + rng.normal(size=n) > 0).astype(float)
    elif mode == 'rct':
        X = (rng.random(n) < 0.5).astype(float)
    else:                                    # do(X = mode)
        X = np.full(n, float(mode))
    M, Y = _core(w, n, rng, X, Zc, U, Zc2)

    # ── pre-X 观测：混杂子 Zc + n_noise 个纯噪声（各读两次，用于自估噪声）──
    pre = [Zc] + [rng.normal(size=n) for _ in range(w['n_noise'])]
    nu = w['nu']
    Zpre = np.column_stack([z + nu * rng.normal(size=n) for z in pre])
    Zpre2 = np.column_stack([z + nu * rng.normal(size=n) for z in pre])

    # ── post-X 观测：三类混在一起，她只看得到时间戳 ──
    post = []
    if w['collider']:
        post.append(w['cx'] * X + w['cy'] * Y + rng.normal(size=n) * 0.5)   # 不该纳入
    if w['mediator']:
        post.append(M)                                                      # 不该纳入(要总效应)
    if w['late']:
        post.append(Zc2)                                                    # 该纳入! 只是记晚了
    Zpost = (np.column_stack([z + nu * rng.normal(size=n) for z in post])
             if post else np.zeros((n, 0)))
    return dict(X=X, Y=Y, Zpre=Zpre, Zpre2=Zpre2, Zpost=Zpost)


def true_ate(w, n=400000, seed=12345):
    rng = np.random.default_rng(seed)
    y1 = gen(w, n, rng, mode=1.0)['Y'].mean()
    rng = np.random.default_rng(seed)
    y0 = gen(w, n, rng, mode=0.0)['Y'].mean()
    return float(y1 - y0)


# ──────────────────────────────────────────────────────────
def ols_x(X, Y, Z=None):
    """返回 (X 的系数, 该系数的方差)"""
    cols = [np.ones(len(X)), X]
    if Z is not None and Z.shape[1] > 0:
        cols.append(Z)
    A = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(A, Y, rcond=None)
    r = Y - A @ beta
    dof = max(len(Y) - A.shape[1], 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.pinv(A.T @ A)
    return float(beta[1]), float(cov[1, 1])


def _corr(a, b):
    if len(a) < 3:
        return 0.0
    sa, sb = a.std(), b.std()
    if sa < 1e-12 or sb < 1e-12:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# ──────────────────────────────────────────────────────────
def run(w, p, B=8000, rng=None, ate=None, c_obs=C_OBS, c_rct=C_RCT, c_cov=C_COV,
        p_pilot=P_PILOT, force_alpha=None, force_theta=None, force_omega=None,
        bias_aware=True):
    """
    p = [alpha0, beta, theta0, gamma, omega]

    阶段 A（试点，花 p_pilot 的钱）：只用来做决定
        · 两次独立读数 → 自估测量噪声 σ̂²
        · θ = θ₀ + γ·σ̂² → 决定哪些协变量进校正集
        · Δ̂ = |观察估计 − 实验估计| → 量出观察性研究有多偏
    阶段 B（剩下的钱）：按 α = α₀ + β·Δ̂ 分配观察 / 实验
    最后把两阶段的数据合并，权重 = 逆方差，
    但观察那一侧的方差要加上**量出来的偏差平方** b̂²：
        v_obs_eff = v_obs + max(0, Δ̂² − (v_o1 + v_r1))
    """
    a0, be, t0, ga, om = p
    rng = rng or np.random.default_rng(w['seed'] * 7919 + 13)
    ate = true_ate(w) if ate is None else ate

    # ── 阶段 A：试点 ──
    pa = p_pilot * B
    n_o1 = int((0.4 * pa) / c_obs)
    n_r1 = int((0.6 * pa) / c_rct)
    d_o1 = gen(w, n_o1, rng, 'obs')
    d_r1 = gen(w, n_r1, rng, 'rct')

    # 噪声自估：两次独立读数
    sig2 = float(np.mean((d_o1['Zpre'] - d_o1['Zpre2']).var(axis=0)) / 2.0)

    # θ 门槛：噪声越大，真实关联被压得越低，门槛要跟着降
    th = float(np.clip(t0 + ga * sig2, 0.0, 1.0)) if force_theta is None else force_theta
    om_ = om if force_omega is None else force_omega
    r_pre = np.array([abs(_corr(d_o1['Zpre'][:, j], d_o1['X']))
                      for j in range(d_o1['Zpre'].shape[1])])
    r_post = np.array([abs(_corr(d_o1['Zpost'][:, j], d_o1['X']))
                       for j in range(d_o1['Zpost'].shape[1])])
    sel_pre = r_pre > th
    sel_post = r_post > (th + om_)          # ω=1 ⇒ X 之后的永不纳入
    m = int(sel_pre.sum() + sel_post.sum())

    e_o1, v_o1 = ols_x(d_o1['X'], d_o1['Y'], _select(d_o1, sel_pre, sel_post))
    e_r1, v_r1 = ols_x(d_r1['X'], d_r1['Y'], _select(d_r1, sel_pre, sel_post))

    # Δ̂：观察与实验之差 = 观察性研究残余偏差的估计
    Dh = abs(e_o1 - e_r1)
    b2 = max(0.0, Dh * Dh - (v_o1 + v_r1)) if bias_aware else 0.0

    # ── 阶段 B ──
    al = float(np.clip(a0 + be * Dh, 0.0, 1.0)) if force_alpha is None else force_alpha
    rem = (1 - p_pilot) * B - m * c_cov
    if rem <= 0:
        rem = (1 - p_pilot) * B * 0.05
    n_o2 = int((1 - al) * rem / c_obs)
    n_r2 = int(al * rem / c_rct)
    d_o2 = gen(w, n_o2, rng, 'obs') if n_o2 > 0 else None
    d_r2 = gen(w, n_r2, rng, 'rct') if n_r2 > 0 else None

    def _pool(d1, d2):
        if d2 is None or len(d2['X']) == 0:
            return ols_x(d1['X'], d1['Y'], _select(d1, sel_pre, sel_post))
        X = np.concatenate([d1['X'], d2['X']])
        Y = np.concatenate([d1['Y'], d2['Y']])
        z1 = _select(d1, sel_pre, sel_post)
        z2 = _select(d2, sel_pre, sel_post)
        Z = np.vstack([z for z in (z1, z2) if z is not None]) if (z1 is not None or z2 is not None) else None
        return ols_x(X, Y, Z)

    e_o, v_o = _pool(d_o1, d_o2)
    e_r, v_r = _pool(d_r1, d_r2)

    # ── 合并：观察侧的方差加上量出来的偏差平方 ──
    v_o = v_o if (v_o > 0 and np.isfinite(v_o)) else 1e9
    v_r = v_r if (v_r > 0 and np.isfinite(v_r)) else 1e9
    v_o_eff = v_o + b2
    w_o = (1.0 / v_o_eff) / (1.0 / v_o_eff + 1.0 / v_r)
    est = w_o * e_o + (1 - w_o) * e_r
    return dict(err=abs(est - ate), est=float(est), ate=ate, alpha=al, theta=th,
                m=m, Dh=Dh, b2=b2, sig2=sig2, w_obs=float(w_o),
                e_obs=float(e_o), e_rct=float(e_r),
                n_o=len(d_o1['X']) + (0 if d_o2 is None else len(d_o2['X'])),
                n_r=len(d_r1['X']) + (0 if d_r2 is None else len(d_r2['X'])))


def _select(d, sel_pre, sel_post):
    parts = []
    if sel_pre.any():
        parts.append(d['Zpre'][:, sel_pre])
    if sel_post.any() and d['Zpost'].shape[1] > 0:
        parts.append(d['Zpost'][:, sel_post])
    return np.column_stack(parts) if parts else None


_ATE_CACHE = {}


def evaluate(p, worlds, nseed=12, B=8000, ate_cache=None, **kw):
    if ate_cache is None:
        ate_cache = _ATE_CACHE
    errs = []
    for k, w in enumerate(worlds):
        if ate_cache is not None and w['seed'] in ate_cache:
            ate = ate_cache[w['seed']]
        else:
            ate = true_ate(w)
            if ate_cache is not None:
                ate_cache[w['seed']] = ate
        for s in range(nseed):
            rng = np.random.default_rng(1000 * (k + 1) + s)
            errs.append(run(w, p, B=B, rng=rng, ate=ate, **kw)['err'])
    return float(np.mean(errs)), float(np.std(errs) / np.sqrt(len(errs)))
