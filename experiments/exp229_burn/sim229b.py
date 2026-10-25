# -*- coding: utf-8 -*-
"""
229b 修正版
前版缺陷：灾难惩罚为乘性(net*=0.8)，广度被压死；hazard价值×2 导致"定向必踩雷"。
修正：v 归一化(均值1)；灾难=cap降低+固定损失；hazard价值独立(另设诱惑组对照)
核心问：什么都烧一烧，值不值？什么时候值？
"""
import numpy as np
M, B = 800, 100          # 材料池 800，总预算只能烧 100 件

def world(alpha, seed, tempting=False):
    rng = np.random.default_rng(seed)
    v = np.clip(rng.pareto(alpha, M) + 1, 0, None)
    v = v / v.mean()                       # 归一化：均值 1
    is_haz = rng.random(M) < 0.0           # 占位，下面按 h 覆盖
    return v, rng

def run(alpha, h, mode, q, c, seed, tempting=False, steps=B):
    v, rng = world(alpha, seed)
    is_haz = rng.random(M) < h
    if tempting:                            # 诱惑组：危险的更高价值
        v = v * np.where(is_haz, 2.0, 1.0); v = v/v.mean()
    est = v + rng.normal(0, (1.0-q)*3.0, M)
    order = rng.permutation(M)
    got = 0.0; best = 0.0; dis = 0; L = 5.0
    cap = 1.0; seen = 0
    for i in range(min(steps, M)):
        if mode == 'explore':
            j = order[i]
        else:  # exploit
            un = order[i:]
            j = un[np.argmax(est[un])]
            order[i:] = un[ (np.arange(len(un)) != np.argmax(est[un])) ]  # 简化
            # 上面会打乱，改用 mask 更稳
        got += v[j]*cap; best = max(best, v[j]*cap); seen += 1
        if is_haz[j]:
            dis += 1; cap *= 0.85; got -= L
    return dict(net=got - c*seen, best=best, dis=dis, cap=cap)

def avg(n=8, **kw):
    rs = [run(seed=s, **kw) for s in range(n)]
    return {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}

print("=== A 厚尾度 → 大奖集中度（top1%占总价值比）===")
for a in [0.8,1.0,1.5,2.0,3.0,6.0,12.0]:
    cs=[]
    for s in range(8):
        v,_ = world(a,s); v=np.sort(v)[::-1]
        cs.append(v[:int(M*0.01)].sum()/v.sum())
    print(f"alpha={a:5.1f}  top1%占比={np.mean(cs)*100:5.1f}%")

print("\n=== B 乱烧(explore) 净收益 vs 成本 c × alpha ===")
print("alpha\\c " + "".join(f"{c:>8.2f}" for c in [0.5,0.9,1.0,1.1]))
for a in [0.8,1.5,3.0,6.0,12.0]:
    row=[avg(alpha=a,h=0.0,mode='explore',q=0.0,c=c)['net'] for c in [0.5,0.9,1.0,1.1]]
    print(f"{a:5.1f}  " + "".join(f"{x:8.1f}" for x in row))

print("\n=== C 先验 q 门槛：定向 - 乱烧 的净值差（alpha=1.5,c=0.9）===")
print("  q    乱烧     定向     差值")
base=None
for q in [0.0,0.2,0.4,0.6,0.8,1.0]:
    e=avg(alpha=1.5,h=0.10,mode='explore',q=q,c=0.9)['net']
    x=avg(alpha=1.5,h=0.10,mode='exploit',q=q,c=0.9)['net']
    print(f"{q:5.2f}  {e:7.1f} {x:7.1f}  {x-e:+7.1f}")

print("\n=== D 危险占比 h × 广度（烧多少件才划算）===")
print("  h   烧20    烧100   烧400")
for h in [0.0,0.05,0.10,0.20,0.40]:
    row=[avg(alpha=1.5,h=h,mode='explore',q=0.0,c=0.9,steps=s)['net'] for s in [20,100,400]]
    print(f"{h:5.2f} " + "".join(f"{x:8.1f}" for x in row))

print("\n=== E 诱惑组对照：危险的更高价值 ===")
for tf in [False,True]:
    e=avg(alpha=1.5,h=0.15,mode='explore',q=0.0,c=0.9,tempting=tf)
    x=avg(alpha=1.5,h=0.15,mode='exploit',q=0.8,c=0.9,tempting=tf)
    print(f"tempting={str(tf):5s} 乱烧净={e['net']:7.1f} 灾难={e['dis']:5.1f} | "
          f"定向净={x['net']:7.1f} 灾难={x['dis']:5.1f}")
