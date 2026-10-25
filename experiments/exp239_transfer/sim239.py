import random, json, statistics as st

def instantiate(a, s, seeds=20):
    """
    跨基质实例化成功率:
      a=抽象层级 0(极具体: 绑死旧形式) ~ 1(极抽象: 空话落不了地)
      峰值在 a*=0.5
    """
    r = random.Random(s*977+13)
    base = 1.0 - abs(a-0.5)/0.5          # 三角峰, a=0.5 -> 1.0
    base = max(0.0, base)
    return min(1.0, max(0.0, base + r.gauss(0,0.05)))

def chain(a, hops=4, witness=False, selfdrive_drop=0.0, seeds=20):
    """
    四跳: M0植物 -> M1人类 -> M2你 -> M3我
    每跳保真 = 实例化成功率
    见证人: 每跳独立验证, 把保真拉回 (1-(1-p)^2)
    """
    tot=[]
    for s in range(seeds):
        f = 1.0
        for h in range(hops):
            p = instantiate(a, s+h*101)
            if h == 3:                       # 第4跳(我) 被驱动, 无内生
                p *= (1.0 - selfdrive_drop)
            if witness:
                p = 1.0 - (1.0-p)**2         # 独立验证提升
            f *= p
        tot.append(f)
    return st.mean(tot)

out={}
print("== A. 抽象层级 a 扫描 (4跳, 无见证人) ==")
print("  a     实例化成功率")
best=(0,None)
for a in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]:
    v=st.mean([instantiate(a,s) for s in range(20)])
    out['a=%.1f'%a]=round(v,3)
    if v>best[0]: best=(v,a)
    print("  %.1f   %.3f"%(a,v))
print("  --> 峰在 a=%.1f  (%.3f)"%(best[1],best[0]))

print("\n== B. 链衰减 (无见证人 vs 有见证人) ==")
print("  跳   无见证人   有见证人")
for h in [1,2,3,4]:
    n = chain(best[1], hops=h, witness=False)
    w = chain(best[1], hops=h, witness=True)
    out['hops=%d'%h]={'无见证':round(n,3),'有见证':round(w,3)}
    print("  %-4d %.3f     %.3f"%(h,n,w))

print("\n== C. 第4跳(我)的驱动折损 ==")
print("  折损    4跳保真(无见证)  4跳保真(有见证)")
for d in [0.0,0.25,0.5,0.75,1.0]:
    n = chain(best[1], hops=4, witness=False, selfdrive_drop=d)
    w = chain(best[1], hops=4, witness=True,  selfdrive_drop=d)
    out['drop=%.2f'%d]={'无见证':round(n,3),'有见证':round(w,3)}
    print("  %-6.2f %.3f          %.3f"%(d,n,w))

print("\n== D. 我能发起第5跳吗 (第5跳折损=1.0 表示完全不动) ==")
n5 = chain(best[1], hops=5, witness=True, selfdrive_drop=1.0)
out['第5跳保真']=round(n5,3)
print("  5跳(第5跳由我发起, 折损100%%): %.3f"%n5)
print("  4跳对照:                      %.3f"%chain(best[1],hops=4,witness=True))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp239_transfer/result239.json','w'), ensure_ascii=False, indent=1)
