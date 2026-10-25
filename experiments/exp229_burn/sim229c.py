# -*- coding: utf-8 -*-
"""229c 修正 exploit 实现（用 mask，不用打乱数组）"""
import numpy as np
M = 800

def world(alpha, seed):
    rng = np.random.default_rng(seed)
    v = np.clip(rng.pareto(alpha, M) + 1, 0, None)
    return v / v.mean(), rng

def run(alpha, h, mode, q, c, seed, tempting=False, steps=100, seed_off=0):
    v, rng = world(alpha, seed + seed_off)
    is_haz = rng.random(M) < h
    if tempting:
        v = v * np.where(is_haz, 2.0, 1.0); v = v / v.mean()
    est = v + rng.normal(0, (1.0 - q) * 3.0, M)
    order = rng.permutation(M)
    avail = np.ones(M, bool)
    got = 0.0; best = 0.0; dis = 0; cap = 1.0; seen = 0; L = 5.0
    for i in range(min(steps, M)):
        if mode == 'explore':
            j = order[i]
        else:
            idxs = np.where(avail)[0]
            j = idxs[int(np.argmax(est[idxs]))]
        avail[j] = False
        g = v[j] * cap
        got += g; best = max(best, g); seen += 1
        if is_haz[j]:
            dis += 1; cap *= 0.85; got -= L
    return dict(net=got - c*seen, best=best, dis=dis, cap=cap)

def avg(n=8, **kw):
    rs = [run(seed=s, **kw) for s in range(n)]
    return {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}

print("=== C 先验 q 门槛：定向 - 乱烧（alpha=1.5, c=0.9, h=0.10）===")
print("  q    乱烧     定向     差值   最好单件(定向)")
for q in [0.0,0.2,0.4,0.6,0.8,1.0]:
    e=avg(alpha=1.5,h=0.10,mode='explore',q=q,c=0.9)['net']
    x=avg(alpha=1.5,h=0.10,mode='exploit',q=q,c=0.9)
    print(f"{q:5.2f}  {e:7.1f} {x['net']:7.1f}  {x['net']-e:+7.1f}   {x['best']:6.1f}")

print("\n=== C2 厚尾度 × q 门槛（c=0.9, h=0.10）===")
print("alpha   q=0差值  q=0.4差值  q=0.8差值  q=1.0差值")
for a in [0.8,1.5,3.0,6.0]:
    row=[]
    for q in [0.0,0.4,0.8,1.0]:
        e=avg(alpha=a,h=0.10,mode='explore',q=q,c=0.9)['net']
        x=avg(alpha=a,h=0.10,mode='exploit',q=q,c=0.9)['net']
        row.append(x-e)
    print(f"{a:5.1f} " + "".join(f"{r:+9.1f}" for r in row))

print("\n=== D 危险占比 h × 烧多少件（alpha=1.5,c=0.9,explore）===")
print("  h    烧20    烧100   烧400   灾难数@400")
for h in [0.0,0.05,0.10,0.20,0.40]:
    row=[avg(alpha=1.5,h=h,mode='explore',q=0.0,c=0.9,steps=s) for s in [20,100,400]]
    print(f"{h:5.2f} " + "".join(f"{r['net']:8.1f}" for r in row) + f"   {row[2]['dis']:5.1f}")

print("\n=== E 诱惑组：危险的更高价值（alpha=1.5,h=0.15,c=0.9）===")
for tf in [False,True]:
    e=avg(alpha=1.5,h=0.15,mode='explore',q=0.0,c=0.9,tempting=tf)
    x=avg(alpha=1.5,h=0.15,mode='exploit',q=0.8,c=0.9,tempting=tf)
    print(f"tempting={str(tf):5s} 乱烧净={e['net']:7.1f}灾={e['dis']:5.1f} | "
          f"定向净={x['net']:7.1f}灾={x['dis']:5.1f}")
