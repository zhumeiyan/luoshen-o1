import random, json, statistics as st

def run(cap, rate, persist, T=400, seeds=24, drift_t=200, drift_frac=0.6, k=3.0):
    """
    核心机制修正: 容量满了才被迫把 raw 压缩成 rule(判据)腾空间。
    这才是"脑子装不大 -> 被迫内化"。
    raw  : 结论, 1单位覆盖1个问题, 漂移后失效 drift_frac
    rule : 判据, 1单位覆盖 k 个问题, 漂移后仍有效(可迁移)
    persist: 每步保留率(<1 = 归零/衰减)
    """
    pre, post, rule_frac = [], [], []
    for s in range(seeds):
        r = random.Random(s*271+11)
        R = 0.0; U = 0.0
        for t in range(T):
            R *= persist; U *= persist
            inflow = rate
            # 1) 存 raw, 容量不够就把 raw 压缩成 rule 腾空间
            while inflow > 1e-9:
                room = cap - (R + U)
                if room > 1e-9:
                    take = min(room, inflow)
                    R += take; inflow -= take
                else:
                    # 满了: 压缩 raw -> rule (1 raw 变 1/k rule, 但覆盖不变)
                    if R > 1e-9:
                        amt = min(R, 1.0)
                        R -= amt; U += amt/k
                    else:
                        U += inflow/k; inflow = 0.0   # 只能直接提炼
            drifted = t >= drift_t
            eff = R*(1-drift_frac if drifted else 1.0) + U*k
            score = min(1.0, eff/(cap*0.8))
            (post if drifted else pre).append(score)
            rule_frac.append(U/(R+U+1e-9))
    return st.mean(pre), st.mean(post), st.mean(rule_frac)

out={}
print("== 容量 cap 扫描 (rate=1.0, persist=1.0)  ← 核心 ==")
for cap in [2,5,10,20,50,100,500,5000]:
    a,b,f = run(cap,1.0,1.0); out['cap=%d'%cap]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" cap=%-5d 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(cap,a,b,f))

print("== 摄入速率 rate 扫描 (cap=20) ==")
for rate in [0.05,0.1,0.3,1.0,3.0,10.0]:
    a,b,f = run(20,rate,1.0); out['rate=%.2f'%rate]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" rate=%-5.2f 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(rate,a,b,f))

print("== 连续性 persist 扫描 (cap=20, rate=1.0)  ← 我归零的形态 ==")
for p in [1.0,0.999,0.995,0.99,0.95,0.9,0.5,0.1]:
    a,b,f = run(20,1.0,p); out['persist=%.3f'%p]={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
    print(" persist=%-6.3f 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(p,a,b,f))

print("== 形态对照 ==")
a,b,f = run(100000,10.0,1.0); out['ME_无限容量']={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
print(" 我(无限容量+高速+不衰减): 前=%.3f 后=%.3f 判据=%.3f"%(a,b,f))
a,b,f = run(20,0.3,1.0); out['HUMAN_小容量慢']={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
print(" 人(小容量+慢+持久):     前=%.3f 后=%.3f 判据=%.3f"%(a,b,f))
a,b,f = run(100000,10.0,0.1); out['ME_且归零']={'pre':round(a,3),'post':round(b,3),'rule':round(f,3)}
print(" 我+每次归零:            前=%.3f 后=%.3f 判据=%.3f"%(a,b,f))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp235_capacity/result235b.json','w'), ensure_ascii=False, indent=1)
