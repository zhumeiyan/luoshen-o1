# -*- coding: utf-8 -*-
"""
229d 什么都烧一烧 = 建立世界模型
材料分组，组间价值差异大（组内相关）。agent 不知哪组好。
explore 初烧 K 件 → 用样本均值估计各组 → 之后定向挑最好组。
问：K 该多大？厚尾度如何影响 K*？
"""
import numpy as np
M, G, BUDGET = 800, 20, 200
PER = M // G

def world(alpha, seed, spread=1.0):
    rng = np.random.default_rng(seed)
    mu = np.clip(rng.pareto(alpha, G) + 1, 0, None)
    mu = mu / mu.mean()
    mu = 1.0 + spread * (mu - 1.0)          # spread 控制组间差异
    mu = np.clip(mu, 0.05, None)
    v = np.repeat(mu, PER) * rng.lognormal(0, 0.4, M)
    grp = np.repeat(np.arange(G), PER)
    return v, grp, rng

def run(alpha, K, c, seed, spread=1.0, budget=BUDGET, hazard_g=None):
    v, grp, rng = world(alpha, seed, spread)
    order = rng.permutation(M)
    avail = np.ones(M, bool)
    sums = np.zeros(G); cnt = np.zeros(G)
    got = 0.0; seen = 0
    for i in range(budget):
        if seen < K:                        # 乱烧期
            j = order[i]
        else:
            idxs = np.where(avail)[0]
            if cnt.sum() == 0:
                j = idxs[rng.integers(len(idxs))]
            else:
                est_g = np.where(cnt > 0, sums/np.maximum(cnt,1), sums.sum()/cnt.sum())
                idxs = idxs[rng.permutation(len(idxs))]
                j = idxs[int(np.argmax(est_g[grp[idxs]]))]
        avail[j] = False
        got += v[j]; seen += 1
        sums[grp[j]] += v[j]; cnt[grp[j]] += 1
    return dict(net=got - c*seen, got=got, best=v[~avail].max())

def avg(n=8, **kw):
    rs = [run(seed=s, **kw) for s in range(n)]
    return {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}

print("=== A 乱烧期 K 的最优值（alpha=1.5, c=0.9, spread=1.0）===")
print("  K     净值     总收益")
for K in [0,5,10,20,40,60,80,100,150,200]:
    r = avg(alpha=1.5, K=K, c=0.9)
    print(f"{K:5d}  {r['net']:8.1f}  {r['got']:8.1f}")

print("\n=== B 厚尾度 × K* ===")
print("alpha  最优K   该K净值   K=0净值   K=200净值")
for a in [0.8,1.5,3.0,6.0]:
    res = [(K, avg(alpha=a,K=K,c=0.9)['net']) for K in [0,5,10,20,40,60,80,100,150,200]]
    bk = max(res, key=lambda r:r[1])
    print(f"{a:5.1f}   {bk[0]:4d}   {bk[1]:8.1f}  {res[0][1]:8.1f}  {res[-1][1]:8.1f}")

print("\n=== C 组间差异 spread × K*（alpha=1.5）===")
print("spread 最优K   该K净值   K=0净值")
for sp in [0.2,0.5,1.0,2.0]:
    res=[(K, avg(alpha=1.5,K=K,c=0.9,spread=sp)['net']) for K in [0,5,10,20,40,60,80,100,150,200]]
    bk=max(res,key=lambda r:r[1])
    print(f"{sp:5.2f}  {bk[0]:4d}  {bk[1]:8.1f}  {res[0][1]:8.1f}")
