import json,math,random,subprocess,sys,time
def jitter(n=4000):
    out=[];a=0
    for _ in range(n):
        t0=time.perf_counter_ns()
        for _ in range(400): a=(a*1103515245+12345)&0x7fffffff
        out.append(time.perf_counter_ns()-t0)
    return out
J=jitter(); m0=sum(J)/len(J); sd0=(sum((x-m0)**2 for x in J)/len(J))**0.5
ts=[]
for _ in range(120):
    t0=time.perf_counter_ns(); p=subprocess.Popen([sys.executable,"-c","pass"]); p.kill(); p.wait()
    ts.append(time.perf_counter_ns()-t0)
CA=sum(ts)/len(ts); CM=CA*8.0
rng=random.Random(20261019)

# ---- 经验密度比查找表（非参数，零分布假设）----
NB=60; LO=m0-4*sd0; HI=m0+8*sd0; W=(HI-LO)/NB
def hist(vals):
    h=[0]*NB
    for v in vals:
        b=int((v-LO)/W)
        if 0<=b<NB: h[b]+=1
    return [c/len(vals) for c in h]
H0=hist(J)                                   # 背景：真实抖动
def emp_lr(sig):
    H1=hist([x+sig*sd0 for x in J])          # 信号：真实抖动+移位
    return [(H1[i]+1e-4)/(H0[i]+1e-4) for i in range(NB)]
def lr_lookup(sig):
    L=emp_lr(sig)
    def f(o):
        b=int((o-LO)/W)
        return L[b] if 0<=b<NB else L[-1] if o>=HI else L[0]
    return f

def run(pi,sig,mode,N=2500,tau=1.0):
    thr_lr=(CA/CM)*((1-pi)/pi)               # 纯决策论，不依赖分布
    L=lr_lookup(sig) if sig>0 else None
    if sig>0: thr_z=sd0*(sig/2.0+math.log(max(thr_lr,1e-12))/sig)
    else: thr_z=float('inf')
    tot=0.0;hits=0;fps=0;miss=0;acted=0
    for _ in range(N):
        d=1 if rng.random()<pi else 0
        o=rng.choice(J)+(sig*sd0 if d else 0.0)
        z=o-m0
        if mode=='emp':   act=(sig>0 and L(o)>thr_lr)
        elif mode=='gauss':act=(z>thr_z)
        elif mode.startswith('scan'): act=(z>tau*sd0)
        elif mode=='never': act=False
        else: act=True
        if act:
            acted+=1; tot+=CA
            if d: hits+=1
            else: fps+=1
        else:
            if d: miss+=1; tot+=CM
    return dict(mode=mode,prior=pi,sig=sig,cost=tot/N,acted=acted,hits=hits,fps=fps,miss=miss)
res=[]
TAUS=[0.5,1.0,1.5,2.0,3.0]
for pi in [0.3,0.5,0.7]:
    for s in [0.0,1.0,2.0,4.0]:
        for m in ['emp','gauss','always','never']: res.append(run(pi,s,m))
        for t in TAUS: res.append(run(pi,s,'scan_t%.1f'%t,tau=t))
json.dump(dict(m0=m0,sd0=sd0,CA=CA,CM=CM,res=res),open('s4.json','w'),indent=1)
print("真实抢占 %.0f ns | 漏报 %.0f ns | 真实噪声 sd %.0f"%(CA,CM,sd0))
print("\nprior sig | emp(0调参) gauss(0调参) scan_best(5次扫) fixed1.0(157) never | 赢家")
w={'emp':0,'gauss':0,'scan':0,'fixed':0,'never':0}
for pi in [0.3,0.5,0.7]:
    for s in [0.0,1.0,2.0,4.0]:
        g={r['mode']:r for r in res if r['prior']==pi and r['sig']==s}
        e=g['emp']['cost']; gu=g['gauss']['cost']
        sb=min(g['scan_t%.1f'%t]['cost'] for t in TAUS)
        f1=g['scan_t1.0']['cost']; nv=g['never']['cost']; al=g['always']['cost']
        cand={'emp':e,'gauss':gu,'scan':sb,'fixed':f1,'never':nv}
        tag=min(cand,key=cand.get); w[tag]+=1
        print(" %.1f  %.1f | %9.0f %11.0f %14.0f %13.0f %8.0f | %s"%(pi,s,e,gu,sb,f1,nv,tag))
print("\n胜出格数:",w)
print("\nemp 在各格行动次数(sig=0应恒0):",[(r['sig'],r['acted']) for r in res if r['mode']=='emp' and r['sig']==0.0])
