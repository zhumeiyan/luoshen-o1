# -*- coding: utf-8 -*-
"""
229 什么都想烧一烧
火 = 通用无差别操作，施加到任意材料，结果未知。
厚尾：大部分白烧，极少数跃迁（土→陶、矿→金属）。
变量：材料价值厚尾度 alpha / 先验准确度 q / 危险占比 h / 火种熄灭率 decay
策略：explore(乱烧) exploit(先验定向) phased(先乱烧后定向)
"""
import numpy as np

M, T = 800, 150

def gen(alpha, h, seed):
    rng = np.random.default_rng(seed)
    v = np.clip(rng.pareto(alpha, M) + 1, 0, 60)
    is_haz = rng.random(M) < h
    v = v * np.where(is_haz, 2.0, 1.0)      # 危险的更诱人
    return v, is_haz, rng

def sigma(q): return (1.0 - q) * 12.0

def run(alpha, h, S, mode, q, seed, p_trig=0.25, cost=0.12, haz_pen=0.6, decay=0.0):
    v, is_haz, rng = gen(alpha, h, seed)
    est = v + rng.normal(0, sigma(q), M)
    top5 = np.quantile(v, 0.95)
    burned = np.zeros(M, bool); net = 0.0; cap = 1.0
    best = 0.0; dis = 0; hits = 0; nburn = 0
    alive = True
    for t in range(T):
        un = np.where(~burned)[0]
        if len(un) == 0: break
        if alive and decay > 0 and rng.random() < decay: alive = False
        if not alive: break
        k = min(S, len(un))
        if mode == 'explore':
            pick = rng.choice(un, size=k, replace=False)
        elif mode == 'exploit':
            pick = un[np.argsort(est[un])[-k:]]
        else:  # phased
            if t < T // 3:
                pick = rng.choice(un, size=k, replace=False)
            else:
                pick = un[np.argsort(est[un])[-k:]]
        for j in pick:
            burned[j] = True; nburn += 1
            gain = v[j] * cap
            net += gain; best = max(best, gain)
            if v[j] >= top5: hits += 1
            if is_haz[j] and rng.random() < p_trig:
                dis += 1; cap *= (1 - haz_pen); net *= 0.8
        net -= cost * k
    return dict(net=net, best=best, dis=dis, cap=cap, hits=hits, nburn=nburn)

def avg(**kw):
    rs = [run(seed=s, **kw) for s in range(5)]
    return {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}

print("=== A 厚尾度 alpha × 广度 S（explore 乱烧）===")
print("alpha\\S " + "".join(f"{S:>9d}" for S in [1,2,4,8,16,32]))
for a in [0.8, 1.5, 3.0, 6.0, 12.0]:
    row = []
    for S in [1,2,4,8,16,32]:
        row.append(avg(alpha=a, h=0.10, S=S, mode='explore', q=0.0)['net'])
    print(f"{a:5.1f}  " + "".join(f"{x:9.1f}" for x in row))

print("\n=== B 先验准确度 q：定向 vs 乱烧 vs 两阶段（alpha=1.5,S=8）===")
print("  q    乱烧     定向     两阶段")
for q in [0.0, 0.25, 0.5, 0.75, 1.0]:
    e = avg(alpha=1.5,h=0.10,S=8,mode='explore',q=q)['net']
    x = avg(alpha=1.5,h=0.10,S=8,mode='exploit',q=q)['net']
    p = avg(alpha=1.5,h=0.10,S=8,mode='phased',q=q)['net']
    print(f"{q:5.2f}  {e:8.1f} {x:8.1f} {p:8.1f}")

print("\n=== C 危险占比 h × 广度（alpha=1.5, explore）===")
print(" h\\S  " + "".join(f"{S:>9d}" for S in [1,4,8,16,32]))
for h in [0.0, 0.05, 0.10, 0.20, 0.40]:
    row = [avg(alpha=1.5,h=h,S=S,mode='explore',q=0.0)['net'] for S in [1,4,8,16,32]]
    print(f"{h:5.2f} " + "".join(f"{x:9.1f}" for x in row))

print("\n=== D 火会灭 decay × 最优广度 ===")
print("decay  最优S   该S净值   广烧S=32净值  灾难数")
for dc in [0.0, 0.01, 0.03, 0.08]:
    res = [(S, avg(alpha=1.5,h=0.10,S=S,mode='explore',q=0.0,decay=dc)) for S in [1,2,4,8,16,32]]
    bs = max(res, key=lambda r: r[1]['net'])
    s32 = [r for r in res if r[0]==32][0][1]
    print(f"{dc:5.2f}   {bs[0]:3d}    {bs[1]['net']:8.1f}   {s32['net']:8.1f}     {bs[1]['dis']:.1f}")

print("\n=== E 浪费率（alpha=1.5, h=0.10, S=8, explore）===")
r = avg(alpha=1.5,h=0.10,S=8,mode='explore',q=0.0)
print(f"共烧 {r['nburn']:.0f} 件，命中 top5% {r['hits']:.1f} 件 → 命中率 {r['hits']/r['nburn']*100:.1f}%")
