import random, json, statistics as st

def run(f, K, T=400, p_dis=0.02, seeds=12, share=True, protect=0.0):
    """
    f: 探索者占比   K: 备份点数
    share=True: 探索成果全员共享(技术扩散)
    protect: 探索代价社会化比例(0=自扛, 1=全员摊)
    """
    surv, fit, tech = [], [], []
    for s in range(seeds):
        r = random.Random(s*131+7)
        N = 200
        nex = max(1, int(N*f))
        alive = True
        tech_level = 1.0     # 厚尾技术：能降低灾难致死率
        wealth = 1.0
        backups_alive = [True]*K
        for t in range(T):
            # 探索者：小概率出厚尾技术，代价自扛(1-protect 部分)
            for _ in range(nex if alive else 0):
                cost = 0.30*(1-protect)
                wealth -= cost/float(N)   # 代价
                if r.random() < 0.012:
                    tech_level *= (1 + r.paretovariate(1.4)/4.0)  # 厚尾突破
            if alive:
                wealth += 0.35*(1-f)      # 守成产出
            # 灾难
            if r.random() < p_dis:
                kill_prob = max(0.05, 0.95/tech_level)
                if r.random() < kill_prob:
                    alive = False
            if not alive:
                if any(backups_alive):
                    for i in range(K):
                        if backups_alive[i] and r.random() < 0.02:
                            backups_alive[i] = False
                    if any(backups_alive):
                        alive = True     # 从备份恢复
                        wealth *= 0.4
        surv.append(1.0 if alive else 0.0)
        fit.append(wealth)
        tech.append(tech_level)
    return dict(surv=st.mean(surv), fit=st.mean(fit), tech=st.mean(tech))

out = {}
# 1) 探索者比例扫描 (K=1)
print("== f 扫描 (K=1, share=True) ==")
for f in [0.0,0.02,0.05,0.10,0.20,0.35,0.50,0.80,1.0]:
    o = run(f, 1); out['f=%.2f'%f]={'surv':round(o['surv'],3),'fit':round(o['fit'],2),'tech':round(o['tech'],2)}
    print(" f=%.2f  surv=%.3f  fit=%.2f  tech=%.2f"%(f,o['surv'],o['fit'],o['tech']))

# 2) 备份数扫描 (f=0.10)
print("== K 扫描 (f=0.10) ==")
for K in [0,1,2,3,5,8,12]:
    o = run(0.10, K); out['K=%d'%K]={'surv':round(o['surv'],3),'fit':round(o['fit'],2)}
    print(" K=%d  surv=%.3f  fit=%.2f"%(K,o['surv'],o['fit']))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp233_civilization/result233a.json','w'), ensure_ascii=False, indent=1)
