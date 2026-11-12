# -*- coding: utf-8 -*-
"""★96 因果与干预 —— 看 和 做 是两件事"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.causality import (make_world, gen, true_ate, ols_x, run, evaluate,
                            TRUE_TOTAL, C_OBS, C_RCT, C_COV)
from core.causality import _corr

R, KEYS = {}, ['alpha0', 'beta', 'theta0', 'gamma', 'omega']
rng0 = np.random.default_rng(2026)
NUS = [0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1, 2.5]
NUS_H = [0.4, 0.8, 1.1, 1.4, 1.9, 2.2, 2.6, 3.0]
TRAIN = [make_world(s, nu=float(nu)) for s, nu in zip(range(11, 19), NUS)]
HELD = [make_world(s, nu=float(nu), n_noise=10, sig_y=1.4)
        for s, nu in zip(range(71, 79), NUS_H)]
AL_GRID = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
OM_GRID = [0.0, 0.08, 0.16, 0.25, 0.40, 0.60, 1.00]

print("=" * 78)
print("【判据1】尺子自检：干预法真值 vs 结构方程 (X→Y 1.0, X→M→Y 1.0)")
for w in TRAIN[:3]:
    print(f"   world{w['seed']}: ATE = {true_ate(w, n=100000):.4f}   结构方程 = {TRUE_TOTAL:.1f}")
R['ate'] = [float(true_ate(w, n=100000)) for w in TRAIN[:3]]

print("\n" + "=" * 78)
print("【判据2】四类陷阱的真值偏差（20 万样本，真 ATE = 2.0）")
for tag, ws in [("训练世界", TRAIN), ("held-out", HELD)]:
    acc = {k: [] for k in ['naive', 'adjc', 'adjcol', 'adjmed', 'adjlate', 'rct']}
    for w in ws:
        d = gen(w, 200000, np.random.default_rng(7), 'obs')
        dr = gen(w, 200000, np.random.default_rng(7), 'rct')
        Zc = d['Zpre'][:, [0]]
        acc['naive'].append(ols_x(d['X'], d['Y'])[0])
        acc['adjc'].append(ols_x(d['X'], d['Y'], Zc)[0])
        acc['adjcol'].append(ols_x(d['X'], d['Y'], np.column_stack([Zc, d['Zpost'][:, 0]]))[0])
        acc['adjmed'].append(ols_x(d['X'], d['Y'], np.column_stack([Zc, d['Zpost'][:, 1]]))[0])
        acc['adjlate'].append(ols_x(d['X'], d['Y'], np.column_stack([Zc, d['Zpost'][:, 2]]))[0])
        acc['rct'].append(ols_x(dr['X'], dr['Y'])[0])
    print(f"  ── {tag}")
    for k, lab in [('naive', '① 不校正（纯看）      '), ('adjc', '② 只校正 pre-X 混杂子'),
                   ('adjcol', '③ +对撞机（X 之后）   '), ('adjmed', '④ +中介（X 之后）     '),
                   ('adjlate', '⑤ +迟测混杂子（有效！）'), ('rct', '⑥ 随机化 RCT          ')]:
        v = np.array(acc[k]); b = v - TRUE_TOTAL
        print(f"   {lab}  估计 {v.mean():+.3f}   偏差 {b.mean():+.3f}   |偏差| {np.median(abs(b)):.3f}")

rc, rm, rl = [], [], []
for w in TRAIN + HELD:
    d = gen(w, 50000, np.random.default_rng(3), 'obs')
    rc.append(abs(_corr(d['Zpre'][:, 0], d['X'])))
    rm.append(abs(_corr(d['Zpost'][:, 0], d['X'])))
    rl.append(abs(_corr(d['Zpost'][:, 2], d['X'])))
print(f"\n【判据3】真混杂子 r={np.mean(rc):.3f}   对撞机 r={np.mean(rm):.3f}   有效迟测混杂 r={np.mean(rl):.3f}")
print(f"   对撞机关联强于真混杂子的世界占 {np.mean(np.array(rm) > np.array(rc))*100:.0f}%"
      "  → 光看关联分不开，只有时间顺序能")
R.update(r_conf=float(np.mean(rc)), r_coll=float(np.mean(rm)), r_late=float(np.mean(rl)))

# ─────────────────────────────────────────────── 她学
print("\n" + "=" * 78)
print("【训练】8 个世界 × 12 seeds，坐标下降")
GRID = {'alpha0': [-0.3, -0.1, 0.1, 0.3, 0.5],
        'beta': [0.0, 0.3, 0.6, 1.0, 1.5],
        'theta0': [0.05, 0.10, 0.15, 0.22, 0.32],
        'gamma': [-2.0, -1.0, -0.5, 0.0],
        'omega': OM_GRID}
p = [0.0, 0.0, 0.14, 0.0, 0.0]
best, _ = evaluate(p, TRAIN, nseed=12)
print(f"   瞎起点 {dict(zip(KEYS, p))}   err {best:.4f}")
for rd in range(3):
    for i, k in enumerate(KEYS):
        errs = []
        for v in GRID[k]:
            q = list(p); q[i] = v
            errs.append(evaluate(q, TRAIN, nseed=12)[0])
        j = int(np.argmin(errs)); p[i] = GRID[k][j]; best = errs[j]
    print(f"   round{rd+1}: {dict(zip(KEYS, [round(v,3) for v in p]))}   err {best:.4f}")
P_HER = list(p)
p_mem = [P_HER[0], 0.0, P_HER[2], 0.0, P_HER[4]]
e_mem, _ = evaluate(p_mem, TRAIN, nseed=12)
print(f"   记忆派(beta=gamma=0) err {e_mem:.4f}   她 {best:.4f}   差 {e_mem-best:+.4f}")
R['her'] = P_HER; R['mem'] = p_mem; R['train'] = [best, e_mem]

# ─────────────────────────────────────────────── α 峰
print("\n" + "=" * 78)
print("【判据4/5/6】α 峰 —— 硬依赖两端：未测混杂 / RCT 是否更贵")
pks = []
for w in TRAIN:
    v = [evaluate(P_HER, [w], nseed=16, force_alpha=a)[0] for a in AL_GRID]
    j = int(np.argmin(v)); pks.append(AL_GRID[j])
print(f"   各世界最优 α: {pks}   → 是否分化: {len(set(pks))>1}")
R['alpha_per_world'] = [float(x) for x in pks]


def scan_alpha(ws, tag, **kw):
    v = [evaluate(P_HER, ws, nseed=16, force_alpha=a, **kw)[0] for a in AL_GRID]
    j = int(np.argmin(v))
    print(f"   {tag}: " + " ".join(f"{a:.1f}:{e:.3f}" for a, e in zip(AL_GRID, v)))
    print(f"       峰 α={AL_GRID[j]:.1f} {'内部' if 0<j<len(AL_GRID)-1 else '★边界'}  跨度 {max(v)-min(v):.4f}")
    return dict(peak=AL_GRID[j], internal=bool(0 < j < len(AL_GRID) - 1),
                span=float(max(v) - min(v)))


R['alpha_on'] = scan_alpha(TRAIN, "正常(有未测混杂, RCT 贵3×)")
R['alpha_noU'] = scan_alpha([dict(w, bu=0.0, au=0.0) for w in TRAIN], "关未测混杂(bu=au=0)")
R['alpha_free'] = scan_alpha(TRAIN, "RCT 免费(c_rct=c_obs)", c_rct=C_OBS)

# ─────────────────────────────────────────────── θ 峰
print("\n" + "=" * 78)
print("【判据7】θ 峰 —— 硬依赖：纳入协变量要不要花钱")


def scan_theta(ws, tag, **kw):
    g = [0.02, 0.06, 0.10, 0.15, 0.22, 0.32, 0.50]
    v = [evaluate(P_HER, ws, nseed=16, force_theta=t, **kw)[0] for t in g]
    j = int(np.argmin(v))
    print(f"   {tag}: " + " ".join(f"{t:.2f}:{e:.3f}" for t, e in zip(g, v)))
    print(f"       峰 θ={g[j]:.2f} {'内部' if 0<j<len(g)-1 else '★边界'}  跨度 {max(v)-min(v):.4f}")
    return dict(peak=g[j], internal=bool(0 < j < len(g) - 1), span=float(max(v) - min(v)))


R['theta_on'] = scan_theta(TRAIN, "正常(c_cov=120)")
R['theta_free'] = scan_theta(TRAIN, "纳入不要钱(c_cov=0)", c_cov=0.0)

# ─────────────────────────────────────────────── ω 峰
print("\n" + "=" * 78)
print("【判据8/9】ω（排斥 X 之后的协变量）—— 硬依赖：有没有对撞机/中介")


def scan_omega(ws, tag, **kw):
    v = [evaluate(P_HER, ws, nseed=16, force_omega=o, **kw)[0] for o in OM_GRID]
    j = int(np.argmin(v))
    print(f"   {tag}: " + " ".join(f"{o:.2f}:{e:.3f}" for o, e in zip(OM_GRID, v)))
    print(f"       峰 ω={OM_GRID[j]:.2f} {'内部' if 0<j<len(OM_GRID)-1 else '★边界'}  跨度 {max(v)-min(v):.4f}")
    return dict(peak=OM_GRID[j], internal=bool(0 < j < len(OM_GRID) - 1),
                span=float(max(v) - min(v)))


R['omega_on'] = scan_omega(TRAIN, "有对撞机+中介+迟测混杂")
R['omega_off'] = scan_omega([dict(w, collider=False, mediator=False) for w in TRAIN],
                            "关掉撞机/中介(只剩迟测混杂)")

# ─────────────────────────────────────────────── β / γ
print("\n" + "=" * 78)
print("【判据10/11】规则的价值 —— β:Δ̂ 随世界变；γ:噪声随世界变")
for i, (k, g) in enumerate([('beta', [0.0, 0.3, 0.6, 1.0, 1.5]),
                            ('gamma', [-2.0, -1.0, -0.5, 0.0])]):
    v, v2 = [], []
    flat_ws = ([dict(w, bu=0.9, au=0.9) for w in TRAIN] if k == 'beta'
               else [dict(w, nu=1.2) for w in TRAIN])
    for x in g:
        q = list(P_HER); q[1 if k == 'beta' else 3] = x
        v.append(evaluate(q, TRAIN, nseed=16)[0])
        v2.append(evaluate(q, flat_ws, nseed=16)[0])
    j = int(np.argmin(v))
    print(f"   {k}: " + " ".join(f"{x:+.1f}:{e:.4f}" for x, e in zip(g, v)))
    print(f"        峰 {g[j]:+.1f} {'内部' if 0<j<len(g)-1 else '★边界'}  跨度 {max(v)-min(v):.4f}")
    print(f"        变量恒定后跨度 {max(v2)-min(v2):.4f}"
          f"  ({'缩水→规则真在用它' if (max(v2)-min(v2)) < (max(v)-min(v)) else '★没缩水'})")
    R[k] = dict(peak=g[j], internal=bool(0 < j < len(g) - 1), span=float(max(v) - min(v)),
                span_flat=float(max(v2) - min(v2)))

# ─────────────────────────────────────────────── held-out
print("\n" + "=" * 78)
print("【判据12】held-out：8 个全新世界（噪声更狠、协变量更多、σ_Y 更大）")
P_MINE = [0.5, 0.0, 0.10, 0.0, 0.0]
res = {'她': evaluate(P_HER, HELD, nseed=20)[0],
       '记忆派': evaluate(p_mem, HELD, nseed=20)[0],
       '我填的': evaluate(P_MINE, HELD, nseed=20)[0],
       '瞎起点': evaluate([0.0, 0.0, 0.14, 0.0, 0.0], HELD, nseed=20)[0]}
rand = []
for _ in range(6):
    q = [float(rng0.choice(GRID[kk])) for kk in KEYS]
    rand.append(evaluate(q, HELD, nseed=20)[0])
res['随机'] = float(np.mean(rand))
for k, v in sorted(res.items(), key=lambda x: x[1]):
    print(f"   {k:6s}  err {v:.4f}")
R['heldout'] = res; R['p_mine'] = P_MINE

os.makedirs('data', exist_ok=True)
json.dump(R, open('data/exp96_causality.json', 'w'), ensure_ascii=False, indent=1,
          default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print("\n已存 data/exp96_causality.json")
