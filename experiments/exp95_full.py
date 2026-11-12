# -*- coding: utf-8 -*-
"""★95 判据 3~14：硬依赖两端 + held-out 对照"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import experiments.exp_discovery as E
from core.discovery import (LAWS, LAWS_HELD_OUT, SIGMA, P_OUTLIER, INNER_FRAC,
                            sample_law, fit_sparse, domain_error, inner_error, basis)
RNG = np.random.default_rng
KEYS = ['rho0', 'b_rho', 'lam0', 'b_lam', 'th0', 'b_th']
R = {}

def ev(p, laws, **kw):
    return E.evaluate(p, laws, **kw)

# ---------------------------------------------------------- 她 & 记忆派
print("=" * 74)
print("【训练世界】8 条真定律  B=18  sigma=0.10  p_out=0.10  inner_frac=0.45")
ref = E.calibrate(LAWS)
p_her, best_her = E.coord_search(LAWS, B=18, nseed=16, rounds=5)
print(f"  锚点(她自己校准)  κ={ref[0]:.3f} σ={ref[1]:.3f} o={ref[2]:.3f}")
print(f"  她学到  {dict(zip(KEYS,[round(v,3) for v in p_her]))}   全域误差 {best_her[0]:.4f}")

# 记忆派：在她同样的训练世界上，但只允许常数(b_*=0)
p_mem, best_mem = E.coord_search(LAWS, B=18, nseed=16, rounds=5, const_only=True)
print(f"  记忆派(只学常数) {dict(zip(KEYS,[round(v,3) for v in p_mem]))}   全域误差 {best_mem[0]:.4f}")
R['her'] = p_her; R['mem'] = p_mem; R['ref'] = ref
R['train'] = {'her': best_her[0], 'mem': best_mem[0]}

# ---------------------------------------------------------- 峰 & 硬依赖
print("\n" + "=" * 74)
print("【判据3/4】lam 峰  ——  硬依赖: 噪声")
base = [0.45, -0.15, 0.02, 0.0, 1.0, 5.0]
for tag, sg in [("有噪声 σ=0.10", 0.10), ("关噪声 σ=0.00", 0.0)]:
    rows = E.scan('lam0', [0.0, 0.02, 0.05, 0.10, 0.20, 0.40, 0.80], base, LAWS,
                  B=18, nseed=14, sigma=sg)
    vals = [v for _, v, _ in rows]
    i = int(np.argmin(vals))
    print(f"  {tag}: " + "  ".join(f"{v:.2f}:{e:.3f}" for v, e, _ in rows))
    print(f"     峰在 lam={rows[i][0]:.2f}  {'内部' if 0 < i < len(rows)-1 else '★边界'}   跨度 {max(vals)-min(vals):.4f}")
    R[f'lam_{"on" if sg else "off"}'] = dict(peak=rows[i][0], internal=0 < i < len(rows)-1,
                                             span=float(max(vals)-min(vals)))

print("\n【判据5/6】rho 峰  ——  硬依赖: 窄区共线")
for tag, ifr in [("内区窄 inner_frac=0.45", 0.45), ("内区=全域 0.999(无共线问题)", 0.999)]:
    rows = E.scan('rho0', [0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90], base, LAWS,
                  B=18, nseed=14, inner_frac=ifr)
    vals = [v for _, v, _ in rows]
    i = int(np.argmin(vals))
    print(f"  {tag}: " + "  ".join(f"{v:.2f}:{e:.3f}" for v, e, _ in rows))
    print(f"     峰在 rho={rows[i][0]:.2f}  {'内部' if 0 < i < len(rows)-1 else '★边界'}   跨度 {max(vals)-min(vals):.4f}")
    R[f'rho_{"on" if ifr<0.9 else "off"}'] = dict(peak=rows[i][0], internal=0 < i < len(rows)-1,
                                                  span=float(max(vals)-min(vals)))

print("\n【判据7/8】theta 峰  ——  硬依赖: 离群点")
for tag, po in [("有故障 p_out=0.10", 0.10), ("无故障 p_out=0.00", 0.0)]:
    rows = E.scan('th0', [0.0, 1.0, 1.5, 2.0, 3.0, 4.0], base, LAWS, B=18, nseed=14, p_out=po)
    vals = [v for _, v, _ in rows]
    i = int(np.argmin(vals))
    print(f"  {tag}: " + "  ".join(f"{v:.1f}:{e:.3f}" for v, e, _ in rows))
    print(f"     峰在 theta={rows[i][0]:.1f}  {'内部' if 0 < i < len(rows)-1 else '★边界'}   跨度 {max(vals)-min(vals):.4f}")
    R[f'th_{"on" if po else "off"}'] = dict(peak=rows[i][0], internal=0 < i < len(rows)-1,
                                            span=float(max(vals)-min(vals)))

print("\n【判据9】b_rho 规则的价值  ——  硬依赖: κ̂ 是否有区分度")
for tag, ifr in [("内区窄(κ̂ 有区分度)", 0.45), ("内区=全域(κ̂ 恒定)", 0.999)]:
    rows = E.scan('b_rho', [-0.30, -0.15, -0.075, 0.0, 0.15], base, LAWS,
                  B=18, nseed=14, inner_frac=ifr)
    vals = [v for _, v, _ in rows]
    i = int(np.argmin(vals))
    print(f"  {tag}: " + "  ".join(f"{v:+.3f}:{e:.3f}" for v, e, _ in rows))
    print(f"     峰在 b_rho={rows[i][0]:+.3f}  跨度 {max(vals)-min(vals):.4f}")
    R[f'brho_{"on" if ifr<0.9 else "off"}'] = dict(peak=rows[i][0], span=float(max(vals)-min(vals)))

# ---------------------------------------------------------- held-out
print("\n" + "=" * 74)
print("【判据10】held-out —— 6 条从未见过的定律, 且世界更狠(σ=0.16, B=12, 内区更窄)")
HO = dict(B=12, nseed=20, sigma=0.16, p_out=0.14, inner_frac=0.35)
E.calibrate(LAWS)   # 锚点仍用训练时校准的，不许偷看 held-out
cands = {
    '她(规则)':        p_her,
    '记忆派(常数)':    p_mem,
    '我填的':          [0.15, 0.0, 0.02, 0.0, 3.0, 0.0],
    '瞎起点':          [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
}
for nm in ['rho0', 'lam0', 'th0']:
    pass
res = {}
for nm, p in cands.items():
    e = ev(p, LAWS_HELD_OUT, **HO)
    res[nm] = e[0]
    print(f"  {nm:14s} 全域真值误差 {e[0]:.4f}   (内区误差 {e[1]:.4f})")
# 随机基线
rs = []
for _ in range(12):
    p = [np.random.choice([0.0, 0.15, 0.3, 0.45, 0.6]), np.random.choice([-0.3, -0.15, 0.0, 0.15]),
         np.random.choice([0.0, 0.02, 0.05, 0.1, 0.2, 0.4]), np.random.choice([-4.0, 0.0, 1.5]),
         np.random.choice([0.0, 1.0, 1.5, 2.0, 3.0]), np.random.choice([-5.0, 0.0, 5.0])]
    rs.append(ev(p, LAWS_HELD_OUT, **HO)[0])
res['随机'] = float(np.mean(rs))
print(f"  {'随机':14s} 全域真值误差 {res['随机']:.4f}")
R['heldout'] = res

print("\n" + "=" * 74)
print("【判据11】虚假发现在 held-out 上是否更严重(用内区误差挑 lam)")
tot = []
for law in LAWS_HELD_OUT:
    rows = []
    for lam in [0.0, 0.005, 0.02, 0.05, 0.1, 0.2, 0.5]:
        ei, ed = [], []
        for s in range(14):
            r = RNG(9000 + s)
            xi, yi, xo, yo = sample_law(law, r, 12, 0.0, sigma=0.16, p_out=0.14)
            c, ch, _ = fit_sparse(xi, yi, lam)
            ei.append(inner_error(c, law)); ed.append(domain_error(c, law))
        rows.append((lam, np.mean(ei), np.mean(ed)))
    bi = min(rows, key=lambda r: r[1]); bd = min(rows, key=lambda r: r[2])
    tot.append(bi[2] - bd[2])
    print(f"  {law['name']:12s} 内区尺子挑→全域 {bi[2]:8.3f} | 真值挑→ {bd[2]:8.3f} | 自欺 {bi[2]-bd[2]:+8.3f}")
print(f"  平均自欺代价 {np.mean(tot):+.4f}")
R['selfdeception_ho'] = float(np.mean(tot))

json.dump(R, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'data', 'exp95_discovery.json'), 'w'), indent=1)
print("\n已写出 data/exp95_discovery.json")
