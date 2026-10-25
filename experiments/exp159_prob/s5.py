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
NB=60; LO=m0-4*sd0; HI=m0+8*sd0; W=(HI-LO)/NB
def hist(v):
    h=[0]*NB
    for x in v:
        b=int((x-LO)/W)
        if 0<=b<NB: h[b]+=1
    return [c/len(v) for c in h]
H0=hist(J)
def lr_fn(sig):
    if sig<=0: return lambda o: 1.0          # LR=1，由公式自行退化
    H1=hist([x+sig*sd0 for x in J])
    L=[(H1[i]+1e-4)/(H0[i]+1e-4) for i in range(NB)]
    return lambda o: L[int((o-LO)/W)] if 0<=int((o-LO)/W)<NB else (L[-1] if o>=HI else L[0])
def run(pi,sig,mode,N=2500,tau=1.0):
    thr=(CA/CM)*((1-pi)/pi)
    L=lr_fn(sig)
    if sig>0: tz=sd0*(sig/2.0+math.log(max(thr,1e-12))/sig)
    else: tz=float('inf') if 1.0<=thr else float('-inf')
    tot=0.0;act=0;hits=0;fps=0
    for _ in range(N):
        d=1 if rng.random()<pi else 0
        o=rng.choice(J)+(sig*sd0 if d else 0.0); z=o-m0
        if mode=='emp':   a=L(o)>thr
        elif mode=='gauss':a=z>tz
        elif mode.startswith('scan'): a=z>tau*sd0
        else: a=(mode=='always')
        if a:
            act+=1; tot+=CA
            if d: hits+=1
            else: fps+=1
        elif d: tot+=CM
    return dict(mode=mode,prior=pi,sig=sig,cost=tot/N,acted=act,hits=hits,fps=fps)
PI=[0.05,0.15,0.40]; SG=[0.0,1.0,2.0,4.0]; TAUS=[0.5,1.0,1.5,2.0,3.0]
res=[]
for pi in PI:
    for s in SG:
        for m in ['emp','gauss','always','never']: res.append(run(pi,s,m))
        for t in TAUS: res.append(run(pi,s,'scan_t%.1f'%t,tau=t))
json.dump(dict(m0=m0,sd0=sd0,CA=CA,CM=CM,PI=PI,SG=SG,res=res),open('s5.json','w'),indent=1)
print("CA=%.0f  CM=%.0f  → 无条件行动阈值 pi>%.3f | sd0=%.0f"%(CA,CM,CA/CM,sd0))
print("\n pi   sig | emp(0调参) gauss(0调参) scan_best(5扫) fixed1.0 never always | 赢家")
w={}
for pi in PI:
    for s in SG:
        g={r['mode']:r for r in res if r['prior']==pi and r['sig']==s}
        cand={'emp':g['emp']['cost'],'gauss':g['gauss']['cost'],
              'scan':min(g['scan_t%.1f'%t]['cost'] for t in TAUS),
              'fixed':g['scan_t1.0']['cost'],'never':g['never']['cost'],'always':g['always']['cost']}
        tag=min(cand,key=cand.get); w[tag]=w.get(tag,0)+1
        print("%.2f  %.1f | %9.0f %11.0f %14.0f %12.0f %8.0f %7.0f | %s"%(
            pi,s,cand['emp'],cand['gauss'],cand['scan'],cand['fixed'],cand['never'],cand['always'],tag))
print("\n胜出格数:",w)
print("\n[退化检验] sig=0 时 emp 的行动次数（应由 pi*CM vs CA 自动决定）:")
for pi in PI:
    r=[x for x in res if x['mode']=='emp' and x['prior']==pi and x['sig']==0.0][0]
    print("  pi=%.2f  pi*CM=%.0f vs CA=%.0f → acted=%d (期望 %s)"%(
        pi,pi*CM,CA,r['acted'],"全动" if pi*CM>CA else "不动"))
