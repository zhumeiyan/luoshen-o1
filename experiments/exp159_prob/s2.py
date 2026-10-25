import json, math, random, subprocess, sys, time
def real_jitter(n=4000):
    out=[];a=0
    for _ in range(n):
        t0=time.perf_counter_ns()
        for _ in range(400): a=(a*1103515245+12345)&0x7fffffff
        out.append(time.perf_counter_ns()-t0)
    return out
J=sorted(real_jitter()); mu0=sum(J)/len(J)
sd0=(sum((x-mu0)**2 for x in J)/len(J))**0.5
ts=[]
for _ in range(150):
    t0=time.perf_counter_ns(); p=subprocess.Popen([sys.executable,"-c","pass"]); p.kill(); p.wait()
    ts.append(time.perf_counter_ns()-t0)
CA=sum(ts)/len(ts); CM=CA*8.0
rng=random.Random(20261019)

def run(pi,sig,mode,N=2500,tau=1.0):
    fp_cost=C_fp=CA; miss_cost=CM
    # 闭式阈值（密度比，非尾概率比）
    if sig<=0: thr_z=float('inf')
    else:
        thr_lr=(C_fp/miss_cost)*((1-pi)/pi)
        thr_z=sd0*(sig/2.0 + math.log(max(thr_lr,1e-12))/sig)
    tot=0.0;hits=0;fps=0;miss=0;acted=0
    for _ in range(N):
        d=1 if rng.random()<pi else 0
        # 用经验分布重采样（真实噪声形状），再按信号移位
        idx=min(len(J)-1,int(abs(rng.gauss(0,1))*0.35*len(J)))
        o=J[idx]+ (sig*sd0 if d else 0.0) + rng.gauss(0,sd0*0.15)
        z=o-mu0
        if mode=='bayes': act = (z>thr_z)
        elif mode.startswith('scan'): act = (z> tau*sd0)
        elif mode=='always': act=True
        else: act=False
        if act:
            acted+=1; tot+=C_fp
            if d: hits+=1
            else: fps+=1
        else:
            if d: miss+=1; tot+=miss_cost
    return dict(mode=mode,prior=pi,sig=sig,cost=tot/N,hits=hits,fps=fps,miss=miss,
                acted=acted,thr_z=(thr_z if thr_z!=float('inf') else None))
res=[]
for pi in [0.3,0.5,0.7]:
    for s in [0.0,1.0,2.0,4.0]:
        for m in ['bayes','always','never']: res.append(run(pi,s,m))
        for t in [0.5,1.0,1.5,2.0,3.0]: res.append(run(pi,s,'scan_t%.1f'%t,tau=t))
json.dump(dict(mu0=mu0,sd0=sd0,CA=CA,CM=CM,res=res),open('s2.json','w'),indent=1)
print("真实噪声 mu=%.0f sd=%.0f | 真实抢占 %.0f ns | 漏报代价 %.0f"%(mu0,sd0,CA,CM))
print("\nprior sig | bayes(0次额外实验)  scan_best(5次扫描)  fixed1.0(157做法)  never | 谁赢")
nb=ns=0
for pi in [0.3,0.5,0.7]:
    for s in [0.0,1.0,2.0,4.0]:
        g={r['mode']:r for r in res if r['prior']==pi and r['sig']==s}
        b=g['bayes']['cost']; scans=[g['scan_t%.1f'%t]['cost'] for t in [0.5,1.0,1.5,2.0,3.0]]
        sb=min(scans); f1=g['scan_t1.0']['cost']; nv=g['never']['cost']
        best=min(b,sb,f1,nv)
        tag='bayes' if b==best else ('scan_best' if sb==best else ('fixed' if f1==best else 'never'))
        if tag=='bayes': nb+=1
        if tag=='scan_best': ns+=1
        print(" %.1f  %.1f | %9.0f %14.0f %14.0f %9.0f | %s"%(pi,s,b,sb,f1,nv,tag))
print("\nbayes 零调参胜出 %d/12 格 | scan_best 胜 %d/12 格"%(nb,ns))
r0=[r for r in res if r['mode']=='bayes']
print("bayes 在 sig=0 时的行动次数:", [ (r['sig'],r['acted']) for r in r0 if r['sig']==0.0])
