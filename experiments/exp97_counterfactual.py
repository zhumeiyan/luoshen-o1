# -*- coding: utf-8 -*-
"""★97 反事实与后悔"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.counterfactual import make_world, gen_cases, run, evaluate, MISS_PEN

R = {}
KEYS = ['n_meas', 'w0', 'w1', 'theta']
NM_GRID = [1, 2, 4, 8, 16, 32, 64, 128]
rng0 = np.random.default_rng(2026)

TAUS = [0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6]
MIS = [0.8, 1.0, 1.2, 1.4, 1.6, 1.2, 1.8, 1.0]
SGS = [0.5, 0.6, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6]
TRAIN = [make_world(s, tau=t, mis=m, sig=g)
         for s, t, m, g in zip(range(11, 19), TAUS, MIS, SGS)]
HELD = [make_world(s, tau=t, mis=m, sig=g, nu=1.6, bu=1.4, au=1.1)
        for s, t, m, g in zip(range(71, 79), [0.7, 1.0, 1.3, 1.6, 2.0, 2.4, 2.8, 3.2],
                              [1.0, 1.4, 1.8, 2.2, 1.6, 2.5, 2.0, 1.3],
                              [0.7, 0.9, 1.1, 1.3, 1.5, 1.8, 2.0, 2.2])]

print("=" * 78)
print("【判据1】尺子自检：U 已知时反事实误差应为 0；因果阶梯应成立")
rng = np.random.default_rng(0)
lad = {}
for tau in [0.0, 0.5, 1.0, 2.0]:
    ww = dict(TRAIN[0], tau=tau)
    c = gen_cases(ww, 40000, rng)
    b = 1.0 + tau * c['U']
    oracle = np.abs(b * c['Xp'] + ww['a_conf'] * c['Z'] + ww['au'] * c['U'] - c['Ycf']).mean()
    pop = np.abs(c['Y'] + 1.0 * (c['Xp'] - c['X']) - c['Ycf']).mean()
    naive = np.abs(c['Y'] - c['Ycf']).mean()
    lad[f'tau={tau}'] = dict(oracle=float(oracle), pop=float(pop), naive=float(naive))
    print(f"   tau={tau:.1f}  oracle(U已知) {oracle:.4f}   群体平均 {pop:.4f}   不调整(纯关联) {naive:.4f}")
R['ladder'] = lad
print("   → oracle=0 说明真值实现正确；反事实比干预难：群体做法的误差随异质性上升")

print("\n" + "=" * 78)
print("【判据2】后验宽度有不可约下限 —— ε 是这次实现的一部分，重复测量消不掉")
sds = []
for nm in NM_GRID:
    r = run(TRAIN[0], [nm, 0.8, 0.3, 2.0], n_cases=3000, rng=np.random.default_rng(1))
    sds.append(r['sd'])
print("   n_meas: " + " ".join(f"{n}:{s:.3f}" for n, s in zip(NM_GRID, sds)))
R['sd_saturate'] = [float(x) for x in sds]

# ─────────────────────────────────────────────── 她学
print("\n" + "=" * 78)
print("【训练】8 世界 × 8 seeds，坐标下降")
GRID = {'n_meas': NM_GRID, 'w0': [0.5, 0.8, 0.9, 0.95, 0.99, 0.999],
        'w1': [0.0, 1.0, 2.0, 3.0, 5.0, 10.0], 'theta': [0.4, 0.6, 0.8, 1.0, 1.5, 9.0]}
p = [1, 0.5, 0.0, 9.0]      # 瞎起点：只测一次、全信群体、从不 abstain
best = evaluate(p, TRAIN, nseed=8, n_cases=800)[0]
print(f"   瞎起点 {dict(zip(KEYS,p))}   err {best:.4f}")
for rd in range(3):
    for i, k in enumerate(KEYS):
        es = []
        for v in GRID[k]:
            q = list(p); q[i] = v
            es.append(evaluate(q, TRAIN, nseed=8, n_cases=800)[0])
        j = int(np.argmin(es)); p[i] = GRID[k][j]; best = es[j]
    print(f"   round{rd+1}: {dict(zip(KEYS,[round(v,2) if not isinstance(v,int) else v for v in p]))}   err {best:.4f}")
P_HER = list(p)
p_mem = [P_HER[0], P_HER[1], 0.0, P_HER[3]]
e_mem = evaluate(p_mem, TRAIN, nseed=8, n_cases=800)[0]
print(f"   记忆派(w1=0，常数权重) err {e_mem:.4f}   她 {best:.4f}   差 {e_mem-best:+.4f}")
R['her'] = [float(x) for x in P_HER]; R['mem'] = [float(x) for x in p_mem]
R['train'] = [float(best), float(e_mem)]

# ─────────────────────────────────────────────── 扫描
def scan(idx, grid, tag, ws=None, **kw):
    ws = ws or TRAIN
    v = []
    for x in grid:
        q = list(P_HER); q[idx] = x
        v.append(evaluate(q, ws, nseed=10, n_cases=800, **kw)[0])
    j = int(np.argmin(v))
    print(f"   {tag}: " + " ".join(f"{x}:{e:.4f}" for x, e in zip(grid, v)))
    print(f"        峰 {grid[j]} {'内部' if 0<j<len(grid)-1 else '★边界'}  跨度 {max(v)-min(v):.4f}")
    return dict(peak=float(grid[j]), internal=bool(0 < j < len(grid) - 1),
                span=float(max(v) - min(v)))

print("\n" + "=" * 78)
print("【判据3】n_meas 峰 —— 硬依赖两端：ε 是不是不可约")
R['nm_on'] = scan(0, NM_GRID, "正常(ε 不可约)")
R['nm_noeps'] = scan(0, NM_GRID, "关掉 ε (sig→0) → 后验可任意窄",
                     ws=[dict(w, sig=0.02) for w in TRAIN])
R['nm_free'] = scan(0, NM_GRID, "测量免费", ws=None) if False else None
del R['nm_free']

print("\n" + "=" * 78)
print("【判据4/5】w0（信个体反事实 vs 群体平均）—— 硬依赖：异质性 / 模型错误")
G0=[0.5,0.8,0.9,0.95,0.99,0.999]
R['w0_on'] = scan(1, G0, "正常(有异质性 + 模型有错)")
R['w0_notau'] = scan(1, G0, "关掉异质性(tau=0→反事实退化为群体ATE)",
                     ws=[dict(w, tau=0.0, tau_hat=0.0) for w in TRAIN])
R['w0_nomis'] = scan(1, G0, "★ 模型完全正确(mis=0)",
                     ws=[dict(w, mis=0.0, tau_hat=w['tau'], a_hat=w['a_conf'], au_hat=w['au'])
                         for w in TRAIN])

print("\n" + "=" * 78)
print("【判据6】w1（后验越宽越退回群体平均 = partial pooling）—— 硬依赖：后验宽度是否随个体变")
G1=[0.0,1.0,2.0,3.0,5.0,10.0]
R['w1_on'] = scan(2, G1, "正常")
R['w1_flat'] = scan(2, G1, "后验宽度恒定(bu=au=0→无信息可分个体)",
                    ws=[dict(w, bu=0.0, au=0.0) for w in TRAIN])

print("\n" + "=" * 78)
print("【判据7】theta（abstain）—— 反事实不可证伪，唯一诚实的是知道自己不确定")
for t in [0.4, 0.6, 0.8, 1.0, 1.5, 9.0]:
    r = run(TRAIN[2], [P_HER[0], P_HER[1], P_HER[2], t], n_cases=4000,
            rng=np.random.default_rng(3))
    print(f"   theta={t}: abstain率 {r['abst']:.3f}  作答的误差 {r['err_ans']:.4f}  "
          f"abstain掉的误差 {r['err_abst'] if r['err_abst']==r['err_abst'] else float('nan'):.4f}  err {r['err']:.4f}")
R['abst'] = dict(theta=[0.4, 0.6, 0.8, 1.0, 1.5, 9.0])
R['theta_on'] = scan(3, [0.4, 0.6, 0.8, 1.0, 1.5, 9.0], "theta 扫描")

print("\n" + "=" * 78)
print("【判据8】held-out：8 个全新世界（异质性、模型错误、噪声、混杂强度全变）")
P_MINE = [16, 0.999, 0.0, 0.6]     # 我本来会填：多测、全信个体模型、一视同仁、门槛严
res = {'她': evaluate(P_HER, HELD, nseed=12, n_cases=800)[0],
       '记忆派': evaluate(p_mem, HELD, nseed=12, n_cases=800)[0],
       '我填的': evaluate(P_MINE, HELD, nseed=12, n_cases=800)[0],
       '瞎起点': evaluate([1, 0.5, 0.0, 9.0], HELD, nseed=12, n_cases=800)[0]}
rand = []
for _ in range(6):
    q = [float(rng0.choice(NM_GRID)), float(rng0.choice([0.5, 0.8, 0.95, 0.999])),
         float(rng0.choice([0.0, 2.0, 5.0])), float(rng0.choice([0.4, 0.8, 1.5, 9.0]))]
    rand.append(evaluate(q, HELD, nseed=12, n_cases=800)[0])
res['随机'] = float(np.mean(rand))
for k, v in sorted(res.items(), key=lambda x: x[1]):
    print(f"   {k:6s}  err {v:.4f}")
R['heldout'] = {k: float(v) for k, v in res.items()}; R['p_mine'] = [float(x) for x in P_MINE]

os.makedirs('data', exist_ok=True)
json.dump(R, open('data/exp97_counterfactual.json', 'w'), ensure_ascii=False, indent=1,
          default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
print("\n已存 data/exp97_counterfactual.json")
