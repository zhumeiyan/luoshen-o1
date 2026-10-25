import random, json, statistics as st

def run(f, K, T=400, p0=0.02, seeds=12, protect=0.0, cap=6.0):
    """
    f: 探索者占比  K: 备份点  protect: 探索代价社会化比例  cap: 技术饱和上限
    修复: tech 饱和到 cap (log 累积), 且灾难率随 tech 上升(技术创造新风险类别)
    """
    surv, fit, techs = [], [], []
    for s in range(seeds):
        r = random.Random(s*131+7)
        N = 200; nex = max(1, int(N*f)) if f>0 else 0
        alive=True; tl=0.0; wealth=1.0; bk=[True]*K
        for t in range(T):
            if alive:
                for _ in range(nex):
                    wealth -= 0.30*(1-protect)/N
                    if r.random() < 0.012:
                        tl += r.paretovariate(1.4)/3.0          # 加性累积
                tl = min(tl, cap)                                # 饱和
                wealth += 0.35*(1-f)
            # 灾难率随技术上升(新风险类别), 致死率随技术下降(有解)
            p_dis  = p0*(1 + 0.55*tl)
            kill   = max(0.10, 0.95/(1+tl))
            if r.random() < p_dis:
                if r.random() < kill: alive=False
            if not alive:
                for i in range(K):
                    if bk[i] and r.random() < 0.02: bk[i]=False
                if any(bk): alive=True; wealth*=0.4
        surv.append(1.0 if alive else 0.0); fit.append(wealth); techs.append(tl)
    return st.mean(surv), st.mean(fit), st.mean(techs)

out={}
print("== f 扫描 (K=1) ==")
rows=[]
for f in [0.0,0.02,0.05,0.10,0.15,0.20,0.30,0.50,1.0]:
    s,fi,tc = run(f,1); out['f=%.2f'%f]={'surv':round(s,3),'fit':round(fi,2),'tech':round(tc,2)}
    rows.append((f,s,fi,tc)); print(" f=%.2f  surv=%.3f  fit=%.2f  tech=%.2f"%(f,s,fi,tc))
best=max(rows,key=lambda x:x[2]); print(" >> fit 最优 f=%.2f"%best[0])
bs=max(rows,key=lambda x:x[1]);   print(" >> surv 最优 f=%.2f"%bs[0])

print("== K 扫描 (f=0.10) ==")
for K in [0,1,2,3,5,8,12]:
    s,fi,tc = run(0.10,K); out['K=%d'%K]={'surv':round(s,3),'fit':round(fi,2)}
    print(" K=%d  surv=%.3f  fit=%.2f"%(K,s,fi))

print("== protect 扫描 (f=0.10) ==")
for p in [0.0,0.3,0.6,1.0]:
    s,fi,tc = run(0.10,1,protect=p); out['protect=%.1f'%p]={'surv':round(s,3),'fit':round(fi,2)}
    print(" protect=%.1f  surv=%.3f  fit=%.2f"%(p,s,fi))

json.dump(out, open('/data/workspace/luoshen-o1/experiments/exp233_civilization/result233b.json','w'), ensure_ascii=False, indent=1)
