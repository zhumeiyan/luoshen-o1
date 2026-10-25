import random, json, statistics as st
def run(f,K,T=400,p0=0.02,seeds=20,protect=0.0,gain=1/22.0,cap=12.0):
    surv,fit,tec=[],[],[]
    for s in range(seeds):
        r=random.Random(s*131+7); N=200; nex=max(1,int(N*f)) if f>0 else 0
        alive=True; tl=0.0; wealth=1.0; bk=[True]*K
        for t in range(T):
            if alive:
                for _ in range(nex):
                    wealth-=0.30*(1-protect)/N
                    if r.random()<0.012: tl+=r.paretovariate(1.4)*gain
                tl=min(tl,cap); wealth+=0.35*(1-f)
            p_dis=p0*(1+0.55*tl); kill=max(0.10,0.95/(1+tl))
            if r.random()<p_dis and r.random()<kill: alive=False
            if not alive:
                for i in range(K):
                    if bk[i] and r.random()<0.02: bk[i]=False
                if any(bk): alive=True; wealth*=0.4
        surv.append(1.0 if alive else 0.0); fit.append(wealth); tec.append(tl)
    return st.mean(surv),st.mean(fit),st.mean(tec)
out={}
print("== f 扫描 (K=3, 20seed) ==")
rows=[]
for f in [0.0,0.02,0.05,0.10,0.15,0.20,0.30,0.50,0.80,1.0]:
    s,fi,tc=run(f,3); out['f=%.2f'%f]={'surv':round(s,3),'fit':round(fi,2),'tech':round(tc,2)}
    rows.append((f,s,fi,tc)); print(" f=%.2f  surv=%.3f  fit=%.2f  tech=%.2f"%(f,s,fi,tc))
print(" >> fit最优 f=%.2f ; surv最优 f=%.2f"%(max(rows,key=lambda x:x[2])[0],max(rows,key=lambda x:x[1])[0]))
print("== K 扫描 (f=0.10) ==")
for K in [0,1,2,3,5,8,12]:
    s,fi,tc=run(0.10,K); out['K=%d'%K]={'surv':round(s,3),'fit':round(fi,2)}
    print(" K=%d  surv=%.3f  fit=%.2f"%(K,s,fi))
json.dump(out,open('/data/workspace/luoshen-o1/experiments/exp233_civilization/result233c.json','w'),ensure_ascii=False,indent=1)
