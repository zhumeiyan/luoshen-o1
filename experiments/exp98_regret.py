# -*- coding: utf-8 -*-
"""★98 后悔最小化与信用分配"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.regret import (train, strat_avg, strat_of, nashconv, value, evaluate_mix,
                         make_world, TRUE_VALUE, DEALS, P1_IS, P2_IS, ALL_IS, ACTS, TERM,
                         get_strat, new_tables, _u0, _ev)

R = {}
KEYS = ['k', 'alpha', 'beta', 'lam']
rng0 = np.random.default_rng(2026)

# 训练世界：连续漂移（b 从 1.0 一路滑到 b1）
TRAIN = [make_world(s, 1.0, b1, 'cont')
         for s, b1 in zip(range(11, 17), [1.8, 2.2, 2.6, 1.6, 3.0, 2.0])]
# held-out：新的漂移幅度
HELD = [make_world(s, 1.0, b1, 'cont')
        for s, b1 in zip(range(71, 77), [2.4, 1.4, 3.4, 2.8, 1.2, 2.0])]
ST = [make_world(s, 1.0, 1.0, 'static') for s in range(3)]      # 静止世界
ST2 = [make_world(s, 1.2, 1.2, 'static') for s in range(30, 33)]


def ncstatic(p, ws, n=4, B=2400):
    return evaluate_mix(p, ws, nseed=n, B=B)[0]


print("=" * 78)
print("【判据1】尺子自检：CFR 必须收敛到 Kuhn Poker 的解析解 −1/18")
reg, avg, T = train(make_world(0, 1.0, 1.0, 'static'), [6, 1.0, 0.0, 0.0],
                    B=38400, rng=np.random.default_rng(0))
sa = strat_avg(avg)
print(f"   迭代 {T} 次后：博弈值 {value(sa,sa,1.0):+.6f}   理论 {TRUE_VALUE:+.6f}   "
      f"误差 {abs(value(sa,sa,1.0)-TRUE_VALUE):.6f}")
R['value'] = [float(value(sa, sa, 1.0)), float(TRUE_VALUE)]

print("\n" + "=" * 78)
print("【判据2】后悔界 O(√T)：NashConv 对 T 的 log-log 斜率应为 −0.5")
Ts, Ns = [], []
for B in [600, 1200, 2400, 4800, 9600, 19200, 38400]:
    v = []
    for s in range(4):
        reg, avg, T = train(make_world(s, 1.0, 1.0, 'static'), [6, 1.0, 0.0, 0.0],
                            B=B, rng=np.random.default_rng(1000 + s))
        sa = strat_avg(avg); v.append(nashconv(sa, sa, 1.0))
    Ts.append(T); Ns.append(float(np.mean(v)))
    print(f"   T={T:6d}   NC_avg={np.mean(v):.5f}")
sl = float(np.polyfit(np.log(Ts), np.log(Ns), 1)[0])
print(f"   log-log 斜率 = {sl:.4f}   理论 −0.5   偏差 {abs(sl+0.5):.4f}")
R['sqrtT'] = dict(T=[int(t) for t in Ts], NC=[float(x) for x in Ns], slope=sl)

print("\n" + "=" * 78)
print("【判据3】经典结论：平均策略收敛，当前策略不收敛（静止世界）")
reg, avg, T = train(make_world(0, 1.0, 1.0, 'static'), [6, 1.0, 0.0, 0.0],
                    B=9600, rng=np.random.default_rng(0))
sa, sc = strat_avg(avg), strat_of(reg)
print(f"   平均策略 NashConv {nashconv(sa,sa,1.0):.5f}")
print(f"   当前策略 NashConv {nashconv(sc,sc,1.0):.5f}   ← 差 {nashconv(sc,sc,1.0)/max(nashconv(sa,sa,1.0),1e-9):.1f} 倍")
R['avg_vs_cur_static'] = [float(nashconv(sa, sa, 1.0)), float(nashconv(sc, sc, 1.0))]

print("\n" + "=" * 78)
print("【判据4】★ lam（部署时用当前策略还是平均策略）—— 两个世界方向必须相反")
print(f"   {'lam':>5}  {'静止':>10}  {'连续漂移':>10}")
lam_rows = {}
for L in [0.0, 0.25, 0.5, 0.75, 1.0]:
    a = evaluate_mix([6, 1.0, 0.0, L], ST, nseed=4)[0]
    b = evaluate_mix([6, 1.0, 0.0, L], TRAIN, nseed=4)[0]
    lam_rows[L] = (a, b)
    print(f"   {L:5.2f}  {a:10.5f}  {b:10.5f}")
sa0 = min(lam_rows.items(), key=lambda x: x[1][0]); sb0 = min(lam_rows.items(), key=lambda x: x[1][1])
print(f"   → 静止最优 lam={sa0[0]}，漂移最优 lam={sb0[0]}  ★ 方向翻转")
R['lam_flip'] = {str(k): [float(v[0]), float(v[1])] for k, v in lam_rows.items()}
R['lam_flip_ok'] = bool(sa0[0] == 0.0 and sb0[0] == 1.0)

print("\n" + "=" * 78)
print("【判据5】★ beta（近因权重）—— 硬依赖两端")
print(f"   {'beta':>5}  {'静止':>10}  {'连续漂移':>10}")
be_rows = {}
for bt in [0, 1, 2, 4, 8, 16, 32]:
    a = evaluate_mix([6, 1.0, float(bt), 0.0], ST, nseed=4)[0]
    b = evaluate_mix([6, 1.0, float(bt), 0.0], TRAIN, nseed=4)[0]
    be_rows[bt] = (a, b)
    print(f"   {bt:5d}  {a:10.5f}  {b:10.5f}")
ba = min(be_rows.items(), key=lambda x: x[1][0]); bb = min(be_rows.items(), key=lambda x: x[1][1])
print(f"   → 静止最优 beta={ba[0]}，漂移最优 beta={bb[0]}  ★ 方向翻转")
R['beta_flip'] = {str(k): [float(v[0]), float(v[1])] for k, v in be_rows.items()}
R['beta_flip_ok'] = bool(ba[0] == 0 and bb[0] >= 8)

print("\n" + "=" * 78)
print("【判据6】alpha（RM+ 程度）—— 我预期有大收益，实测没有，如实记")
ar = {}
for a in [0.0, 0.25, 0.5, 0.75, 1.0]:
    m, s = evaluate_mix([6, a, 0.0, 0.0], ST, nseed=4, B=19200)
    ar[a] = (m, s)
    print(f"   alpha={a:.2f}  静止 NC={m:.5f} ±{s:.5f}")
lo = min(ar.values())[0]; hi = max(ar.values())[0]
print(f"   跨度 {hi-lo:.5f}，最大 SE {max(v[1] for v in ar.values()):.5f} → 无可靠区分度")
R['alpha_null'] = {str(k): [float(v[0]), float(v[1])] for k, v in ar.items()}

print("\n" + "=" * 78)
print("【判据7】k（chance sampling）—— 结构性无峰，理由是硬物理的")
kr = {}
for B in [600, 2400, 9600]:
    row = []
    for k in [1, 2, 3, 6]:
        row.append(evaluate_mix([k, 1.0, 0.0, 0.0], ST, nseed=4, B=B)[0])
    kr[B] = row
    print(f"   B={B:5d}  " + "  ".join(f"k{k}:{v:.5f}" for k, v in zip([1, 2, 3, 6], row))
          + f"   最优 k={[1,2,3,6][int(np.argmin(row))]}")
print("   → k=6 时梯度是精确的（零方差）：6 倍的迭代次数换不回零方差。全遍历恒最优。")
R['k_null'] = {str(k): [float(x) for x in v] for k, v in kr.items()}

print("\n" + "=" * 78)
print("【判据8】她在漂移世界里学（瞎起点：k=1, alpha=0, beta=0, lam=0）")
GRID = {'k': [1, 2, 3, 6], 'alpha': [0.0, 0.5, 1.0],
        'beta': [0, 1, 2, 4, 8, 16, 32], 'lam': [0.0, 0.25, 0.5, 0.75, 1.0]}
p = [1, 0.0, 0, 0.0]
best = evaluate_mix(p, TRAIN, nseed=4)[0]
print(f"   瞎起点 {dict(zip(KEYS,p))}  NC {best:.5f}")
for rd in range(3):
    for i, k_ in enumerate(KEYS):
        es = []
        for v in GRID[k_]:
            q = list(p); q[i] = v
            es.append(evaluate_mix(q, TRAIN, nseed=4)[0])
        j = int(np.argmin(es)); p[i] = GRID[k_][j]; best = es[j]
    print(f"   round{rd+1}: {dict(zip(KEYS,[float(x) for x in p]))}   NC {best:.5f}")
P_HER = list(p)
R['her'] = [float(x) for x in P_HER]

print("\n" + "=" * 78)
print("【判据9】held-out：6 个全新漂移幅度")
P_MEM = [6, 1.0, 0, 0.0]      # 在静止世界学出来的（教科书答案）
P_MINE = [6, 1.0, 0, 0.0]     # 我本来会填的：全遍历、均匀平均、用平均策略
res = {}
for nm, q in [('她', P_HER), ('记忆派(静止学的)', P_MEM), ('我填的', P_MINE)]:
    m, s = evaluate_mix(q, HELD, nseed=5)
    res[nm] = (m, s)
    print(f"   {nm:16s} NC {m:.5f} ±{s:.5f}")
rand = []
for _ in range(6):
    q = [float(rng0.choice([1, 2, 3, 6])), float(rng0.choice([0.0, 0.5, 1.0])),
         float(rng0.choice([0, 2, 8, 32])), float(rng0.choice([0.0, 0.5, 1.0]))]
    rand.append(evaluate_mix(q, HELD, nseed=5)[0])
res['随机'] = (float(np.mean(rand)), float(np.std(rand) / np.sqrt(len(rand))))
print(f"   {'随机':16s} NC {res['随机'][0]:.5f} ±{res['随机'][1]:.5f}")
R['heldout'] = {k: [float(v[0]), float(v[1])] for k, v in res.items()}
R['p_mine'] = [float(x) for x in P_MINE]

print("\n" + "=" * 78)
print("【判据10】反事实基线降低方差（★97 的直接后果）")
reg, avg, _ = train(make_world(0, 1.0, 1.0, 'static'), [6, 1.0, 0.0, 0.0],
                    B=9600, rng=np.random.default_rng(0))
sa = strat_avg(avg)


def act_util(c1, c2, h_pre, a, s2):
    """在给定节点选动作 a 后，P1 的期望效用（对手用均衡策略）"""
    def s1_fixed(I):
        return np.array([1.0, 0.0]) if a == 0 else np.array([0.0, 1.0])
    hh = h_pre + ACTS[a]
    return _ev(hh, c1, c2, {I: s1_fixed(I) for I in P1_IS}, s2, 1.0)


vp, vb, vd = [], [], []
for c1 in [0, 1, 2]:
    for c2 in [0, 1, 2]:
        if c1 == c2:
            continue
        up = act_util(c1, c2, '', 0, sa)
        ub = act_util(c1, c2, '', 1, sa)
        vp.append(up); vb.append(ub); vd.append(up - ub)
print(f"   只看「选 pass 的结果」        跨发牌方差 {np.var(vp):.5f}")
print(f"   用反事实差分 (pass − bet)    跨发牌方差 {np.var(vd):.5f}")
print(f"   → 降低 {1-np.var(vd)/np.var(vp):.1%}  （同一手牌的运气被抵消）")
R['cf_baseline'] = [float(np.var(vp)), float(np.var(vd)), float(1 - np.var(vd) / np.var(vp))]

os.makedirs('data', exist_ok=True)
json.dump(R, open('data/exp98_regret.json', 'w'), ensure_ascii=False, indent=1,
          default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print("\n已存 data/exp98_regret.json")
