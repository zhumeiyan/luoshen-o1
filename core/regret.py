#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regret —— 后悔最小化与信用分配（★98）

══════════════════════════════════════════════════════════════════
  ★96 她学会「做」：P(Y|X) ≠ P(Y|do(X))
  ★97 她学会「如果当时没这么做」：反事实 Y_i(x')
  这一课把反事实变成**行动的依据** —— 后悔。

══════════════════════════════════════════════════════════════════
  硬真值（全部可算，不由我编）
══════════════════════════════════════════════════════════════════
  1. Kuhn Poker（3 张牌 J/Q/K，ante 1，bet b）
     **博弈值对 P1 = −1/18**（b=1 时）。这是解析解。
     → CFR 跑到底，值必须收敛到 −0.05556，否则我的实现是错的。

  2. CFR 的后悔界    总后悔 = O(√T)   → log(后悔) 对 log(T) 斜率 = −0.5
     Zinkevich et al. 2007，CFR 的核心定理。

  3. **平均策略收敛，当前策略不收敛**
     CFR 的经典结论：最后一步的策略在某些博弈里会振荡，
     只有**整个轨迹的平均**收敛到 Nash。
     → 这不是调参能改的，是算法性质。

  4. NashConv = max_a u(a,σ₂) − min_b u(σ₁,b) ≥ 0，= 0 ⟺ Nash
     exploitability = NashConv / 2

══════════════════════════════════════════════════════════════════
  她的四个旋钮
══════════════════════════════════════════════════════════════════
  k       每次迭代遍历几个发牌结果（chance sampling MCCFR）
          k=6 全遍历（无方差，贵）  k=1 只采一个（便宜，方差大）
          总预算 B 固定 → 迭代次数 T = B/k
          → 真权衡：每步准 vs 走得多

  alpha   RM+ 程度：累积后悔的负部保留多少
          0 = regret matching+（负后悔裁到 0 = 忘掉「我后悔过」）
          1 = vanilla（负后悔一直留着）
          → 真权衡：忘得快 vs 记得牢

  beta    策略平均的近因权重  w_t = (t+1)^beta
          0 = 均匀平均（CFR 理论保证）  >0 = 更信最近

  gamma   后悔的折旧  reg *= (t/(t+1))^gamma
          0 = 不折旧   >0 = 旧后悔慢慢失效

  硬依赖直觉：世界静止 → 均匀平均 + 不折旧最好（理论保证）
             世界漂移 → 忘得快才跟得上
"""

import numpy as np
import itertools

CARDS = [0, 1, 2]
DEALS = [(a, b) for a in CARDS for b in CARDS if a != b]      # 6 种
ACTS = ['p', 'b']
TERM = {'pp', 'bp', 'bb', 'pbp', 'pbb'}
P1_IS = [(0, c, '') for c in CARDS] + [(0, c, 'pb') for c in CARDS]
P2_IS = [(1, c, 'p') for c in CARDS] + [(1, c, 'b') for c in CARDS]
ALL_IS = P1_IS + P2_IS

TRUE_VALUE = -1.0 / 18.0      # Kuhn Poker 对 P1 的博弈值（b=1）


def _u0(h, c1, c2, b):
    """P1 的效用"""
    if h == 'pp':   return 1.0 if c1 > c2 else -1.0          # 摊牌 pot=2
    if h == 'bp':   return 1.0                                # P2 弃牌
    if h == 'bb':   return (1.0 + b) if c1 > c2 else -(1.0 + b)
    if h == 'pbp':  return -1.0                               # P1 弃牌
    if h == 'pbb':  return (1.0 + b) if c1 > c2 else -(1.0 + b)
    raise ValueError(h)


def tutil_cfr(h, c1, c2, b):
    """CFR 遍历用：返回「该节点轮到谁」的效用（配合逐层取反）"""
    return _u0(h, c1, c2, b) if len(h) % 2 == 0 else -_u0(h, c1, c2, b)


def new_tables():
    return {I: np.zeros(2) for I in ALL_IS}


def get_strat(r):
    p = np.maximum(r, 0.0)
    s = p.sum()
    return p / s if s > 1e-12 else np.ones(2) / 2.0


def _walk(h, c1, c2, p0, p1, reg, avg, w_avg, b):
    if h in TERM:
        return tutil_cfr(h, c1, c2, b)
    pl = len(h) % 2
    card = c1 if pl == 0 else c2
    I = (pl, card, h)
    nu = get_strat(reg[I])
    u = np.zeros(2)
    for a in range(2):
        nh = h + ACTS[a]
        if pl == 0:
            u[a] = -_walk(nh, c1, c2, p0 * nu[a], p1, reg, avg, w_avg, b)
        else:
            u[a] = -_walk(nh, c1, c2, p0, p1 * nu[a], reg, avg, w_avg, b)
    node_u = float((nu * u).sum())
    own, opp = (p0, p1) if pl == 0 else (p1, p0)
    for a in range(2):
        reg[I][a] += (u[a] - node_u) * opp
    avg[I] += w_avg * own * nu
    return node_u


def train(w, p, B=2400, rng=None, record_cur=None):
    k = int(round(p[0])); alpha = p[1]; beta = p[2]; gamma = p[3]
    rng = rng or np.random.default_rng(0)
    b0, b1, mode = w['b0'], w['b1'], w.get('mode', 'static')
    T = max(int(B // k), 2)
    reg, avg = new_tables(), new_tables()
    for t in range(T):
        if mode == 'static':
            b = b0
        elif mode == 'step':
            b = b0 if t < T // 2 else b1
        else:                       # 'cont' 连续漂移：世界一直在动
            b = b0 + (b1 - b0) * (t / max(T - 1, 1))
        idx = rng.choice(6, size=k, replace=False)
        w_avg = (t + 1.0) ** min(beta, 100.0)   # 超出 float64 就溢出，这是她自己的表示极限
        for di in idx:
            c1, c2 = DEALS[int(di)]
            _walk('', c1, c2, 1.0 / k, 1.0 / k, reg, avg, w_avg, b)
        disc = ((t + 1.0) / (t + 2.0)) ** gamma
        for I in ALL_IS:
            r = reg[I]
            r = np.maximum(r, 0.0) + alpha * np.minimum(r, 0.0)
            reg[I] = r * disc
    return reg, avg, T


# ───────────────────────────────────────── 评估
def _ev(h, c1, c2, s1, s2, b):
    if h in TERM:
        return _u0(h, c1, c2, b)
    pl = len(h) % 2
    card = c1 if pl == 0 else c2
    nu = (s1 if pl == 0 else s2)[(pl, card, h)]
    tot = 0.0
    for a in range(2):
        if nu[a] > 0:
            tot += nu[a] * _ev(h + ACTS[a], c1, c2, s1, s2, b)
    return tot


def value(s1, s2, b):
    return sum(_ev('', c1, c2, s1, s2, b) for (c1, c2) in DEALS) / 6.0


def _pure(keys):
    for bits in itertools.product([0, 1], repeat=len(keys)):
        yield {k: (np.array([1.0, 0.0]) if x == 0 else np.array([0.0, 1.0]))
               for k, x in zip(keys, bits)}


def _br(s_opp, my_keys, b, maximize):
    best = None
    for ps in _pure(my_keys):
        v = value(ps, s_opp, b) if maximize else value(s_opp, ps, b)
        if best is None or (v > best if maximize else v < best):
            best = v
    return best


def nashconv(s1, s2, b):
    """= 0 ⟺ Nash；exploitability = nashconv / 2"""
    return _br(s2, P1_IS, b, True) - _br(s1, P2_IS, b, False)


def strat_of(reg):
    return {I: get_strat(r) for I, r in reg.items()}


def strat_avg(avg):
    return {I: (a / a.sum() if a.sum() > 1e-12 else np.ones(2) / 2.0)
            for I, a in avg.items()}


def make_world(seed, b0=1.0, b1=1.0, mode='static', B=2400):
    return dict(seed=seed, b0=b0, b1=b1, mode=mode, B=B)


def run(w, p, B=None, rng=None):
    B = B or w.get('B', 2400)
    reg, avg, T = train(w, p, B=B, rng=rng)
    b = w['b0'] if w.get('mode', 'static') == 'static' else w['b1']
    sa, sc = strat_avg(avg), strat_of(reg)
    lam = p[3] if len(p) > 3 else 0.0
    mix = {I: (1 - lam) * sa[I] + lam * sc[I] for I in sa}
    return dict(nc_avg=float(nashconv(sa, sa, b)), nc_cur=float(nashconv(sc, sc, b)),
                nc_mix=float(nashconv(mix, mix, b)),
                val=float(value(sa, sa, b)), T=T)


def evaluate(p, worlds, nseed=3, B=None):
    na, nc = [], []
    for w in worlds:
        for s in range(nseed):
            r = run(w, p, B=B, rng=np.random.default_rng(1000 + s + w['seed']))
            na.append(r['nc_avg']); nc.append(r['nc_cur'])
    return float(np.mean(na)), float(np.mean(nc))


def evaluate_mix(p, worlds, nseed=3, B=None):
    v = []
    for w in worlds:
        for s in range(nseed):
            v.append(run(w, p, B=B, rng=np.random.default_rng(1000 + s + w['seed']))['nc_mix'])
    return float(np.mean(v)), float(np.std(v) / np.sqrt(len(v)))
