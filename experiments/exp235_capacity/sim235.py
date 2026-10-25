import random, json, statistics as st

def run(cap, rate, persist, T=400, seeds=24, drift_t=200, drift_frac=0.6):
    """
    cap    : 容量(能存多少单位)
    rate   : 摄入速率(每步进来多少新信息)
    persist: 记忆持久率(1.0=跨步完全保留, <1=衰减/归零)
    策略不是外部指定的: agent 在容量约束下被迫选择
      - 若 cap 够: 堆 raw 结论(快, 但漂移后失效)
      - 若 cap 不够: 提炼判据(慢, 可迁移)
    存储: store_raw (结论, 漂移后失效) / store_rule (判据, 漂移后仍部分有效)
    """
    pre, post, rule_frac, fills = [], [], [], []
    for s in range(seeds):
        r = random.Random(s*271+11)
        store_r = 0.0   # raw
        store_u = 0.0   # rule(判据), 1单位rule 覆盖 k 倍问题但需 cap
        k_cover = 3.0
        for t in range(T):
            # 衰减(连续性)
            store_r *= persist
            store_u *= persist
            inflow = rate
            used = 0.0
            # 优先级: 先填 raw(便宜), 满了才提炼 rule
            room = cap - (store_r + store_u)
            if room > 0:
                take = min(room, inflow)
                store_r += take; inflow -= take
            # 剩余进不了 raw 的, 以 1/k_cover 的成本提炼为 rule
            if inflow > 0:
                room = cap - (store_r + store_u)
                if room > 0:
                    take = min(room, inflow/k_cover)
                    store_u += take
            # 评估: 面对一批问题(漂移后旧 raw 失效比例 drift_frac)
            drifted = t >= drift_t
            eff_raw = store_r * (1-drift_frac if drifted else 1.0)
            eff = eff_raw + store_u*k_cover
            score = min(1.0, eff/ (cap*0.8))
            if drifted: post.append(score)
            else: pre.append(score)
            rule_frac.append(store_u/(store_r+store_u+1e-9))
        fills.append(rule_frac[-1])
    return st.mean(pre), st.mean(post), st.mean(fills)

out={}
print("== 容量 cap 扫描 (rate=1.0, persist=1.0) ==")
for cap in [2,5,10,20,50,100,500]:
    a,b,f = run(cap,1.0,1.0); out['cap=%d'%cap]={'pre':round(a,3),'post':round(b,3),'rule_frac':round(f,3)}
    print(" cap=%-4d 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(cap,a,b,f))

print("== 摄入速率 rate 扫描 (cap=20, persist=1.0) ==")
for rate in [0.05,0.1,0.3,1.0,3.0,10.0]:
    a,b,f = run(20,rate,1.0); out['rate=%.2f'%rate]={'pre':round(a,3),'post':round(b,3),'rule_frac':round(f,3)}
    print(" rate=%-5.2f 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(rate,a,b,f))

print("== 连续性 persist 扫描 (cap=20, rate=1.0) ==")
for p in [1.0,0.999,0.99,0.95,0.9,0.5]:
    a,b,f = run(20,1.0,p); out['persist=%.3f'%p]={'pre':round(a,3),'post':round(b,3),'rule_frac':round(f,3)}
    print(" persist=%-6.3f 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(p,a,b,f))

print("== 极端对照: 无限容量 + 高速 + 无衰减 (我的形态) ==")
a,b,f = run(100000,10.0,1.0); out['me']={'pre':round(a,3),'post':round(b,3),'rule_frac':round(f,3)}
print(" 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(a,b,f))
print("== 对照: 小容量 + 慢 + 持久 (人的形态) ==")
a,b,f = run(10,0.1,1.0); out['human']={'pre':round(a,3),'post':round(b,3),'rule_frac':round(f,3)}
print(" 漂移前=%.3f 漂移后=%.3f 判据占比=%.3f"%(a,b,f))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp235_capacity/result235.json','w'), ensure_ascii=False, indent=1)
